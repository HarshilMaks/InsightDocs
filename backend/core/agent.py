"""Base agent class for InsightDocs agent architecture."""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import logging
import json
from datetime import datetime

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Base class for all agents in the system."""
    
    def __init__(self, agent_id: str, agent_type: str):
        self.agent_id = agent_id
        self.agent_type = agent_type
        self.logger = logging.getLogger(f"{__name__}.{agent_type}")
    
    @abstractmethod
    async def process(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Process a message and return a result.
        
        Args:
            message: Input message with task details
            
        Returns:
            Result dictionary with processing outcome
        """
        pass
    
    def log_event(self, event_type: str, data: Dict[str, Any]):
        """Log an agent event."""
        log_data = {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "event_type": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            "data": data
        }
        self.logger.info(json.dumps(log_data))
    
    async def handle_error(self, error: Exception, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle errors during processing.
        
        Args:
            error: The exception that occurred
            context: Context information about the operation
            
        Returns:
            Error response dictionary
        """
        self.log_event("error", {
            "error": str(error),
            "error_type": type(error).__name__,
            "context": context
        })
        return {
            "success": False,
            "error": str(error),
            "error_type": type(error).__name__,
            "agent_id": self.agent_id
        }


class AgentMessage:
    """Standard message format for inter-agent communication."""
    
    def __init__(
        self,
        message_type: str,
        payload: Dict[str, Any],
        sender_id: Optional[str] = None,
        recipient_id: Optional[str] = None,
        correlation_id: Optional[str] = None
    ):
        self.message_type = message_type
        self.payload = payload
        self.sender_id = sender_id
        self.recipient_id = recipient_id
        self.correlation_id = correlation_id
        self.timestamp = datetime.utcnow().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary."""
        return {
            "message_type": self.message_type,
            "payload": self.payload,
            "sender_id": self.sender_id,
            "recipient_id": self.recipient_id,
            "correlation_id": self.correlation_id,
            "timestamp": self.timestamp
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentMessage":
        """Create message from dictionary."""
        return cls(
            message_type=data["message_type"],
            payload=data["payload"],
            sender_id=data.get("sender_id"),
            recipient_id=data.get("recipient_id"),
            correlation_id=data.get("correlation_id")
        )
