"""
services/llm_service.py
Centralized wrapper around Groq API's chat completions endpoint.

ALL LLM calls in this project go through this service.
Includes multi-level fallbacks:
  1. Primary model with JSON mode (response_format={"type": "json_object"}).
  2. Retry without response_format if Groq raises json_validate_failed / 400 error.
  3. Automatic candidate model fallback if primary model is unavailable or fails.
  4. Robust extraction via utils.json_parser.
"""

import logging
from config import config
from utils.json_parser import extract_json

logger = logging.getLogger("crisis_agent.llm")

try:
    from groq import Groq
except ImportError:  # pragma: no cover
    Groq = None


class LLMServiceError(Exception):
    """Raised when Groq API cannot produce any usable response across all attempts."""
    pass


DEFAULT_FALLBACK_MODELS = [
    "openai/gpt-oss-120b",
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "mixtral-8x7b-32768",
    "gemma2-9b-it",
]


class LLMService:
    def __init__(self, api_key: str = None, model: str = None, timeout: int = None):
        self.api_key = (api_key or config.GROQ_API_KEY or "").strip()
        self.model = (model or config.GROQ_MODEL or "openai/gpt-oss-120b").strip()
        self.timeout = timeout or config.GROQ_TIMEOUT or 60
        self._client = None

        if self.api_key and Groq is not None:
            self._client = Groq(api_key=self.api_key)

    def is_available(self) -> bool:
        """True if a Groq API key is configured and Groq SDK is installed."""
        return self._client is not None

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
        json_mode: bool = True,
        max_tokens: int = 2048,
    ) -> str:
        """
        Sends a chat completion request to Groq and returns the raw text output.
        Handles JSON validation failures, model fallbacks, and timeouts cleanly.
        """
        if Groq is None:
            raise LLMServiceError(
                "The 'groq' package is not installed. Run: pip install groq"
            )
        if not self._client:
            raise LLMServiceError(
                "GROQ_API_KEY is not configured. Add it to your .env file."
            )

        candidate_models = [self.model]
        for fb in DEFAULT_FALLBACK_MODELS:
            if fb not in candidate_models:
                candidate_models.append(fb)

        last_exception = None

        for model in candidate_models:
            # Step A: Attempt with json_mode if requested
            if json_mode:
                text = self._call_groq_single(
                    model=model,
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    use_json_format=True,
                )
                if text:
                    if model != self.model:
                        logger.info("Fell back to working Groq model: %s", model)
                        self.model = model
                    return text

                # Step B: If json_format failed (e.g. json_validate_failed), retry without response_format
                logger.warning(
                    "Model '%s' failed with response_format json_object. Retrying plain text mode...",
                    model,
                )
                text = self._call_groq_single(
                    model=model,
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    use_json_format=False,
                )
                if text:
                    if model != self.model:
                        logger.info("Fell back to working Groq model (plain text): %s", model)
                        self.model = model
                    return text
            else:
                text = self._call_groq_single(
                    model=model,
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    use_json_format=False,
                )
                if text:
                    if model != self.model:
                        logger.info("Fell back to working Groq model: %s", model)
                        self.model = model
                    return text

        raise LLMServiceError(
            f"Groq API call failed across all candidate models ({candidate_models}). Check API key, quotas, or model availability."
        )

    def _call_groq_single(
        self,
        model: str,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        max_tokens: int,
        use_json_format: bool,
    ) -> str:
        """Executes a single Groq API call. Returns text string on success, None on error."""
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
        if use_json_format:
            kwargs["response_format"] = {"type": "json_object"}

        try:
            completion = self._client.chat.completions.create(**kwargs)
            if completion and completion.choices and len(completion.choices) > 0:
                content = completion.choices[0].message.content
                if content and content.strip():
                    return content.strip()
            logger.warning("Groq model '%s' returned empty content.", model)
            return ""
        except Exception as exc:
            err_msg = str(exc)
            logger.warning(
                "Groq model '%s' call failed (use_json_format=%s): %s",
                model,
                use_json_format,
                err_msg,
            )
            return ""

    def generate_json(
        self,
        system_prompt: str,
        user_prompt: str,
        default_dict: dict = None,
        temperature: float = 0.2,
    ) -> dict:
        """
        High-level helper: Calls generate(...) and parses the response into a dict.
        Guarantees a dictionary return (default_dict or {}) even if LLM fails completely.
        """
        fallback_data = dict(default_dict) if default_dict is not None else {}
        try:
            raw_text = self.generate(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=temperature,
                json_mode=True,
            )
            parsed = extract_json(raw_text)
            if parsed and isinstance(parsed, dict):
                return parsed
            logger.warning("Failed to parse valid dict from Groq output. Raw: %.150s", raw_text)
        except Exception as exc:
            logger.error("generate_json encountered exception: %s", exc)

        return fallback_data
