"""
src/response_generator.py

Phase 3 — Groq-powered response generation for each branch.

WHY THIS IS SEPARATE FROM classifier.py:
Classification and response generation are two DIFFERENT AI tasks:
  - Classification: low temperature (0.1), small output, JSON mode,
    needs to be deterministic and consistent.
  - Response generation: higher temperature (0.7), longer output,
    plain text mode, needs to sound natural and empathetic.

By keeping them separate, each can use its own prompt, temperature,
and token budget without awkward if/else branching.

HOW PROMPT CHAINING WORKS HERE:
The classification result (type, urgency, sub_topic, entities) from
Phase 2 is injected INTO the generation prompt. This is Anthropic's
"prompt chaining" pattern — the output of step 1 feeds into step 2,
giving the generator all the context it needs to write a tailored response.
"""

import logging

from src.groq_client import call_groq, GroqCallError
from src.config import (
    RESPONSE_PROMPTS,
    GROQ_MODEL,
    GROQ_TEMPERATURE_GENERATE,
    GROQ_MAX_TOKENS_GENERATE,
)
from src.models import ClassificationResult

logger = logging.getLogger(__name__)


def generate_response(
    classification: ClassificationResult,
    raw_input: str,
    prompt_key: str,
    case_id: str = "N/A",
) -> str:
    """
    Generates a customer-facing response using a branch-specific prompt.

    Args:
        classification: The output from Phase 2 (type, urgency, entities, etc.)
        raw_input: The original customer request text
        prompt_key: Which prompt to use from config.RESPONSE_PROMPTS
                    (e.g. "complaint_acknowledgement", "enquiry_response")
        case_id: The case reference number to include in the response

    Returns:
        The generated response text (plain text, not JSON)
    """
    system_prompt = RESPONSE_PROMPTS.get(prompt_key)
    if not system_prompt:
        logger.warning(f"No response prompt found for key '{prompt_key}'. Using generic.")
        system_prompt = "You are a professional customer service agent. Write a helpful response."

    # Build the user prompt with all context from the classification chain
    user_prompt = f"""Case Reference: {case_id}
Request Type: {classification.request_type}
Urgency Level: {classification.urgency}
Sub-topic: {classification.sub_topic}
Key Entities: {', '.join(classification.key_entities) if classification.key_entities else 'None identified'}

Original Customer Request:
\"{raw_input}\"

Generate the appropriate response now."""

    try:
        response = call_groq(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            model=GROQ_MODEL,
            json_mode=False,          # Plain text response, not JSON
            temperature=GROQ_TEMPERATURE_GENERATE,
            max_tokens=GROQ_MAX_TOKENS_GENERATE,
        )
        return response.strip()
    except GroqCallError as e:
        logger.error(f"Response generation failed for case {case_id}: {e}")
        return f"[Auto-generation failed. Manual response required for case {case_id}.]"
