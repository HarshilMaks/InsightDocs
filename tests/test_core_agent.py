"""Tests for core agent framework."""
import pytest
from insightdocs.core.agent import BaseAgent, AgentMessage


class TestAgent(BaseAgent):
    """Test agent implementation."""
    
    async def process(self, message):
        return {
            "success": True,
            "agent_id": self.agent_id,
            "message_type": message.get("message_type")
        }


@pytest.mark.asyncio
async def test_base_agent_process():
    """Test base agent processing."""
    agent = TestAgent("test_agent", "TestAgent")
    
    result = await agent.process({"message_type": "test"})
    
    assert result["success"] is True
    assert result["agent_id"] == "test_agent"
    assert result["message_type"] == "test"


@pytest.mark.asyncio
async def test_agent_error_handling():
    """Test agent error handling."""
    agent = TestAgent("test_agent", "TestAgent")
    
    error = Exception("Test error")
    result = await agent.handle_error(error, {"context": "test"})
    
    assert result["success"] is False
    assert result["error"] == "Test error"
    assert result["agent_id"] == "test_agent"


def test_agent_message_creation():
    """Test agent message creation."""
    message = AgentMessage(
        message_type="test",
        payload={"data": "test_data"},
        sender_id="sender",
        recipient_id="recipient"
    )
    
    assert message.message_type == "test"
    assert message.payload["data"] == "test_data"
    assert message.sender_id == "sender"
    assert message.recipient_id == "recipient"


def test_agent_message_serialization():
    """Test agent message serialization."""
    message = AgentMessage(
        message_type="test",
        payload={"data": "test_data"}
    )
    
    message_dict = message.to_dict()
    
    assert message_dict["message_type"] == "test"
    assert message_dict["payload"]["data"] == "test_data"
    assert "timestamp" in message_dict


def test_agent_message_deserialization():
    """Test agent message deserialization."""
    message_dict = {
        "message_type": "test",
        "payload": {"data": "test_data"},
        "sender_id": "sender",
        "recipient_id": "recipient"
    }
    
    message = AgentMessage.from_dict(message_dict)
    
    assert message.message_type == "test"
    assert message.payload["data"] == "test_data"
    assert message.sender_id == "sender"
