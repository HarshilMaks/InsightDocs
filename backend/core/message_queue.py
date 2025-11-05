"""Message queue management for agent communication."""
import redis
import json
from typing import Dict, Any, Optional
from backend.config import settings
from backend.core.agent import AgentMessage
import logging

logger = logging.getLogger(__name__)


class MessageQueue:
    """Redis-based message queue for agent communication."""
    
    def __init__(self):
        self.redis_client = redis.from_url(settings.redis_url, decode_responses=True)
    
    def publish(self, channel: str, message: AgentMessage) -> bool:
        """Publish a message to a channel.
        
        Args:
            channel: Channel name to publish to
            message: AgentMessage to publish
            
        Returns:
            True if successful, False otherwise
        """
        try:
            message_json = json.dumps(message.to_dict())
            self.redis_client.publish(channel, message_json)
            logger.info(f"Published message to channel: {channel}")
            return True
        except Exception as e:
            logger.error(f"Failed to publish message: {e}")
            return False
    
    def enqueue(self, queue_name: str, message: AgentMessage) -> bool:
        """Add a message to a queue.
        
        Args:
            queue_name: Queue name
            message: AgentMessage to enqueue
            
        Returns:
            True if successful, False otherwise
        """
        try:
            message_json = json.dumps(message.to_dict())
            self.redis_client.rpush(queue_name, message_json)
            logger.info(f"Enqueued message to queue: {queue_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to enqueue message: {e}")
            return False
    
    def dequeue(self, queue_name: str, timeout: int = 0) -> Optional[AgentMessage]:
        """Retrieve a message from a queue.
        
        Args:
            queue_name: Queue name
            timeout: Blocking timeout in seconds (0 for non-blocking)
            
        Returns:
            AgentMessage if available, None otherwise
        """
        try:
            if timeout > 0:
                result = self.redis_client.blpop(queue_name, timeout=timeout)
                if result:
                    _, message_json = result
                else:
                    return None
            else:
                message_json = self.redis_client.lpop(queue_name)
            
            if message_json:
                message_dict = json.loads(message_json)
                return AgentMessage.from_dict(message_dict)
            return None
        except Exception as e:
            logger.error(f"Failed to dequeue message: {e}")
            return None
    
    def get_queue_length(self, queue_name: str) -> int:
        """Get the length of a queue.
        
        Args:
            queue_name: Queue name
            
        Returns:
            Number of messages in queue
        """
        try:
            return self.redis_client.llen(queue_name)
        except Exception as e:
            logger.error(f"Failed to get queue length: {e}")
            return 0


# Global message queue instance
message_queue = MessageQueue()
