"""LLM client for interacting with Gemini and other LLM providers."""
from __future__ import annotations

import asyncio
import json
import logging
import threading
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence, Tuple

import google.generativeai as genai
from google.api_core import exceptions as gexc

from backend.config import settings

logger = logging.getLogger(__name__)
_GENAI_LOCK = threading.RLock()


class GeminiAPIError(RuntimeError):
    """Base error for Gemini API failures."""

    status_code = 500
    error_code = "gemini_error"

    def __init__(
        self,
        message: str,
        *,
        error_code: Optional[str] = None,
        status_code: Optional[int] = None,
        attempts: Optional[List[Dict[str, Any]]] = None,
        active_model: Optional[str] = None,
    ):
        super().__init__(message)
        self.error_code = error_code or self.error_code
        self.status_code = status_code or self.status_code
        self.attempts = attempts or []
        self.active_model = active_model


class GeminiInvalidKeyError(GeminiAPIError):
    status_code = 401
    error_code = "invalid_api_key"


class GeminiExpiredKeyError(GeminiAPIError):
    status_code = 401
    error_code = "expired_api_key"


class GeminiRateLimitError(GeminiAPIError):
    status_code = 429
    error_code = "rate_limited"


class GeminiModelUnavailableError(GeminiAPIError):
    status_code = 503
    error_code = "model_unavailable"


class GeminiTransientError(GeminiAPIError):
    status_code = 503
    error_code = "transient_error"


class GeminiConfigurationError(GeminiAPIError):
    status_code = 503
    error_code = "gemini_not_configured"


@dataclass
class GeminiStatus:
    """Human-readable Gemini health status."""

    status: str
    model_status: str
    message: str
    active_model: Optional[str] = None
    fallback_models: List[str] = field(default_factory=list)
    available_models: List[str] = field(default_factory=list)
    checked_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _dedupe_models(models: Sequence[str]) -> List[str]:
    ordered: List[str] = []
    for model in models:
        cleaned = model.strip()
        if cleaned and cleaned not in ordered:
            ordered.append(cleaned)
    return ordered


def _resolve_model_candidates(model_candidates: Optional[Sequence[str]] = None) -> List[str]:
    if model_candidates is None:
        return list(settings.gemini_model_chain)

    if isinstance(model_candidates, str):
        raw_models = [part.strip() for part in model_candidates.split(",")]
    else:
        raw_models = [str(model).strip() for model in model_candidates]
    return _dedupe_models(raw_models)


def _normalize_model_name(model_name: str) -> str:
    return model_name.rsplit("/", 1)[-1].strip().lower()


def _model_matches(candidate: str, discovered_name: str) -> bool:
    candidate_name = _normalize_model_name(candidate)
    discovered = _normalize_model_name(discovered_name)
    return (
        discovered == candidate_name
        or discovered.startswith(candidate_name)
        or candidate_name in discovered
    )


def _make_generation_config(
    *,
    temperature: float,
    max_output_tokens: Optional[int] = None,
) -> Any:
    config_kwargs: Dict[str, Any] = {"temperature": temperature}
    if max_output_tokens is not None:
        config_kwargs["max_output_tokens"] = max_output_tokens
    return genai.types.GenerationConfig(**config_kwargs)


def _classify_gemini_exception(exc: Exception) -> Tuple[str, str, int]:
    message = str(exc).strip() or exc.__class__.__name__
    lowered = message.lower()

    if isinstance(exc, gexc.Unauthenticated):
        if any(token in lowered for token in ("expired", "revoked")):
            return "expired_api_key", "The Gemini API key appears to be expired or revoked.", 401
        return "invalid_api_key", "The Gemini API key is invalid or unauthorized.", 401

    if isinstance(exc, gexc.PermissionDenied):
        if any(token in lowered for token in ("expired", "revoked")):
            return "expired_api_key", "The Gemini API key appears to be expired or revoked.", 401
        if any(token in lowered for token in ("quota", "rate limit", "rate-limit", "exceeded", "resource exhausted")):
            return "rate_limited", "Gemini quota or rate limit has been exceeded.", 429
        if any(token in lowered for token in ("model", "not available", "not found", "unsupported")):
            return "model_unavailable", "That Gemini model is not available for this key.", 503
        if any(token in lowered for token in ("invalid api key", "api key not valid", "unauthenticated", "invalid credentials", "permission denied")):
            return "invalid_api_key", "The Gemini API key does not have permission to access Gemini.", 401
        return "model_unavailable", "That Gemini model is not available for this key.", 503

    if isinstance(exc, gexc.ResourceExhausted):
        return "rate_limited", "Gemini quota or rate limit has been exceeded.", 429

    if isinstance(exc, (gexc.NotFound, gexc.InvalidArgument, gexc.FailedPrecondition)):
        if any(token in lowered for token in ("model", "not found", "not available", "unsupported")):
            return "model_unavailable", "That Gemini model is not available for this key.", 503
        if any(token in lowered for token in ("quota", "rate limit", "rate-limit", "exceeded", "resource exhausted")):
            return "rate_limited", "Gemini quota or rate limit has been exceeded.", 429
        return "model_unavailable", "That Gemini model is not available for this key.", 503

    if isinstance(exc, (gexc.ServiceUnavailable, gexc.DeadlineExceeded)):
        return "transient_error", "Gemini is temporarily unavailable.", 503

    if any(token in lowered for token in ("expired", "revoked")):
        return "expired_api_key", "The Gemini API key appears to be expired or revoked.", 401
    if any(token in lowered for token in ("invalid api key", "api key not valid", "unauthenticated", "invalid credentials")):
        return "invalid_api_key", "The Gemini API key is invalid or unauthorized.", 401
    if any(token in lowered for token in ("quota", "rate limit", "rate-limit", "exceeded", "resource exhausted")):
        return "rate_limited", "Gemini quota or rate limit has been exceeded.", 429

    return "unknown_error", message, 503


def _exception_to_error(
    code: str,
    message: str,
    attempts: Optional[List[Dict[str, Any]]] = None,
    active_model: Optional[str] = None,
) -> GeminiAPIError:
    if code == "expired_api_key":
        return GeminiExpiredKeyError(message, attempts=attempts, active_model=active_model)
    if code == "invalid_api_key":
        return GeminiInvalidKeyError(message, attempts=attempts, active_model=active_model)
    if code == "rate_limited":
        return GeminiRateLimitError(message, attempts=attempts, active_model=active_model)
    if code == "model_unavailable":
        return GeminiModelUnavailableError(message, attempts=attempts, active_model=active_model)
    if code == "transient_error":
        return GeminiTransientError(message, attempts=attempts, active_model=active_model)
    if code == "gemini_not_configured":
        return GeminiConfigurationError(message, attempts=attempts, active_model=active_model)
    return GeminiAPIError(message, error_code=code, status_code=503, attempts=attempts, active_model=active_model)


def _summarize_attempts(attempts: List[Dict[str, Any]]) -> str:
    if not attempts:
        return "Gemini generation failed."
    details = "; ".join(f"{attempt['model']}: {attempt['message']}" for attempt in attempts)
    return f"Gemini generation failed after trying: {details}"


def _probe_accessible_models(api_key: str) -> List[str]:
    with _GENAI_LOCK:
        genai.configure(api_key=api_key)
        models = list(genai.list_models())

    accessible: List[str] = []
    for model in models:
        model_name = _normalize_model_name(getattr(model, "name", ""))
        if not model_name:
            continue

        supported_methods = {
            str(method).lower()
            for method in getattr(model, "supported_generation_methods", []) or []
        }
        if supported_methods and "generatecontent" not in supported_methods:
            continue

        accessible.append(model_name)

    return accessible


def _generate_content_with_model(
    api_key: str,
    model_name: str,
    prompt: str,
    generation_config: Any,
) -> str:
    with _GENAI_LOCK:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(prompt, generation_config=generation_config)
    return (getattr(response, "text", "") or "").strip()


def probe_gemini_status(
    api_key: Optional[str],
    model_candidates: Optional[Sequence[str]] = None,
) -> Dict[str, Any]:
    """Check whether a Gemini key can see and use the configured models."""
    candidates = _resolve_model_candidates(model_candidates)
    fallback_models = candidates[1:]

    if not api_key:
        return GeminiStatus(
            status="missing",
            model_status="unavailable",
            message="No Gemini API key has been saved yet.",
            active_model=None,
            fallback_models=fallback_models,
            available_models=[],
        ).to_dict()

    try:
        accessible_models = _probe_accessible_models(api_key)
    except Exception as exc:
        code, message, _ = _classify_gemini_exception(exc)
        status = "unknown"
        if code == "invalid_api_key":
            status = "invalid"
        elif code == "expired_api_key":
            status = "expired"
        elif code == "rate_limited":
            status = "rate_limited"
        elif code == "model_unavailable":
            status = "unsupported"
        return GeminiStatus(
            status=status,
            model_status="unavailable",
            message=message,
            active_model=None,
            fallback_models=fallback_models,
            available_models=[],
        ).to_dict()

    matched_models = [
        candidate
        for candidate in candidates
        if any(_model_matches(candidate, discovered) for discovered in accessible_models)
    ]

    if matched_models:
        active_model = matched_models[0]
        if active_model == candidates[0]:
            return GeminiStatus(
                status="healthy",
                model_status="primary",
                message=f"Gemini key is valid. Using {active_model}.",
                active_model=active_model,
                fallback_models=fallback_models,
                available_models=matched_models,
            ).to_dict()

        return GeminiStatus(
            status="degraded",
            model_status="fallback",
            message=(
                f"Preferred model {candidates[0]} is unavailable for this key. "
                f"Using {active_model} instead."
            ),
            active_model=active_model,
            fallback_models=fallback_models,
            available_models=matched_models,
        ).to_dict()

    if accessible_models:
        message = (
            "The Gemini key is valid, but none of the configured models are available. "
            f"Configured priority: {', '.join(candidates)}."
        )
    else:
        message = (
            "The Gemini key is valid, but no supported Gemini models were returned for this key."
        )

    return GeminiStatus(
        status="unsupported",
        model_status="unavailable",
        message=message,
        active_model=None,
        fallback_models=fallback_models,
        available_models=[],
    ).to_dict()


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------

class LLMClient:
    """Client for interacting with LLM services."""

    def __init__(self, api_key: str = None, model_candidates: Optional[Sequence[str]] = None):
        self.api_key = api_key or settings.gemini_api_key
        self.model_candidates = _resolve_model_candidates(model_candidates)

    def get_status(self) -> Dict[str, Any]:
        """Probe the effective key and configured model chain."""
        return probe_gemini_status(self.api_key, self.model_candidates)

    def _run_prompt(
        self,
        prompt: str,
        *,
        temperature: float,
        max_output_tokens: Optional[int] = None,
    ) -> str:
        effective_key = self.api_key or settings.gemini_api_key
        if not effective_key:
            raise GeminiConfigurationError("No Gemini API key is configured.")

        generation_config = _make_generation_config(
            temperature=temperature,
            max_output_tokens=max_output_tokens,
        )

        attempts: List[Dict[str, Any]] = []
        for model_name in self.model_candidates:
            try:
                text = _generate_content_with_model(
                    effective_key,
                    model_name,
                    prompt,
                    generation_config,
                )
                if attempts:
                    logger.info(
                        "Gemini fallback succeeded after %s failed attempt(s); active model=%s",
                        len(attempts),
                        model_name,
                    )
                return text
            except Exception as exc:
                code, message, _ = _classify_gemini_exception(exc)
                attempts.append({"model": model_name, "error_code": code, "message": message})
                logger.warning("Gemini model %s failed: %s", model_name, message)
                if code in {"invalid_api_key", "expired_api_key"}:
                    raise _exception_to_error(code, message, attempts=attempts, active_model=model_name) from exc

        if not attempts:
            raise GeminiConfigurationError("No Gemini models were configured.")

        final_code = self._select_final_error_code(attempts)
        final_message = _summarize_attempts(attempts)
        raise _exception_to_error(final_code, final_message, attempts=attempts) from None

    @staticmethod
    def _select_final_error_code(attempts: List[Dict[str, Any]]) -> str:
        priorities = [
            "expired_api_key",
            "invalid_api_key",
            "rate_limited",
            "transient_error",
            "model_unavailable",
            "unknown_error",
        ]
        present_codes = {attempt["error_code"] for attempt in attempts}
        for code in priorities:
            if code in present_codes:
                return code
        return "unknown_error"

    async def summarize(self, text: str) -> str:
        """Generate a summary of the given text."""
        try:
            prompt = (
                "Please provide a clear, comprehensive summary of the following document. "
                "Include the main topics, key findings, and important details.\n\n"
                f"{text}"
            )
            return await asyncio.to_thread(
                self._run_prompt,
                prompt,
                temperature=settings.gemini_temperature,
                max_output_tokens=1024,
            )
        except GeminiAPIError:
            raise
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
            raw = await asyncio.to_thread(
                self._run_prompt,
                prompt,
                temperature=0.0,
                max_output_tokens=512,
            )
            try:
                entities = json.loads(_strip_code_fences(raw))
                return entities if isinstance(entities, list) else []
            except json.JSONDecodeError:
                return []
        except GeminiAPIError:
            raise
        except Exception as e:
            logger.error(f"Error extracting entities: {e}")
            return []

    async def generate_rag_response(
        self,
        query: str,
        context_chunks: List[Dict[str, Any]],
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        max_tokens: int = 1000,
    ) -> str:
        """Generate response using RAG (Retrieval-Augmented Generation)."""
        try:
            context_sections = []
            for i, chunk in enumerate(context_chunks, start=1):
                if isinstance(chunk, dict):
                    text = chunk.get("text", "")
                    citation = chunk.get("citation", {}) or {}
                    label = citation.get("citation_label") or f"Source {i}"
                    document_name = citation.get("document_name", "Document")
                    page_number = citation.get("page_number")
                    chunk_index = citation.get("chunk_index")
                    location_bits = []
                    if page_number is not None:
                        location_bits.append(f"page {page_number}")
                    if chunk_index is not None:
                        location_bits.append(f"chunk {chunk_index}")
                    location_text = ", ".join(location_bits) if location_bits else "location unavailable"
                    context_sections.append(
                        f"Source {i} — {label} | {document_name} ({location_text})\n{text}"
                    )
                else:
                    context_sections.append(f"Source {i}\n{chunk}")

            context_text = "\n\n".join(context_sections)
            conversation_sections = []
            for i, turn in enumerate(conversation_history or [], start=1):
                user_text = turn.get("query") or turn.get("user") or ""
                assistant_text = turn.get("response") or turn.get("assistant") or ""
                if not user_text and not assistant_text:
                    continue
                conversation_sections.append(
                    f"Turn {i}\nUser: {user_text}\nAssistant: {assistant_text}".strip()
                )

            prompt_sections = [
                "Answer the user's follow-up question using only the provided sources.",
                "Use the conversation history to resolve references like 'it', 'this', or 'that'.",
                "Cite every factual claim inline with the matching source number, like [1] or [2].",
                "If the answer cannot be found in the sources, say so clearly.",
            ]
            if conversation_sections:
                prompt_sections.append("Conversation history:\n" + "\n\n".join(conversation_sections))
            prompt_sections.append(f"Context:\n{context_text}")
            prompt_sections.append(f"Question: {query}\n\nAnswer:")
            prompt = "\n\n".join(prompt_sections)

            return await asyncio.to_thread(
                self._run_prompt,
                prompt,
                temperature=settings.gemini_temperature,
                max_output_tokens=max_tokens,
            )
        except GeminiAPIError:
            raise
        except Exception as e:
            logger.error(f"Error generating RAG response: {e}")
            return f"Error generating response: {str(e)}"

    # ------------------------------------------------------------------
    # New feature capabilities
    # ------------------------------------------------------------------

    async def generate_quiz(self, text: str, num_questions: int = 10) -> List[Dict[str, Any]]:
        """Generate quiz questions from document content."""
        raw = ""
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
            raw = await asyncio.to_thread(
                self._run_prompt,
                prompt,
                temperature=0.0,
                max_output_tokens=4096,
            )
            raw = _strip_code_fences(raw)
            return json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("Quiz response was not valid JSON, returning raw text")
            return [{"question": raw, "options": [], "correct_answer": "", "explanation": ""}]
        except GeminiAPIError:
            raise
        except Exception as e:
            logger.error(f"Error generating quiz: {e}")
            return []

    async def generate_mindmap(self, text: str) -> Dict[str, Any]:
        """Generate a mind map structure (nodes + edges) from document content."""
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
            raw = await asyncio.to_thread(
                self._run_prompt,
                prompt,
                temperature=0.0,
                max_output_tokens=4096,
            )
            raw = _strip_code_fences(raw)
            return json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("Mindmap response was not valid JSON")
            return {"central_topic": "Unknown", "nodes": [], "edges": []}
        except GeminiAPIError:
            raise
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
            raw = await asyncio.to_thread(
                self._run_prompt,
                prompt,
                temperature=settings.gemini_temperature,
                max_output_tokens=512,
            )
            suggestions = []
            for line in raw.split("\n"):
                line = line.strip()
                if line and (line[0].isdigit() or line.startswith('-') or line.startswith('•')):
                    suggestion = line.lstrip('0123456789.-•) ').strip()
                    if suggestion:
                        suggestions.append(suggestion)
            return suggestions[:5]
        except GeminiAPIError:
            raise
        except Exception as e:
            logger.error(f"Error generating suggestions: {e}")
            return []

    async def recommend_option(
        self, context: Dict[str, Any], options: List[str]
    ) -> Dict[str, Any]:
        """Provide recommendation for decision making."""
        try:
            options_text = "\n".join(f"{i + 1}. {opt}" for i, opt in enumerate(options))
            prompt = (
                "Analyze the following options and provide a recommendation.\n\n"
                f"Context: {context}\n\nOptions:\n{options_text}\n\n"
                "Provide your recommendation with reasoning."
            )
            raw = await asyncio.to_thread(
                self._run_prompt,
                prompt,
                temperature=settings.gemini_temperature,
                max_output_tokens=512,
            )
            return {"recommendation": raw, "options_analyzed": len(options)}
        except GeminiAPIError:
            raise
        except Exception as e:
            logger.error(f"Error generating recommendation: {e}")
            return {"recommendation": "Unable to generate recommendation", "error": str(e)}


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def _strip_code_fences(text: str) -> str:
    raw = text.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1] if "\n" in raw else raw
        raw = raw.rsplit("```", 1)[0]
    return raw.strip()
