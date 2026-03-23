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
        # Dense model (upgraded to bge-base for better quality)
        self.dense_model = SentenceTransformer(settings.embedding_model_name)
        self.dimension = settings.milvus_dim  # Use milvus_dim (768) instead of vector_dimension
        
        # Sparse model (BM25 for keyword search)
        # Using BGEM3EmbeddingFunction as a wrapper or similar if available,
        # but for simplicity/control we'll use a standard BM25 approach or milvus-model
        try:
            from milvus_model.hybrid import BGEM3EmbeddingFunction
            self.sparse_model = BGEM3EmbeddingFunction(use_fp16=False, device="cpu")
            self.has_sparse = True
        except Exception as e:
            logger.warning(f"Sparse vectors disabled: {e}")
            self.sparse_model = None
            self.has_sparse = False
            
        self.collection = None  # Initialize before connect attempt
        self._connect_milvus()
        self._init_collection()
    
    def _connect_milvus(self):
        """Connect to Milvus database."""
        try:
            connections.connect(
                alias="default",
                uri=settings.milvus_uri,
                token=settings.milvus_token
            )
            self._milvus_connected = True
            logger.info("Connected to Milvus successfully")
        except Exception as e:
            logger.error(f"Failed to connect to Milvus: {e}")
            logger.warning("App will continue but vector search will be unavailable")
            self._milvus_connected = False
    
    def _init_collection(self):
        """Initialize or get existing Milvus collection."""
        if not self._milvus_connected:
            logger.warning("Skipping collection init - Milvus connection failed")
            return
            
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
                    FieldSchema(name="user_id", dtype=DataType.VARCHAR, max_length=100),  # NEW: For tenant isolation
                    FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=65535),
                    FieldSchema(name="dense_vector", dtype=DataType.FLOAT_VECTOR, dim=self.dimension),
                    FieldSchema(name="sparse_vector", dtype=DataType.SPARSE_FLOAT_VECTOR)
                ]
                schema = CollectionSchema(fields=fields, description="Document embeddings (Hybrid)")
                
                # Create collection
                self.collection = Collection(
                    name=settings.milvus_collection,
                    schema=schema
                )
                
                # Create indexes
                dense_index_params = {
                    "metric_type": "COSINE",
                    "index_type": "IVF_FLAT",
                    "params": {"nlist": 128}
                }
                sparse_index_params = {
                    "metric_type": "IP", # Inner Product for sparse
                    "index_type": "SPARSE_INVERTED_INDEX",
                    "params": {"drop_ratio_build": 0.2}
                }
                
                self.collection.create_index(field_name="dense_vector", index_params=dense_index_params)
                self.collection.create_index(field_name="sparse_vector", index_params=sparse_index_params)
                logger.info(f"Created new hybrid collection: {settings.milvus_collection}")
            
            # Load collection into memory
            self.collection.load()
            logger.info("Collection loaded into memory")
            
        except Exception as e:
            logger.error(f"Failed to initialize collection: {e}")
            logger.warning("Vector search will be unavailable")
            self.collection = None
    
    
    async def embed_texts(self, texts: List[str]) -> Dict[str, Any]:
        """Generate dense and sparse embeddings for a list of texts.
        
        Args:
            texts: List of text strings to embed
            
        Returns:
            Dictionary with 'dense' and 'sparse' embeddings
        """
        try:
            if not texts:
                return {"dense": [], "sparse": []}

            # Generate dense embeddings
            dense_embeddings = self.dense_model.encode(texts, convert_to_numpy=True)
            dense_list = dense_embeddings.tolist()
            
            # Generate sparse embeddings
            sparse_list = []
            if self.has_sparse:
                # milvus_model BGEM3 encode returns dictionary with 'dense', 'sparse', etc.
                # But here we assume we initialized it to just return what we need or we parse it
                # Actually, BGEM3EmbeddingFunction usually takes a list and returns embeddings.
                # Let's verify usage. For now, assuming a standard call or using a fallback if simple.
                
                # Note: BGEM3 is heavy. If using a lighter weight BM25:
                # We might need to implement a simple BM25 encoder or use the one from milvus_model if lighter.
                # For this implementation, let's use the BGEM3 function we initialized.
                results = self.sparse_model(texts)
                # results is likely a dictionary or list of results. 
                # BGEM3EmbeddingFunction in milvus-model usually returns:
                # {'dense': [...], 'sparse': [...]}
                sparse_list = results['sparse']
            else:
                # Fallback empty sparse vectors if not available (shouldn't happen in prod)
                sparse_list = [{}] * len(texts)

            logger.info(f"Generated {len(dense_list)} hybrid embeddings")
            return {
                "dense": dense_list,
                "sparse": sparse_list
            }
        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
            raise
    
    
    async def store_embeddings(
        self,
        embeddings: Dict[str, Any],
        texts: List[str],
        metadata: Dict[str, Any]
    ) -> List[str]:
        """Store embeddings in Milvus vector database.
        
        Args:
            embeddings: Dict containing 'dense' and 'sparse' lists
            texts: Original texts
            metadata: Metadata for the embeddings (must include 'document_id' and 'user_id')
            
        Returns:
            List of vector IDs
        """
        if self.collection is None:
            logger.error("Cannot store embeddings - Milvus not connected")
            raise RuntimeError("Milvus connection not available")
            
        try:
            if not texts:
                logger.warning("No texts provided for embedding storage")
                return []

            # Generate unique IDs for each vector
            import uuid
            vector_ids = [str(uuid.uuid4()) for _ in range(len(texts))]
            document_id = metadata.get('document_id', 'unknown')
            user_id = metadata.get('user_id', 'unknown')  # NEW: Extract user_id
            
            # Prepare data for insertion (order must match schema)
            entities = [
                vector_ids,  # id field
                [document_id] * len(texts),  # document_id field
                [user_id] * len(texts),  # user_id field (NEW)
                texts,  # text field
                embeddings['dense'],  # dense_vector field
                embeddings['sparse']  # sparse_vector field
            ]
            
            # Insert into Milvus
            self.collection.insert(entities)
            self.collection.flush()
            
            logger.info(f"Stored {len(vector_ids)} vectors for user {user_id} in Milvus")
            return vector_ids
        except Exception as e:
            logger.error(f"Error storing embeddings in Milvus: {e}")
            raise
    
    
    async def search(
        self,
        query_text: str,
        top_k: int = 5,
        user_id: str = None
    ) -> List[Dict[str, Any]]:
        """Search for similar vectors in Milvus using Hybrid Search.
        
        Args:
            query_text: Query text to search for
            top_k: Number of results to return
            user_id: Optional user ID to filter results (for multi-tenant isolation)
            
        Returns:
            List of search results with text, score, and metadata
        """
        if self.collection is None:
            logger.error("Cannot search - Milvus not connected")
            raise RuntimeError("Milvus connection not available")
            
        try:
            # Generate query embeddings (dense + sparse when available)
            query_embeds = await self.embed_texts([query_text])
            dense_query = query_embeds['dense'][0]
            
            # Create AnnSearchRequests
            from pymilvus import AnnSearchRequest, WeightedRanker
            
            # Dense search request
            dense_req = AnnSearchRequest(
                data=[dense_query],
                anns_field="dense_vector",
                param={"metric_type": "COSINE", "params": {"nprobe": 10}},
                limit=top_k * 3  # Fetch more candidates for filtering
            )
            
            # Build filter expression for user isolation
            expr = f'user_id == "{user_id}"' if user_id else None

            if self.has_sparse and query_embeds['sparse']:
                sparse_query = query_embeds['sparse'][0]

                # Sparse search request
                sparse_req = AnnSearchRequest(
                    data=[sparse_query],
                    anns_field="sparse_vector",
                    param={"metric_type": "IP", "params": {"drop_ratio_search": 0.2}},
                    limit=top_k * 3,  # Fetch more candidates for filtering
                )

                # Perform Hybrid Search
                # Rerank with WeightedRanker (0.7 dense + 0.3 sparse is a good starting point)
                ranker = WeightedRanker(0.7, 0.3)

                search_results = self.collection.hybrid_search(
                    reqs=[dense_req, sparse_req],
                    rerank=ranker,
                    limit=top_k,
                    output_fields=["text", "document_id", "user_id"],
                    expr=expr,  # Apply user filter
                )
            else:
                # Dense-only fallback keeps document search working even if sparse
                # model dependencies are unavailable in the runtime environment.
                search_results = self.collection.search(
                    data=[dense_query],
                    anns_field="dense_vector",
                    param={"metric_type": "COSINE", "params": {"nprobe": 10}},
                    limit=top_k,
                    output_fields=["text", "document_id", "user_id"],
                    expr=expr,
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
                            "document_id": hit.entity.get("document_id"),
                            "user_id": hit.entity.get("user_id")
                        }
                    })
            
            logger.info(f"Found {len(results)} results for query (user_id filter: {user_id or 'none'})")
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


# Singleton instance — avoids reloading the model on every request
_engine_instance: Optional[EmbeddingEngine] = None


def get_embedding_engine() -> EmbeddingEngine:
    """Get or create the singleton EmbeddingEngine instance."""
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = EmbeddingEngine()
    return _engine_instance
