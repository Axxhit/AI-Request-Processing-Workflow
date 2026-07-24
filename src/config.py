"""
Centralized configuration for the AI Request Processing Workflow.

WHY THIS FILE EXISTS:
Instead of scattering magic strings, API model names, and threshold values
across multiple files, we keep them in ONE place. This means:
  - Changing the Groq model = change 1 line, not 10
  - Adjusting confidence threshold = change 1 line
  - All prompts are co-located for easy review and iteration
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# ──────────────────────────────────────────────
# API Configuration
# ──────────────────────────────────────────────
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = "llama-3.3-70b-versatile"  # Best free model for classification + generation
GROQ_TEMPERATURE_CLASSIFY = 0.1         # Low = deterministic classification (no creativity)
GROQ_TEMPERATURE_GENERATE = 0.7         # Higher = more natural response writing
GROQ_MAX_TOKENS_CLASSIFY = 512          # Classification output is small JSON
GROQ_MAX_TOKENS_GENERATE = 1024         # Responses need more room

# ──────────────────────────────────────────────
# Workflow Configuration
# ──────────────────────────────────────────────
CONFIDENCE_THRESHOLD = 0.7  # Below this → route to human review queue

# SLA timers (in hours) by service sub-type
SLA_TIMERS = {
    "account_change": 24,
    "new_service": 48,
    "cancellation": 24,
    "technical_support": 72,
    "default": 48,
}

# Team routing map
TEAM_ROUTING = {
    "complaint": "senior_support",
    "general_enquiry": "frontline_support",
    "service_request": {
        "billing": "billing_operations",
        "technical": "technical_support",
        "account": "account_management",
        "default": "general_operations",
    },
    "escalation": "supervisor_team",
}

# ──────────────────────────────────────────────
# Database Configuration
# ──────────────────────────────────────────────
DATABASE_PATH = "cases.db"

# ──────────────────────────────────────────────
# Classification Prompt
# ──────────────────────────────────────────────
CLASSIFICATION_SYSTEM_PROMPT = """You are an expert request classifier for a BPO (Business Process Outsourcing) customer service operations team. You analyze incoming customer requests and classify them accurately.

CLASSIFICATION CATEGORIES:

1. "complaint" (default urgency: "high")
   Customer expressing dissatisfaction, reporting a problem with service or product quality, billing disputes, or demanding corrective action.
   Examples: wrong charges, poor service, defective product, broken promises.

2. "general_enquiry" (default urgency: "low")
   Information requests, questions about products or services, how-to queries, status checks, or general curiosity. No expressed dissatisfaction.
   Examples: pricing questions, store hours, product availability, order status.

3. "service_request" (default urgency: "medium")
   Customer requesting a specific action to be taken: account changes, new service setup, cancellations, modifications, returns, address updates.
   Examples: cancel subscription, change plan, update address, request refund process.

4. "escalation" (default urgency: "critical")
   Previously unresolved issues, threats of legal action, regulatory complaints, requests to speak with management, repeated complaints, or situations involving safety or security concerns.
   Examples: "I've called 5 times about this", "I want to speak to a manager", "I will report this to authorities".

CLASSIFICATION RULES:
- If a request contains BOTH complaint AND escalation signals, classify as "escalation"
- If urgency indicators suggest higher urgency than the default, override the default
- Provide a confidence score from 0.0 to 1.0 reflecting how clearly the request fits one category
- Extract key entities: names, account numbers, product names, dates, amounts mentioned

You MUST respond with valid JSON matching this exact schema:
{
  "request_type": "complaint" | "general_enquiry" | "service_request" | "escalation",
  "urgency": "low" | "medium" | "high" | "critical",
  "confidence": 0.0 to 1.0,
  "sub_topic": "specific sub-category of the request",
  "key_entities": ["entity1", "entity2"],
  "reasoning": "1-2 sentence explanation of why this classification was chosen"
}"""

# ──────────────────────────────────────────────
# Response Generation Prompts (one per branch)
# ──────────────────────────────────────────────
RESPONSE_PROMPTS = {
    "complaint_acknowledgement": """You are a senior customer service agent handling a complaint.
Write an empathetic, professional acknowledgement that:
- Validates the customer's frustration
- Confirms the issue has been received and escalated to a senior handler
- Provides a reference number (use the case ID provided)
- Sets expectation for a follow-up within 2 hours
- Keeps the tone warm but professional, not robotic
Keep the response under 150 words.""",

    "enquiry_response": """You are a helpful customer service agent answering a general enquiry.
Write a clear, informative response that:
- Directly answers the customer's question
- Provides relevant additional information they might find useful
- Offers to help with anything else
- Keeps the tone friendly and conversational
Keep the response under 150 words.""",

    "service_confirmation": """You are a customer service agent confirming a service request.
Write a professional confirmation that:
- Confirms what action has been requested
- Mentions it has been routed to the appropriate department
- Provides a reference number (use the case ID provided)
- Sets expectation for completion timeline based on the SLA
- Lists any next steps the customer needs to take
Keep the response under 150 words.""",

    "escalation_acknowledgement": """You are a senior customer service supervisor handling an urgent escalation.
Write an urgent, high-priority acknowledgement that:
- Takes the situation very seriously
- Confirms a supervisor has been personally notified
- Provides a reference number (use the case ID provided)
- Commits to personal follow-up
- Assures the customer that auto-resolution has been paused for manual review
- Keeps the tone authoritative, empathetic, and reassuring
Keep the response under 150 words.""",
}
