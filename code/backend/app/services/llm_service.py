import google.generativeai as genai
from typing import Dict, Any, List
from utils.logger import get_logger, log_token_usage
from core.config import get_settings

logger = get_logger("llm")
settings = get_settings()

# Configure Gemini globally from ENV / .env
genai.configure(api_key=settings.google_api_key)


class LLMService:
    """
    Service for interacting with Gemini LLMs.
    Provides both natural language generation (RAG answers)
    and embeddings (for vector search with Milvus).
    """

    def __init__(self):
        self.model_name = settings.gemini_model
        self.temperature = settings.gemini_temperature

    async def generate_response(
        self, prompt: str, max_tokens: int = 512
    ) -> Dict[str, Any]:
        """
        Uses Gemini to generate a text response to the given prompt.
        """
        logger.info("Generating LLM response", extra={"prompt_length": len(prompt)})

        try:
            model = genai.GenerativeModel(self.model_name)

            response = model.generate_content(
                prompt,
                generation_config={
                    "max_output_tokens": max_tokens,
                    "temperature": self.temperature,
                },
            )

            # Some Gemini responses may have multiple candidates;
            # take the first text output.
            answer = response.text or ""

            # Gemini doesn’t return token counts yet; approximate.
            usage = {
                "model": self.model_name,
                "prompt_tokens": len(prompt.split()),
                "completion_tokens": len(answer.split()),
            }
            usage["total_tokens"] = usage["prompt_tokens"] + usage["completion_tokens"]

            # Log token usage
            log_token_usage(**usage)

            return {
                "answer": answer,
                "usage": usage,
            }

        except Exception as e:
            logger.error("LLM generation failed", exc_info=True)
            raise RuntimeError(f"LLMService error: {str(e)}")

    async def embed_text(self, text: str) -> List[float]:
        """
        Uses Gemini embedding model to convert text into a vector embedding.
        This is essential before storing content in Milvus.
        """
        logger.info("Generating embedding", extra={"text_length": len(text)})

        try:
            # Gemini embeddings are a separate endpoint
            embedding_response = genai.embed_content(
                model="models/embedding-001",  # Gemini embedding model
                content=text,
            )

            embedding = embedding_response["embedding"]
            logger.debug(
                "Generated embedding", extra={"dims": len(embedding)}
            )
            return embedding

        except Exception as e:
            logger.error("LLM embedding failed", exc_info=True)
            raise RuntimeError(f"LLMService embed error: {str(e)}")