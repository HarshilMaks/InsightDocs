"""Analysis Agent for content extraction, summarization, and embeddings."""
from typing import Dict, Any, List
import logging
from backend.core import BaseAgent
from backend.utils.embeddings import get_embedding_engine
from backend.utils.llm_client import LLMClient

logger = logging.getLogger(__name__)


class AnalysisAgent(BaseAgent):
    """Agent responsible for content analysis and embeddings."""
    
    def __init__(self, agent_id: str = "analysis_agent"):
        super().__init__(agent_id, "AnalysisAgent")
        self.embedding_engine = get_embedding_engine()
        self.llm_client = LLMClient()
    
    async def process(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Process analysis tasks.
        
        Handles:
        - Content extraction
        - Text summarization
        - Embedding generation
        
        Args:
            message: Message with analysis task details
            
        Returns:
            Analysis result
        """
        try:
            task_type = message.get("task_type")
            
            if task_type == "embed":
                return await self._generate_embeddings(message)
            elif task_type == "summarize":
                return await self._summarize_content(message)
            elif task_type == "extract":
                return await self._extract_entities(message)
            else:
                return {
                    "success": False,
                    "error": f"Unknown task type: {task_type}"
                }
        except Exception as e:
            return await self.handle_error(e, message)
    
    async def _generate_embeddings(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Generate embeddings for text chunks.
        
        Args:
            message: Message containing chunks to embed
            
        Returns:
            Embeddings result
        """
        chunks = message.get("chunks", [])
        
        self.log_event("embed_start", {"chunk_count": len(chunks)})
        
        # Generate embeddings
        embeddings = await self.embedding_engine.embed_texts(chunks)
        
        # Store in vector database
        vector_ids = await self.embedding_engine.store_embeddings(
            embeddings,
            chunks,
            message.get("metadata", {})
        )
        
        self.log_event("embed_complete", {
            "chunk_count": len(chunks),
            "vector_ids": len(vector_ids)
        })
        
        return {
            "success": True,
            "vector_ids": vector_ids,
            "embedding_count": len(embeddings),
            "agent_id": self.agent_id
        }
    
    async def _summarize_content(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Summarize document content.
        
        Args:
            message: Message with content to summarize
            
        Returns:
            Summarization result
        """
        content = message.get("content", "")
        
        self.log_event("summarize_start", {"content_length": len(content)})
        
        # Generate summary using LLM
        summary = await self.llm_client.summarize(content)
        
        self.log_event("summarize_complete", {"summary_length": len(summary)})
        
        return {
            "success": True,
            "summary": summary,
            "agent_id": self.agent_id
        }
    
    async def _extract_entities(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Extract entities from content.
        
        Args:
            message: Message with content for entity extraction
            
        Returns:
            Extracted entities
        """
        content = message.get("content", "")
        
        self.log_event("extract_start", {"content_length": len(content)})
        
        # Extract entities using LLM
        entities = await self.llm_client.extract_entities(content)
        
        self.log_event("extract_complete", {"entity_count": len(entities)})
        
        return {
            "success": True,
            "entities": entities,
            "agent_id": self.agent_id
        }
