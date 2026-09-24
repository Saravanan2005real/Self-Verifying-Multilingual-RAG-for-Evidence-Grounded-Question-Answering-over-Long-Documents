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
    INDEX_DIR,
    CHUNK_SIZE,
    CHUNK_OVERLAP,
    SEMANTIC_CHUNKING_ENABLED,
    SEMANTIC_MODEL,
    OLLAMA_BASE_URL,
)
from src.language_detection import get_language_name
from src.ocr import is_tesseract_available, is_ocr_available, get_ocr_engine_name
from src.semantic_chunker import OllamaSemanticAdvisor
from src.vector_store import FAISSVectorStore
from main import process_document

# Page Configuration
st.set_page_config(
    page_title="Stage 1 & 2: Document Parsing & Multilingual Vector Retrieval",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Session State Initialization
if "processed_data" not in st.session_state:
    st.session_state.processed_data = None
if "output_file" not in st.session_state:
    st.session_state.output_file = None
if "vector_store" not in st.session_state:
    st.session_state.vector_store = None
if "vector_store_doc" not in st.session_state:
    st.session_state.vector_store_doc = None

# Auto-load existing processed document if available and not yet loaded in session
if st.session_state.processed_data is None:
    existing_processed = sorted(PROCESSED_DIR.glob("*_chunks.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if existing_processed:
        try:
            with open(existing_processed[0], "r", encoding="utf-8") as f:
                st.session_state.processed_data = json.load(f)
            st.session_state.output_file = str(existing_processed[0])
        except Exception:
            pass


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

    # Ensure FAISS Vector Store is ready for the current document
    doc_name = data.get("document_name", "document")
    if (
        st.session_state.vector_store is None
        or st.session_state.vector_store_doc != doc_name
    ):
        idx_p = INDEX_DIR / f"{Path(doc_name).stem}_chunks.index"
        meta_p = INDEX_DIR / f"{Path(doc_name).stem}_chunks.json"
        if idx_p.exists() and meta_p.exists():
            try:
                st.session_state.vector_store = FAISSVectorStore.load_from_disk(idx_p, meta_p)
                st.session_state.vector_store_doc = doc_name
            except Exception:
                st.session_state.vector_store = None

        if st.session_state.vector_store is None:
            v_store = FAISSVectorStore()
            v_store.build_from_chunks(chunks)
            try:
                v_store.save(idx_p, meta_p)
            except Exception:
                pass
            st.session_state.vector_store = v_store
            st.session_state.vector_store_doc = doc_name

    # Download Button & Quick Actions
    st.markdown("---")
    st.markdown("### 3. Multilingual Vector Retrieval")

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
        search_query = st.text_input(
            "Search chunks with multilingual vector retrieval:",
            value="",
            help="Performs semantic vector retrieval using multilingual embeddings (supports English, Tamil, Hindi)."
        )

    # Display Vector Retrieval results if query is entered
    if search_query and search_query.strip():
        retrieved_results = st.session_state.vector_store.retrieve(search_query.strip(), top_k=5)
        st.caption(f"Top {len(retrieved_results)} semantically relevant chunks retrieved via FAISS vector search for: **'{search_query}'**")

        if not retrieved_results:
            st.info("No matching chunks found.")

        for c in retrieved_results:
            chunk_id = c.get("chunk_id", "")
            page_num = c.get("page", c.get("page_number", 1))
            section_label = str(c.get("section") or "General")
            lang_code = c.get("language", "unknown")
            lang_label = f"{get_language_name(lang_code)} ({lang_code})"
            sim_score = c.get("similarity_score", c.get("score", 0.0))

            meta_parts = [
                f"**ID:** {chunk_id}",
                f"**Page:** {page_num}",
                f"**Section:** {section_label}",
                f"**Language:** {lang_label}",
                f"**Similarity Score:** {sim_score:.4f}",
            ]
            if "word_count" in c:
                meta_parts.append(f"**Word Count:** {c['word_count']}")

            original_chunk_text = c.get("text", "")

            with st.container(border=True):
                st.markdown(" | ".join(meta_parts))
                st.write(original_chunk_text)

    # 4. Extracted Semantic Chunks (Always displays all document chunks)
    st.markdown("---")
    st.markdown(f"### 4. Extracted Semantic Chunks ({len(chunks)} Chunks)")

    for c in chunks:
        chunk_id = c.get("chunk_id", "")
        page_num = c.get("page_number", c.get("page", 1))
        section_label = str(c.get("section") or "General")
        lang_code = c.get("language", "unknown")
        lang_label = f"{get_language_name(lang_code)} ({lang_code})"

        meta_parts = [
            f"**ID:** {chunk_id}",
            f"**Page:** {page_num}",
            f"**Section:** {section_label}",
            f"**Language:** {lang_label}",
            f"**Word Count:** {c.get('word_count', 0)}",
        ]

        c_strat = c.get("metadata", {}).get("chunking_strategy", data.get("chunking_strategy", "deterministic"))
        if c_strat == "llama3.2_semantic":
            meta_parts.append("**Chunking Strategy:** Llama 3.2 Semantic")
        elif "fallback" in str(c_strat):
            meta_parts.append("**Chunking Strategy:** Deterministic Fallback")
        else:
            meta_parts.append("**Chunking Strategy:** Deterministic")

        if c.get("ocr_applied"):
            meta_parts.append("**OCR:** Applied")

        original_chunk_text = c.get("text", "")

        with st.container(border=True):
            st.markdown(" | ".join(meta_parts))
            st.write(original_chunk_text)



    # Raw JSON Inspector Expander
    with st.expander("Inspect Full Raw JSON Payload"):
        st.json(data)
