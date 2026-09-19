"""
services/llm_service.py
Reusable wrapper around the Groq API's chat completions endpoint.

This is the ONLY place in the project that talks to the LLM. Every agent
calls LLMService.generate(...), so swapping models / providers stays a
one-file change. Ollama is intentionally NOT used anywhere in this project.
"""

import logging

from config import config

logger = logging.getLogger("crisis_agent.llm")

try:
    from groq import Groq
except ImportError:  # pragma: no cover
    Groq = None


class LLMServiceError(Exception):
    """Raised when Groq cannot be reached or returns something unusable."""
    pass


class LLMService:
    def __init__(self, api_key: str = None, model: str = None, timeout: int = None):
        self.api_key = api_key or config.GROQ_API_KEY
        self.model = model or config.GROQ_MODEL
        self.timeout = timeout or config.GROQ_TIMEOUT
        self._client = None

        if self.api_key and Groq is not None:
            self._client = Groq(api_key=self.api_key)

    def is_available(self) -> bool:
        """True if a Groq API key is configured (no network call needed)."""
        return self._client is not None

    def generate(self, system_prompt: str, user_prompt: str, temperature: float = 0.2,
                 json_mode: bool = True, max_tokens: int = 1024) -> str:
        """
        Sends a chat completion request to Groq and returns the raw text
        response. Raises LLMServiceError on any failure so calling agents
        can handle it gracefully (fallback / error message).
        """
        if Groq is None:
            raise LLMServiceError(
                "The 'groq' package is not installed. Run: pip install groq"
            )
        if not self._client:
            raise LLMServiceError(
                "GROQ_API_KEY is not configured. Add it to your .env file "
                "(get a free key at https://console.groq.com/keys)."
            )

        candidate_models = [self.model]
        for fb in ["openai/gpt-oss-120b", "openai/gpt-oss-20b", "qwen/qwen3.8-27b", "groq/compound"]:
            if fb not in candidate_models:
                candidate_models.append(fb)

        last_exception = None
        for model in candidate_models:
            kwargs = dict(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=self.timeout,
            )
            if json_mode:
                kwargs["response_format"] = {"type": "json_object"}

            try:
                completion = self._client.chat.completions.create(**kwargs)
                text = completion.choices[0].message.content
                if text and text.strip():
                    if model != self.model:
                        logger.info("Fell back to working Groq model: %s", model)
                        self.model = model
                    return text.strip()
            except Exception as exc:
                last_exception = exc
                logger.warning("Groq API call for model '%s' failed: %s", model, exc)
                if "model_not_found" in str(exc).lower() or "404" in str(exc):
                    continue
                raise LLMServiceError(f"Groq API error: {exc}") from exc

        raise LLMServiceError(f"Groq API error across all models: {last_exception}") from last_exception
