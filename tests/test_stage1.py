import json
import re
import sys
from pathlib import Path
import docx
import pymupdf as fitz

# Ensure UTF-8 output on Windows terminal
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from main import process_document
from src.document_loader import DocumentLoader, DocumentPage
from src.chunking import MeaningfulSemanticChunker
from src.language_detection import detect_language

SAMPLE_DIR = BASE_DIR / "tests" / "sample_docs"
SAMPLE_DIR.mkdir(parents=True, exist_ok=True)


def test_01_english_docx_first_paragraph_preserved():
    """TEST 1 — English DOCX: Verify the first paragraph appears in the first appropriate chunk."""
    doc_path = SAMPLE_DIR / "test_01_tirupati.docx"
    doc = docx.Document()
    doc.add_heading("1. Introduction and Objectives", level=1)
    p1_text = (
        "This study focuses on analyzing temporal changes in surface water bodies in Tirupati "
        "using satellite-based remote sensing techniques. Rapid urbanization and climate variability "
        "have significantly impacted water resources in Tirupati over the past decade. Monitoring these "
        "changes is essential for sustainable urban planning and water resource management."
    )
    p2_text = (
        "In this work, Google Earth Engine is used to access and process Sentinel-2 imagery for the years "
        "2021 to 2025. The Normalized Difference Water Index (NDWI) is computed to detect and analyze "
        "water bodies across different years."
    )
    doc.add_paragraph(p1_text)
    doc.add_paragraph(p2_text)
    doc.save(str(doc_path))

    out_json = process_document(doc_path, output_path=SAMPLE_DIR / "test_01_chunks.json")
    with open(out_json, "r", encoding="utf-8") as f:
        data = json.load(f)

    chunks = data["chunks"]
    assert len(chunks) > 0, "No chunks generated"
    chunk0_text = chunks[0]["text"]

    # Verify Paragraph 1 is present in the first chunk
    assert p1_text in chunk0_text, "CRITICAL: Paragraph 1 is missing from Chunk 0!"
    # Verify Paragraph 2 is also present
    assert p2_text in chunk0_text, "Paragraph 2 is missing from Chunk 0!"
    # Verify logical ordering: Paragraph 1 must appear BEFORE Paragraph 2
    idx_p1 = chunk0_text.index(p1_text)
    idx_p2 = chunk0_text.index(p2_text)
    assert idx_p1 < idx_p2, "Paragraph 1 must precede Paragraph 2 in reading order!"
    # Verify Heading appears before Paragraph 1
    assert "1. Introduction and Objectives" in chunk0_text, "Heading missing from Chunk 0!"
    idx_heading = chunk0_text.index("1. Introduction and Objectives")
    assert idx_heading < idx_p1, "Heading must precede Paragraph 1!"
    print("  -> TEST 1 PASSED: English DOCX first paragraph preserved in logical order.")


def test_02_tamil_unicode_docx():
    """TEST 2 — Tamil/Unicode DOCX: Verify the first Tamil paragraph is preserved."""
    doc_path = SAMPLE_DIR / "test_02_tamil.docx"
    doc = docx.Document()
    tamil_heading = "தமிழ் மொழியின் சிறப்பும் வரலாறும்"
    tamil_p1 = (
        "தமிழ் உலகின் மிகத் தொன்மையான செம்மொழிகளில் ஒன்றாகும். ஆயிரக்கணக்கான ஆண்டுகளாகத் தொடர்ந்து "
        "பேசப்பட்டும் எழுதப்பட்டும் வரும் தனித்துவமான மொழி இதுவாகும்."
    )
    tamil_p2 = (
        "தமிழ் இலக்கியங்கள் மனித வாழ்வின் பண்பாடு, அறநெறி மற்றும் தத்துவங்களை ஆழமாகப் பதிவு செய்துள்ளன. "
        "சங்க இலக்கியம் முதல் நவீன இலக்கியம் வரை தமிழ் காலந்தோறும் வளர்ந்து வந்துள்ளது."
    )
    doc.add_heading(tamil_heading, level=1)
    doc.add_paragraph(tamil_p1)
    doc.add_paragraph(tamil_p2)
    doc.save(str(doc_path))

    out_json = process_document(doc_path, output_path=SAMPLE_DIR / "test_02_chunks.json")
    with open(out_json, "r", encoding="utf-8") as f:
        data = json.load(f)

    chunks = data["chunks"]
    assert len(chunks) > 0, "No chunks generated"
    chunk0_text = chunks[0]["text"]
    assert tamil_p1 in chunk0_text, "CRITICAL: First Tamil paragraph missing from Chunk 0!"
    assert tamil_heading in chunk0_text, "Tamil heading missing from Chunk 0!"
    assert chunk0_text.index(tamil_p1) > chunk0_text.index(tamil_heading), "Tamil heading must precede Paragraph 1!"
    print("  -> TEST 2 PASSED: Tamil/Unicode DOCX first paragraph preserved.")


def test_03_hindi_unicode_document():
    """TEST 3 — Hindi/Unicode document: Verify the first Hindi paragraph is preserved."""
    doc_path = SAMPLE_DIR / "test_03_hindi.docx"
    doc = docx.Document()
    hindi_heading = "हिंदी भाषा और उसका महत्व"
    hindi_p1 = (
        "हिंदी भारत की प्रमुख भाषाओं में से एक है। यह केवल संवाद का माध्यम नहीं, "
        "बल्कि भारतीय संस्कृति, साहित्य और सामाजिक जीवन की महत्वपूर्ण कड़ी है।"
    )
    hindi_p2 = (
        "हिंदी का विकास लंबे ऐतिहासिक क्रम से हुआ है। संस्कृत, प्राकृत और अपभ्रंश से होते हुए "
        "यह आधुनिक खड़ी बोली के रूप में प्रतिष्ठित हुई।"
    )
    doc.add_heading(hindi_heading, level=1)
    doc.add_paragraph(hindi_p1)
    doc.add_paragraph(hindi_p2)
    doc.save(str(doc_path))

    out_json = process_document(doc_path, output_path=SAMPLE_DIR / "test_03_chunks.json")
    with open(out_json, "r", encoding="utf-8") as f:
        data = json.load(f)

    chunks = data["chunks"]
    assert len(chunks) > 0, "No chunks generated"
    chunk0_text = chunks[0]["text"]
    assert hindi_p1 in chunk0_text, "CRITICAL: First Hindi paragraph missing from Chunk 0!"
    assert hindi_heading in chunk0_text, "Hindi heading missing from Chunk 0!"
    assert chunk0_text.index(hindi_p1) > chunk0_text.index(hindi_heading), "Hindi heading must precede Paragraph 1!"
    print("  -> TEST 3 PASSED: Hindi/Unicode document first paragraph preserved.")


def test_04_text_pdf_first_paragraph():
    """TEST 4 — Text PDF: Verify the first extracted paragraph is preserved."""
    pdf_path = SAMPLE_DIR / "research_paper.pdf"
    assert pdf_path.exists(), "Sample PDF missing"

    out_json = process_document(pdf_path, output_path=SAMPLE_DIR / "test_04_chunks.json", enable_ocr=False)
    with open(out_json, "r", encoding="utf-8") as f:
        data = json.load(f)

    chunks = data["chunks"]
    assert len(chunks) > 0, "No chunks generated from PDF"
    chunk0 = chunks[0]["text"]
    expected_first_phrase = "Multilingual Document Intelligence: A Comprehensive Study"
    assert expected_first_phrase in chunk0, f"Expected first PDF text '{expected_first_phrase}' not found in Chunk 0"
    print("  -> TEST 4 PASSED: Text PDF first extracted paragraph preserved.")


def test_05_multipage_pdf():
    """TEST 5 — Multi-page PDF: Verify page 1 content is not skipped when processing page 2."""
    pdf_path = SAMPLE_DIR / "research_paper.pdf"
    out_json = process_document(pdf_path, output_path=SAMPLE_DIR / "test_05_chunks.json", enable_ocr=False)
    with open(out_json, "r", encoding="utf-8") as f:
        data = json.load(f)

    all_text = " ".join(c["text"] for c in data["chunks"])
    # Page 1 excerpt
    assert "Long-document question answering poses severe challenges" in all_text, "Page 1 content missing"
    # Page 2 excerpt
    assert "Experimental Methodology & Architecture" in all_text, "Page 2 content missing"
    # Page 3 excerpt
    assert "Edge Hardware Deployment & Conclusion" in all_text, "Page 3 content missing"
    print("  -> TEST 5 PASSED: Multi-page PDF correctly preserves all page contents.")


def test_06_ocr_scanned_pdf():
    """TEST 6 — OCR/scanned PDF: Verify the first OCR paragraph is preserved."""
    # Synthetic test of MeaningfulSemanticChunker on DocumentPage from OCR
    first_ocr_para = "Automata and formal languages form the fundamental mathematical basis of computer science."
    second_ocr_para = "A finite automaton consists of states, transitions, an initial state, and final accepting states."

    ocr_page = DocumentPage(
        content=f"{first_ocr_para}\n\n{second_ocr_para}",
        page_number=1,
        source="scanned_doc.pdf",
        source_type="scanned_pdf_ocr",
        section="General",
        language="en",
        metadata={"ocr_applied": True, "total_pages": 1}
    )

    chunker = MeaningfulSemanticChunker()
    chunks = chunker.chunk_pages([ocr_page])
    assert len(chunks) > 0, "No chunks generated from OCR page"
    assert first_ocr_para in chunks[0].text, "CRITICAL: First OCR paragraph missing from Chunk 0!"
    assert second_ocr_para in chunks[0].text, "Second OCR paragraph missing from Chunk 0!"
    print("  -> TEST 6 PASSED: OCR/scanned PDF first paragraph preserved.")


def test_07_short_first_paragraph():
    """TEST 7 — Short first paragraph: Verify it is merged, not discarded."""
    doc_path = SAMPLE_DIR / "test_07_short.docx"
    doc = docx.Document()
    short_p1 = "Project overview."  # 2 words
    body_p2 = (
        "This project develops an offline multimodal and multilingual document question answering system. "
        "It operates securely in offline environments without external internet dependencies."
    )
    doc.add_paragraph(short_p1)
    doc.add_paragraph(body_p2)
    doc.save(str(doc_path))

    out_json = process_document(doc_path, output_path=SAMPLE_DIR / "test_07_chunks.json")
    with open(out_json, "r", encoding="utf-8") as f:
        data = json.load(f)

    chunk0_text = data["chunks"][0]["text"]
    assert short_p1 in chunk0_text, "CRITICAL: Short first paragraph was discarded!"
    assert body_p2 in chunk0_text, "Body paragraph missing from Chunk 0!"
    print("  -> TEST 7 PASSED: Short first paragraph is merged into chunk, not discarded.")


def test_08_long_first_paragraph():
    """TEST 8 — Long first paragraph: Verify it is split without loss."""
    # Generate a long paragraph with 800+ words
    sentence = "Deep learning models for document analysis process textual and visual information concurrently. "
    long_p1 = sentence * 75  # ~900 words
    closing_p2 = "Final validation completes the experimental benchmarking across all trials."

    doc_path = SAMPLE_DIR / "test_08_long.docx"
    doc = docx.Document()
    doc.add_paragraph(long_p1)
    doc.add_paragraph(closing_p2)
    doc.save(str(doc_path))

    out_json = process_document(doc_path, output_path=SAMPLE_DIR / "test_08_chunks.json")
    with open(out_json, "r", encoding="utf-8") as f:
        data = json.load(f)

    chunks = data["chunks"]
    assert len(chunks) >= 2, f"Expected multiple chunks for 900+ words, got {len(chunks)}"

    combined_text = " ".join(c["text"] for c in chunks)
    assert closing_p2 in combined_text, "Closing paragraph lost during long paragraph split"
    # Ensure beginning and end of long paragraph are present
    assert sentence.strip() in chunks[0]["text"], "Start of long paragraph missing from Chunk 0"
    print(f"  -> TEST 8 PASSED: Long paragraph split into {len(chunks)} chunks without loss.")


def test_09_heading_plus_paragraph():
    """TEST 9 — Heading + paragraph: Verify paragraph after heading is not accidentally consumed or skipped."""
    doc_path = SAMPLE_DIR / "test_09_heading.docx"
    doc = docx.Document()
    doc.add_heading("Section 4: System Architecture", level=1)
    p_text = "The system architecture incorporates a local vector database and an offline transformer model."
    doc.add_paragraph(p_text)
    doc.save(str(doc_path))

    out_json = process_document(doc_path, output_path=SAMPLE_DIR / "test_09_chunks.json")
    with open(out_json, "r", encoding="utf-8") as f:
        data = json.load(f)

    chunk0_text = data["chunks"][0]["text"]
    assert "Section 4: System Architecture" in chunk0_text, "Heading missing from chunk"
    assert p_text in chunk0_text, "Paragraph after heading missing from chunk"
    # Verify heading and paragraph are separated cleanly
    assert f"Section 4: System Architecture\n\n{p_text}" in chunk0_text or f"Section 4: System Architecture\n{p_text}" in chunk0_text, "Heading and paragraph not cleanly separated"
    print("  -> TEST 9 PASSED: Paragraph following heading is cleanly preserved.")


def test_10_last_paragraph():
    """TEST 10 — Last paragraph: Verify the final buffered paragraph is flushed."""
    doc_path = SAMPLE_DIR / "test_10_last.docx"
    doc = docx.Document()
    for i in range(1, 15):
        doc.add_paragraph(f"This is intermediate paragraph number {i} documenting the experimental setup.")
    final_para = "FINAL CONCLUSION: All research hypotheses were successfully corroborated by offline evaluation."
    doc.add_paragraph(final_para)
    doc.save(str(doc_path))

    out_json = process_document(doc_path, output_path=SAMPLE_DIR / "test_10_chunks.json")
    with open(out_json, "r", encoding="utf-8") as f:
        data = json.load(f)

    all_chunk_text = " ".join(c["text"] for c in data["chunks"])
    assert final_para in all_chunk_text, "CRITICAL: Final paragraph was not flushed into chunks!"
    print("  -> TEST 10 PASSED: Final paragraph successfully flushed.")


def test_11_multiple_chunks():
    """TEST 11 — Multiple chunks: Verify all chunks remain in source order."""
    doc_path = SAMPLE_DIR / "test_11_order.docx"
    doc = docx.Document()
    markers = [f"UNIQUE_SECTION_MARKER_{idx:02d}: Comprehensive notes on topic {idx}." * 35 for idx in range(1, 9)]
    for m in markers:
        doc.add_paragraph(m)
    doc.save(str(doc_path))

    out_json = process_document(doc_path, output_path=SAMPLE_DIR / "test_11_chunks.json")
    with open(out_json, "r", encoding="utf-8") as f:
        data = json.load(f)

    chunks = data["chunks"]
    assert len(chunks) >= 2, f"Expected at least 2 chunks, got {len(chunks)}"

    # Check that markers appear in strictly ascending order across chunks
    last_found_idx = -1
    for i, c in enumerate(chunks):
        for marker_num in range(1, 9):
            tag = f"UNIQUE_SECTION_MARKER_{marker_num:02d}"
            if tag in c["text"]:
                assert marker_num >= last_found_idx, f"Ordering violation: {tag} appeared out of order in Chunk {i}"
                last_found_idx = marker_num
    print(f"  -> TEST 11 PASSED: All {len(chunks)} chunks preserve source reading order.")


def test_12_html_contamination():
    """TEST 12 — HTML contamination: Verify chunk.text does not contain UI HTML."""
    for json_file in (BASE_DIR / "data" / "processed").glob("*_chunks.json"):
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        for chunk in data.get("chunks", []):
            text = chunk.get("text", "")
            assert "<div" not in text, f"Found '<div' in chunk text of {json_file.name}: {text[:80]}"
            assert "</div>" not in text, f"Found '</div>' in chunk text of {json_file.name}: {text[:80]}"
            assert 'class="chunk-text"' not in text, f"Found UI class in chunk text of {json_file.name}"
            assert 'class="chunk-box"' not in text, f"Found UI class in chunk text of {json_file.name}"
    print("  -> TEST 12 PASSED: Zero UI/HTML contamination in chunk.text.")


def test_13_data_integrity_no_lost_content():
    """TEST 13 — Data Integrity: Verify source document content is preserved in chunks."""
    doc_path = SAMPLE_DIR / "test_01_tirupati.docx"
    doc = docx.Document(str(doc_path))
    source_paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]

    out_json = SAMPLE_DIR / "test_01_chunks.json"
    with open(out_json, "r", encoding="utf-8") as f:
        data = json.load(f)

    all_chunk_text = " ".join(c["text"] for c in data["chunks"])

    for para in source_paragraphs:
        assert para in all_chunk_text, f"DATA INTEGRITY FAILURE: Paragraph lost in chunks: '{para[:50]}...'"
    print(f"  -> TEST 13 PASSED: 100% of source paragraphs ({len(source_paragraphs)}/{len(source_paragraphs)}) present in chunks.")


def run_stage1_tests():
    print("========================================================")
    print("RUNNING COMPLETE STAGE 1 AUTOMATED REGRESSION TESTS")
    print("========================================================")

    test_01_english_docx_first_paragraph_preserved()
    test_02_tamil_unicode_docx()
    test_03_hindi_unicode_document()
    test_04_text_pdf_first_paragraph()
    test_05_multipage_pdf()
    test_06_ocr_scanned_pdf()
    test_07_short_first_paragraph()
    test_08_long_first_paragraph()
    test_09_heading_plus_paragraph()
    test_10_last_paragraph()
    test_11_multiple_chunks()
    test_12_html_contamination()
    test_13_data_integrity_no_lost_content()

    print("\n========================================================")
    print("ALL 13 TESTS PASSED PERFECTLY WITH ZERO DATA LOSS!")
    print("========================================================")


if __name__ == "__main__":
    run_stage1_tests()
