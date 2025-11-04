"""Core framework components."""
from .agent import BaseAgent, AgentMessage
from .message_queue import MessageQueue, message_queue

__all__ = [
    "BaseAgent",
    "AgentMessage",
    "MessageQueue",
    "message_queue",
]
