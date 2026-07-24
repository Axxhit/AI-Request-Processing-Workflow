"""
src/workflows/service_request.py

Branch 3: SERVICE REQUEST remediation pipeline (Urgency: MEDIUM)

Triggered when classification.request_type == "service_request".
Customer is requesting a specific action — account changes, plan
upgrades, cancellations, address updates, password resets.

This branch's strategy is EXTRACT + ROUTE + CONFIRM + TRACK:
  Step 1: Extract key details from the request (what, who, when)
  Step 2: Route to the correct department based on service type
  Step 3: Generate a confirmation message with ticket# and timeline
  Step 4: Set an SLA timer based on the service type

WHY DEPARTMENT-LEVEL ROUTING?  Service requests are procedural —
a billing change goes to billing_operations, a password reset goes
to technical_support. Unlike complaints (which all go to senior),
these need to reach the team with the right system access.
"""

from datetime import datetime, timedelta

from src.workflows.base import BaseWorkflow
from src.response_generator import generate_response
from src.config import TEAM_ROUTING, SLA_TIMERS


class ServiceRequestWorkflow(BaseWorkflow):

    def get_steps(self):
        return [
            self.extract_details,
            self.route_to_department,
            self.generate_confirmation,
            self.set_sla_timer,
        ]

    def extract_details(self):
        """Extract service request details (type, account, specifics)"""
        # Key entities were extracted during classification.
        # Here we structure them for downstream use.
        entities = self.classification.key_entities or []
        sub_topic = self.classification.sub_topic or "general"
        self.result["service_type"] = sub_topic
        self.result["extracted_entities"] = entities
        return f"Extracted: service_type={sub_topic}, entities={entities}"

    def route_to_department(self):
        """Route request to the appropriate department"""
        service_type = self.result.get("service_type", "").lower()
        routing_map = TEAM_ROUTING.get("service_request", {})

        # Try to match the sub-topic to a specific department
        if isinstance(routing_map, dict):
            team = routing_map.get("default", "general_operations")
            for keyword, dept in routing_map.items():
                if keyword != "default" and keyword in service_type:
                    team = dept
                    break
        else:
            team = str(routing_map)

        self.result["assigned_team"] = team
        return f"Routed to {team}"

    def generate_confirmation(self):
        """Generate confirmation message with reference number and timeline"""
        self.result["generated_response"] = generate_response(
            classification=self.classification,
            raw_input=self.raw_input,
            prompt_key="service_confirmation",
            case_id=self.case_id,
        )
        return "Confirmation message generated with reference number"

    def set_sla_timer(self):
        """Set SLA deadline based on service type"""
        service_type = self.result.get("service_type", "").lower()

        # Find matching SLA or use default
        sla_hours = SLA_TIMERS.get("default", 48)
        for keyword, hours in SLA_TIMERS.items():
            if keyword != "default" and keyword in service_type:
                sla_hours = hours
                break

        deadline = datetime.now() + timedelta(hours=sla_hours)
        self.result["sla_deadline"] = deadline
        self.result["sla_hours"] = sla_hours
        self.result["status"] = "in_progress"
        return f"SLA set: {sla_hours}h (deadline: {deadline.strftime('%Y-%m-%d %H:%M')})"
