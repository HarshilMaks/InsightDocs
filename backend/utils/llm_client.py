"""LLM client for interacting with Gemini and other LLM providers."""
from typing import List, Dict, Any
import json
import logging
import google.generativeai as genai
from backend.config import settings

logger = logging.getLogger(__name__)


class LLMClient:
    """Client for interacting with LLM services."""

    def __init__(self):
        genai.configure(api_key=settings.gemini_api_key)
        self.model = genai.GenerativeModel(settings.gemini_model)

    # ------------------------------------------------------------------
    # Core capabilities
    # ------------------------------------------------------------------

    async def summarize(self, text: str) -> str:
        """Generate a summary of the given text."""
        try:
            prompt = (
                "Please provide a clear, comprehensive summary of the following document. "
                "Include the main topics, key findings, and important details.\n\n"
                f"{text}"
            )
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            logger.error(f"Error generating summary: {e}")
            return f"Error generating summary: {str(e)}"

    async def extract_entities(self, text: str) -> List[Dict[str, Any]]:
        """Extract named entities from text."""
        try:
            prompt = (
                "Extract named entities (people, organizations, locations, dates) "
                "from the following text. Return them as a JSON list of objects "
                "with 'type' and 'value' fields.\n\n"
                f"Text:\n{text}"
            )
            response = self.model.generate_content(prompt)
            try:
                entities = json.loads(response.text)
                return entities if isinstance(entities, list) else []
            except json.JSONDecodeError:
                return []
        except Exception as e:
            logger.error(f"Error extracting entities: {e}")
            return []

    async def generate_rag_response(
        self, query: str, context_chunks: List[str], max_tokens: int = 1000
    ) -> str:
        """Generate response using RAG (Retrieval-Augmented Generation)."""
        try:
            context_text = "\n\n".join(
                f"Context {i+1}:\n{chunk}" for i, chunk in enumerate(context_chunks)
            )
            prompt = (
                "Answer the following question based on the provided context. "
                "If the answer cannot be found in the context, say so.\n\n"
                f"Context:\n{context_text}\n\n"
                f"Question: {query}\n\nAnswer:"
            )
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            logger.error(f"Error generating RAG response: {e}")
            return f"Error generating response: {str(e)}"

    # ------------------------------------------------------------------
    # New feature capabilities
    # ------------------------------------------------------------------

    async def generate_quiz(self, text: str, num_questions: int = 10) -> List[Dict[str, Any]]:
        """Generate quiz questions from document content.

        Returns a list of {question, options, correct_answer, explanation}.
        """
        try:
            prompt = (
                f"Based on the following document content, generate {num_questions} "
                "multiple-choice quiz questions to test understanding.\n\n"
                "Return ONLY a JSON array where each element has:\n"
                '  "question": the question text,\n'
                '  "options": ["A) ...", "B) ...", "C) ...", "D) ..."],\n'
                '  "correct_answer": the letter of the correct option (e.g. "A"),\n'
                '  "explanation": a brief explanation of why that answer is correct.\n\n'
                f"Document:\n{text[:12000]}"
            )
            response = self.model.generate_content(prompt)
            # Strip markdown code fences if present
            raw = response.text.strip()
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[1]  # remove first line
                raw = raw.rsplit("```", 1)[0]  # remove last fence
            return json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("Quiz response was not valid JSON, returning raw text")
            return [{"question": response.text, "options": [], "correct_answer": "", "explanation": ""}]
        except Exception as e:
            logger.error(f"Error generating quiz: {e}")
            return []

    async def generate_mindmap(self, text: str) -> Dict[str, Any]:
        """Generate a mind map structure (nodes + edges) from document content.

        Returns {central_topic, nodes: [{id, label, group}], edges: [{source, target, label}]}.
        """
        try:
            prompt = (
                "Analyze the following document and extract a mind map structure.\n\n"
                "Return ONLY a JSON object with:\n"
                '  "central_topic": the main topic of the document,\n'
                '  "nodes": an array of {"id": "n1", "label": "concept", "group": "category"},\n'
                '  "edges": an array of {"source": "n1", "target": "n2", "label": "relationship"}.\n\n'
                "Include 10-20 key concepts as nodes and their relationships as edges.\n\n"
                f"Document:\n{text[:12000]}"
            )
            response = self.model.generate_content(prompt)
            raw = response.text.strip()
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[1]
                raw = raw.rsplit("```", 1)[0]
            return json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("Mindmap response was not valid JSON")
            return {"central_topic": "Unknown", "nodes": [], "edges": []}
        except Exception as e:
            logger.error(f"Error generating mindmap: {e}")
            return {"central_topic": "Error", "nodes": [], "edges": []}

    # ------------------------------------------------------------------
    # Planning agent support
    # ------------------------------------------------------------------

    async def generate_suggestions(
        self, current_state: str, context: Dict[str, Any]
    ) -> List[str]:
        """Generate next step suggestions based on current state."""
        try:
            prompt = (
                "Based on the current state and context, suggest 3-5 logical next steps.\n\n"
                f"Current State: {current_state}\nContext: {context}\n\n"
                "Return suggestions as a numbered list."
            )
            response = self.model.generate_content(prompt)
            suggestions = []
            for line in response.text.split('\n'):
                line = line.strip()
                if line and (line[0].isdigit() or line.startswith('-') or line.startswith('•')):
                    suggestion = line.lstrip('0123456789.-•) ').strip()
                    if suggestion:
                        suggestions.append(suggestion)
            return suggestions[:5]
        except Exception as e:
            logger.error(f"Error generating suggestions: {e}")
            return []

    async def recommend_option(
        self, context: Dict[str, Any], options: List[str]
    ) -> Dict[str, Any]:
        """Provide recommendation for decision making."""
        try:
            options_text = "\n".join(f"{i+1}. {opt}" for i, opt in enumerate(options))
            prompt = (
                "Analyze the following options and provide a recommendation.\n\n"
                f"Context: {context}\n\nOptions:\n{options_text}\n\n"
                "Provide your recommendation with reasoning."
            )
            response = self.model.generate_content(prompt)
            return {"recommendation": response.text, "options_analyzed": len(options)}
        except Exception as e:
            logger.error(f"Error generating recommendation: {e}")
            return {"recommendation": "Unable to generate recommendation", "error": str(e)}
