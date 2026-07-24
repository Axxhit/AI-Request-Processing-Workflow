"""
src/classifier.py

Phase 2 — Task: classify_request()

Takes raw customer request text, sends it to Groq using the
classification prompt defined in config.py, and returns a validated
ClassificationResult. This is the only function the rest of the app
(router, Streamlit pages) calls to classify a request — nobody else
builds the prompt or talks to Groq directly for classification.
"""

import logging

from pydantic import ValidationError

from src.config import (
    CLASSIFICATION_SYSTEM_PROMPT,
    GROQ_MODEL,
    GROQ_TEMPERATURE_CLASSIFY,
    GROQ_MAX_TOKENS_CLASSIFY,
)
from src.groq_client import call_groq_json, GroqCallError
from src.models import ClassificationResult

logger = logging.getLogger(__name__)


class ClassificationError(Exception):
    """
    Raised when a request cannot be classified — either Groq failed
    (network/API issue) or it returned JSON that doesn't match the
    expected ClassificationResult schema. The caller (router.py) is
    responsible for deciding what happens next (e.g. send to human
    review) rather than this function silently guessing.
    """
    pass


def classify_request(raw_text: str) -> ClassificationResult:
    """
    Classifies a single raw customer request into one of the 4
    categories, with an urgency level, confidence score, sub-topic,
    key entities, and reasoning.

    Raises ClassificationError if Groq fails after retries, or if the
    response doesn't match the ClassificationResult schema.
    """
    if not raw_text or not raw_text.strip():
        raise ClassificationError("Cannot classify an empty request.")

    try:
        raw_result = call_groq_json(
            system_prompt=CLASSIFICATION_SYSTEM_PROMPT,
            user_prompt=raw_text.strip(),
            model=GROQ_MODEL,
            temperature=GROQ_TEMPERATURE_CLASSIFY,
            max_tokens=GROQ_MAX_TOKENS_CLASSIFY,
        )
    except GroqCallError as e:
        logger.error(f"Groq call failed during classification: {e}")
        raise ClassificationError(f"Could not classify request: {e}") from e

    try:
        return ClassificationResult(**raw_result)
    except ValidationError as e:
        logger.error(f"Groq classification response failed schema validation: {raw_result}")
        raise ClassificationError(
            f"Groq returned a classification that doesn't match the expected format: {e}"
        ) from e