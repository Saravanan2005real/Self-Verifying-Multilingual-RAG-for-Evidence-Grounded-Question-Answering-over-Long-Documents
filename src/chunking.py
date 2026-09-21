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

# Multilingual sentence terminators including Indic, Arabic/Urdu, and East Asian scripts
MULTILINGUAL_SENTENCE_TERMINATORS = (
    ".", "?", "!", ":", ";",
    "।", "॥",  # Devanagari danda and double danda (Hindi, Marathi, Nepali, etc.)
    "؟", "۔",  # Arabic / Urdu question mark and full stop
    "。", "！", "？",  # CJK full stop, exclamation, question mark
)

def normalize_native_text(text: str) -> str:
    """
    Normalize native text (PDF, DOCX, TXT) without destroying authentic paragraph boundaries.
    Preserves double-newline paragraph separation and cleans scanner watermarks and whitespace.
    """
    if not text:
        return ""
    # Strip scanner stamps
    t = re.sub(r"(?i)scanned\s+by\s+camscanner[^\n]*", "", text)
    # Normalize Windows CRLF to standard LF
    t = t.replace("\r\n", "\n").replace("\r", "\n")
    # Clean UI artifacts if any leaked into text
    t = re.sub(r"</?(?:div|span|p)[^>]*>", "", t)
    # Split paragraphs by 2 or more newlines
    raw_paras = re.split(r"\n\s*\n+", t)
    clean_paras = []
    for p in raw_paras:
        p_str = p.strip()
        if p_str:
            # Normalize whitespace within paragraph lines while preserving single newlines if intentional
            lines = [re.sub(r"[ \t]+", " ", line).strip() for line in p_str.split("\n")]
            cleaned_p = "\n".join(l for l in lines if l)
            if cleaned_p:
                clean_paras.append(cleaned_p)
    return "\n\n".join(clean_paras)

def clean_and_normalize_ocr_text(text: str) -> str:
    """
    Reconstruct OCR line fragments into coherent sentences and paragraphs.
    Strips scanner watermarks, respects existing paragraph breaks,
    and supports multilingual sentence terminators.
    """
    if not text or not text.strip():
        return ""

    # Remove scanner stamps
    text = re.sub(r"(?i)scanned\s+by\s+camscanner[^\n]*", "", text)
    text = re.sub(r"</?(?:div|span|p)[^>]*>", "", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # If text already has double newlines (paragraphs), process block-by-block
    blocks = re.split(r"\n\s*\n+", text)
    reconstructed_blocks = []

    for block in blocks:
        lines = [line.strip() for line in block.split("\n") if line.strip()]
        if not lines:
            continue

        current_para = []
        for line in lines:
            if not current_para:
                current_para.append(line)
                continue

            prev_line = current_para[-1]
            # Check if previous line ended with a sentence terminator
            prev_ended = any(prev_line.endswith(term) for term in MULTILINGUAL_SENTENCE_TERMINATORS)
            # Check if previous line ended with closing quote/bracket preceded by terminator
            if not prev_ended and len(prev_line) >= 2 and prev_line[-1] in ('"', "'", "”", "’", ")", "]", "}", "»"):
                prev_ended = any(prev_line[:-1].rstrip().endswith(term) for term in MULTILINGUAL_SENTENCE_TERMINATORS)

            # Check if current line looks like an explicit heading or bullet point
            is_heading_or_bullet = bool(re.match(r"^([•\-\*]|\d+(?:\.\d+)*\s+|#+\s*|[A-Z\u0900-\u0D7F\u0600-\u06FF]{2,}:)", line))

            if prev_ended or is_heading_or_bullet:
                current_para.append(line)
            else:
                # Join unwrapped line seamlessly
                current_para[-1] = f"{prev_line} {line}"

        if current_para:
            reconstructed_blocks.append("\n".join(current_para))

    return "\n\n".join(reconstructed_blocks)

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
            # Use OCR reconstruction only for OCR pages; preserve native paragraph formatting for native pages
            if page.metadata.get("ocr_applied", False) or page.source_type == "scanned_pdf_ocr":
                normalized_content = clean_and_normalize_ocr_text(page.content)
            else:
                normalized_content = normalize_native_text(page.content)

            if not normalized_content.strip():
                continue

            # Split by double newline into cohesive paragraphs
            paras = [p.strip() for p in re.split(r"\n\s*\n+", normalized_content) if p.strip()]
            for p in paras:
                # Skip only empty or purely non-alphanumeric noise fragments (e.g. '___', '---')
                if not any(c.isalnum() for c in p):
                    continue

                words = p.split()

                # Detect inline headings supporting universal Unicode scripts
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
            # Clean any leaked UI HTML tags from chunk text
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

            # If unit itself exceeds max_words, split by sentences without loss
            if u_words > self.max_words:
                sentences = [s.strip() for s in re.split(r"(?<=[.!?।॥؟۔。！？])\s+", u_text) if s.strip()]
                # If no sentence boundaries were detected, split into word chunks
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

# Backward-compatibility alias
IntelligentChunker = MeaningfulSemanticChunker
