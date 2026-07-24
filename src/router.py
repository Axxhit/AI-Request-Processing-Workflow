"""
src/router.py

The central orchestrator that ties classification → branching → execution.

WHY THIS FILE EXISTS:
This is the ONE function the Streamlit UI calls to process a request
end-to-end. It:
  1. Classifies the request via classifier.py (Phase 2)
  2. Checks confidence — low confidence goes to human review
  3. Routes to the correct workflow branch (Phase 3)
  4. Executes the branch's 4-step pipeline
  5. Builds a complete CaseRecord with all results
  6. Saves to SQLite (Phase 1 database layer)
  7. Returns the CaseRecord for the UI to display

The Streamlit page doesn't need to know about Groq, workflows,
or databases — it just calls process_request(text) and gets back
a fully populated CaseRecord.

ROUTING IS CODE, NOT AI:
The routing decision is a simple Python dict lookup, NOT another
LLM call. Per Anthropic's guidance: "Use code for plumbing, LLM
for judgment." The LLM already made the judgment (classification).
Routing is mechanical dispatch — it doesn't need AI.
"""

import logging
from datetime import datetime

from src.classifier import classify_request, ClassificationError
from src.models import CaseRecord, ClassificationResult, WorkflowStep
from src.database import insert_case
from src.config import CONFIDENCE_THRESHOLD
from src.workflows import (
    ComplaintWorkflow,
    EnquiryWorkflow,
    ServiceRequestWorkflow,
    EscalationWorkflow,
)

logger = logging.getLogger(__name__)

# ── Branch dispatch table ───────────────────────────────────
# Maps classification label → workflow class.
# Adding a new branch = add one entry here + one workflow file.
BRANCH_MAP = {
    "complaint": ComplaintWorkflow,
    "general_enquiry": EnquiryWorkflow,
    "service_request": ServiceRequestWorkflow,
    "escalation": EscalationWorkflow,
}


def process_request(raw_text: str) -> CaseRecord:
    """
    End-to-end processing: raw text → classify → route → remediate → save.

    This is the ONLY function the UI needs to call.

    Returns a fully populated CaseRecord with:
      - classification (type, urgency, confidence, reasoning)
      - workflow_steps (4 steps with status/output/timestamp)
      - generated_response (customer-facing draft)
      - assigned_team, status, SLA/follow-up times, flags
    """
    # ── Step 1: Classify ────────────────────────────────────
    try:
        classification = classify_request(raw_text)
        logger.info(
            f"Classified as {classification.request_type} "
            f"(urgency={classification.urgency}, confidence={classification.confidence:.2f})"
        )
    except ClassificationError as e:
        # Classification failed entirely — create a case flagged for human review
        logger.error(f"Classification failed: {e}")
        classification = ClassificationResult(
            request_type="general_enquiry",
            urgency="medium",
            confidence=0.0,
            sub_topic="classification_failed",
            key_entities=[],
            reasoning=f"Auto-classification failed: {e}",
        )

    # ── Step 2: Build initial CaseRecord ────────────────────
    case = CaseRecord(
        raw_input=raw_text,
        classification=classification,
    )

    # ── Step 3: Confidence check → human review? ────────────
    if classification.confidence < CONFIDENCE_THRESHOLD:
        logger.info(
            f"Confidence {classification.confidence:.2f} < {CONFIDENCE_THRESHOLD} — "
            f"routing to human review"
        )
        case.human_review_required = True
        case.status = "pending_review"
        case.assigned_team = "human_review_queue"
        case.workflow_steps = [
            WorkflowStep(
                step_number=1,
                action="Route to human review (low confidence)",
                status="completed",
                output=f"Confidence {classification.confidence:.2f} below threshold {CONFIDENCE_THRESHOLD}. "
                       f"Best guess: {classification.request_type} ({classification.urgency}). "
                       f"Reason: {classification.reasoning}",
                timestamp=datetime.now(),
            )
        ]
        insert_case(case)
        return case

    # ── Step 4: Route to correct branch ─────────────────────
    workflow_class = BRANCH_MAP.get(classification.request_type)

    if workflow_class is None:
        # Unknown type — shouldn't happen with enum-constrained output, but safety first
        logger.warning(f"Unknown request type: {classification.request_type}")
        case.human_review_required = True
        case.status = "pending_review"
        case.assigned_team = "human_review_queue"
        case.workflow_steps = [
            WorkflowStep(
                step_number=1,
                action="Route to human review (unknown type)",
                status="completed",
                output=f"Request type '{classification.request_type}' has no matching workflow.",
                timestamp=datetime.now(),
            )
        ]
        insert_case(case)
        return case

    # ── Step 5: Execute the branch pipeline ─────────────────
    workflow = workflow_class(
        classification=classification,
        raw_input=raw_text,
        case_id=case.id,
    )
    execution_result = workflow.execute()

    # ── Step 6: Populate CaseRecord with results ────────────
    case.workflow_steps = execution_result["steps"]
    result = execution_result["result"]

    case.generated_response = result.get("generated_response", "")
    case.assigned_team = result.get("assigned_team", "")
    case.status = result.get("status", "processed")
    case.is_escalated = result.get("is_escalated", False)
    case.human_review_required = result.get("human_review_required", False)
    case.follow_up_at = result.get("follow_up_at")
    case.sla_deadline = result.get("sla_deadline")

    # ── Step 7: Save to database ────────────────────────────
    insert_case(case)
    logger.info(f"Case {case.id} saved — status={case.status}, team={case.assigned_team}")

    return case
