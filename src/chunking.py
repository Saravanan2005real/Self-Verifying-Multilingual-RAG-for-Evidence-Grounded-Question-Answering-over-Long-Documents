import re
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

from src.document_loader import DocumentPage
from src.language_detection import (
    detect_language,
    detect_script,
    clean_prose_for_detection,
    detect_text_language,
    analyze_document_languages
)

@dataclass
class DocumentChunk:
    """
    Represents a meaningful semantic chunk with complete provenance metadata.
    Preserves document name, page number, section, character offsets, language, and word count.
    """
    chunk_id: str
    document_name: str
    page_number: int
    section: Optional[str]
    chunk_index: int
    text: str
    word_count: int
    char_count: int
    char_start: int
    char_end: int
    language: str
    source_type: str
    ocr_applied: bool
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert chunk into a clean, JSON-serializable dictionary."""
        return {
            "chunk_id": self.chunk_id,
            "document_name": self.document_name,
            "page_number": self.page_number,
            "section": self.section,
            "chunk_index": self.chunk_index,
            "text": self.text,
            "word_count": self.word_count,
            "char_count": self.char_count,
            "char_start": self.char_start,
            "char_end": self.char_end,
            "language": self.language,
            "source_type": self.source_type,
            "ocr_applied": self.ocr_applied,
            "metadata": self.metadata,
        }

def clean_and_normalize_ocr_text(text: str) -> str:
    """
    Reconstruct OCR line fragments into coherent sentences and paragraphs.
    Strips scanner watermarks and repairs mid-sentence line wraps.
    """
    # Remove scanner stamps
    text = re.sub(r"(?i)scanned\s+by\s+camscanner[^\n]*", "", text)

    lines = [line.strip() for line in text.split("\n") if line.strip()]
    if not lines:
        return ""

    paragraphs = []
    current_para = []

    for line in lines:
        if not current_para:
            current_para.append(line)
            continue

        prev_line = current_para[-1]
        # If previous line ends with sentence terminal (. ? ! :), start new line/paragraph
        if prev_line and prev_line[-1] in (".", "?", "!", ":"):
            current_para.append(line)
        else:
            # Join line wraps seamlessly
            current_para[-1] = f"{prev_line} {line}"

    return "\n\n".join(current_para)

def resolve_chunk_language(
    text: str,
    default_lang: str = "en",
    allowed_langs: Optional[List[str]] = None
) -> str:
    """Deterministically identify the chunk language with confidence thresholding."""
    script_lang = detect_script(text, min_char_threshold=10)
    if script_lang:
        return script_lang

    prose = clean_prose_for_detection(text)
    if len(prose) < 60:
        return default_lang

    detected_lang, conf = detect_text_language(text, default=default_lang, confidence_threshold=0.85)
    if conf >= 0.85:
        if allowed_langs is None or detected_lang in allowed_langs:
            return detected_lang

    return default_lang

class MeaningfulSemanticChunker:
    """
    Intelligent structure-aware semantic chunker.
    Creates cohesive chunks representing complete, understandable ideas.
    Enforces a target chunk size around 300-800 words with small overlap.
    Never creates tiny orphan fragments.
    """

    def __init__(
        self,
        min_words: int = 250,
        target_words: int = 450,
        max_words: int = 750,
        overlap_words: int = 40
    ):
        self.min_words = min_words
        self.target_words = target_words
        self.max_words = max_words
        self.overlap_words = overlap_words

    def chunk_pages(
        self, 
        pages: List[DocumentPage], 
        doc_analysis: Optional[Dict[str, Any]] = None
    ) -> List[DocumentChunk]:
        """Group document pages and paragraphs into meaningful, cohesive semantic chunks."""
        if not pages:
            return []

        if doc_analysis is None:
            doc_analysis = analyze_document_languages([p.content for p in pages])

        allowed_langs = doc_analysis.get("detected_languages")
        doc_primary_lang = doc_analysis.get("primary_language", "en")
        doc_name = pages[0].source

        # 1. Collect normalized paragraph units with their page attribution
        units: List[Dict[str, Any]] = []
        for page in pages:
            normalized_content = clean_and_normalize_ocr_text(page.content)
            if not normalized_content.strip():
                continue

            # Split by double newline into cohesive paragraphs
            paras = [p.strip() for p in re.split(r"\n\s*\n", normalized_content) if p.strip()]
            for p in paras:
                # Skip tiny noise fragments that lack alphabetic content
                words = p.split()
                if len(words) < 2 or sum(1 for c in p if c.isalpha()) < 3:
                    continue

                # Detect inline headings
                heading_match = re.search(
                    r"(?:^|\n)(?:#+\s*|(?:\d+(\.\d+)*\s+)|(?:UNIT\s+[IVXLCDM]+))([A-Z\u0900-\u0D7F][^\n:]{2,50})(?::|\n|$)",
                    p
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

        if not units:
            return []

        # 2. Assemble units into meaningful chunks (300-800 words)
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
                    metadata={"page_start": current_page_number}
                )
            )
            global_chunk_idx += 1
            char_tracker += total_chars + 2

            # Reset with overlap
            if overlap_suffix:
                current_unit_texts = [overlap_suffix]
                current_word_count = len(overlap_suffix.split())
            else:
                current_unit_texts = []
                current_word_count = 0

        for unit in units:
            u_text = unit["text"]
            u_words = unit["word_count"]
            u_page = unit["page_number"]
            u_section = unit["section"]

            if unit["ocr_applied"]:
                current_ocr_applied = True

            # If this is a distinct major heading and current chunk already has sufficient words (>= 200), flush
            is_major_heading = bool(re.search(r"(?i)^(UNIT\s+[IVXLCDM]+|CHAPTER\s+\d+|SECTION\s+\d+)", u_text[:40]))
            if is_major_heading and current_word_count >= 200:
                emit_current_chunk()
                current_page_number = u_page
                current_section = u_section

            # If unit itself exceeds max_words, split by sentences
            if u_words > self.max_words:
                sentences = [s.strip() for s in re.split(r"(?<=[.!?।])\s+", u_text) if s.strip()]
                for s in sentences:
                    s_words = len(s.split())
                    if current_word_count + s_words > self.target_words and current_word_count >= self.min_words:
                        # Extract overlap
                        overlap_str = " ".join(current_unit_texts[-1].split()[-self.overlap_words:]) if current_unit_texts else ""
                        emit_current_chunk(overlap_suffix=overlap_str)
                        current_page_number = u_page
                    current_unit_texts.append(s)
                    current_word_count += s_words
                continue

            # Standard accumulation
            if current_word_count + u_words > self.target_words and current_word_count >= self.min_words:
                # Calculate small overlap from the end of current text
                last_unit = current_unit_texts[-1] if current_unit_texts else ""
                last_unit_words = last_unit.split()
                if len(last_unit_words) > self.overlap_words:
                    overlap_str = " ".join(last_unit_words[-self.overlap_words:])
                else:
                    overlap_str = last_unit

                emit_current_chunk(overlap_suffix=overlap_str)
                current_page_number = u_page
                current_section = u_section

            if not current_unit_texts:
                current_page_number = u_page
                current_section = u_section

            current_unit_texts.append(u_text)
            current_word_count += u_words

        # Flush remaining buffer (if very small, merge with previous chunk to avoid tiny fragments)
        if current_unit_texts:
            remaining_words = sum(len(t.split()) for t in current_unit_texts)
            if remaining_words < 100 and chunks:
                # Merge into last chunk
                prev = chunks[-1]
                merged_text = prev.text + "\n\n" + "\n\n".join(current_unit_texts)
                prev.text = merged_text
                prev.word_count = len(merged_text.split())
                prev.char_count = len(merged_text)
                prev.char_end = prev.char_start + len(merged_text)
            else:
                emit_current_chunk()

        return chunks

# Backward-compatibility alias
IntelligentChunker = MeaningfulSemanticChunker
