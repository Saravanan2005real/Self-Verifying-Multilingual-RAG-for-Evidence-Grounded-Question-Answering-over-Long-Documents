import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
import numpy as np
import faiss

from src.config import INDEX_DIR, EMBEDDING_DIM
from src.embeddings import MultilingualEmbedder
from src.chunking import DocumentChunk

logger = logging.getLogger(__name__)


class FAISSVectorStore:
    """
    FAISS-based vector index for semantic retrieval over multilingual document chunks.
    Uses IndexFlatIP with L2-normalized vectors for exact cosine similarity search.
    Preserves all chunk metadata and supports cross-lingual querying across English,
    Tamil, Hindi, and other languages.
    """

    def __init__(
        self,
        embedder: Optional[MultilingualEmbedder] = None,
        dimension: Optional[int] = None
    ):
        self.embedder = embedder or MultilingualEmbedder()
        self.dimension = dimension or self.embedder.get_dimension()
        self.index: Optional[faiss.IndexFlatIP] = None
        self.chunks: List[Dict[str, Any]] = []

    def build_from_chunks(
        self,
        chunks: List[Union[Dict[str, Any], DocumentChunk]],
        batch_size: int = 32
    ) -> int:
        """
        Extract chunk texts, compute multilingual embeddings, and build the FAISS index.
        
        Args:
            chunks: List of DocumentChunk instances or chunk dictionaries.
            batch_size: Encoding batch size.
            
        Returns:
            Number of indexed chunks.
        """
        if not chunks:
            self.index = faiss.IndexFlatIP(self.dimension)
            self.chunks = []
            return 0

        # Standardize chunks into uniform dictionary representation
        standardized_chunks: List[Dict[str, Any]] = []
        texts: List[str] = []

        for c in chunks:
            if hasattr(c, "to_dict"):
                c_dict = c.to_dict()
            elif isinstance(c, dict):
                c_dict = dict(c)
            else:
                raise TypeError(f"Unsupported chunk type: {type(c)}")

            standardized_chunks.append(c_dict)
            texts.append(c_dict.get("text", ""))

        # Generate L2-normalized embeddings
        embeddings = self.embedder.embed_texts(texts, batch_size=batch_size)
        if embeddings.shape[1] != self.dimension:
            self.dimension = embeddings.shape[1]

        # Build FAISS IndexFlatIP (cosine similarity on L2-normalized vectors)
        self.index = faiss.IndexFlatIP(self.dimension)
        self.index.add(embeddings)
        self.chunks = standardized_chunks

        logger.info(f"Successfully built FAISS vector store with {self.index.ntotal} vectors (dim={self.dimension}).")
        return self.index.ntotal

    def search(
        self,
        query: str,
        top_k: int = 5,
        score_threshold: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        Perform semantic search against the FAISS index.
        
        Args:
            query: The search query in any supported language (cross-lingual).
            top_k: Maximum number of nearest chunk results to return.
            score_threshold: Optional minimum cosine similarity score (0.0 to 1.0).
            
        Returns:
            List of result dictionaries containing chunk ID, text, page, section,
            language, and similarity score.
        """
        if self.index is None or self.index.ntotal == 0:
            return []

        k = min(top_k, self.index.ntotal)
        if k <= 0:
            return []

        query_vec = self.embedder.embed_query(query).reshape(1, -1)
        scores, indices = self.index.search(query_vec, k)

        results: List[Dict[str, Any]] = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0 or idx >= len(self.chunks):
                continue

            sim_score = float(score)
            if score_threshold is not None and sim_score < score_threshold:
                continue

            chunk_data = self.chunks[idx]
            result = {
                "chunk_id": chunk_data.get("chunk_id", f"chunk_{idx}"),
                "text": chunk_data.get("text", ""),
                "page_number": chunk_data.get("page_number", 1),
                "section": chunk_data.get("section"),
                "language": chunk_data.get("language", "unknown"),
                "score": round(sim_score, 4),
                "document_name": chunk_data.get("document_name", ""),
                "word_count": chunk_data.get("word_count", 0),
                "char_count": chunk_data.get("char_count", 0),
                "char_start": chunk_data.get("char_start", 0),
                "char_end": chunk_data.get("char_end", 0),
                "metadata": chunk_data.get("metadata", {}),
            }
            results.append(result)

        return results

    def save(
        self,
        index_path: Union[str, Path],
        metadata_path: Optional[Union[str, Path]] = None
    ) -> None:
        """
        Persist the FAISS binary index and chunk metadata JSON to disk.
        """
        if self.index is None:
            raise ValueError("Cannot save an empty or uninitialized FAISS index.")

        idx_p = Path(index_path)
        idx_p.parent.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self.index, str(idx_p))

        if metadata_path is None:
            meta_p = idx_p.with_suffix(".json")
        else:
            meta_p = Path(metadata_path)

        meta_p.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "dimension": self.dimension,
            "total_chunks": len(self.chunks),
            "chunks": self.chunks
        }
        with open(meta_p, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

        logger.info(f"Saved FAISS index to {idx_p} and metadata to {meta_p}")

    def load(
        self,
        index_path: Union[str, Path],
        metadata_path: Optional[Union[str, Path]] = None
    ) -> None:
        """
        Load a saved FAISS index and chunk metadata from disk.
        """
        idx_p = Path(index_path)
        if not idx_p.exists():
            raise FileNotFoundError(f"FAISS index file not found: {idx_p}")

        if metadata_path is None:
            meta_p = idx_p.with_suffix(".json")
        else:
            meta_p = Path(metadata_path)

        if not meta_p.exists():
            raise FileNotFoundError(f"FAISS metadata file not found: {meta_p}")

        self.index = faiss.read_index(str(idx_p))
        self.dimension = self.index.d

        with open(meta_p, "r", encoding="utf-8") as f:
            meta_data = json.load(f)

        self.chunks = meta_data.get("chunks", [])
        logger.info(f"Loaded FAISS index from {idx_p} ({self.index.ntotal} vectors, {len(self.chunks)} chunks).")

    @classmethod
    def load_from_disk(
        cls,
        index_path: Union[str, Path],
        metadata_path: Optional[Union[str, Path]] = None,
        embedder: Optional[MultilingualEmbedder] = None
    ) -> "FAISSVectorStore":
        """Factory method to instantiate and load a vector store in one call."""
        store = cls(embedder=embedder)
        store.load(index_path=index_path, metadata_path=metadata_path)
        return store
