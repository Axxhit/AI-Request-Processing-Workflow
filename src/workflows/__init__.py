# src/workflows/__init__.py
# Export all workflow classes for clean imports elsewhere.

from src.workflows.complaint import ComplaintWorkflow
from src.workflows.enquiry import EnquiryWorkflow
from src.workflows.service_request import ServiceRequestWorkflow
from src.workflows.escalation import EscalationWorkflow

__all__ = [
    "ComplaintWorkflow",
    "EnquiryWorkflow",
    "ServiceRequestWorkflow",
    "EscalationWorkflow",
]
