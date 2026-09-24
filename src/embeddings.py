import logging
from typing import List, Union, Optional, Any, Dict
import numpy as np

from src.config import EMBEDDING_MODEL, EMBEDDING_DIM

logger = logging.getLogger(__name__)

# Global singleton instance for efficient reuse across retrieval calls
_GLOBAL_EMBEDDER: Optional["MultilingualEmbedder"] = None


class MultilingualEmbedder:
    """
    Lightweight multilingual embedding generator supporting English, Tamil, Hindi,
    and 50+ languages using SentenceTransformers.
    Produces L2-normalized float32 vectors for cosine similarity computation via FAISS.
    Runs locally and offline.
    """

    def __init__(
        self,
        model_name: str = EMBEDDING_MODEL,
        device: Optional[str] = None
    ):
        self.model_name = model_name
        self.device = device
        self._model = None
        self._dimension: Optional[int] = None

    @property
    def model(self):
        """Lazy loader for the SentenceTransformer model."""
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                logger.info(f"Loading multilingual embedding model: {self.model_name}")
                self._model = SentenceTransformer(self.model_name, device=self.device)
            except Exception as e:
                logger.error(f"Failed to load embedding model '{self.model_name}': {e}")
                raise RuntimeError(
                    f"Could not load multilingual embedding model '{self.model_name}': {e}"
                ) from e
        return self._model

    def get_dimension(self) -> int:
        """Return the embedding dimension of the underlying model (default: 384)."""
        if self._dimension is not None:
            return self._dimension

        try:
            if hasattr(self.model, "get_embedding_dimension"):
                self._dimension = int(self.model.get_embedding_dimension())
            else:
                self._dimension = int(self.model.get_sentence_embedding_dimension())
            return self._dimension
        except Exception as e:
            logger.warning(f"Could not infer dimension from model: {e}. Falling back to default: {EMBEDDING_DIM}")
            self._dimension = EMBEDDING_DIM
            return self._dimension

    def embed_texts(
        self,
        texts: List[str],
        batch_size: int = 32
    ) -> np.ndarray:
        """
        Encode a list of text strings into L2-normalized float32 embeddings.
        
        Args:
            texts: List of text strings to embed.
            batch_size: Mini-batch size for model inference.
            
        Returns:
            np.ndarray of shape (len(texts), embedding_dim) as float32.
        """
        if not texts:
            dim = self.get_dimension()
            return np.empty((0, dim), dtype=np.float32)

        # Sanitize texts (handle None, non-strings, and empty strings gracefully)
        cleaned_texts: List[str] = []
        for t in texts:
            if t is None:
                cleaned_texts.append(" ")
            elif isinstance(t, str):
                cleaned_texts.append(t.strip() if t.strip() else " ")
            else:
                # Handle unexpected data types by converting to string
                str_t = str(t).strip()
                cleaned_texts.append(str_t if str_t else " ")

        try:
            embeddings = self.model.encode(
                cleaned_texts,
                batch_size=batch_size,
                show_progress_bar=False,
                normalize_embeddings=True,
                convert_to_numpy=True
            )
            return np.asarray(embeddings, dtype=np.float32)
        except Exception as e:
            logger.error(f"Error during batch text embedding generation: {e}")
            raise RuntimeError(f"Embedding generation failed: {e}") from e

    def embed_text(self, text: str) -> np.ndarray:
        """
        Encode a single text string into an L2-normalized 1D float32 vector.
        
        Args:
            text: The text string to embed.
            
        Returns:
            np.ndarray 1D array of shape (embedding_dim,) as float32.
        """
        sanitized = " " if text is None or not str(text).strip() else str(text)
        return self.embed_texts([sanitized])[0]

    def embed_query(self, query: str) -> np.ndarray:
        """
        Encode a search query string into an L2-normalized 1D float32 vector.
        
        Args:
            query: The user search query string.
            
        Returns:
            np.ndarray 1D array of shape (embedding_dim,) as float32.
        """
        return self.embed_text(query)

    def embed_chunks(
        self,
        chunks: List[Union[Dict[str, Any], Any]],
        batch_size: int = 32
    ) -> np.ndarray:
        """
        Extract text from document chunk dictionaries or objects and generate embeddings.
        
        Args:
            chunks: List of chunk dictionaries or DocumentChunk objects.
            batch_size: Mini-batch size for model inference.
            
        Returns:
            np.ndarray 2D array of shape (len(chunks), embedding_dim) as float32.
        """
        if not chunks:
            dim = self.get_dimension()
            return np.empty((0, dim), dtype=np.float32)

        extracted_texts: List[str] = []
        for c in chunks:
            if isinstance(c, dict):
                extracted_texts.append(c.get("text", ""))
            elif hasattr(c, "text"):
                extracted_texts.append(getattr(c, "text", ""))
            elif isinstance(c, str):
                extracted_texts.append(c)
            else:
                extracted_texts.append(str(c) if c is not None else "")

        return self.embed_texts(extracted_texts, batch_size=batch_size)


def get_default_embedder() -> MultilingualEmbedder:
    """Retrieve or initialize the global shared MultilingualEmbedder singleton."""
    global _GLOBAL_EMBEDDER
    if _GLOBAL_EMBEDDER is None:
        _GLOBAL_EMBEDDER = MultilingualEmbedder()
    return _GLOBAL_EMBEDDER


def embed_text(text: str, embedder: Optional[MultilingualEmbedder] = None) -> np.ndarray:
    """Convenience function to embed a single text string."""
    emb = embedder or get_default_embedder()
    return emb.embed_text(text)


def embed_texts(
    texts: List[str],
    embedder: Optional[MultilingualEmbedder] = None,
    batch_size: int = 32
) -> np.ndarray:
    """Convenience function to embed a list of text strings."""
    emb = embedder or get_default_embedder()
    return emb.embed_texts(texts, batch_size=batch_size)


def embed_query(query: str, embedder: Optional[MultilingualEmbedder] = None) -> np.ndarray:

    """Convenience function to embed a search query string."""
    emb = embedder or get_default_embedder()
    return emb.embed_query(query)


def embed_chunks(
    chunks: List[Union[Dict[str, Any], Any]],
    embedder: Optional[MultilingualEmbedder] = None,
    batch_size: int = 32
) -> np.ndarray:
    """Convenience function to embed a list of document chunks."""
    emb = embedder or get_default_embedder()
    return emb.embed_chunks(chunks, batch_size=batch_size)
