"""Data Agent for handling data ingestion, transformation, and storage."""
from typing import Dict, Any, List
import logging
from pathlib import Path
from backend.core import BaseAgent, AgentMessage
from backend.utils.document_processor import DocumentProcessor
from backend.storage.file_storage import FileStorage

logger = logging.getLogger(__name__)


class DataAgent(BaseAgent):
    """Agent responsible for data ingestion and transformation."""
    
    def __init__(self, agent_id: str = "data_agent"):
        super().__init__(agent_id, "DataAgent")
        self.document_processor = DocumentProcessor()
        self.file_storage = FileStorage()
    
    async def process(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Process data-related tasks.
        
        Handles:
        - File upload and storage
        - Document parsing
        - Data transformation
        
        Args:
            message: Message with task details
            
        Returns:
            Processing result
        """
        try:
            task_type = message.get("task_type")
            
            if task_type == "ingest":
                return await self._ingest_document(message)
            elif task_type == "transform":
                return await self._transform_data(message)
            elif task_type == "store":
                return await self._store_data(message)
            else:
                return {
                    "success": False,
                    "error": f"Unknown task type: {task_type}"
                }
        except Exception as e:
            return await self.handle_error(e, message)
    
    async def _ingest_document(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Ingest a document into the system.
        
        Args:
            message: Message containing file path and metadata
            
        Returns:
            Ingestion result with document ID
        """
        file_path = message.get("file_path")
        filename = message.get("filename")
        
        self.log_event("ingest_start", {"file_path": file_path})
        
        # Store file
        stored_path = await self.file_storage.store_file(file_path, filename)
        
        # Parse document
        parsed_content = await self.document_processor.parse_document(stored_path)
        
        self.log_event("ingest_complete", {
            "file_path": stored_path,
            "content_length": len(parsed_content.get("text", ""))
        })
        
        return {
            "success": True,
            "stored_path": stored_path,
            "content": parsed_content,
            "agent_id": self.agent_id
        }
    
    async def _transform_data(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Transform data according to specifications.
        
        Args:
            message: Message with transformation details
            
        Returns:
            Transformed data result
        """
        content = message.get("content")
        chunk_size = message.get("chunk_size", 1000)
        
        self.log_event("transform_start", {"chunk_size": chunk_size})
        
        # Chunk content
        chunks = await self.document_processor.chunk_text(content, chunk_size)
        
        self.log_event("transform_complete", {"chunk_count": len(chunks)})
        
        return {
            "success": True,
            "chunks": chunks,
            "chunk_count": len(chunks),
            "agent_id": self.agent_id
        }
    
    async def _store_data(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Store processed data.
        
        Args:
            message: Message with data to store
            
        Returns:
            Storage result
        """
        self.log_event("store_start", message)
        
        # In a real implementation, this would save to database
        # For now, we'll just acknowledge the storage request
        
        return {
            "success": True,
            "stored": True,
            "agent_id": self.agent_id
        }
