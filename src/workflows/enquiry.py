"""
src/workflows/enquiry.py

Branch 2: GENERAL ENQUIRY remediation pipeline (Urgency: LOW)

Triggered when classification.request_type == "general_enquiry".
Customer is asking a question — pricing, hours, product info,
shipping details, return policies.

This branch's strategy is ANSWER + RESOLVE + CLOSE:
  Step 1: Identify the sub-topic (what exactly are they asking about?)
  Step 2: Generate a helpful AI response (the main value-add)
  Step 3: Mark as auto-responded (track that AI handled it)
  Step 4: Log as resolved (close the loop, update metrics)

WHY AUTO-RESOLVE?  General enquiries are low-risk, low-urgency.
If the AI can answer accurately, there's no reason to involve a
human. This is the highest-volume category, so auto-resolution
here has the biggest impact on team workload.
"""

from datetime import datetime

from src.workflows.base import BaseWorkflow
from src.response_generator import generate_response
from src.config import TEAM_ROUTING


class EnquiryWorkflow(BaseWorkflow):

    def get_steps(self):
        return [
            self.classify_subtopic,
            self.generate_ai_response,
            self.mark_auto_responded,
            self.log_as_resolved,
        ]

    def classify_subtopic(self):
        """Classify enquiry sub-topic for routing context"""
        # The sub_topic was already identified during classification (Phase 2).
        # This step records it explicitly in the workflow result.
        sub_topic = self.classification.sub_topic or "general"
        self.result["sub_topic"] = sub_topic
        return f"Sub-topic identified: {sub_topic}"

    def generate_ai_response(self):
        """Generate AI-powered response from knowledge base"""
        self.result["generated_response"] = generate_response(
            classification=self.classification,
            raw_input=self.raw_input,
            prompt_key="enquiry_response",
            case_id=self.case_id,
        )
        return "Helpful response generated from knowledge base"

    def mark_auto_responded(self):
        """Mark case as auto-responded by AI"""
        team = TEAM_ROUTING.get("general_enquiry", "frontline_support")
        self.result["assigned_team"] = team
        self.result["auto_responded"] = True
        return f"Marked as auto-responded (handled by {team})"

    def log_as_resolved(self):
        """Log case as resolved — no further action needed"""
        self.result["status"] = "resolved"
        self.result["resolved_at"] = datetime.now()
        return "Case closed as resolved"
