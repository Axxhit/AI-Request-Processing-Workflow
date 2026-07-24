"""
tests/test_classifier.py

Tests classification accuracy against the sample dataset.
Each sample has an expected_request_type — we verify the AI
correctly identifies at least 80% of them.

Run with:  python -m pytest tests/ -v
"""

import json
import os
import pytest
import time

from src.database import init_db
from src.classifier import classify_request, ClassificationError
from src.router import process_request


# ── Load sample data ────────────────────────────────────────
SAMPLE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "sample_requests.json")

with open(SAMPLE_PATH, "r") as f:
    SAMPLES = json.load(f)


# ── Initialization ──────────────────────────────────────────
@pytest.fixture(scope="session", autouse=True)
def setup_db():
    """Initialize the database once for all tests."""
    init_db()


# ── Individual classification tests ─────────────────────────
class TestClassification:
    """Tests that the classifier returns valid, structured results."""

    def test_classify_complaint(self):
        """A clear complaint should be classified as complaint."""
        result = classify_request(
            "I was charged twice for my order and nobody will help me. This is terrible."
        )
        assert result.request_type == "complaint"
        assert result.confidence >= 0.5
        assert result.urgency in ["medium", "high", "critical"]
        time.sleep(2)  # Rate limit protection

    def test_classify_enquiry(self):
        """A simple question should be classified as general_enquiry."""
        result = classify_request(
            "What are your business hours on weekends?"
        )
        assert result.request_type == "general_enquiry"
        assert result.confidence >= 0.5
        assert result.urgency == "low"
        time.sleep(2)

    def test_classify_service_request(self):
        """An action request should be classified as service_request."""
        result = classify_request(
            "Please cancel my subscription effective end of this month."
        )
        assert result.request_type == "service_request"
        assert result.confidence >= 0.5
        time.sleep(2)

    def test_classify_escalation(self):
        """A threatening escalation should be classified as escalation."""
        result = classify_request(
            "I've contacted you 5 times about this and nothing is resolved. "
            "I want to speak to a manager immediately or I'm filing a formal complaint."
        )
        assert result.request_type == "escalation"
        assert result.urgency == "critical"
        assert result.confidence >= 0.5
        time.sleep(2)

    def test_classification_has_required_fields(self):
        """Every classification result must have all required fields populated."""
        result = classify_request("I need to update my shipping address.")
        assert result.request_type in ["complaint", "general_enquiry", "service_request", "escalation"]
        assert result.urgency in ["low", "medium", "high", "critical"]
        assert 0.0 <= result.confidence <= 1.0
        assert isinstance(result.sub_topic, str) and len(result.sub_topic) > 0
        assert isinstance(result.reasoning, str) and len(result.reasoning) > 0
        assert isinstance(result.key_entities, list)
        time.sleep(2)

    def test_empty_input_raises_error(self):
        """Empty input should raise ClassificationError, not crash."""
        with pytest.raises(ClassificationError):
            classify_request("")

    def test_whitespace_input_raises_error(self):
        """Whitespace-only input should raise ClassificationError."""
        with pytest.raises(ClassificationError):
            classify_request("   \n\t  ")


# ── End-to-end pipeline tests ───────────────────────────────
class TestEndToEnd:
    """Tests that the full pipeline (classify → route → execute → save) works."""

    def test_complaint_pipeline(self):
        """Complaint goes through all 4 steps and produces a response."""
        case = process_request(
            "Your product broke after one day and I want a full refund NOW."
        )
        assert case.classification.request_type == "complaint"
        assert len(case.workflow_steps) == 4
        assert all(s.status == "completed" for s in case.workflow_steps)
        assert case.generated_response != ""
        assert case.assigned_team == "senior_support"
        assert case.is_escalated is True
        time.sleep(2)

    def test_enquiry_pipeline(self):
        """Enquiry auto-resolves with a generated response."""
        case = process_request(
            "Do you accept PayPal for payments?"
        )
        assert case.classification.request_type == "general_enquiry"
        assert len(case.workflow_steps) == 4
        assert case.status == "resolved"
        assert case.generated_response != ""
        time.sleep(2)

    def test_escalation_pipeline(self):
        """Escalation pauses for human review."""
        case = process_request(
            "This is the third week with no resolution. I'm contacting a lawyer."
        )
        assert case.classification.request_type == "escalation"
        assert case.human_review_required is True
        assert case.status == "paused_for_review"
        assert case.assigned_team == "supervisor_team"
        time.sleep(2)


# ── Batch accuracy test ─────────────────────────────────────
class TestBatchAccuracy:
    """Runs the classifier against all sample data and checks accuracy."""

    def test_sample_dataset_accuracy(self):
        """At least 80% of sample requests should be classified correctly."""
        correct = 0
        total = min(len(SAMPLES), 10)  # Test first 10 to stay within rate limits

        for sample in SAMPLES[:total]:
            try:
                result = classify_request(sample["text"])
                if result.request_type == sample["expected_request_type"]:
                    correct += 1
                time.sleep(2)  # Rate limit: ~30 RPM
            except ClassificationError:
                pass  # Count as incorrect

        accuracy = correct / total
        print(f"\nClassification accuracy: {correct}/{total} = {accuracy:.0%}")
        assert accuracy >= 0.8, f"Accuracy {accuracy:.0%} is below 80% threshold"
