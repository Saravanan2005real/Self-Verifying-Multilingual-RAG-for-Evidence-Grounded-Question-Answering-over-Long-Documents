import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
import numpy as np
import faiss

from src.config import INDEX_DIR, EMBEDDING_DIM
from src.embeddings import MultilingualEmbedder, get_default_embedder

logger = logging.getLogger(__name__)


class FAISSVectorStore:
    """
    FAISS-based vector index for semantic retrieval over multilingual document chunks.
    Uses IndexFlatIP with L2-normalized float32 vectors for exact cosine similarity search.
    Preserves all chunk metadata and original chunk texts with 100% fidelity.
    Supports cross-lingual querying across English, Tamil, Hindi, and 50+ languages.
    """

    def __init__(
        self,
        embedder: Optional[MultilingualEmbedder] = None,
        dimension: Optional[int] = None
    ):
        self.embedder = embedder or get_default_embedder()
        self.dimension = dimension or self.embedder.get_dimension()
        self.index: Optional[faiss.IndexFlatIP] = None
        self.chunks: List[Dict[str, Any]] = []

    def build_from_chunks(
        self,
        chunks: List[Union[Dict[str, Any], Any]],
        batch_size: int = 32
    ) -> int:
        """
        Extract chunk texts, compute multilingual embeddings, and build the FAISS index.
        Preserves original text, metadata, and handles edge cases such as empty chunks,
        missing metadata, and duplicate chunk IDs.
        
        Args:
            chunks: List of DocumentChunk instances, chunk dictionaries, or strings.
            batch_size: Encoding batch size.
            
        Returns:
            Number of indexed chunks.
        """
        if not chunks:
            self.index = faiss.IndexFlatIP(self.dimension)
            self.chunks = []
            logger.info("Initialized empty FAISS index (0 chunks).")
            return 0

        # Standardize chunks into uniform dictionary representations
        standardized_chunks: List[Dict[str, Any]] = []
        texts: List[str] = []
        seen_ids = set()

        for idx, c in enumerate(chunks):
            if c is None:
                continue

            if hasattr(c, "to_dict"):
                c_dict = dict(c.to_dict())
            elif isinstance(c, dict):
                c_dict = dict(c)
            elif hasattr(c, "text"):
                c_dict = {
                    "chunk_id": getattr(c, "chunk_id", f"chunk_{idx}"),
                    "text": getattr(c, "text", ""),
                    "page_number": getattr(c, "page_number", 1),
                    "section": getattr(c, "section", "General"),
                    "language": getattr(c, "language", "unknown"),
                    "metadata": getattr(c, "metadata", {})
                }
            elif isinstance(c, str):
                c_dict = {
                    "chunk_id": f"chunk_{idx}",
                    "text": c,
                    "page_number": 1,
                    "section": "General",
                    "language": "unknown",
                    "metadata": {}
                }
            else:
                c_dict = {
                    "chunk_id": f"chunk_{idx}",
                    "text": str(c),
                    "page_number": 1,
                    "section": "General",
                    "language": "unknown",
                    "metadata": {}
                }

            # Preserve exact text without any modification, trimming, or rewriting
            raw_text = c_dict.get("text", "")
            if not isinstance(raw_text, str):
                raw_text = str(raw_text) if raw_text is not None else ""
            c_dict["text"] = raw_text

            # Handle duplicate or missing chunk IDs
            raw_id = c_dict.get("chunk_id")
            if not raw_id:
                raw_id = f"chunk_{idx}"
            if raw_id in seen_ids:
                dedup_id = f"{raw_id}_dup{idx}"
                logger.warning(f"Duplicate chunk_id '{raw_id}' detected. Disambiguating to '{dedup_id}'.")
                raw_id = dedup_id
            seen_ids.add(raw_id)
            c_dict["chunk_id"] = raw_id

            # Safe fallbacks for missing metadata
            if "page_number" not in c_dict:
                c_dict["page_number"] = c_dict.get("page", 1)
            if "page" not in c_dict:
                c_dict["page"] = c_dict.get("page_number", 1)
            if not c_dict.get("section"):
                c_dict["section"] = "General"
            if not c_dict.get("language"):
                c_dict["language"] = "unknown"
            if not isinstance(c_dict.get("metadata"), dict):
                c_dict["metadata"] = {}

            standardized_chunks.append(c_dict)
            texts.append(raw_text)

        if not standardized_chunks:
            self.index = faiss.IndexFlatIP(self.dimension)
            self.chunks = []
            return 0

        # Generate L2-normalized embeddings via multilingual embedder
        embeddings = self.embedder.embed_texts(texts, batch_size=batch_size)
        if embeddings.shape[1] != self.dimension:
            self.dimension = embeddings.shape[1]

        # Build FAISS IndexFlatIP (exact cosine similarity on L2-normalized vectors)
        self.index = faiss.IndexFlatIP(self.dimension)
        self.index.add(embeddings)
        self.chunks = standardized_chunks

        logger.info(
            f"Successfully built FAISS vector store with {self.index.ntotal} vectors (dim={self.dimension})."
        )
        return self.index.ntotal

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        score_threshold: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve the top-K most relevant chunks for a user search query.
        Accepts queries in English, Tamil, Hindi, or any supported language,
        matching against chunks cross-lingually.
        
        Args:
            query: The user search query string.
            top_k: Maximum number of relevant chunks to return (default: 5).
            score_threshold: Optional minimum cosine similarity score (0.0 to 1.0).
            
        Returns:
            List of result dictionaries containing:
                - chunk_id
                - original chunk text (under 'text' and 'original_text')
                - page (under 'page' and 'page_number')
                - section
                - language
                - similarity score (under 'similarity_score' and 'score')
                - preserved metadata
        """
        # Edge case: empty, whitespace-only, or non-string query
        if query is None or not str(query).strip():
            logger.debug("Empty query passed to retrieve(); returning empty results list.")
            return []

        # Edge case: uninitialized or empty index
        if self.index is None or self.index.ntotal == 0 or not self.chunks:
            logger.warning("retrieve() called on an empty or uninitialized FAISS index.")
            return []

        k = min(int(top_k), self.index.ntotal)
        if k <= 0:
            return []

        # Generate L2-normalized query embedding
        query_vec = self.embedder.embed_query(str(query)).reshape(1, -1)
        scores, indices = self.index.search(query_vec, k)

        results: List[Dict[str, Any]] = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0 or idx >= len(self.chunks):
                continue

            sim_score = float(score)
            if score_threshold is not None and sim_score < score_threshold:
                continue

            chunk_data = self.chunks[idx]
            original_text = chunk_data.get("text", "")
            page_num = chunk_data.get("page_number", chunk_data.get("page", 1))

            result = {
                # Required core fields
                "chunk_id": chunk_data.get("chunk_id", f"chunk_{idx}"),
                "text": original_text,
                "original_text": original_text,
                "page": page_num,
                "page_number": page_num,
                "section": chunk_data.get("section", "General"),
                "language": chunk_data.get("language", "unknown"),
                "similarity_score": round(sim_score, 4),
                "score": round(sim_score, 4),
                # Metadata & context preservation
                "document_name": chunk_data.get("document_name", ""),
                "chunk_index": chunk_data.get("chunk_index", idx),
                "word_count": chunk_data.get("word_count", len(original_text.split())),
                "char_count": chunk_data.get("char_count", len(original_text)),
                "char_start": chunk_data.get("char_start", 0),
                "char_end": chunk_data.get("char_end", 0),
                "source_type": chunk_data.get("source_type", ""),
                "ocr_applied": chunk_data.get("ocr_applied", False),
                "metadata": dict(chunk_data.get("metadata", {})),
            }
            results.append(result)

        return results

    def search(
        self,
        query: str,
        top_k: int = 5,
        score_threshold: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """Alias for retrieve() to ensure backward compatibility."""
        return self.retrieve(query=query, top_k=top_k, score_threshold=score_threshold)

    def save(
        self,
        index_path: Union[str, Path],
        metadata_path: Optional[Union[str, Path]] = None
    ) -> None:
        """
        Persist the FAISS binary index and chunk metadata JSON to disk.
        """
        if self.index is None:
            raise ValueError("Cannot save an uninitialized FAISS index.")

        idx_p = Path(index_path).resolve()
        idx_p.parent.mkdir(parents=True, exist_ok=True)

        try:
            faiss.write_index(self.index, str(idx_p))
        except Exception as e:
            raise RuntimeError(f"Failed to write FAISS index to {idx_p}: {e}") from e

        if metadata_path is None:
            meta_p = idx_p.with_suffix(".json")
        else:
            meta_p = Path(metadata_path).resolve()

        meta_p.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "dimension": self.dimension,
            "total_chunks": len(self.chunks),
            "chunks": self.chunks
        }
        with open(meta_p, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

        logger.info(f"Saved FAISS index to '{idx_p}' and metadata to '{meta_p}'.")

    def load(
        self,
        index_path: Union[str, Path],
        metadata_path: Optional[Union[str, Path]] = None
    ) -> None:
        """
        Load a saved FAISS index and chunk metadata from disk.
        Handles missing and corrupt file errors gracefully.
        """
        idx_p = Path(index_path).resolve()
        if not idx_p.exists():
            raise FileNotFoundError(f"FAISS index file not found: {idx_p}")

        if metadata_path is None:
            meta_p = idx_p.with_suffix(".json")
        else:
            meta_p = Path(metadata_path).resolve()

        if not meta_p.exists():
            raise FileNotFoundError(f"FAISS metadata JSON file not found: {meta_p}")

        # Load FAISS index with error checking
        try:
            self.index = faiss.read_index(str(idx_p))
            self.dimension = self.index.d
        except Exception as e:
            raise RuntimeError(f"Corrupt or invalid FAISS vector index file: {idx_p} ({e})") from e

        # Load metadata JSON with error checking
        try:
            with open(meta_p, "r", encoding="utf-8") as f:
                meta_data = json.load(f)
        except Exception as e:
            raise RuntimeError(f"Corrupt or invalid FAISS metadata JSON file: {meta_p} ({e})") from e

        self.chunks = meta_data.get("chunks", [])
        logger.info(
            f"Loaded FAISS index from '{idx_p}' ({self.index.ntotal} vectors, {len(self.chunks)} chunks)."
        )

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


# ---------------------------------------------------------------------------
# High-Level Helper Functions
# ---------------------------------------------------------------------------

def build_vector_index(
    chunks: List[Union[Dict[str, Any], Any]],
    embedder: Optional[MultilingualEmbedder] = None,
    batch_size: int = 32
) -> FAISSVectorStore:
    """Build a FAISSVectorStore from a list of chunks."""
    store = FAISSVectorStore(embedder=embedder)
    store.build_from_chunks(chunks, batch_size=batch_size)
    return store


def save_vector_index(
    store: FAISSVectorStore,
    index_path: Union[str, Path],
    metadata_path: Optional[Union[str, Path]] = None
) -> None:
    """Save an initialized FAISSVectorStore to disk."""
    store.save(index_path=index_path, metadata_path=metadata_path)


def load_vector_index(
    index_path: Union[str, Path],
    metadata_path: Optional[Union[str, Path]] = None,
    embedder: Optional[MultilingualEmbedder] = None
) -> FAISSVectorStore:
    """Load a FAISSVectorStore from disk."""
    return FAISSVectorStore.load_from_disk(
        index_path=index_path,
        metadata_path=metadata_path,
        embedder=embedder
    )


def retrieve(
    query: str,
    top_k: int = 5,
    vector_store: Optional[FAISSVectorStore] = None,
    index_path: Optional[Union[str, Path]] = None,
    metadata_path: Optional[Union[str, Path]] = None
) -> List[Dict[str, Any]]:
    """
    Top-level retrieval function:
    retrieve(query, top_k=5)
    
    Accepts a query and returns the top_k most relevant chunks.
    If vector_store is provided, searches that store.
    Otherwise, if index_path is provided, loads and searches it.
    """
    if vector_store is not None:
        return vector_store.retrieve(query=query, top_k=top_k)

    if index_path is not None:
        store = load_vector_index(index_path=index_path, metadata_path=metadata_path)
        return store.retrieve(query=query, top_k=top_k)

    # Attempt to locate the latest index from INDEX_DIR
    idx_dir = Path(INDEX_DIR)
    index_files = sorted(idx_dir.glob("*.index"), key=lambda p: p.stat().st_mtime, reverse=True)
    if index_files:
        store = load_vector_index(index_path=index_files[0])
        return store.retrieve(query=query, top_k=top_k)

    logger.warning("retrieve() called without an active vector store or existing index file.")
    return []


def build_index_from_processed_json(
    json_path: Union[str, Path],
    save_dir: Optional[Union[str, Path]] = None,
    embedder: Optional[MultilingualEmbedder] = None,
    batch_size: int = 32
) -> FAISSVectorStore:
    """
    Load chunks from a processed JSON file (e.g. data/processed/*_chunks.json),
    build the FAISS index, and persist it to disk.
    
    Returns:
        The built and saved FAISSVectorStore instance.
    """
    path = Path(json_path).resolve()
    if not path.exists():
        raise FileNotFoundError(f"Processed chunks JSON not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    chunks = data.get("chunks", [])
    store = FAISSVectorStore(embedder=embedder)
    store.build_from_chunks(chunks, batch_size=batch_size)

    # Determine save destination
    out_dir = Path(save_dir).resolve() if save_dir else Path(INDEX_DIR).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    idx_file = out_dir / f"{path.stem}.index"
    meta_file = out_dir / f"{path.stem}.json"
    store.save(index_path=idx_file, metadata_path=meta_file)

    logger.info(f"Built and saved index for '{path.name}' to '{idx_file}'.")
    return store
