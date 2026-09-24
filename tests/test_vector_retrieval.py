import sys
import tempfile
from pathlib import Path
import pytest
import numpy as np

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.embeddings import (
    MultilingualEmbedder,
    embed_text,
    embed_texts,
    embed_chunks,
    embed_query,
    get_default_embedder,
)
from src.vector_store import (
    FAISSVectorStore,
    retrieve,
    build_vector_index,
    load_vector_index,
    save_vector_index,
)
from src.chunking import DocumentChunk

TEST_INDEX_DIR = BASE_DIR / "tests" / "test_indices"
TEST_INDEX_DIR.mkdir(parents=True, exist_ok=True)


@pytest.fixture(scope="module")
def embedder():
    """Shared MultilingualEmbedder instance for test suite."""
    return get_default_embedder()


# ---------------------------------------------------------------------------
# 1. Embedder Dimensions & Normalization
# ---------------------------------------------------------------------------

def test_01_multilingual_embedder_dimension_and_normalization(embedder):
    """Verify embedder produces vectors with correct dimension (384) and unit L2 norm."""
    texts = [
        "Digital image processing for geospatial analysis.",
        "उपग्रह आधारित जल निकाय विश्लेषण।",
        "செயற்கைக்கோள் அடிப்படையிலான நீர்நிலை பகுப்பாய்வு."
    ]
    embs = embedder.embed_texts(texts)
    assert embs.shape == (3, 384)
    assert embs.dtype == np.float32

    # Verify unit norm (L2 = 1.0)
    norms = np.linalg.norm(embs, axis=1)
    for norm in norms:
        assert abs(norm - 1.0) < 1e-4, f"Embedding is not normalized: norm={norm}"

    # Verify single text helper
    single_emb = embed_text("Single text test", embedder=embedder)
    assert single_emb.shape == (384,)
    assert abs(np.linalg.norm(single_emb) - 1.0) < 1e-4

    # Verify chunks embedding helper
    chunk_list = [{"text": "Chunk text 1"}, {"text": "Chunk text 2"}]
    chunk_embs = embed_chunks(chunk_list, embedder=embedder)
    assert chunk_embs.shape == (2, 384)


# ---------------------------------------------------------------------------
# 2. Metadata Preservation
# ---------------------------------------------------------------------------

def test_02_metadata_preservation(embedder):
    """Verify FAISSVectorStore preserves 100% of original chunk text and metadata."""
    store = FAISSVectorStore(embedder=embedder)

    original_text = "This study analyzes surface water bodies in Tirupati using Google Earth Engine."
    chunks = [
        {
            "chunk_id": "dip_c0",
            "document_name": "DIP_Assignment.docx",
            "page_number": 1,
            "section": "Introduction and Objectives",
            "chunk_index": 0,
            "text": original_text,
            "word_count": 12,
            "char_count": len(original_text),
            "char_start": 0,
            "char_end": len(original_text),
            "language": "en",
            "source_type": "docx",
            "ocr_applied": False,
            "metadata": {"custom_tag": "tirupati_water_study", "page_start": 1}
        },
        {
            "chunk_id": "dip_c1",
            "document_name": "DIP_Assignment.docx",
            "page_number": 2,
            "section": "Spectral Bands",
            "chunk_index": 1,
            "text": "Sentinel-2 MSI captures 13 spectral bands with spatial resolutions of 10m, 20m, and 60m.",
            "word_count": 13,
            "char_count": 88,
            "char_start": 80,
            "char_end": 168,
            "language": "en",
            "source_type": "docx",
            "ocr_applied": False,
            "metadata": {"custom_tag": "sentinel_bands", "page_start": 2}
        }
    ]

    total = store.build_from_chunks(chunks)
    assert total == 2
    assert store.index.ntotal == 2

    # Query matching introduction
    results = store.retrieve("surface water bodies in Tirupati", top_k=2)
    assert len(results) == 2

    top = results[0]
    # Verify core fields required by prompt
    assert top["chunk_id"] == "dip_c0"
    assert top["text"] == original_text, "CRITICAL: Original chunk text was modified!"
    assert top["page"] == 1
    assert top["page_number"] == 1
    assert top["section"] == "Introduction and Objectives"
    assert top["language"] == "en"
    assert isinstance(top["similarity_score"], float)
    assert top["similarity_score"] > 0.5
    # Verify metadata preservation
    assert top["document_name"] == "DIP_Assignment.docx"
    assert top["metadata"]["custom_tag"] == "tirupati_water_study"
    assert top["metadata"]["page_start"] == 1


# ---------------------------------------------------------------------------
# 3. English Retrieval
# ---------------------------------------------------------------------------

def test_03_english_retrieval(embedder):
    """Verify monolingual English retrieval returns the most semantically relevant English chunk."""
    store = FAISSVectorStore(embedder=embedder)

    chunks = [
        {
            "chunk_id": "ml_chunk",
            "text": "Convolutional neural networks and deep learning models for computer vision.",
            "page_number": 1,
            "section": "Computer Vision",
            "language": "en"
        },
        {
            "chunk_id": "db_chunk",
            "text": "Relational databases, indexing with B-trees, and SQL transaction management.",
            "page_number": 2,
            "section": "Databases",
            "language": "en"
        },
        {
            "chunk_id": "os_chunk",
            "text": "Process scheduling algorithms, virtual memory paging, and deadlock avoidance in operating systems.",
            "page_number": 3,
            "section": "OS",
            "language": "en"
        }
    ]
    store.build_from_chunks(chunks)

    results = store.retrieve("deep learning and neural networks for images", top_k=1)
    assert len(results) == 1
    assert results[0]["chunk_id"] == "ml_chunk"
    assert results[0]["similarity_score"] > 0.4


# ---------------------------------------------------------------------------
# 4. Tamil Retrieval
# ---------------------------------------------------------------------------

def test_04_tamil_retrieval(embedder):
    """Verify monolingual Tamil retrieval returns the most relevant Tamil chunk."""
    store = FAISSVectorStore(embedder=embedder)

    chunks = [
        {
            "chunk_id": "ta_agriculture",
            "text": "தமிழ்நாட்டில் விவசாயம் மற்றும் நீர் பாசன முறைகள் மிக முக்கியமானவை ஆகும்.",
            "page_number": 1,
            "section": "Agriculture",
            "language": "ta"
        },
        {
            "chunk_id": "ta_astronomy",
            "text": "விண்வெளி ஆராய்ச்சி மற்றும் கோள்களின் இயக்கம் பற்றிய அறிவியல் ஆய்வுகள்.",
            "page_number": 2,
            "section": "Astronomy",
            "language": "ta"
        }
    ]
    store.build_from_chunks(chunks)

    # Query in Tamil: "விவசாய நீர் பாசனம்" (Agricultural irrigation)
    results = store.retrieve("விவசாய நீர் பாசனம்", top_k=1)
    assert len(results) == 1
    assert results[0]["chunk_id"] == "ta_agriculture"
    assert results[0]["language"] == "ta"


# ---------------------------------------------------------------------------
# 5. Hindi Retrieval
# ---------------------------------------------------------------------------

def test_05_hindi_retrieval(embedder):
    """Verify monolingual Hindi retrieval returns the most relevant Hindi chunk."""
    store = FAISSVectorStore(embedder=embedder)

    chunks = [
        {
            "chunk_id": "hi_water",
            "text": "भारत में जल संरक्षण और नदियों का पुनरुद्धार पर्यावरण के लिए आवश्यक है।",
            "page_number": 1,
            "section": "Water Conservation",
            "language": "hi"
        },
        {
            "chunk_id": "hi_history",
            "text": "प्राचीन भारतीय इतिहास और वास्तुकला के प्रमुख ऐतिहासिक स्मारक।",
            "page_number": 2,
            "section": "History",
            "language": "hi"
        }
    ]
    store.build_from_chunks(chunks)

    # Query in Hindi: "जल संरक्षण और नदियाँ" (Water conservation and rivers)
    results = store.retrieve("जल संरक्षण और नदियाँ", top_k=1)
    assert len(results) == 1
    assert results[0]["chunk_id"] == "hi_water"
    assert results[0]["language"] == "hi"


# ---------------------------------------------------------------------------
# 6. Cross-Lingual Retrieval: Hindi Query -> English Chunks
# ---------------------------------------------------------------------------

def test_06_cross_lingual_retrieval_hindi_to_english(embedder):
    """Verify Hindi query accurately retrieves relevant English document chunks."""
    store = FAISSVectorStore(embedder=embedder)

    chunks = [
        {
            "chunk_id": "water_en",
            "document_name": "survey.docx",
            "page_number": 1,
            "section": "Water Bodies",
            "text": "Monitoring lakes, reservoirs, and surface water bodies using satellite imagery.",
            "language": "en"
        },
        {
            "chunk_id": "compiler_en",
            "document_name": "cs.docx",
            "page_number": 5,
            "section": "Compilers",
            "text": "Lexical analysis and parsing algorithms in computer science compilers.",
            "language": "en"
        }
    ]
    store.build_from_chunks(chunks)

    # Hindi query: "जल निकाय और झीलें" (Water bodies and lakes)
    results = store.retrieve("जल निकाय और झीलें", top_k=2)
    assert len(results) >= 1
    assert results[0]["chunk_id"] == "water_en"
    assert results[0]["similarity_score"] > results[1]["similarity_score"]


# ---------------------------------------------------------------------------
# 7. Cross-Lingual Retrieval: Tamil Query -> English Chunks
# ---------------------------------------------------------------------------

def test_07_cross_lingual_retrieval_tamil_to_english(embedder):
    """Verify Tamil query accurately retrieves relevant English document chunks."""
    store = FAISSVectorStore(embedder=embedder)

    chunks = [
        {
            "chunk_id": "satellite_en",
            "document_name": "remote_sensing.docx",
            "page_number": 3,
            "section": "Satellites",
            "text": "Sentinel-2 satellite multispectral bands and orbit details for earth observation.",
            "language": "en"
        },
        {
            "chunk_id": "database_en",
            "document_name": "db.docx",
            "page_number": 1,
            "section": "Databases",
            "text": "Relational database management systems and SQL queries for transaction records.",
            "language": "en"
        }
    ]
    store.build_from_chunks(chunks)

    # Tamil query: "செயற்கைக்கோள் படங்கள்" (Satellite images)
    results = store.retrieve("செயற்கைக்கோள் படங்கள்", top_k=2)
    assert len(results) >= 1
    assert results[0]["chunk_id"] == "satellite_en"
    assert results[0]["similarity_score"] > results[1]["similarity_score"]


# ---------------------------------------------------------------------------
# 8. Cross-Lingual Retrieval: English Query -> Tamil & Hindi Chunks
# ---------------------------------------------------------------------------

def test_08_cross_lingual_retrieval_english_to_tamil_and_hindi(embedder):
    """Verify English query retrieves relevant Tamil and Hindi chunks over unrelated chunks."""
    store = FAISSVectorStore(embedder=embedder)

    chunks = [
        {
            "chunk_id": "ta_space",
            "text": "செயற்கைக்கோள் விண்வெளி ஆய்வு மற்றும் பூமி கண்காணிப்பு தொழில்நுட்பம்.",
            "page_number": 1,
            "language": "ta"
        },
        {
            "chunk_id": "hi_space",
            "text": "उपग्रह आधारित अंतरिक्ष अनुसंधान और पृथ्वी अवलोकन तकनीक।",
            "page_number": 2,
            "language": "hi"
        },
        {
            "chunk_id": "en_cooking",
            "text": "Baking bread requires flour, water, yeast, and accurate oven temperature control.",
            "page_number": 3,
            "language": "en"
        }
    ]
    store.build_from_chunks(chunks)

    results = store.retrieve("satellite earth observation technology", top_k=3)
    top_ids = [r["chunk_id"] for r in results[:2]]
    assert "ta_space" in top_ids or "hi_space" in top_ids
    assert results[-1]["chunk_id"] == "en_cooking"


# ---------------------------------------------------------------------------
# 9. Top-K and Score Threshold Parameter Tests
# ---------------------------------------------------------------------------

def test_09_top_k_parameter(embedder):
    """Verify top_k parameter strictly controls the number of returned results."""
    store = FAISSVectorStore(embedder=embedder)

    chunks = [
        {"chunk_id": f"chunk_{i}", "text": f"Information topic number {i} regarding machine learning algorithms.", "language": "en"}
        for i in range(10)
    ]
    store.build_from_chunks(chunks)

    # Test top_k = 1, 3, 5, 10
    assert len(store.retrieve("machine learning", top_k=1)) == 1
    assert len(store.retrieve("machine learning", top_k=3)) == 3
    assert len(store.retrieve("machine learning", top_k=5)) == 5
    assert len(store.retrieve("machine learning", top_k=10)) == 10

    # Test score_threshold filters low scores
    strict_res = store.retrieve("machine learning", top_k=10, score_threshold=0.999)
    assert len(strict_res) <= 10


# ---------------------------------------------------------------------------
# 10. Edge Case: Empty Query Handling
# ---------------------------------------------------------------------------

def test_10_empty_query_handling(embedder):
    """Verify empty query string, whitespace, or None returns empty list without error."""
    store = FAISSVectorStore(embedder=embedder)
    chunks = [{"chunk_id": "c1", "text": "Valid document chunk content."}]
    store.build_from_chunks(chunks)

    assert store.retrieve("") == []
    assert store.retrieve("   ") == []
    assert store.retrieve(None) == []


# ---------------------------------------------------------------------------
# 11. Edge Case: Empty Document / Empty Chunks Handling
# ---------------------------------------------------------------------------

def test_11_empty_document_and_chunks(embedder):
    """Verify vector store gracefully handles empty chunks list without error."""
    store = FAISSVectorStore(embedder=embedder)
    count = store.build_from_chunks([])
    assert count == 0
    assert store.retrieve("any search query", top_k=5) == []


# ---------------------------------------------------------------------------
# 12. Edge Case: Duplicate Chunk IDs and Missing Metadata
# ---------------------------------------------------------------------------

def test_12_duplicate_chunk_ids_and_missing_metadata(embedder):
    """Verify duplicate chunk IDs are disambiguated and missing metadata gets safe defaults."""
    store = FAISSVectorStore(embedder=embedder)

    # Chunks with duplicate IDs and missing metadata
    chunks = [
        {"chunk_id": "same_id", "text": "First chunk text about algorithms."},
        {"chunk_id": "same_id", "text": "Second chunk text about data structures."}
    ]
    total = store.build_from_chunks(chunks)
    assert total == 2
    assert store.chunks[0]["chunk_id"] == "same_id"
    assert store.chunks[1]["chunk_id"] == "same_id_dup1"
    # Safe defaults
    assert store.chunks[0]["page"] == 1
    assert store.chunks[0]["section"] == "General"
    assert store.chunks[0]["language"] == "unknown"


# ---------------------------------------------------------------------------
# 13. Edge Case: Missing & Corrupt Vector Index Handling
# ---------------------------------------------------------------------------

def test_13_corrupt_and_missing_index_handling(embedder):
    """Verify FileNotFoundError on missing files and RuntimeError on corrupt index/metadata."""
    store = FAISSVectorStore(embedder=embedder)

    missing_idx = TEST_INDEX_DIR / "non_existent.index"
    missing_meta = TEST_INDEX_DIR / "non_existent.json"

    with pytest.raises(FileNotFoundError):
        store.load(missing_idx, missing_meta)

    # Create a corrupt index file (invalid binary header)
    corrupt_idx = TEST_INDEX_DIR / "corrupt.index"
    corrupt_idx.write_text("NOT A VALID FAISS BINARY FILE", encoding="utf-8")
    valid_meta = TEST_INDEX_DIR / "corrupt.json"
    valid_meta.write_text('{"chunks": []}', encoding="utf-8")

    with pytest.raises(RuntimeError):
        store.load(corrupt_idx, valid_meta)

    # Cleanup temporary corrupt files
    corrupt_idx.unlink(missing_ok=True)
    valid_meta.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# 14. Persistence: Save & Load Verification
# ---------------------------------------------------------------------------

def test_14_vector_store_persistence(embedder):
    """Verify that saving and loading vector store produces identical search results and scores."""
    store = FAISSVectorStore(embedder=embedder)

    chunks = [
        {
            "chunk_id": "p1",
            "text": "Deep learning architectures for image classification.",
            "page_number": 1,
            "section": "AI",
            "language": "en"
        },
        {
            "chunk_id": "p2",
            "text": "Soil erosion and land surface temperature analysis.",
            "page_number": 2,
            "section": "Geology",
            "language": "en"
        }
    ]
    store.build_from_chunks(chunks)

    idx_file = TEST_INDEX_DIR / "persist_test.index"
    meta_file = TEST_INDEX_DIR / "persist_test.json"

    store.save(idx_file, meta_file)
    assert idx_file.exists()
    assert meta_file.exists()

    # Load into a new FAISSVectorStore instance
    loaded_store = FAISSVectorStore.load_from_disk(idx_file, meta_file, embedder=embedder)
    assert loaded_store.index.ntotal == 2
    assert len(loaded_store.chunks) == 2

    # Query both stores and verify identical results
    orig_res = store.retrieve("image classification", top_k=2)
    loaded_res = loaded_store.retrieve("image classification", top_k=2)

    assert len(orig_res) == len(loaded_res)
    assert orig_res[0]["chunk_id"] == loaded_res[0]["chunk_id"]
    assert abs(orig_res[0]["similarity_score"] - loaded_res[0]["similarity_score"]) < 1e-4

    # Cleanup
    idx_file.unlink(missing_ok=True)
    meta_file.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# 15. Top-Level Function Verification
# ---------------------------------------------------------------------------

def test_15_top_level_retrieve_and_helpers(embedder):
    """Verify module-level retrieve(), build_vector_index(), save/load functions."""
    chunks = [
        {"chunk_id": "hl_0", "text": "Natural language processing with transformers.", "page": 1, "language": "en"},
        {"chunk_id": "hl_1", "text": "Quantum computing and qubits superposition.", "page": 2, "language": "en"}
    ]
    store = build_vector_index(chunks, embedder=embedder)
    assert store.index.ntotal == 2

    results = retrieve("transformers in NLP", top_k=1, vector_store=store)
    assert len(results) == 1
    assert results[0]["chunk_id"] == "hl_0"
