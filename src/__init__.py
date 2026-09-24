"""
Multilingual Self-Verifying RAG Package - Stage 1
"""
__version__ = "0.1.0"

from src.ocr import is_ocr_available, is_tesseract_available, extract_text_from_image, get_ocr_engine_name
from src.document_loader import DocumentLoader, DocumentPage
from src.chunking import MeaningfulSemanticChunker, IntelligentChunker, DocumentChunk
from src.embeddings import MultilingualEmbedder, embed_text, embed_chunks, embed_query
from src.vector_store import FAISSVectorStore, retrieve, build_vector_index, load_vector_index, save_vector_index

