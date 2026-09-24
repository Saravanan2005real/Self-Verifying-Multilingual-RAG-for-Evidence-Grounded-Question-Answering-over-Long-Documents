import logging
from typing import List, Union, Optional
import numpy as np

from src.config import EMBEDDING_MODEL, EMBEDDING_DIM

logger = logging.getLogger(__name__)


class MultilingualEmbedder:
    """
    Lightweight multilingual embedding generator supporting English, Tamil, Hindi,
    and 50+ languages using sentence-transformers.
    Produces L2-normalized float32 vectors for cosine similarity computation via FAISS.
    """

    def __init__(
        self,
        model_name: str = EMBEDDING_MODEL,
        device: Optional[str] = None
    ):
        self.model_name = model_name
        self.device = device
        self._model = None

    @property
    def model(self):
        """Lazy loader for SentenceTransformer model."""
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            logger.info(f"Loading multilingual embedding model: {self.model_name}")
            self._model = SentenceTransformer(self.model_name, device=self.device)
        return self._model

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

        # Sanitize texts (replace empty strings with space to avoid model warnings)
        cleaned_texts = [t.strip() if t and t.strip() else " " for t in texts]

        embeddings = self.model.encode(
            cleaned_texts,
            batch_size=batch_size,
            show_progress_bar=False,
            normalize_embeddings=True,
            convert_to_numpy=True
        )

        return np.asarray(embeddings, dtype=np.float32)

    def embed_query(self, query: str) -> np.ndarray:
        """
        Encode a single search query into an L2-normalized 1D float32 vector.
        
        Args:
            query: The user search query string.
            
        Returns:
            np.ndarray 1D array of shape (embedding_dim,) as float32.
        """
        if not query or not query.strip():
            query = " "
        return self.embed_texts([query])[0]

    def get_dimension(self) -> int:
        """Return the embedding dimension of the underlying model."""
        try:
            if hasattr(self.model, "get_embedding_dimension"):
                return self.model.get_embedding_dimension()
            return self.model.get_sentence_embedding_dimension()
        except Exception:
            return EMBEDDING_DIM
