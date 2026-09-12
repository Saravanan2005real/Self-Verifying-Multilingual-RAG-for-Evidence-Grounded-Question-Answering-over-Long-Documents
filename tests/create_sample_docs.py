import sys
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

def create_sample_pdf(pdf_path: Path):
    """Generate a 3-page synthetic PDF with research content using PyMuPDF."""
    import pymupdf as fitz
    
    doc = fitz.open()
    
    # Page 1: Abstract & Introduction
    page1 = doc.new_page(width=595, height=842)
    text1 = (
        "Multilingual Document Intelligence: A Comprehensive Study\n\n"
        "Authors: Dr. A. Sharma, Dr. R. Ramanujan, Dr. V. Rao\n"
        "Affiliation: Edge Computing & Language AI Lab\n\n"
        "1. Introduction\n"
        "Long-document question answering poses severe challenges for offline edge deployments.\n"
        "In many production environments, access to cloud-based APIs is restricted due to privacy\n"
        "and compliance regulations. This paper introduces an offline framework for long, heterogeneous\n"
        "documents across multiple languages including English, Hindi, Tamil, and Telugu.\n\n"
        "2. Related Work\n"
        "Standard dense retrieval pipelines frequently suffer from cross-lingual misalignment and lack of\n"
        "faithful page-grounded attribution."
    )
    page1.insert_text((50, 70), text1, fontsize=11, fontname="helv")
    
    # Page 2: Experiments & Architecture
    page2 = doc.new_page(width=595, height=842)
    text2 = (
        "3. Experimental Methodology & Architecture\n\n"
        "We deployed an offline embedding model combined with a local 3.2 billion parameter language model.\n"
        "All vector indexing was handled via FAISS IndexFlatIP to ensure normalized cosine similarity.\n\n"
        "Key Benchmark Results (Experiment 4B):\n"
        "- Baseline Dense Retrieval Recall: 64.2%\n"
        "- Proposed Hybrid Framework Recall: 92.7%\n"
        "- Net Relative Improvement: 28.5% improvement in retrieval recall over naive dense search.\n"
        "- Average Inference Latency: 1.4 seconds per query on 16GB CPU architecture.\n\n"
        "The experiments were replicated across 500 multi-hop queries."
    )
    page2.insert_text((50, 70), text2, fontsize=11, fontname="helv")

    # Page 3: Conclusion & Hardware
    page3 = doc.new_page(width=595, height=842)
    text3 = (
        "4. Edge Hardware Deployment & Conclusion\n\n"
        "The entire system was benchmarked on standard consumer hardware equipped with 16 GB of RAM\n"
        "and integrated Intel Iris Xe graphics. Zero cloud APIs were queried during evaluation.\n\n"
        "5. Reproducibility & Open Source\n"
        "The model weights for Qwen 2.5 3B were quantized in Q4_K_M format, requiring exactly 2.0 GB of RAM.\n"
        "In conclusion, self-verifying local RAG demonstrates high citation fidelity and eliminates hallucinations\n"
        "on unsupported queries."
    )
    page3.insert_text((50, 70), text3, fontsize=11, fontname="helv")

    doc.save(str(pdf_path))
    doc.close()
    print(f"Created sample PDF at: {pdf_path}")

def create_sample_docx(docx_path: Path):
    """Generate a sample DOCX with text and tables using python-docx."""
    import docx
    
    doc = docx.Document()
    doc.add_heading("Laboratory Research Protocol - DOCX Evaluation", level=1)
    
    doc.add_paragraph(
        "This document verifies the python-docx parser for tables and structured text in the RAG pipeline."
    )
    doc.add_heading("System Configuration Details", level=2)
    doc.add_paragraph(
        "The target environment specifies Windows 11 64-bit with 16GB total visible memory."
    )
    
    # Table test
    table = doc.add_table(rows=1, cols=3)
    hdr_cells = table.rows[0].cells
    hdr_cells[0].text = "Component"
    hdr_cells[1].text = "Specification"
    hdr_cells[2].text = "Status"

    rows_data = [
        ("Language Model", "Qwen 2.5 3B Local Ollama", "Active"),
        ("Embeddings", "Paraphrase-Multilingual-MiniLM-L12", "Active"),
        ("Vector DB", "FAISS CPU IndexFlatIP", "Ready"),
        ("Tesseract OCR", "UB-Mannheim OCR Engine", "Optional Fallback")
    ]
    for comp, spec, status in rows_data:
        row_cells = table.add_row().cells
        row_cells[0].text = comp
        row_cells[1].text = spec
        row_cells[2].text = status

    doc.save(str(docx_path))
    print(f"Created sample DOCX at: {docx_path}")

if __name__ == "__main__":
    sample_dir = BASE_DIR / "tests" / "sample_docs"
    sample_dir.mkdir(parents=True, exist_ok=True)
    create_sample_pdf(sample_dir / "research_paper.pdf")
    create_sample_docx(sample_dir / "experiment_report.docx")
