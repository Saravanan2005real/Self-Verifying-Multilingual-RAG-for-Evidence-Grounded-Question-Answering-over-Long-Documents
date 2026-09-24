import sys
import shutil
from pathlib import Path
import pytest
import numpy as np

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.embeddings import MultilingualEmbedder
from src.vector_store import FAISSVectorStore
from src.chunking import DocumentChunk

TEST_INDEX_DIR = BASE_DIR / "tests" / "test_indices"
TEST_INDEX_DIR.mkdir(parents=True, exist_ok=True)


@pytest.fixture(scope="module")
def embedder():
    """Shared MultilingualEmbedder instance for tests."""
    return MultilingualEmbedder()


def test_01_multilingual_embedder_dimension_and_normalization(embedder):
    """Verify embedder produces vectors with correct dimension and unit L2 norm."""
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


def test_02_vector_store_build_and_metadata_preservation(embedder):
    """Verify FAISSVectorStore builds correctly and preserves 100% of chunk metadata."""
    store = FAISSVectorStore(embedder=embedder)

    chunks = [
        {
            "chunk_id": "doc1_c0",
            "document_name": "doc1.docx",
            "page_number": 1,
            "section": "Introduction",
            "chunk_index": 0,
            "text": "This study analyzes surface water bodies in Tirupati using Google Earth Engine.",
            "word_count": 12,
            "char_count": 79,
            "char_start": 0,
            "char_end": 79,
            "language": "en",
            "source_type": "docx",
            "ocr_applied": False,
            "metadata": {"custom_tag": "research_intro"}
        },
        {
            "chunk_id": "doc1_c1",
            "document_name": "doc1.docx",
            "page_number": 2,
            "section": "Methodology",
            "chunk_index": 1,
            "text": "Convolutional filtering and Normalized Difference Water Index (NDWI) are computed.",
            "word_count": 11,
            "char_count": 82,
            "char_start": 81,
            "char_end": 163,
            "language": "en",
            "source_type": "docx",
            "ocr_applied": False,
            "metadata": {"custom_tag": "method"}
        }
    ]

    total = store.build_from_chunks(chunks)
    assert total == 2
    assert store.index.ntotal == 2

    # Query matching introduction
    results = store.search("surface water in Tirupati", top_k=2)
    assert len(results) == 2

    top = results[0]
    assert top["chunk_id"] == "doc1_c0"
    assert top["page_number"] == 1
    assert top["section"] == "Introduction"
    assert top["language"] == "en"
    assert "Tirupati" in top["text"]
    assert isinstance(top["score"], float)
    assert top["score"] > 0.5
    assert top["metadata"]["custom_tag"] == "research_intro"


def test_03_cross_lingual_retrieval_hindi(embedder):
    """Verify that a Hindi query can accurately retrieve relevant English content."""
    store = FAISSVectorStore(embedder=embedder)

    chunks = [
        {
            "chunk_id": "water_en",
            "document_name": "survey.docx",
            "page_number": 1,
            "section": "Water Bodies",
            "text": "Monitoring lakes, reservoirs, and water bodies using satellite imagery.",
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
    results = store.search("जल निकाय और झीलें", top_k=2)
    assert len(results) >= 1
    assert results[0]["chunk_id"] == "water_en"
    assert results[0]["score"] > results[1]["score"]


def test_04_cross_lingual_retrieval_tamil(embedder):
    """Verify that a Tamil query can accurately retrieve relevant English content."""
    store = FAISSVectorStore(embedder=embedder)

    chunks = [
        {
            "chunk_id": "satellite_en",
            "document_name": "remote_sensing.docx",
            "page_number": 3,
            "section": "Satellites",
            "text": "Sentinel-2 satellite multispectral bands and orbit details.",
            "language": "en"
        },
        {
            "chunk_id": "database_en",
            "document_name": "db.docx",
            "page_number": 1,
            "section": "Databases",
            "text": "Relational database management systems and SQL queries.",
            "language": "en"
        }
    ]

    store.build_from_chunks(chunks)

    # Tamil query: "செயற்கைக்கோள் படங்கள்" (Satellite images)
    results = store.search("செயற்கைக்கோள் படங்கள்", top_k=2)
    assert len(results) >= 1
    assert results[0]["chunk_id"] == "satellite_en"
    assert results[0]["score"] > results[1]["score"]


def test_05_score_threshold_and_top_k(embedder):
    """Verify top_k limiting and score_threshold filtering."""
    store = FAISSVectorStore(embedder=embedder)

    chunks = [
        {"chunk_id": f"chunk_{i}", "text": f"Information topic number {i} regarding machine learning.", "language": "en"}
        for i in range(10)
    ]
    store.build_from_chunks(chunks)

    # top_k = 3
    results = store.search("machine learning", top_k=3)
    assert len(results) == 3

    # High threshold should filter out less relevant or all if impossible
    strict_results = store.search("machine learning", top_k=10, score_threshold=0.999)
    assert len(strict_results) <= len(results)


def test_06_persistence_save_and_load(embedder):
    """Verify that FAISS vector index and metadata can be saved and loaded with identical search results."""
    store = FAISSVectorStore(embedder=embedder)

    chunks = [
        {"chunk_id": "c1", "text": "Deep learning architectures for image classification.", "page_number": 1, "section": "AI", "language": "en"},
        {"chunk_id": "c2", "text": "Soil erosion and land surface temperature analysis.", "page_number": 2, "section": "Geology", "language": "en"}
    ]
    store.build_from_chunks(chunks)

    idx_file = TEST_INDEX_DIR / "test_store.index"
    meta_file = TEST_INDEX_DIR / "test_store.json"

    store.save(idx_file, meta_file)
    assert idx_file.exists()
    assert meta_file.exists()

    # Load into new store instance
    loaded_store = FAISSVectorStore.load_from_disk(idx_file, meta_file, embedder=embedder)
    assert loaded_store.index.ntotal == 2
    assert len(loaded_store.chunks) == 2

    # Query both and verify identical results
    orig_res = store.search("image classification", top_k=2)
    loaded_res = loaded_store.search("image classification", top_k=2)

    assert len(orig_res) == len(loaded_res)
    assert orig_res[0]["chunk_id"] == loaded_res[0]["chunk_id"]
    assert abs(orig_res[0]["score"] - loaded_res[0]["score"]) < 1e-4

    # Cleanup test files
    if idx_file.exists():
        idx_file.unlink()
    if meta_file.exists():
        meta_file.unlink()


def test_07_empty_chunks_edge_case(embedder):
    """Verify graceful handling when building index with empty chunk list."""
    store = FAISSVectorStore(embedder=embedder)
    count = store.build_from_chunks([])
    assert count == 0
    results = store.search("test query", top_k=5)
    assert results == []
