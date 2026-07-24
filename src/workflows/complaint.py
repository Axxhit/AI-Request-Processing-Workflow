"""
src/workflows/complaint.py

Branch 1: COMPLAINT remediation pipeline (Urgency: HIGH)

Triggered when classification.request_type == "complaint".
Customer is expressing dissatisfaction — billing disputes, service
quality issues, product defects, broken promises.

This branch's strategy is ACKNOWLEDGE + ESCALATE + PROTECT:
  Step 1: Generate empathetic acknowledgement (shows we heard them)
  Step 2: Escalate to senior handler (ensures qualified person handles it)
  Step 3: Log as high-priority case (makes it visible in dashboards)
  Step 4: Set 2-hour follow-up (guarantees timely action)

WHY 2 HOURS?  Industry standard for high-urgency complaints is 1-4
hours. 2 hours is aggressive enough to show urgency but realistic
enough that a senior handler can review the case first.
"""

from datetime import datetime, timedelta

from src.workflows.base import BaseWorkflow
from src.response_generator import generate_response
from src.config import TEAM_ROUTING


class ComplaintWorkflow(BaseWorkflow):

    def get_steps(self):
        return [
            self.acknowledge_receipt,
            self.escalate_to_senior,
            self.log_priority_case,
            self.set_followup_reminder,
        ]

    def acknowledge_receipt(self):
        """Generate empathetic acknowledgement for customer complaint"""
        self.result["generated_response"] = generate_response(
            classification=self.classification,
            raw_input=self.raw_input,
            prompt_key="complaint_acknowledgement",
            case_id=self.case_id,
        )
        return "Empathetic acknowledgement draft generated"

    def escalate_to_senior(self):
        """Escalate case to senior support handler"""
        team = TEAM_ROUTING.get("complaint", "senior_support")
        self.result["assigned_team"] = team
        self.result["is_escalated"] = True
        return f"Escalated to {team}"

    def log_priority_case(self):
        """Log case with HIGH priority flag"""
        self.result["status"] = "escalated"
        self.result["priority"] = "HIGH"
        return "Case flagged as HIGH priority in system"

    def set_followup_reminder(self):
        """Set 2-hour follow-up reminder"""
        follow_up = datetime.now() + timedelta(hours=2)
        self.result["follow_up_at"] = follow_up
        return f"Follow-up scheduled for {follow_up.strftime('%Y-%m-%d %H:%M')}"
