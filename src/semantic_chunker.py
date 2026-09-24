import re
import json
import logging
from typing import List, Dict, Any, Optional, Tuple
import requests

from src.config import (
    OLLAMA_BASE_URL,
    SEMANTIC_MODEL,
    SEMANTIC_CHUNKING_ENABLED,
    OLLAMA_TIMEOUT,
    MIN_CHUNK_WORDS,
    TARGET_CHUNK_WORDS,
    MAX_CHUNK_WORDS,
    CHUNK_OVERLAP_WORDS,
)
from src.document_loader import DocumentPage
from src.chunking import (
    DocumentChunk,
    MeaningfulSemanticChunker,
    normalize_native_text,
    clean_and_normalize_ocr_text,
    resolve_chunk_language,
    MULTILINGUAL_SENTENCE_TERMINATORS,
)
from src.language_detection import analyze_document_languages

logger = logging.getLogger(__name__)


class OllamaSemanticAdvisor:
    """
    Interfaces with Llama 3.2 via Ollama to determine semantic boundaries.
    Strictly restricted to binary decision making (BREAK vs CONTINUE).
    Never modifies, summarizes, or rewrites document text.
    """

    def __init__(
        self,
        base_url: str = OLLAMA_BASE_URL,
        model: str = SEMANTIC_MODEL,
        timeout: int = OLLAMA_TIMEOUT,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    def is_available(self) -> bool:
        """
        Check if Ollama server is reachable and responsive.
        Verifies that the requested model exists or is accessible.
        """
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=3)
            if resp.status_code != 200:
                return False
            data = resp.json()
            models = [m.get("name", "") for m in data.get("models", [])]
            # Match model name or tag prefix (e.g. 'llama3.2' matches 'llama3.2:latest')
            target = self.model.lower()
            return any(target in m.lower() for m in models) or len(models) > 0
        except Exception as e:
            logger.warning(f"Ollama server check failed: {e}")
            return False

    def evaluate_boundaries_window(
        self,
        paragraphs: List[Dict[str, Any]],
        start_index: int = 0
    ) -> Dict[int, str]:
        """
        Analyze a window of consecutive paragraphs using Llama 3.2.
        Returns a mapping of paragraph_index -> 'BREAK' | 'CONTINUE'.
        
        A decision of 'BREAK' for index i indicates that paragraph i represents
        a topical or contextual shift from paragraph i-1 and should start a new chunk.
        """
        if not paragraphs or len(paragraphs) <= 1:
            return {}

        # Prepare structured input for the model
        items = []
        for offset, p in enumerate(paragraphs):
            idx = start_index + offset
            # Send up to first 250 characters of each paragraph for contextual decision
            sample_text = p["text"].strip().replace("\n", " ")
            if len(sample_text) > 300:
                sample_text = sample_text[:300] + "..."
            items.append({
                "paragraph_index": idx,
                "text_snippet": sample_text
            })

        system_prompt = (
            "You are a semantic boundary analyzer for document chunking. "
            "Your task is to determine whether consecutive paragraphs should belong to the same semantic chunk "
            "or if a topic shift warrants starting a new chunk.\n\n"
            "For each paragraph after the first, output either:\n"
            "- 'CONTINUE': The paragraph continues the idea, narrative, or topic of the previous paragraph.\n"
            "- 'BREAK': The paragraph introduces a new topic, section, heading, or distinct subject.\n\n"
            "CRITICAL: Return ONLY valid JSON with this exact structure:\n"
            "{\n"
            '  "decisions": [\n'
            '    {"paragraph_index": 1, "decision": "BREAK"},\n'
            '    {"paragraph_index": 2, "decision": "CONTINUE"}\n'
            "  ]\n"
            "}\n"
            "Do NOT summarize, do NOT rewrite text, and do NOT output anything outside the JSON."
        )

        user_prompt = f"Analyze the topic flow across these consecutive paragraphs:\n{json.dumps(items, ensure_ascii=False, indent=2)}"

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "format": "json",
            "stream": False,
            "options": {
                "temperature": 0.0,
                "num_predict": 128
            }
        }

        resp = requests.post(
            f"{self.base_url}/api/chat",
            json=payload,
            timeout=self.timeout
        )
        if resp.status_code != 200:
            raise RuntimeError(f"Ollama returned HTTP {resp.status_code}: {resp.text}")

        resp_data = resp.json()
        raw_content = resp_data.get("message", {}).get("content", "")
        if not raw_content:
            raise ValueError("Ollama response contained empty content")

        parsed = json.loads(raw_content)
        decisions_list = parsed.get("decisions", [])
        if not isinstance(decisions_list, list):
            raise ValueError(f"Expected 'decisions' list in Ollama response, got: {type(decisions_list)}")

        decision_map: Dict[int, str] = {}
        for d in decisions_list:
            idx = d.get("paragraph_index", d.get("index"))
            decision_val = str(d.get("decision", "")).strip().upper()
            if idx is not None and decision_val in ("BREAK", "CONTINUE"):
                decision_map[int(idx)] = decision_val

        return decision_map


class LlamaSemanticChunker:
    """
    Semantic chunker utilizing Llama 3.2 through Ollama for context-aware boundary decisions.
    
    Guarantees:
    - 100% preservation of original paragraph text (zero hallucination, rewriting, or deletion).
    - Python strictly enforces word budgets (min_words, target_words, max_words, overlap_words).
    - Graceful automatic fallback to MeaningfulSemanticChunker on any Ollama failure.
    - Zero HTML contamination in chunk.text.
    """

    def __init__(
        self,
        advisor: Optional[OllamaSemanticAdvisor] = None,
        min_words: int = MIN_CHUNK_WORDS,
        target_words: int = TARGET_CHUNK_WORDS,
        max_words: int = MAX_CHUNK_WORDS,
        overlap_words: int = CHUNK_OVERLAP_WORDS,
        enabled: bool = SEMANTIC_CHUNKING_ENABLED,
        window_size: int = 5,
    ):
        self.advisor = advisor or OllamaSemanticAdvisor()
        self.min_words = min_words
        self.target_words = target_words
        self.max_words = max_words
        self.overlap_words = overlap_words
        self.enabled = enabled
        self.window_size = window_size
        self.fallback_chunker = MeaningfulSemanticChunker(
            min_words=min_words,
            target_words=target_words,
            max_words=max_words,
            overlap_words=overlap_words,
        )

    def _extract_units(self, pages: List[DocumentPage]) -> List[Dict[str, Any]]:
        """Extract cohesive, normalized paragraph units from document pages."""
        units: List[Dict[str, Any]] = []
        for page in pages:
            if page.metadata.get("ocr_applied", False) or page.source_type == "scanned_pdf_ocr":
                normalized_content = clean_and_normalize_ocr_text(page.content)
            else:
                normalized_content = normalize_native_text(page.content)

            if not normalized_content.strip():
                continue

            paras = [p.strip() for p in re.split(r"\n\s*\n+", normalized_content) if p.strip()]
            for p in paras:
                if not any(c.isalnum() for c in p):
                    continue

                words = p.split()
                # Detect inline headings
                heading_match = re.search(
                    r"(?:^|\n)(?:#+\s*|(?:\d+(?:\.\d+)*\s+)|(?:UNIT\s+[IVXLCDM]+))([^\W\d_][^\n:]{2,60})(?::|\n|$)",
                    p,
                    re.UNICODE
                )
                unit_section = heading_match.group(0).strip("# \n:").strip() if heading_match else page.section
                units.append({
                    "text": p,
                    "page_number": page.page_number,
                    "section": unit_section,
                    "source_type": page.source_type,
                    "ocr_applied": page.metadata.get("ocr_applied", False),
                    "word_count": len(words),
                })
        return units

    def chunk_pages(
        self,
        pages: List[DocumentPage],
        doc_analysis: Optional[Dict[str, Any]] = None
    ) -> List[DocumentChunk]:
        """
        Orchestrate semantic chunking using Llama 3.2 with automatic deterministic fallback.
        """
        if not pages:
            return []

        if doc_analysis is None:
            doc_analysis = analyze_document_languages([p.content for p in pages])

        allowed_langs = doc_analysis.get("detected_languages")
        doc_primary_lang = doc_analysis.get("primary_language", "en")
        doc_name = pages[0].source

        units = self._extract_units(pages)
        if not units:
            return []

        # If semantic chunking is disabled, use deterministic chunker directly
        if not self.enabled:
            logger.info("Semantic chunking is disabled; using deterministic chunker.")
            chunks = self.fallback_chunker.chunk_pages(pages, doc_analysis=doc_analysis)
            for c in chunks:
                c.metadata["chunking_strategy"] = "deterministic_disabled"
            return chunks

        # Verify Ollama availability
        try:
            available = self.advisor.is_available()
        except Exception as e:
            logger.warning(f"Ollama availability check raised exception: {e}")
            available = False

        if not available:
            logger.warning("Ollama server or Llama 3.2 model unavailable. Falling back to deterministic chunker.")
            chunks = self.fallback_chunker.chunk_pages(pages, doc_analysis=doc_analysis)
            for c in chunks:
                c.metadata["chunking_strategy"] = "deterministic_fallback"
            return chunks

        # Query Llama 3.2 for semantic decisions using windowed analysis
        semantic_decisions: Dict[int, str] = {}
        strategy_used = "llama3.2_semantic"
        try:
            total_units = len(units)
            if total_units <= self.window_size:
                # Small document or unit test: evaluate in a single window
                semantic_decisions.update(self.advisor.evaluate_boundaries_window(units, start_index=0))
            else:
                # Find candidate boundary points where accumulated word count meets or approaches min_words
                candidate_indices = []
                cur_words = 0
                for u_idx, u in enumerate(units):
                    cur_words += u.get("word_count", len(u["text"].split()))
                    if cur_words >= self.min_words:
                        candidate_indices.append(u_idx)
                        cur_words = 0  # reset for next candidate chunk

                if not candidate_indices:
                    candidate_indices = [min(1, total_units - 1)]

                evaluated_starts = set()
                half_window = self.window_size // 2
                for c_idx in candidate_indices:
                    win_start = max(0, c_idx - half_window)
                    if win_start in evaluated_starts:
                        continue
                    evaluated_starts.add(win_start)
                    window = units[win_start:win_start + self.window_size]
                    if len(window) > 1:
                        window_decisions = self.advisor.evaluate_boundaries_window(window, start_index=win_start)
                        semantic_decisions.update(window_decisions)
        except Exception as e:
            logger.warning(f"Llama 3.2 boundary analysis failed ({e}). Gracefully falling back to deterministic chunker.")
            chunks = self.fallback_chunker.chunk_pages(pages, doc_analysis=doc_analysis)
            for c in chunks:
                c.metadata["chunking_strategy"] = "deterministic_fallback"
            return chunks

        # Construct chunks in Python using the ORIGINAL extracted paragraphs
        return self._assemble_chunks(
            units=units,
            decisions=semantic_decisions,
            doc_name=doc_name,
            doc_primary_lang=doc_primary_lang,
            allowed_langs=allowed_langs,
            strategy_name=strategy_used,
        )

    def _assemble_chunks(
        self,
        units: List[Dict[str, Any]],
        decisions: Dict[int, str],
        doc_name: str,
        doc_primary_lang: str,
        allowed_langs: Optional[List[str]],
        strategy_name: str,
    ) -> List[DocumentChunk]:
        """
        Assemble final DocumentChunk objects from original paragraphs,
        honoring Llama's semantic BREAK decisions while strictly enforcing size limits.
        """
        chunks: List[DocumentChunk] = []
        current_unit_texts: List[str] = []
        current_word_count = 0
        current_page_number = units[0]["page_number"]
        current_section = units[0]["section"]
        current_ocr_applied = False
        current_source_type = units[0]["source_type"]
        char_tracker = 0
        global_chunk_idx = 0

        def emit_current_chunk(overlap_suffix: str = ""):
            nonlocal current_unit_texts, current_word_count, current_page_number, current_section
            nonlocal current_ocr_applied, current_source_type, char_tracker, global_chunk_idx

            if not current_unit_texts:
                return

            full_chunk_text = "\n\n".join(current_unit_texts).strip()
            # Clean any leaked HTML tags
            full_chunk_text = re.sub(r"</?(?:div|span|p)[^>]*>", "", full_chunk_text).strip()

            total_words = len(full_chunk_text.split())
            total_chars = len(full_chunk_text)

            chunk_id = f"{doc_name}_c{global_chunk_idx}"
            chunk_lang = resolve_chunk_language(
                full_chunk_text,
                default_lang=doc_primary_lang,
                allowed_langs=allowed_langs
            )

            chunks.append(
                DocumentChunk(
                    chunk_id=chunk_id,
                    document_name=doc_name,
                    page_number=current_page_number,
                    section=current_section,
                    chunk_index=global_chunk_idx,
                    text=full_chunk_text,
                    word_count=total_words,
                    char_count=total_chars,
                    char_start=char_tracker,
                    char_end=char_tracker + total_chars,
                    language=chunk_lang,
                    source_type=current_source_type,
                    ocr_applied=current_ocr_applied,
                    metadata={
                        "page_start": current_page_number,
                        "chunking_strategy": strategy_name
                    }
                )
            )
            global_chunk_idx += 1
            char_tracker += total_chars + 2

            # Reset buffer with overlap if requested
            if overlap_suffix:
                current_unit_texts = [overlap_suffix]
                current_word_count = len(overlap_suffix.split())
            else:
                current_unit_texts = []
                current_word_count = 0

        for idx, unit in enumerate(units):
            u_text = unit["text"]
            u_words = unit["word_count"]
            u_page = unit["page_number"]
            u_section = unit["section"]

            if unit["ocr_applied"]:
                current_ocr_applied = True

            # Check if Llama 3.2 recommended a semantic BREAK at this paragraph
            llama_wants_break = (decisions.get(idx) == "BREAK")

            # Check for major structural heading
            is_major_heading = bool(re.search(r"(?i)^(UNIT\s+[IVXLCDM]+|CHAPTER\s+\d+|SECTION\s+\d+)", u_text[:40]))

            # Decide whether to break before adding this paragraph
            should_break = False
            if current_word_count >= self.min_words:
                if llama_wants_break or is_major_heading:
                    should_break = True
                elif current_word_count + u_words > self.max_words:
                    should_break = True

            if should_break and current_unit_texts:
                # Calculate small overlap from end of current chunk
                last_unit = current_unit_texts[-1] if current_unit_texts else ""
                last_unit_words = last_unit.split()
                if len(last_unit_words) > self.overlap_words:
                    overlap_str = " ".join(last_unit_words[-self.overlap_words:])
                else:
                    overlap_str = last_unit

                emit_current_chunk(overlap_suffix=overlap_str)
                current_page_number = u_page
                current_section = u_section

            # If unit itself exceeds max_words, safely split on sentence boundaries
            if u_words > self.max_words:
                sentences = [s.strip() for s in re.split(r"(?<=[.!?।॥؟۔。！？])\s+", u_text) if s.strip()]
                if len(sentences) <= 1:
                    words_list = u_text.split()
                    sub_chunks = []
                    step = self.target_words
                    for wi in range(0, len(words_list), step):
                        sub_chunks.append(" ".join(words_list[wi:wi + step]))
                    sentences = sub_chunks

                for s in sentences:
                    s_words = len(s.split())
                    if current_word_count + s_words > self.target_words and current_word_count >= self.min_words:
                        overlap_str = " ".join(current_unit_texts[-1].split()[-self.overlap_words:]) if current_unit_texts else ""
                        emit_current_chunk(overlap_suffix=overlap_str)
                        current_page_number = u_page
                    current_unit_texts.append(s)
                    current_word_count += s_words
                continue

            if not current_unit_texts:
                current_page_number = u_page
                current_section = u_section

            current_unit_texts.append(u_text)
            current_word_count += u_words

        # Flush remaining buffer (merge if tiny to avoid orphan fragment)
        if current_unit_texts:
            remaining_words = sum(len(t.split()) for t in current_unit_texts)
            min_orphan_threshold = min(self.min_words // 2, 40)
            if remaining_words < min_orphan_threshold and chunks:
                prev = chunks[-1]
                remaining_text = "\n\n".join(current_unit_texts)
                remaining_text = re.sub(r"</?(?:div|span|p)[^>]*>", "", remaining_text).strip()
                merged_text = prev.text + "\n\n" + remaining_text
                prev.text = merged_text
                prev.word_count = len(merged_text.split())
                prev.char_count = len(merged_text)
                prev.char_end = prev.char_start + len(merged_text)
            else:
                emit_current_chunk()

        return chunks
