"""
src/workflows/escalation.py

Branch 4: ESCALATION remediation pipeline (Urgency: CRITICAL)

Triggered when classification.request_type == "escalation".
Customer has an unresolved issue, is threatening legal action,
demanding management, or reporting safety/security concerns.

This branch's strategy is FLAG + ACKNOWLEDGE + ALERT + FREEZE:
  Step 1: Flag for mandatory human review (AI alone shouldn't handle this)
  Step 2: Draft an urgent acknowledgement (customer needs to know we're on it)
  Step 3: Create supervisor alert (management must be in the loop)
  Step 4: Pause auto-resolution (prevent any automated action that could
          make things worse while a human reviews)

WHY PAUSE AUTO-RESOLUTION?  Escalated cases are high-risk. An automated
response that misunderstands the situation could escalate further (e.g.
sending a "your case is resolved" email to someone threatening legal
action). Freezing the case ensures a human makes the final call.
"""

from datetime import datetime

from src.workflows.base import BaseWorkflow
from src.response_generator import generate_response
from src.config import TEAM_ROUTING


class EscalationWorkflow(BaseWorkflow):

    def get_steps(self):
        return [
            self.flag_for_human_review,
            self.draft_urgent_acknowledgement,
            self.notify_supervisor,
            self.pause_auto_resolution,
        ]

    def flag_for_human_review(self):
        """Flag case for mandatory human review"""
        self.result["human_review_required"] = True
        self.result["is_escalated"] = True
        return "Case flagged for mandatory human review"

    def draft_urgent_acknowledgement(self):
        """Draft urgent acknowledgement from supervisor level"""
        self.result["generated_response"] = generate_response(
            classification=self.classification,
            raw_input=self.raw_input,
            prompt_key="escalation_acknowledgement",
            case_id=self.case_id,
        )
        return "Urgent acknowledgement drafted at supervisor level"

    def notify_supervisor(self):
        """Create supervisor alert notification"""
        team = TEAM_ROUTING.get("escalation", "supervisor_team")
        self.result["assigned_team"] = team
        self.result["supervisor_notified"] = True
        self.result["supervisor_alert"] = {
            "case_id": self.case_id,
            "urgency": "CRITICAL",
            "reason": self.classification.sub_topic,
            "timestamp": datetime.now().isoformat(),
        }
        return f"Supervisor alert created — {team} notified"

    def pause_auto_resolution(self):
        """Pause all automated actions — human-in-the-loop required"""
        self.result["status"] = "paused_for_review"
        self.result["auto_resolution_paused"] = True
        return "Auto-resolution PAUSED. Awaiting human decision."
