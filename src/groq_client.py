"""
src/groq_client.py

A thin, reusable wrapper around the Groq SDK. Both the classifier
(Phase 2) and the response generator (Phase 3) call through this
single function instead of hitting the Groq SDK directly, so retry
behavior, timeouts, and error handling live in exactly one place.
"""

import os
import time
import json
import logging

from groq import Groq, APIConnectionError, APIStatusError, RateLimitError

from src.config import GROQ_API_KEY, GROQ_MODEL

logger = logging.getLogger(__name__)

_client: Groq | None = None


def get_client() -> Groq:
    """Lazily creates a single shared Groq client using GROQ_API_KEY from the environment."""
    global _client
    if _client is None:
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GROQ_API_KEY is not set. Copy .env.example to .env and add your key."
            )
        _client = Groq(api_key=api_key)
    return _client


class GroqCallError(Exception):
    """Raised when a Groq call fails after all retries are exhausted."""
    pass


def call_groq(
    system_prompt: str,
    user_prompt: str,
    model: str = "llama-3.3-70b-versatile",
    json_mode: bool = True,
    temperature: float = 0.1,
    max_tokens: int = 512,
    max_retries: int = 3,
    base_delay: float = 1.0,
) -> str:
    """
    Calls Groq's chat completion endpoint and returns the raw response text.

    Retries on transient failures (rate limits, connection errors, 5xx server
    errors) using exponential backoff: 1s, 2s, 4s... Does NOT retry on 4xx
    client errors other than rate limits (e.g. bad request, auth failure),
    since retrying those just wastes time on a request that will never succeed.
    """
    client = get_client()
    last_error: Exception | None = None

    for attempt in range(1, max_retries + 1):
        try:
            kwargs = {
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
            if json_mode:
                kwargs["response_format"] = {"type": "json_object"}

            response = client.chat.completions.create(**kwargs)
            return response.choices[0].message.content

        except RateLimitError as e:
            last_error = e
            delay = base_delay * (2 ** (attempt - 1))
            logger.warning(f"Groq rate limited (attempt {attempt}/{max_retries}). Retrying in {delay}s.")
            time.sleep(delay)

        except APIConnectionError as e:
            last_error = e
            delay = base_delay * (2 ** (attempt - 1))
            logger.warning(f"Groq connection error (attempt {attempt}/{max_retries}). Retrying in {delay}s.")
            time.sleep(delay)

        except APIStatusError as e:
            last_error = e
            if 500 <= e.status_code < 600:
                delay = base_delay * (2 ** (attempt - 1))
                logger.warning(f"Groq server error {e.status_code} (attempt {attempt}/{max_retries}). Retrying in {delay}s.")
                time.sleep(delay)
            else:
                # 4xx errors (bad request, auth, etc.) won't be fixed by retrying.
                raise GroqCallError(f"Groq API rejected the request ({e.status_code}): {e}") from e

    raise GroqCallError(
        f"Groq call failed after {max_retries} attempts. Last error: {last_error}"
    ) from last_error


def call_groq_json(
    system_prompt: str,
    user_prompt: str,
    **kwargs,
) -> dict:
    """
    Convenience wrapper for JSON-mode calls: calls Groq and parses the
    result as JSON, raising a clear error if the model didn't return
    valid JSON despite json_mode being requested.
    """
    raw_text = call_groq(system_prompt, user_prompt, json_mode=True, **kwargs)
    try:
        return json.loads(raw_text)
    except json.JSONDecodeError as e:
        raise GroqCallError(f"Groq returned invalid JSON: {raw_text[:200]}") from e