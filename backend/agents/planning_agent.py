"""Planning Agent for workflow management and decision support."""
from typing import Dict, Any, List
import logging
from backend.core import BaseAgent
from backend.utils.llm_client import LLMClient

logger = logging.getLogger(__name__)


class PlanningAgent(BaseAgent):
    """Agent responsible for planning and workflow management."""
    
    def __init__(self, agent_id: str = "planning_agent"):
        super().__init__(agent_id, "PlanningAgent")
        self.llm_client = LLMClient()
    
    async def process(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Process planning tasks.
        
        Handles:
        - Next step suggestions
        - Progress tracking
        - Decision support
        
        Args:
            message: Message with planning task details
            
        Returns:
            Planning result
        """
        try:
            task_type = message.get("task_type")
            
            if task_type == "suggest_steps":
                return await self._suggest_next_steps(message)
            elif task_type == "track_progress":
                return await self._track_progress(message)
            elif task_type == "make_decision":
                return await self._support_decision(message)
            else:
                return {
                    "success": False,
                    "error": f"Unknown task type: {task_type}"
                }
        except Exception as e:
            return await self.handle_error(e, message)
    
    async def _suggest_next_steps(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Suggest next steps based on current state.
        
        Args:
            message: Message with current state and context
            
        Returns:
            Suggested next steps
        """
        context = message.get("context", {})
        current_state = message.get("current_state", "")
        
        self.log_event("suggest_steps_start", {"context": context})
        
        # Use LLM to suggest next steps
        suggestions = await self.llm_client.generate_suggestions(
            current_state,
            context
        )
        
        self.log_event("suggest_steps_complete", {
            "suggestion_count": len(suggestions)
        })
        
        return {
            "success": True,
            "suggestions": suggestions,
            "agent_id": self.agent_id
        }
    
    async def _track_progress(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Track progress of ongoing tasks.
        
        Args:
            message: Message with task progress data
            
        Returns:
            Progress tracking result
        """
        task_id = message.get("task_id")
        progress_data = message.get("progress_data", {})
        
        self.log_event("track_progress", {
            "task_id": task_id,
            "progress": progress_data
        })
        
        return {
            "success": True,
            "task_id": task_id,
            "progress_recorded": True,
            "agent_id": self.agent_id
        }
    
    async def _support_decision(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Provide decision support based on analysis.
        
        Args:
            message: Message with decision context
            
        Returns:
            Decision support result
        """
        decision_context = message.get("context", {})
        options = message.get("options", [])
        
        self.log_event("decision_support_start", {
            "context": decision_context,
            "options": options
        })
        
        # Use LLM to analyze options and provide recommendation
        recommendation = await self.llm_client.recommend_option(
            decision_context,
            options
        )
        
        self.log_event("decision_support_complete", {
            "recommendation": recommendation
        })
        
        return {
            "success": True,
            "recommendation": recommendation,
            "agent_id": self.agent_id
        }
