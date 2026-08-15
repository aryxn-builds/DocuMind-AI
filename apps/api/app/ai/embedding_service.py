import logging
from typing import List, Tuple

try:
    import numpy as np
    from sentence_transformers import SentenceTransformer
except ImportError:
    pass

from app.core.config import settings
from app.ai.models import Chunk


logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Singleton service for embedding chunks using a local sentence-transformers model.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(EmbeddingService, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        self.model_name = settings.default_embedding_model
        self.batch_size = settings.embedding_batch_size
        self.model = None

    def embed(self, chunks: List[Chunk]) -> List[Tuple[Chunk, List[float]]]:
        """
        Embeds a list of chunks.
        Returns a list of tuples containing the original Chunk and its L2-normalized embedding vector.
        """
        if not chunks:
            return []
            
        if self.model is None:
            logger.info(f"Loading embedding model: {self.model_name}")
            try:
                self.model = SentenceTransformer(self.model_name)
            except Exception as e:
                logger.error(f"Failed to load embedding model {self.model_name}: {e}")
                raise RuntimeError("Embedding model is not loaded.") from e
            
        texts = [chunk.content for chunk in chunks]
        
        try:
            # For cosine distance, we must normalize embeddings
            embeddings = self.model.encode(texts, batch_size=self.batch_size, normalize_embeddings=True)
            
            result = []
            for chunk, emb in zip(chunks, embeddings):
                result.append((chunk, emb.tolist()))
                
            return result
        except Exception as e:
            logger.error(f"Failed to generate embeddings: {e}")
            raise RuntimeError(f"Embedding generation failed: {e}") from e

    def embed_query(self, text: str) -> List[float]:
        """
        Embeds a single query string for search.
        """
        if self.model is None:
            logger.info(f"Loading embedding model: {self.model_name}")
            try:
                self.model = SentenceTransformer(self.model_name)
            except Exception as e:
                logger.error(f"Failed to load embedding model {self.model_name}: {e}")
                raise RuntimeError("Embedding model is not loaded.") from e
        
        try:
            embedding = self.model.encode([text], normalize_embeddings=True)[0]
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Failed to generate query embedding: {e}")
            raise RuntimeError(f"Query embedding generation failed: {e}") from e
