import re
import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

import pymupdf as fitz  # PyMuPDF
import docx  # python-docx
from PIL import Image

from src.config import OCR_CHAR_THRESHOLD
from src.ocr import is_ocr_available, extract_text_from_image, get_ocr_engine_name
from src.language_detection import detect_language

logger = logging.getLogger(__name__)

@dataclass
class DocumentPage:
    """Represents text, section, and metadata from a specific page/section of a document."""
    content: str
    page_number: int
    source: str
    source_type: str = "pdf"
    section: Optional[str] = None
    language: str = "en"
    metadata: Dict[str, Any] = field(default_factory=dict)

class DocumentLoader:
    """
    Unified loader for PDF, DOCX, and TXT documents.
    Preserves page numbers, section headers, image counts, OCR status, and detected language.
    """

    @classmethod
    def load_document(cls, file_path: str | Path, enable_ocr: bool = True) -> List[DocumentPage]:
        """Auto-detect format by extension and load into DocumentPage objects."""
        path = Path(file_path)
        if not path.is_file():
            raise FileNotFoundError(f"File not found: {file_path}")

        suffix = path.suffix.lower()
        if suffix == ".pdf":
            return cls.load_pdf(path, enable_ocr=enable_ocr)
        elif suffix == ".docx":
            return cls.load_docx(path)
        elif suffix in (".txt", ".md"):
            return cls.load_txt(path)
        else:
            raise ValueError(f"Unsupported document format: {suffix}. Supported: .pdf, .docx, .txt, .md")

    @staticmethod
    def is_page_text_sufficient_and_readable(raw_text: str) -> tuple[bool, str]:
        """
        Evaluates whether raw text extracted via PyMuPDF is sufficient, usable readable text,
        or merely scanner watermarks / empty noise.

        Returns:
            (is_usable: bool, clean_text: str)
        """
        if not raw_text or not raw_text.strip():
            return False, ""

        # Strip scanner watermarks (e.g., 'Scanned by CamScanner')
        cleaned = re.sub(r"(?i)scanned\s+by\s+camscanner", "", raw_text).strip()
        if not cleaned:
            return False, ""

        # Analyze lexical content
        words = re.findall(r"\b[a-zA-Z0-9]{2,}\b", cleaned)
        alpha_words = re.findall(r"\b[a-zA-Z]{2,}\b", cleaned)
        total_chars = len(cleaned)
        letter_chars = sum(1 for c in cleaned if c.isalpha())
        letter_ratio = letter_chars / total_chars if total_chars > 0 else 0.0

        # Criteria for sufficient readable native text:
        # At least 5 readable alphabetic words, >= 25 characters, and >= 40% alphabetic letters
        if len(alpha_words) >= 5 and total_chars >= 25 and letter_ratio >= 0.40:
            return True, cleaned

        return False, cleaned

    @classmethod
    def load_pdf(cls, file_path: Path, enable_ocr: bool = True) -> List[DocumentPage]:
        """
        Extract text page by page from PDF using PyMuPDF.
        Follows strict required decision logic:
        1. First attempt normal text extraction using PyMuPDF.
        2. Measure the extracted text quality/length.
        3. If the page contains sufficient readable text, USE THE ORIGINAL PDF TEXT.
        4. Do NOT run OCR on a page that already has good selectable text.
        5. Only use OCR when enable_ocr=True and the page has no usable text / is genuinely scanned.
        6. If OCR is required, use it only for that page.
        7. Do not replace good extracted PDF text with OCR output.
        """
        pages: List[DocumentPage] = []
        doc = fitz.open(str(file_path))
        doc_name = file_path.name
        current_section = "General"
        ocr_engine = get_ocr_engine_name() if enable_ocr else "Disabled (Native Text Only)"

        print(f"  [PDF Loader] Inspecting {len(doc)} pages in '{doc_name}'...")
        print(f"  [PDF Loader] Local OCR Engine: {ocr_engine}")
        print(f"  [PDF Loader] Per-page extraction decisions:")

        for page_idx in range(len(doc)):
            page_num = page_idx + 1
            page = doc[page_idx]

            # 1. First attempt normal text extraction using PyMuPDF
            raw_text = page.get_text("text")

            # 2. Measure the extracted text quality/length
            has_good_text, native_text = cls.is_page_text_sufficient_and_readable(raw_text)

            extracted_text = ""
            method = "Native PDF text"
            ocr_applied = False
            source_type = "pdf"

            # 3. If sufficient native text exists, use it directly
            # 4. Do NOT OCR a page that already has good native text
            if has_good_text:
                extracted_text = native_text
                method = "Native Text"
                ocr_applied = False
                source_type = "pdf"
            else:
                # 5. Only use OCR when enable_ocr is True, page is scanned, and OCR is available
                images = page.get_images()
                is_scanned = len(images) > 0 or len(native_text.strip()) == 0

                if enable_ocr and is_scanned and is_ocr_available():
                    # 6. If OCR is required, use it only for that page
                    pix = page.get_pixmap(dpi=150)
                    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                    ocr_text = extract_text_from_image(img)

                    if ocr_text.strip():
                        extracted_text = ocr_text.strip()
                        method = "OCR"
                        ocr_applied = True
                        source_type = "scanned_pdf_ocr"
                    else:
                        extracted_text = native_text
                        method = "Native Text"
                else:
                    # 7. Use native text (or empty if no text) without running OCR
                    extracted_text = native_text
                    method = "Native Text"

            # Show debugging per-page decision, character count, method, and first 100 characters preview
            clean_preview = extracted_text.replace("\n", " ").strip()
            clean_preview = re.sub(r"[ \t]+", " ", clean_preview)
            if len(clean_preview) > 100:
                preview_str = clean_preview[:97] + "..."
            elif not clean_preview:
                preview_str = "<no readable text>"
            else:
                preview_str = clean_preview

            print(f"    Page {page_num:2d} | Method: {method:11s} | Chars: {len(extracted_text):4d} | Preview: \"{preview_str}\"")

            # Section detection heuristic
            section_match = re.search(r"(?:^|\n)(\d+(\.\d+)*\s+[A-Z][A-Za-z0-9\s]{2,40})(?:\n|$)", extracted_text)
            if section_match:
                current_section = section_match.group(1).strip()

            pages.append(
                DocumentPage(
                    content=extracted_text,
                    page_number=page_num,
                    source=doc_name,
                    source_type=source_type,
                    section=current_section,
                    language="en",
                    metadata={
                        "total_pages": len(doc),
                        "char_count": len(extracted_text),
                        "extraction_method": method,
                        "needs_ocr": not has_good_text,
                        "ocr_applied": ocr_applied,
                    }
                )
            )

        doc.close()
        return pages

    @classmethod
    def load_docx(cls, file_path: Path) -> List[DocumentPage]:
        """
        Extract text, headings, and tables from DOCX.
        Tracks explicit headings as section metadata and segments into pages.
        """
        doc = docx.Document(str(file_path))
        doc_name = file_path.name

        # Structure blocks with section tags
        structural_blocks: List[Dict[str, str]] = []
        current_section = "General"

        for para in doc.paragraphs:
            text = para.text.strip()
            if not text:
                continue

            # Detect Word Heading styles
            if para.style and para.style.name and para.style.name.lower().startswith("heading"):
                current_section = text
                structural_blocks.append({"type": "heading", "text": text, "section": current_section})
            else:
                structural_blocks.append({"type": "paragraph", "text": text, "section": current_section})

        # Process tables
        for table in doc.tables:
            table_lines = []
            for row in table.rows:
                cells = [cell.text.strip() for cell in row.cells]
                table_lines.append(" | ".join(cells))
            if table_lines:
                table_text = "\n".join(table_lines)
                structural_blocks.append({"type": "table", "text": table_text, "section": current_section})

        if not structural_blocks:
            return [
                DocumentPage(
                    content="",
                    page_number=1,
                    source=doc_name,
                    source_type="docx",
                    section="General",
                    language="unknown",
                    metadata={"total_pages": 1, "char_count": 0, "needs_ocr": False, "ocr_applied": False}
                )
            ]

        # Group blocks into synthetic pages (~350 words per page to simulate realistic page attribution)
        pages: List[DocumentPage] = []
        current_page_blocks = []
        current_words = 0
        page_num = 1
        page_section = current_section

        for block in structural_blocks:
            words = len(block["text"].split())
            if current_words + words > 350 and current_page_blocks:
                content = "\n\n".join(b["text"] for b in current_page_blocks)
                pages.append(
                    DocumentPage(
                        content=content,
                        page_number=page_num,
                        source=doc_name,
                        source_type="docx",
                        section=page_section,
                        language=detect_language(content),
                        metadata={"char_count": len(content), "needs_ocr": False, "ocr_applied": False}
                    )
                )
                page_num += 1
                current_page_blocks = [block]
                current_words = words
                page_section = block["section"]
            else:
                current_page_blocks.append(block)
                current_words += words
                page_section = block["section"]

        if current_page_blocks:
            content = "\n\n".join(b["text"] for b in current_page_blocks)
            pages.append(
                DocumentPage(
                    content=content,
                    page_number=page_num,
                    source=doc_name,
                    source_type="docx",
                    section=page_section,
                    language=detect_language(content),
                    metadata={"char_count": len(content), "needs_ocr": False, "ocr_applied": False}
                )
            )

        total_pages = len(pages)
        for p in pages:
            p.metadata["total_pages"] = total_pages

        return pages

    @classmethod
    def load_txt(cls, file_path: Path) -> List[DocumentPage]:
        """
        Extract text from plain text or markdown file.
        Tracks markdown headings (# Section) and segments into pages.
        """
        doc_name = file_path.name
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                raw_text = f.read()
        except UnicodeDecodeError:
            with open(file_path, "r", encoding="latin-1") as f:
                raw_text = f.read()

        chars_per_page = 2500
        if len(raw_text) <= chars_per_page:
            section_match = re.search(r"(?:^|\n)(?:#+\s*|\bSection\s+)(\w[^\n]{2,40})", raw_text)
            section = section_match.group(1).strip() if section_match else "General"
            return [
                DocumentPage(
                    content=raw_text.strip(),
                    page_number=1,
                    source=doc_name,
                    source_type="txt",
                    section=section,
                    language=detect_language(raw_text),
                    metadata={"total_pages": 1, "char_count": len(raw_text), "needs_ocr": False, "ocr_applied": False}
                )
            ]

        pages: List[DocumentPage] = []
        total_pages = (len(raw_text) + chars_per_page - 1) // chars_per_page
        current_section = "General"

        for i in range(0, len(raw_text), chars_per_page):
            chunk_content = raw_text[i : i + chars_per_page].strip()
            page_num = (i // chars_per_page) + 1

            section_match = re.search(r"(?:^|\n)(?:#+\s*|\bSection\s+)(\w[^\n]{2,40})", chunk_content)
            if section_match:
                current_section = section_match.group(1).strip()

            pages.append(
                DocumentPage(
                    content=chunk_content,
                    page_number=page_num,
                    source=doc_name,
                    source_type="txt",
                    section=current_section,
                    language=detect_language(chunk_content),
                    metadata={"total_pages": total_pages, "char_count": len(chunk_content), "needs_ocr": False, "ocr_applied": False}
                )
            )

        return pages
