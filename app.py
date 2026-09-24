import os
import re
import json
import time
from pathlib import Path
import streamlit as st

# Ensure root directory is imported
import sys
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from src.config import (
    UPLOADS_DIR,
    PROCESSED_DIR,
    CHUNK_SIZE,
    CHUNK_OVERLAP,
    SEMANTIC_CHUNKING_ENABLED,
    SEMANTIC_MODEL,
    OLLAMA_BASE_URL,
)
from src.language_detection import get_language_name
from src.ocr import is_tesseract_available, is_ocr_available, get_ocr_engine_name
from src.semantic_chunker import OllamaSemanticAdvisor
from main import process_document

# Page Configuration
st.set_page_config(
    page_title="Stage 1: Document Parsing & Semantic Chunking",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Session State Initialization
if "processed_data" not in st.session_state:
    st.session_state.processed_data = None
if "output_file" not in st.session_state:
    st.session_state.output_file = None

# Sidebar Controls
with st.sidebar:
    st.title("Stage 1 Configuration")
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
        st.info(f"OCR Engine: {ocr_engine}")
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
    st.subheader("Semantic Chunking")
    try:
        advisor = OllamaSemanticAdvisor()
        ollama_online = advisor.is_available()
    except Exception:
        ollama_online = False

    if ollama_online:
        st.info(f"Ollama: {SEMANTIC_MODEL}")
    else:
        st.warning("Ollama Offline (Fallback active)")

    semantic_toggle = st.checkbox(
        "Enable Llama 3.2 Semantic Chunking",
        value=SEMANTIC_CHUNKING_ENABLED,
        help="Use Llama 3.2 via Ollama to determine contextual semantic boundaries (falls back cleanly if offline)."
    )

    st.markdown("---")
    st.markdown("""
    **Project Stage 1 Scope:**
    - PDF / DOCX / TXT Parsing
    - Scanned Page Detection / OCR
    - Language Identification
    - Llama 3.2 Contextual Boundaries
    - Page & Section Preservation
    - JSON Export
    """)

# Header
st.title("Multilingual Document Ingestion & Semantic Chunking")
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
    process_clicked = st.button("Process Document", type="primary", use_container_width=True, disabled=(uploaded_file is None))

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
                enable_semantic=semantic_toggle,
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
        st.metric(label="Document Name", value=data['document_name'])
    with m2:
        st.metric(label="Format", value=data['document_type'].upper())
    with m3:
        st.metric(label="Pages / Sections", value=data['total_pages'])
    with m4:
        st.metric(label="Total Characters", value=f"{data['total_characters']:,}")
    with m5:
        strat = data.get("chunking_strategy", "deterministic")
        if strat == "llama3.2_semantic":
            strat_label = "Llama 3.2"
        elif "fallback" in strat:
            strat_label = "Fallback"
        else:
            strat_label = "Deterministic"
        st.metric(label=f"Strategy ({data['total_chunks']} chunks)", value=strat_label)
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
                f"{get_language_name(lang)} ({lang}) - {pct:.0f}%"
                for lang, pct in breakdown.items()
            ]
            langs_display = ", ".join(items)

        st.metric(label=title, value=langs_display)

    # Download Button & Quick Actions
    col_dl, col_search = st.columns([1, 2])
    with col_dl:
        json_bytes = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        st.download_button(
            label="Download chunks.json",
            data=json_bytes,
            file_name=f"{Path(data['document_name']).stem}_chunks.json",
            mime="application/json",
            type="primary",
            use_container_width=True
        )

    with col_search:
        filter_text = st.text_input("Filter chunks by keyword or text content:", "")

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
        section_label = str(c.get("section") or "General")
        c_strat = c.get("metadata", {}).get("chunking_strategy", data.get("chunking_strategy", "deterministic"))
        if c_strat == "llama3.2_semantic":
            strat_label = "Llama 3.2 Semantic"
        elif "fallback" in c_strat:
            strat_label = "Deterministic Fallback"
        else:
            strat_label = "Deterministic"

        meta_parts = [
            f"**ID:** {c['chunk_id']}",
            f"**Page:** {c['page_number']}",
            f"**Section:** {section_label}",
            f"**Language:** {lang_label}",
            f"**Word Count:** {c['word_count']}",
            f"**Chunking Strategy:** {strat_label}",
        ]
        if c.get("ocr_applied"):
            meta_parts.append("**OCR:** Applied")

        # Clean document text - completely free of HTML markup
        chunk_text = c.get("text", "")
        chunk_text = re.sub(r"</?[a-zA-Z][^>]*>", "", chunk_text)
        chunk_text = re.sub(r"class\s*=\s*['\"][^'\"]*['\"]", "", chunk_text).strip()

        with st.container(border=True):
            st.markdown(" | ".join(meta_parts))
            st.write(chunk_text)

    # Raw JSON Inspector Expander
    with st.expander("Inspect Full Raw JSON Payload"):
        st.json(data)
