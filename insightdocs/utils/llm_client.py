"""LLM client for interacting with OpenAI and other LLM providers."""
from typing import List, Dict, Any
import logging
from openai import AsyncOpenAI
from insightdocs.config import settings

logger = logging.getLogger(__name__)


class LLMClient:
    """Client for interacting with LLM services."""
    
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.model = "gpt-3.5-turbo"
    
    async def summarize(self, text: str) -> str:
        """Generate a summary of the given text.
        
        Args:
            text: Text to summarize
            
        Returns:
            Summary text
        """
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful assistant that summarizes documents concisely."
                    },
                    {
                        "role": "user",
                        "content": f"Please summarize the following text:\n\n{text}"
                    }
                ],
                max_tokens=500,
                temperature=0.7
            )
            
            summary = response.choices[0].message.content
            logger.info("Generated summary")
            return summary
        except Exception as e:
            logger.error(f"Error generating summary: {e}")
            return f"Error generating summary: {str(e)}"
    
    async def extract_entities(self, text: str) -> List[Dict[str, Any]]:
        """Extract entities from text.
        
        Args:
            text: Text to extract entities from
            
        Returns:
            List of extracted entities
        """
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful assistant that extracts key entities (people, organizations, locations, dates) from text. Return results as a JSON list."
                    },
                    {
                        "role": "user",
                        "content": f"Extract entities from:\n\n{text}"
                    }
                ],
                max_tokens=500,
                temperature=0.3
            )
            
            entities_text = response.choices[0].message.content
            logger.info("Extracted entities")
            
            # Simple parsing - in production, parse JSON properly
            return [{"entity": entities_text}]
        except Exception as e:
            logger.error(f"Error extracting entities: {e}")
            return []
    
    async def generate_suggestions(
        self,
        current_state: str,
        context: Dict[str, Any]
    ) -> List[str]:
        """Generate next step suggestions.
        
        Args:
            current_state: Current state description
            context: Additional context
            
        Returns:
            List of suggested next steps
        """
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful assistant that suggests next steps in a workflow."
                    },
                    {
                        "role": "user",
                        "content": f"Current state: {current_state}\nContext: {context}\n\nSuggest 3-5 next steps."
                    }
                ],
                max_tokens=300,
                temperature=0.7
            )
            
            suggestions_text = response.choices[0].message.content
            suggestions = [s.strip() for s in suggestions_text.split('\n') if s.strip()]
            logger.info(f"Generated {len(suggestions)} suggestions")
            return suggestions
        except Exception as e:
            logger.error(f"Error generating suggestions: {e}")
            return []
    
    async def recommend_option(
        self,
        context: Dict[str, Any],
        options: List[str]
    ) -> Dict[str, Any]:
        """Recommend an option based on context.
        
        Args:
            context: Decision context
            options: Available options
            
        Returns:
            Recommendation with reasoning
        """
        try:
            options_text = "\n".join([f"{i+1}. {opt}" for i, opt in enumerate(options)])
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful assistant that provides decision support."
                    },
                    {
                        "role": "user",
                        "content": f"Context: {context}\n\nOptions:\n{options_text}\n\nWhich option is best and why?"
                    }
                ],
                max_tokens=300,
                temperature=0.5
            )
            
            recommendation = response.choices[0].message.content
            logger.info("Generated recommendation")
            return {
                "recommendation": recommendation,
                "options_considered": len(options)
            }
        except Exception as e:
            logger.error(f"Error generating recommendation: {e}")
            return {"error": str(e)}
    
    async def generate_rag_response(
        self,
        query: str,
        context_chunks: List[str]
    ) -> str:
        """Generate a RAG response using retrieved context.
        
        Args:
            query: User query
            context_chunks: Retrieved context chunks
            
        Returns:
            Generated response
        """
        try:
            context = "\n\n".join([f"[{i+1}] {chunk}" for i, chunk in enumerate(context_chunks)])
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful assistant that answers questions based on provided context. Always cite your sources using [number] notation."
                    },
                    {
                        "role": "user",
                        "content": f"Context:\n{context}\n\nQuestion: {query}\n\nAnswer:"
                    }
                ],
                max_tokens=500,
                temperature=0.7
            )
            
            answer = response.choices[0].message.content
            logger.info("Generated RAG response")
            return answer
        except Exception as e:
            logger.error(f"Error generating RAG response: {e}")
            return f"Error generating response: {str(e)}"
