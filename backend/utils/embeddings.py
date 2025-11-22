"""Embedding generation and vector database management using Milvus."""
from typing import List, Dict, Any, Optional
import logging
from sentence_transformers import SentenceTransformer
from pymilvus import (
    connections,
    Collection,
    CollectionSchema,
    FieldSchema,
    DataType,
    utility
)
from backend.config import settings

logger = logging.getLogger(__name__)


class EmbeddingEngine:
    """Handles embedding generation and vector storage with Milvus."""
    
    def __init__(self):
        # Initialize sentence transformer model
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.dimension = settings.vector_dimension
        
        # Connect to Milvus
        self._connect_milvus()
        
        # Initialize or get collection
        self._init_collection()
    
    def _connect_milvus(self):
        """Connect to Milvus database."""
        try:
            connections.connect(
                alias="default",
                uri=settings.milvus_uri,
                token=settings.milvus_token
            )
            logger.info("Connected to Milvus successfully")
        except Exception as e:
            logger.error(f"Failed to connect to Milvus: {e}")
            raise
    
    def _init_collection(self):
        """Initialize or get existing Milvus collection."""
        try:
            # Check if collection exists
            if utility.has_collection(settings.milvus_collection):
                self.collection = Collection(settings.milvus_collection)
                logger.info(f"Using existing collection: {settings.milvus_collection}")
            else:
                # Create collection schema
                fields = [
                    FieldSchema(name="id", dtype=DataType.VARCHAR, is_primary=True, max_length=100),
                    FieldSchema(name="document_id", dtype=DataType.VARCHAR, max_length=100),
                    FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=65535),
                    FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=self.dimension)
                ]
                schema = CollectionSchema(fields=fields, description="Document embeddings")
                
                # Create collection
                self.collection = Collection(
                    name=settings.milvus_collection,
                    schema=schema
                )
                
                # Create index
                index_params = {
                    "metric_type": "COSINE",
                    "index_type": "IVF_FLAT",
                    "params": {"nlist": 128}
                }
                self.collection.create_index(field_name="vector", index_params=index_params)
                logger.info(f"Created new collection: {settings.milvus_collection}")
            
            # Load collection into memory
            self.collection.load()
            logger.info("Collection loaded into memory")
            
        except Exception as e:
            logger.error(f"Failed to initialize collection: {e}")
            raise
    
    
    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of texts.
        
        Args:
            texts: List of text strings to embed
            
        Returns:
            List of embeddings
        """
        try:
            embeddings = self.model.encode(texts, convert_to_numpy=True)
            # Convert to list of lists for Milvus
            embeddings_list = embeddings.tolist()
            logger.info(f"Generated {len(embeddings_list)} embeddings")
            return embeddings_list
        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
            raise
    
    
    async def store_embeddings(
        self,
        embeddings: List[List[float]],
        texts: List[str],
        metadata: Dict[str, Any]
    ) -> List[str]:
        """Store embeddings in Milvus vector database.
        
        Args:
            embeddings: List of embeddings to store
            texts: Original texts
            metadata: Metadata for the embeddings (must include 'document_id')
            
        Returns:
            List of vector IDs
        """
        try:
            # Generate unique IDs for each vector
            import uuid
            vector_ids = [str(uuid.uuid4()) for _ in range(len(texts))]
            document_id = metadata.get('document_id', 'unknown')
            
            # Prepare data for insertion
            entities = [
                vector_ids,  # id field
                [document_id] * len(texts),  # document_id field
                texts,  # text field
                embeddings  # vector field
            ]
            
            # Insert into Milvus
            self.collection.insert(entities)
            self.collection.flush()
            
            logger.info(f"Stored {len(vector_ids)} vectors in Milvus")
            return vector_ids
        except Exception as e:
            logger.error(f"Error storing embeddings in Milvus: {e}")
            raise
    
    
    async def search(
        self,
        query_text: str,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """Search for similar vectors in Milvus.
        
        Args:
            query_text: Query text to search for
            top_k: Number of results to return
            
        Returns:
            List of search results with text, score, and metadata
        """
        try:
            # Generate query embedding
            query_embeddings = await self.embed_texts([query_text])
            query_embedding = query_embeddings[0]
            
            # Define search parameters
            search_params = {
                "metric_type": "COSINE",
                "params": {"nprobe": 10}
            }
            
            # Search in Milvus
            search_results = self.collection.search(
                data=[query_embedding],
                anns_field="vector",
                param=search_params,
                limit=top_k,
                output_fields=["text", "document_id"]
            )
            
            # Format results
            results = []
            for hits in search_results:
                for hit in hits:
                    results.append({
                        "id": hit.id,
                        "text": hit.entity.get("text"),
                        "score": float(hit.score),
                        "metadata": {
                            "document_id": hit.entity.get("document_id")
                        }
                    })
            
            logger.info(f"Found {len(results)} results for query")
            return results
        except Exception as e:
            logger.error(f"Error searching in Milvus: {e}")
            raise
    
    def close(self):
        """Close Milvus connection."""
        try:
            connections.disconnect("default")
            logger.info("Disconnected from Milvus")
        except Exception as e:
            logger.error(f"Error disconnecting from Milvus: {e}")
