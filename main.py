import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List

# Ensure UTF-8 output on Windows terminal
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from src.config import (
    PROCESSED_DIR,
    CHUNK_SIZE,
    CHUNK_OVERLAP,
    SEMANTIC_CHUNKING_ENABLED,
    SEMANTIC_MODEL,
)
from src.document_loader import DocumentLoader, DocumentPage
from src.chunking import IntelligentChunker, DocumentChunk
from src.ocr import is_tesseract_available
from src.language_detection import get_language_name, analyze_document_languages

def process_document(
    file_path: str | Path,
    output_path: Optional[str | Path] = None,
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP,
    enable_ocr: bool = True,
    enable_semantic: Optional[bool] = None,
) -> Path:
    """
    Stage 1 Ingestion Pipeline:
    Document (PDF/DOCX/TXT)
    -> Text extraction
    -> OCR if needed
    -> Language detection
    -> Page/section metadata preservation
    -> Semantic chunking
    -> Save to chunks.json
    """
    input_file = Path(file_path).resolve()
    if not input_file.is_file():
        raise FileNotFoundError(f"Input document does not exist: {input_file}")

    print(f"\n========================================================")
    print(f"STAGE 1: DOCUMENT INGESTION PIPELINE")
    print(f"========================================================")
    print(f"📄 Processing File : {input_file.name}")
    print(f"📁 Source Format   : {input_file.suffix.lower()}")
    ocr_status = "Available (Tesseract/RapidOCR)" if (enable_ocr and is_tesseract_available()) else ("Disabled (Native Text Only)" if not enable_ocr else "Standby (Text-based mode)")
    print(f"🔍 OCR Engine      : {ocr_status}")

    # 1. Document Parsing & Text Extraction (with OCR fallback)
    print("\n[Step 1/3] Extracting text and page structure...")
    pages: List[DocumentPage] = DocumentLoader.load_document(input_file, enable_ocr=enable_ocr)
    total_pages = len(pages)
    total_chars = sum(len(p.content) for p in pages)
    ocr_applied_count = sum(1 for p in pages if p.metadata.get("ocr_applied", False))

    print(f"  -> Extracted {total_pages} page(s)/section(s) ({total_chars} total characters).")
    if ocr_applied_count > 0:
        print(f"  -> OCR was executed on {ocr_applied_count} page(s).")

    # 2. Document Language Analysis & Semantic Chunking
    print("\n[Step 2/3] Analyzing document languages & performing semantic chunking...")
    doc_lang_analysis = analyze_document_languages([p.content for p in pages])

    sem_enabled = enable_semantic if enable_semantic is not None else SEMANTIC_CHUNKING_ENABLED
    chunker = IntelligentChunker(enabled=sem_enabled)
    chunks: List[DocumentChunk] = chunker.chunk_pages(pages, doc_analysis=doc_lang_analysis)

    detected_languages = doc_lang_analysis["detected_languages"]
    lang_display = doc_lang_analysis["summary_display"]

    avg_words = (sum(c.word_count for c in chunks) / len(chunks)) if chunks else 0
    avg_chars = (sum(c.char_count for c in chunks) / len(chunks)) if chunks else 0

    ocr_pages_count = sum(1 for p in pages if p.metadata.get("extraction_method") == "OCR" or p.metadata.get("ocr_applied", False))
    native_pages_count = total_pages - ocr_pages_count
    chunking_strategy = chunks[0].metadata.get("chunking_strategy", "deterministic") if chunks else "none"

    print(f"\n--- STAGE 1 INGESTION SUMMARY ---")
    print(f"Total pages: {total_pages}")
    print(f"Total extracted characters: {total_chars}")
    print(f"Native-text pages: {native_pages_count}")
    print(f"OCR pages: {ocr_pages_count}")
    print(f"Total chunks: {len(chunks)}")
    print(f"Average chunk size: {avg_words:.0f} words ({avg_chars:.0f} characters)")
    print(f"Detected language: {lang_display}")
    print(f"Chunking strategy: {chunking_strategy}")
    print(f"---------------------------------")

    # 3. Serialize and Save to JSON
    print("\n[Step 3/3] Saving structured chunks to JSON...")
    if output_path is None:
        PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
        out_file = PROCESSED_DIR / f"{input_file.stem}_chunks.json"
    else:
        out_file = Path(output_path).resolve()
        out_file.parent.mkdir(parents=True, exist_ok=True)

    result_payload: Dict[str, Any] = {
        "document_name": input_file.name,
        "document_type": input_file.suffix.lower().lstrip("."),
        "file_size_bytes": input_file.stat().st_size,
        "processed_at": datetime.now().isoformat(),
        "total_pages": total_pages,
        "native_text_pages": native_pages_count,
        "ocr_pages": ocr_pages_count,
        "total_chunks": len(chunks),
        "total_characters": total_chars,
        "average_chunk_words": round(avg_words, 1),
        "average_chunk_chars": round(avg_chars, 1),
        "primary_language": doc_lang_analysis["primary_language"],
        "detected_languages": detected_languages,
        "language_breakdown": doc_lang_analysis["language_breakdown"],
        "language_summary": lang_display,
        "is_multilingual": doc_lang_analysis["is_multilingual"],
        "ocr_used": ocr_pages_count > 0,
        "chunking_strategy": chunking_strategy,
        "chunks": [chunk.to_dict() for chunk in chunks]
    }

    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(result_payload, f, ensure_ascii=False, indent=2)

    print(f"  -> Successfully generated: {out_file}")

    # Preview First 3 Chunks
    preview_count = min(3, len(chunks))
    print(f"\n========================================================")
    print(f"PREVIEW: FIRST {preview_count} MEANINGFUL CHUNKS")
    print(f"========================================================")
    for i in range(preview_count):
        c = chunks[i]
        sec_str = f" | Section: {c.section}" if c.section else ""
        print(f"\n[CHUNK {i+1}] {c.chunk_id} (Page {c.page_number}{sec_str}) [{c.word_count} words, {c.char_count} chars, Lang: {c.language}]")
        print("-" * 60)
        print(c.text)
        print("-" * 60)
    print(f"========================================================\n")

    return out_file

def main():
    parser = argparse.ArgumentParser(
        description="Stage 1: Offline Document Extraction, OCR, Language Detection, and Semantic Chunking."
    )
    parser.add_argument("document", help="Path to input document (.pdf, .docx, .txt)")
    parser.add_argument("--output", "-o", default=None, help="Custom output path for chunks.json")
    parser.add_argument("--chunk-size", type=int, default=CHUNK_SIZE, help=f"Chunk size (default: {CHUNK_SIZE})")
    parser.add_argument("--chunk-overlap", type=int, default=CHUNK_OVERLAP, help=f"Chunk overlap (default: {CHUNK_OVERLAP})")
    parser.add_argument("--native-only", "--no-ocr", action="store_true", help="Extract selectable native PDF text only and skip OCR entirely")
    parser.add_argument("--semantic", dest="semantic", action="store_true", default=None, help="Force Llama 3.2 semantic chunking")
    parser.add_argument("--no-semantic", dest="semantic", action="store_false", help="Disable Llama 3.2 semantic chunking")

    args = parser.parse_args()

    try:
        out_path = process_document(
            file_path=args.document,
            output_path=args.output,
            chunk_size=args.chunk_size,
            chunk_overlap=args.chunk_overlap,
            enable_ocr=not args.native_only,
            enable_semantic=args.semantic,
        )
        print(f"DONE. Chunks saved to: {out_path}")
    except Exception as e:
        print(f"\n[ERROR]: Failed to process document: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
