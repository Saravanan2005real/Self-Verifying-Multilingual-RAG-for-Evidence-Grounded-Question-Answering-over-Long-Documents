import os
import json
import time
from pathlib import Path
import streamlit as st

# Ensure root directory is imported
import sys
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from src.config import UPLOADS_DIR, PROCESSED_DIR, CHUNK_SIZE, CHUNK_OVERLAP
from src.language_detection import get_language_name
from src.ocr import is_tesseract_available, is_ocr_available, get_ocr_engine_name
from main import process_document

# Page Configuration
st.set_page_config(
    page_title="Stage 1: Document Parsing & Semantic Chunking",
    page_icon="📑",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for Modern, Premium Internship Demo
st.markdown("""
<style>
    /* Metric Cards */
    .metric-card {
        background: linear-gradient(135deg, rgba(30, 41, 59, 0.7), rgba(15, 23, 42, 0.8));
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 16px 20px;
        margin-bottom: 15px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
    }
    .metric-title {
        font-size: 0.82rem;
        text-transform: uppercase;
        letter-spacing: 0.8px;
        color: #94a3b8;
        margin-bottom: 6px;
    }
    .metric-value {
        font-size: 1.6rem;
        font-weight: 700;
        color: #f8fafc;
    }

    /* Badges */
    .badge {
        display: inline-block;
        padding: 3px 10px;
        border-radius: 12px;
        font-size: 0.78rem;
        font-weight: 600;
        margin-right: 6px;
    }
    .badge-page {
        background: #1e3a8a;
        color: #93c5fd;
        border: 1px solid #3b82f6;
    }
    .badge-section {
        background: #312e81;
        color: #c7d2fe;
        border: 1px solid #6366f1;
    }
    .badge-lang {
        background: #064e3b;
        color: #6ee7b7;
        border: 1px solid #10b981;
    }
    .badge-id {
        background: #374151;
        color: #e5e7eb;
        border: 1px solid #4b5563;
        font-family: monospace;
    }
    .badge-ocr {
        background: #78350f;
        color: #fde68a;
        border: 1px solid #f59e0b;
    }

    /* Chunk Container */
    .chunk-box {
        background: rgba(15, 23, 42, 0.6);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-left: 4px solid #3b82f6;
        border-radius: 8px;
        padding: 14px 18px;
        margin-bottom: 14px;
        transition: all 0.2s ease-in-out;
    }
    .chunk-box:hover {
        border-color: rgba(59, 130, 246, 0.5);
        box-shadow: 0 4px 15px rgba(59, 130, 246, 0.1);
    }
    .chunk-text {
        font-size: 0.93rem;
        line-height: 1.6;
        color: #cbd5e1;
        margin-top: 10px;
        white-space: pre-wrap;
    }
</style>
""", unsafe_allow_html=True)

# Session State Initialization
if "processed_data" not in st.session_state:
    st.session_state.processed_data = None
if "output_file" not in st.session_state:
    st.session_state.output_file = None

# Sidebar Controls
with st.sidebar:
    st.title("⚙️ Stage 1 Configuration")
    st.caption("Offline Document Ingestion & Chunking")

    # OCR Status & Toggle
    ocr_engine = get_ocr_engine_name()
    ocr_available = is_ocr_available()
    ocr_toggle = st.checkbox(
        "Enable OCR fallback for scanned pages",
        value=False,
        help="If checked, runs local OCR when no selectable text is found. Uncheck to extract native PDF text only."
    )
    if ocr_available:
        st.info(f"● OCR Engine: {ocr_engine}")
    else:
        st.caption("Local OCR engine not active.")

    st.markdown("---")
    st.subheader("Chunking Parameters")
    chunk_size = st.slider(
        "Chunk Size (characters)",
        min_value=200,
        max_value=1200,
        value=CHUNK_SIZE,
        step=50,
        help="Target length of each semantic text chunk"
    )
    chunk_overlap = st.slider(
        "Chunk Overlap (characters)",
        min_value=0,
        max_value=300,
        value=CHUNK_OVERLAP,
        step=20,
        help="Character overlap maintained between adjacent chunks"
    )

    st.markdown("---")
    st.markdown("""
    **Project Stage 1 Scope:**
    - PDF / DOCX / TXT Parsing
    - Scanned Page Detection / OCR
    - Language Identification
    - Page & Section Preservation
    - JSON Export
    """)

# Header
st.title("📄 Multilingual Document Ingestion & Semantic Chunking")
st.caption("Stage 1 Demonstration • Offline Document Parser & Intelligent Chunk Generator")

# File Upload Section
st.markdown("### 1. Upload Document")
uploaded_file = st.file_uploader(
    "Choose a PDF, DOCX, or TXT file to process",
    type=["pdf", "docx", "txt"],
    help="Documents are processed 100% locally on your machine."
)

col_btn, col_info = st.columns([1, 3])
with col_btn:
    process_clicked = st.button("🚀 Process Document", type="primary", use_container_width=True, disabled=(uploaded_file is None))

# Execution Logic
if process_clicked and uploaded_file is not None:
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    temp_path = UPLOADS_DIR / uploaded_file.name

    # Save uploaded file
    with open(temp_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    with st.spinner("Executing Stage 1 Ingestion Pipeline..."):
        start_time = time.time()
        try:
            out_json_path = process_document(
                file_path=temp_path,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                enable_ocr=ocr_toggle,
            )
            elapsed = time.time() - start_time

            # Load generated JSON
            with open(out_json_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            data["elapsed_time"] = f"{elapsed:.2f}s"
            st.session_state.processed_data = data
            st.session_state.output_file = str(out_json_path)

            st.success(f"Processing completed in {elapsed:.2f} seconds!")
        except Exception as e:
            st.error(f"Error processing document: {str(e)}")

# Display Results if Available
if st.session_state.processed_data is not None:
    data = st.session_state.processed_data
    chunks = data.get("chunks", [])

    st.markdown("---")
    st.markdown("### 2. Document Summary & Ingestion Metadata")

    # Metrics Grid
    m1, m2, m3, m4, m5, m6 = st.columns(6)
    with m1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">Document Name</div>
            <div class="metric-value" style="font-size: 1.1rem; word-break: break-all;">{data['document_name']}</div>
        </div>
        """, unsafe_allow_html=True)
    with m2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">Format</div>
            <div class="metric-value">{data['document_type'].upper()}</div>
        </div>
        """, unsafe_allow_html=True)
    with m3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">Pages / Sections</div>
            <div class="metric-value">{data['total_pages']}</div>
        </div>
        """, unsafe_allow_html=True)
    with m4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">Total Characters</div>
            <div class="metric-value">{data['total_characters']:,}</div>
        </div>
        """, unsafe_allow_html=True)
    with m5:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">Semantic Chunks</div>
            <div class="metric-value">{data['total_chunks']}</div>
        </div>
        """, unsafe_allow_html=True)
    with m6:
        breakdown = data.get("language_breakdown", {})
        is_multi = data.get("is_multilingual", False) and len(breakdown) > 1

        if not is_multi:
            primary_lang = data.get("primary_language", "en")
            title = "Detected Language"
            langs_display = f"{get_language_name(primary_lang)} ({primary_lang})"
        else:
            title = "Detected Languages"
            items = [
                f"{get_language_name(lang)} ({lang}) — {pct:.0f}%"
                for lang, pct in breakdown.items()
            ]
            langs_display = "<br>".join(items)

        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">{title}</div>
            <div class="metric-value" style="font-size: 0.95rem; line-height: 1.4;">{langs_display}</div>
        </div>
        """, unsafe_allow_html=True)

    # Download Button & Quick Actions
    col_dl, col_search = st.columns([1, 2])
    with col_dl:
        json_bytes = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        st.download_button(
            label="📥 Download chunks.json",
            data=json_bytes,
            file_name=f"{Path(data['document_name']).stem}_chunks.json",
            mime="application/json",
            type="primary",
            use_container_width=True
        )

    with col_search:
        filter_text = st.text_input("🔍 Filter chunks by keyword or text content:", "")

    st.markdown("---")
    st.markdown(f"### 3. Extracted Semantic Chunks ({len(chunks)} Chunks)")

    # Filter chunks if user typed a keyword
    filtered_chunks = [
        c for c in chunks
        if not filter_text or filter_text.lower() in c["text"].lower() or filter_text.lower() in str(c.get("section", "")).lower()
    ]

    if filter_text:
        st.caption(f"Showing {len(filtered_chunks)} of {len(chunks)} chunks matching '{filter_text}'")

    for c in filtered_chunks:
        lang_label = f"{get_language_name(c['language'])} ({c['language']})"
        section_label = c.get("section") or "General"
        ocr_flag = '<span class="badge badge-ocr">OCR Applied</span>' if c.get("ocr_applied") else ''

        st.markdown(f"""
        <div class="chunk-box">
            <div>
                <span class="badge badge-id">ID: {c['chunk_id']}</span>
                <span class="badge badge-page">📄 Page {c['page_number']}</span>
                <span class="badge badge-section">🏷️ Section: {section_label}</span>
                <span class="badge badge-lang">🌐 {lang_label}</span>
                <span class="badge badge-id">{c['char_count']} chars (offset {c['char_start']}-{c['char_end']})</span>
                {ocr_flag}
            </div>
            <div class="chunk-text">{c['text']}</div>
        </div>
        """, unsafe_allow_html=True)

    # Raw JSON Inspector Expander
    with st.expander("🔍 Inspect Full Raw JSON Payload"):
        st.json(data)
