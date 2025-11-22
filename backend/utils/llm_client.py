"""LLM client for interacting with Gemini and other LLM providers."""
from typing import List, Dict, Any
import logging
import google.generativeai as genai
from backend.config import settings

logger = logging.getLogger(__name__)


class LLMClient:
    """Client for interacting with LLM services."""
    
    def __init__(self):
        genai.configure(api_key=settings.gemini_api_key)
        self.model = genai.GenerativeModel(settings.gemini_model)
    
    async def summarize(self, text: str) -> str:
        """Generate a summary of the given text.
        
        Args:
            text: Text to summarize
            
        Returns:
            Summary text
        """
        try:
            prompt = f"Please summarize the following text concisely:\n\n{text}"
            response = self.model.generate_content(prompt)
            
            summary = response.text
            logger.info("Generated summary")
            return summary
        except Exception as e:
            logger.error(f"Error generating summary: {e}")
            return f"Error generating summary: {str(e)}"
    
    async def extract_entities(self, text: str) -> List[Dict[str, Any]]:
        """Extract named entities from text.
        
        Args:
            text: Text to extract entities from
            
        Returns:
            List of extracted entities
        """
        try:
            prompt = f"""Extract named entities (people, organizations, locations, dates) from the following text.
Return them as a JSON list of objects with 'type' and 'value' fields.

Text:
{text}"""
            response = self.model.generate_content(prompt)
            
            entities_text = response.text
            logger.info("Extracted entities")
            
            # Try to parse JSON, fallback to simple list
            import json
            try:
                entities = json.loads(entities_text)
                return entities if isinstance(entities, list) else []
            except:
                return []
        except Exception as e:
            logger.error(f"Error extracting entities: {e}")
            return []
    
    async def generate_suggestions(
        self,
        current_state: str,
        context: Dict[str, Any]
    ) -> List[str]:
        """Generate next step suggestions based on current state.
        
        Args:
            current_state: Current workflow state
            context: Additional context
            
        Returns:
            List of suggested next steps
        """
        try:
            prompt = f"""Based on the current state and context, suggest 3-5 logical next steps.

Current State: {current_state}
Context: {context}

Return suggestions as a numbered list."""
            response = self.model.generate_content(prompt)
            
            suggestions_text = response.text
            logger.info("Generated suggestions")
            
            # Parse suggestions from numbered list
            suggestions = []
            for line in suggestions_text.split('\n'):
                line = line.strip()
                if line and (line[0].isdigit() or line.startswith('-') or line.startswith('•')):
                    # Remove numbering/bullets
                    suggestion = line.lstrip('0123456789.-•) ').strip()
                    if suggestion:
                        suggestions.append(suggestion)
            
            return suggestions[:5]  # Limit to 5 suggestions
        except Exception as e:
            logger.error(f"Error generating suggestions: {e}")
            return []
    
    async def recommend_option(
        self,
        context: Dict[str, Any],
        options: List[str]
    ) -> Dict[str, Any]:
        """Provide recommendation for decision making.
        
        Args:
            context: Decision context
            options: Available options
            
        Returns:
            Recommendation with reasoning
        """
        try:
            options_text = "\n".join([f"{i+1}. {opt}" for i, opt in enumerate(options)])
            prompt = f"""Analyze the following options and provide a recommendation.

Context: {context}

Options:
{options_text}

Provide your recommendation with reasoning."""
            response = self.model.generate_content(prompt)
            
            recommendation_text = response.text
            logger.info("Generated recommendation")
            
            return {
                "recommendation": recommendation_text,
                "options_analyzed": len(options)
            }
        except Exception as e:
            logger.error(f"Error generating recommendation: {e}")
            return {
                "recommendation": "Unable to generate recommendation",
                "error": str(e)
            }
    
    async def generate_rag_response(
        self,
        query: str,
        context_chunks: List[str],
        max_tokens: int = 1000
    ) -> str:
        """Generate response using RAG (Retrieval-Augmented Generation).
        
        Args:
            query: User query
            context_chunks: Retrieved context chunks
            max_tokens: Maximum tokens in response
            
        Returns:
            Generated response
        """
        try:
            context_text = "\n\n".join([f"Context {i+1}:\n{chunk}" for i, chunk in enumerate(context_chunks)])
            
            prompt = f"""Answer the following question based on the provided context. 
If the answer cannot be found in the context, say so.

Context:
{context_text}

Question: {query}

Answer:"""
            
            response = self.model.generate_content(prompt)
            
            answer = response.text
            logger.info("Generated RAG response")
            return answer
        except Exception as e:
            logger.error(f"Error generating RAG response: {e}")
            return f"Error generating response: {str(e)}"
