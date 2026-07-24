"""
src/models.py

Core data models for the request-processing pipeline.

These are Pydantic models, which means every field is type-validated
at creation time. If the Groq API ever returns malformed JSON (e.g. a
missing field, or "confidence": "high" instead of a float), model
creation raises a clear ValidationError immediately — instead of that
bad data silently flowing into the database or the UI.
"""

from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime
import uuid


class RequestType(str, Enum):
    """The 4 categories the classifier can assign to an incoming request."""
    COMPLAINT = "complaint"
    GENERAL_ENQUIRY = "general_enquiry"
    SERVICE_REQUEST = "service_request"
    ESCALATION = "escalation"


class UrgencyLevel(str, Enum):
    """Urgency tag attached alongside the request type."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ClassificationResult(BaseModel):
    """
    Structured output of the Groq classification call (Phase 2).
    Mirrors the JSON schema we'll ask the LLM to return.
    """
    request_type: str
    urgency: str
    confidence: float = Field(ge=0.0, le=1.0)
    sub_topic: str
    key_entities: list[str] = Field(default_factory=list)
    reasoning: str


class WorkflowStep(BaseModel):
    """
    One step inside a branch's remediation pipeline (Phase 3).
    Each branch (Complaint, Enquiry, Service, Escalation) runs 4 of these
    in sequence, and each one gets logged for the audit trail / UI tracker.
    """
    step_number: int
    action: str
    status: str = "pending"  # pending | executing | completed | failed
    output: str = ""
    timestamp: datetime | None = None


class CaseRecord(BaseModel):
    """
    The full record for one processed request — this is what gets written
    to SQLite and what the Dashboard / Audit Trail / Human Review pages read.
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    raw_input: str
    classification: ClassificationResult
    workflow_steps: list[WorkflowStep] = Field(default_factory=list)
    generated_response: str = ""
    assigned_team: str = ""
    status: str = "processing"
    sla_deadline: datetime | None = None
    follow_up_at: datetime | None = None
    is_escalated: bool = False
    human_review_required: bool = False
    created_at: datetime = Field(default_factory=datetime.now)
