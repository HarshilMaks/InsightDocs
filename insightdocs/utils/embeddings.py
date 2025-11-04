"""Embedding generation and vector database management."""
from typing import List, Dict, Any
import logging
import numpy as np
from sentence_transformers import SentenceTransformer
import faiss
from insightdocs.config import settings

logger = logging.getLogger(__name__)


class EmbeddingEngine:
    """Handles embedding generation and vector storage."""
    
    def __init__(self):
        # Initialize sentence transformer model
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.dimension = settings.vector_dimension
        
        # Initialize FAISS index
        self.index = faiss.IndexFlatL2(self.dimension)
        self.index_metadata = []
    
    async def embed_texts(self, texts: List[str]) -> np.ndarray:
        """Generate embeddings for a list of texts.
        
        Args:
            texts: List of text strings to embed
            
        Returns:
            Numpy array of embeddings
        """
        try:
            embeddings = self.model.encode(texts, convert_to_numpy=True)
            logger.info(f"Generated {len(embeddings)} embeddings")
            return embeddings
        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
            raise
    
    async def store_embeddings(
        self,
        embeddings: np.ndarray,
        texts: List[str],
        metadata: Dict[str, Any]
    ) -> List[str]:
        """Store embeddings in vector database.
        
        Args:
            embeddings: Embeddings to store
            texts: Original texts
            metadata: Metadata for the embeddings
            
        Returns:
            List of vector IDs
        """
        try:
            # Add to FAISS index
            self.index.add(embeddings)
            
            # Store metadata
            vector_ids = []
            for i, text in enumerate(texts):
                vector_id = f"vec_{len(self.index_metadata)}"
                self.index_metadata.append({
                    "id": vector_id,
                    "text": text,
                    "metadata": metadata
                })
                vector_ids.append(vector_id)
            
            logger.info(f"Stored {len(vector_ids)} vectors")
            return vector_ids
        except Exception as e:
            logger.error(f"Error storing embeddings: {e}")
            raise
    
    async def search(
        self,
        query_text: str,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """Search for similar vectors.
        
        Args:
            query_text: Query text to search for
            top_k: Number of results to return
            
        Returns:
            List of search results with text and metadata
        """
        try:
            # Generate query embedding
            query_embedding = await self.embed_texts([query_text])
            
            # Search FAISS index
            distances, indices = self.index.search(query_embedding, top_k)
            
            # Retrieve results
            results = []
            for i, idx in enumerate(indices[0]):
                if idx < len(self.index_metadata):
                    result = self.index_metadata[idx].copy()
                    result['distance'] = float(distances[0][i])
                    results.append(result)
            
            logger.info(f"Found {len(results)} results for query")
            return results
        except Exception as e:
            logger.error(f"Error searching embeddings: {e}")
            raise
    
    def save_index(self, path: str):
        """Save FAISS index to disk.
        
        Args:
            path: Path to save index
        """
        try:
            faiss.write_index(self.index, path)
            logger.info(f"Saved index to {path}")
        except Exception as e:
            logger.error(f"Error saving index: {e}")
            raise
    
    def load_index(self, path: str):
        """Load FAISS index from disk.
        
        Args:
            path: Path to load index from
        """
        try:
            self.index = faiss.read_index(path)
            logger.info(f"Loaded index from {path}")
        except Exception as e:
            logger.error(f"Error loading index: {e}")
            raise
