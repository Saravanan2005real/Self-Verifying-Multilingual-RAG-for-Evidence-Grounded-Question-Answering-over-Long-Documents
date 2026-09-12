# Multilingual Document Processing & Semantic Chunking (Stage 1)

An edge-native, local document ingestion pipeline designed for long and heterogeneous documents (PDF, DOCX, TXT, scanned pages).

Stage 1 strictly implements the first ingestion milestone:
$$\text{Document (PDF/DOCX/TXT)} \longrightarrow \text{Text Extraction} \longrightarrow \text{OCR (if needed)} \longrightarrow \text{Language Detection} \longrightarrow \text{Meaningful Chunks} \longrightarrow \text{chunks.json}$$

---

## 🌟 Stage 1 Features

1. **Multi-format Support**:
   - **PDF**: Page-by-page extraction using PyMuPDF (`pymupdf`).
   - **DOCX**: Heading-aware extraction, table row/column preservation using `python-docx`.
   - **TXT**: Section-aware (`# Heading` / `Section`) paragraph extraction.
2. **Scanned Page Detection & OCR Fallback**:
   - Automatically detects pages where text is sparse/empty and image data is present.
   - Triggers local Tesseract OCR when available; alerts gracefully if Tesseract is in standby mode.
3. **Multilingual Language Detection**:
   - Classifies language per page and per chunk using deterministic `langdetect`.
   - Supports English (`en`), Hindi (`hi`), Tamil (`ta`), Telugu (`te`), and other ISO-639 languages.
4. **Structure-Aware Semantic Chunking**:
   - Preserves page boundaries (never merges text across pages blindly).
   - Detects section headings and language transitions, flushing chunks at structural changes.
   - Configurable chunk size and overlap.
5. **Standardized Provenance Output**:
   - Emits structured `chunks.json` preserving `chunk_id`, `document_name`, `page_number`, `section`, `language`, `source_type`, `char_start`, `char_end`, and `ocr_applied`.

---

## 📁 Directory Structure

```
docxreader/
│
├── .env.example                # Example environment variables (storage paths, OCR)
├── .gitignore                  # Git ignore rules for venv, caches, logs
├── app.py                      # Stage 1 Streamlit demonstration UI
├── main.py                     # Primary CLI entry point
├── requirements.txt            # Python dependencies (Stage 1 only)
├── README.md                   # Documentation & usage instructions
│
├── data/
│   ├── uploads/                # Directory for input documents
│   └── processed/              # Directory for output chunks.json
│
├── src/
│   ├── __init__.py
│   ├── config.py               # Chunk sizes, thresholds, storage paths
│   ├── language_detection.py   # Multilingual detection module
│   ├── ocr.py                  # Scanned page detection, PyTesseract & RapidOCR
│   ├── document_loader.py      # Unified PDF, DOCX, TXT parser (native-first)
│   └── chunking.py             # Page & section-preserving semantic chunker
│
└── tests/
    ├── test_stage1.py          # Automated verification test suite
    ├── create_sample_docs.py   # Sample document generator
    └── sample_docs/            # Synthetic PDF, DOCX, TXT test documents
```

---

## 🚀 Exact Commands to Run Stage 1

### 1. Launch the Stage 1 Streamlit Frontend
```powershell
.\venv\Scripts\python -m streamlit run app.py
```
Open `http://localhost:8501` in your browser to upload documents, inspect extraction & semantic chunks, and download `chunks.json`.

### 2. Run Automated Test Suite
Verifies PDF extraction, DOCX table parsing, multilingual language detection (English, Hindi, Tamil, Telugu), and `chunks.json` schema:
```powershell
.\venv\Scripts\python tests/test_stage1.py
```

### 3. Process Any PDF Document
```powershell
.\venv\Scripts\python main.py tests/sample_docs/research_paper.pdf
```
*Output is automatically saved to:* `data/processed/research_paper_chunks.json`.

### 4. Process Any PDF Using Native Text Only (Skip OCR)
```powershell
.\venv\Scripts\python main.py "data/uploads/FLA-Unit 1.pdf" --native-only
```

### 5. Process Any DOCX Document
```powershell
.\venv\Scripts\python main.py tests/sample_docs/experiment_report.docx
```
*Output is automatically saved to:* `data/processed/experiment_report_chunks.json`.

### 6. Process Any TXT Document with Custom Output Path
```powershell
.\venv\Scripts\python main.py tests/sample_docs/multilingual_doc.txt --output data/processed/my_custom_chunks.json
```

### 7. Custom Chunk Size and Overlap
```powershell
.\venv\Scripts\python main.py tests/sample_docs/research_paper.pdf --chunk-size 400 --chunk-overlap 80
```

---

## 📄 Output `chunks.json` Schema

```json
{
  "document_name": "research_paper.pdf",
  "document_type": "pdf",
  "file_size_bytes": 2993,
  "processed_at": "2026-09-12T16:37:55.028447",
  "total_pages": 3,
  "total_chunks": 5,
  "total_characters": 1741,
  "detected_languages": ["en"],
  "ocr_used": false,
  "chunks": [
    {
      "chunk_id": "research_paper.pdf_p1_c0",
      "document_name": "research_paper.pdf",
      "page_number": 1,
      "section": "1. Introduction",
      "chunk_index": 0,
      "text": "Long-document question answering poses severe challenges...",
      "char_start": 0,
      "char_end": 376,
      "char_count": 376,
      "language": "en",
      "source_type": "pdf",
      "ocr_applied": false,
      "metadata": {
        "total_pages": 3,
        "char_count": 673,
        "images_count": 0,
        "needs_ocr": false,
        "ocr_applied": false
      }
    }
  ]
}
```
