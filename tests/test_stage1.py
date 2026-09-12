import json
import sys
from pathlib import Path

# Ensure UTF-8 output on Windows terminal
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from main import process_document
from src.language_detection import detect_language

def run_stage1_tests():
    print("========================================================")
    print("RUNNING STAGE 1 AUTOMATED TESTS")
    print("========================================================")

    sample_dir = BASE_DIR / "tests" / "sample_docs"
    sample_dir.mkdir(parents=True, exist_ok=True)

    # 1. Test Multilingual Language Detection Unit
    print("\n[Test 1] Testing Multilingual Language Detection...")
    samples = {
        "en": "Artificial intelligence and local edge computing provide privacy.",
        "hi": "यह दस्तावेज़ बहुभाषी सूचना पुनर्प्राप्ति प्रणाली का परीक्षण करता है।",
        "ta": "இந்த ஆவணம் ஆஃப்லைன் தகவல் மீட்டெடுப்பு அமைப்பை சோதிக்கிறது.",
        "te": "ఈ పత్రం ఆఫ్‌లైన్ సమాచార పునరుద్ధరణ వ్యవస్థను పరీక్షిస్తుంది.",
    }
    for expected_lang, text in samples.items():
        detected = detect_language(text)
        print(f"  -> Input ({expected_lang}): '{text[:35]}...' => Detected: '{detected}'")
        assert detected == expected_lang, f"Expected {expected_lang}, got {detected}"
    print("  -> Language detection test PASSED!")

    # 2. Test PDF Ingestion -> chunks.json
    print("\n[Test 2] Testing PDF Parsing & Chunking...")
    pdf_path = sample_dir / "research_paper.pdf"
    assert pdf_path.exists(), f"Sample PDF missing at {pdf_path}"

    pdf_out = process_document(pdf_path, output_path=sample_dir / "pdf_chunks.json")
    with open(pdf_out, "r", encoding="utf-8") as f:
        pdf_data = json.load(f)

    assert pdf_data["total_pages"] == 3, f"Expected 3 pages, got {pdf_data['total_pages']}"
    assert len(pdf_data["chunks"]) > 0, "No chunks generated from PDF"
    first_pdf_chunk = pdf_data["chunks"][0]
    for required_field in ["chunk_id", "document_name", "page_number", "section", "text", "language", "source_type", "ocr_applied"]:
        assert required_field in first_pdf_chunk, f"Missing required field {required_field} in chunk"
    print(f"  -> PDF test PASSED ({len(pdf_data['chunks'])} chunks verified).")

    # 3. Test DOCX Ingestion -> chunks.json
    print("\n[Test 3] Testing DOCX Parsing & Chunking...")
    docx_path = sample_dir / "experiment_report.docx"
    assert docx_path.exists(), f"Sample DOCX missing at {docx_path}"

    docx_out = process_document(docx_path, output_path=sample_dir / "docx_chunks.json")
    with open(docx_out, "r", encoding="utf-8") as f:
        docx_data = json.load(f)

    assert docx_data["total_chunks"] > 0, "No chunks generated from DOCX"
    # Verify table content was captured
    docx_text = " ".join(c["text"] for c in docx_data["chunks"])
    assert "Qwen 2.5 3B Local Ollama" in docx_text or "Component" in docx_text, "DOCX table content was not captured"
    print(f"  -> DOCX test PASSED ({len(docx_data['chunks'])} chunks verified).")

    # 4. Test Multilingual Heterogeneous TXT Document
    print("\n[Test 4] Testing Multilingual Heterogeneous Document...")
    multi_file = sample_dir / "multilingual_doc.txt"
    multi_content = (
        "# Section 1: English Introduction\n"
        "This project evaluates offline edge document intelligence without cloud APIs.\n\n"
        "# Section 2: Hindi Documentation\n"
        "यह प्रणाली हिंदी भाषा में भी सटीक संदर्भ निकालने में सक्षम है। इसमें स्थानीय एल्गोरिदम का उपयोग किया गया है।\n\n"
        "# Section 3: Tamil & Telugu Sections\n"
        "இந்த அமைப்பு தமிழ் ஆவணங்களை நேரடியாக செயலாக்குகிறது.\n"
        "ఈ వ్యవస్థ తెలుగు పత్రాలను కూడా సజావుగా ప్రాసెస్ చేస్తుంది.\n"
    )
    with open(multi_file, "w", encoding="utf-8") as f:
        f.write(multi_content)

    multi_out = process_document(multi_file, output_path=sample_dir / "multi_chunks.json")
    with open(multi_out, "r", encoding="utf-8") as f:
        multi_data = json.load(f)

    detected_langs = multi_data["detected_languages"]
    print(f"  -> Document detected languages: {detected_langs}")
    assert len(detected_langs) >= 2, "Expected at least 2 detected languages in multilingual document"
    print("  -> Multilingual document test PASSED!")

    print("\n========================================================")
    print("ALL STAGE 1 TESTS COMPLETED SUCCESSFULLY!")
    print("========================================================")

if __name__ == "__main__":
    run_stage1_tests()
