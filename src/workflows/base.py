"""
src/workflows/base.py

Abstract base class that every remediation branch inherits from.

WHY THIS EXISTS:
All 4 branches (Complaint, Enquiry, Service, Escalation) share the
same execution pattern:
  1. Get an ordered list of step functions
  2. Execute them one by one in sequence
  3. Record the status/output/timestamp of each step
  4. Return the full list of completed steps + accumulated results

Instead of copy-pasting this loop into 4 files, we write it ONCE here.
Each branch only needs to define its own get_steps() method returning
its specific step functions. The base class handles execution, timing,
error handling, and logging.

This is the Template Method design pattern — the "shape" of execution
is fixed here, but the actual steps are plugged in by subclasses.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from src.models import WorkflowStep, ClassificationResult


class BaseWorkflow(ABC):
    """
    Base class for all remediation workflows.

    Subclasses must implement:
        get_steps() -> list of bound methods, each representing one
                       remediation action. Each method should return
                       a short string describing what it did.
    """

    def __init__(self, classification: ClassificationResult, raw_input: str, case_id: str):
        self.classification = classification
        self.raw_input = raw_input
        self.case_id = case_id
        self.steps: list[WorkflowStep] = []
        self.result: dict = {}  # Accumulates outputs across steps

    def execute(self) -> dict:
        """
        Runs every step returned by get_steps() in order.

        Each step function is called. If it succeeds, the step is marked
        'completed' with its output. If it raises, the step is marked
        'failed' with the error message — but execution CONTINUES to the
        next step. This is intentional: a failure in "set SLA timer"
        shouldn't prevent "generate response" from running.

        Returns a dict with:
          - "steps": list of WorkflowStep objects (for the UI tracker)
          - "result": dict of accumulated outputs (team, response, flags, etc.)
        """
        step_functions = self.get_steps()

        for i, step_fn in enumerate(step_functions, start=1):
            step = WorkflowStep(
                step_number=i,
                action=step_fn.__doc__.strip() if step_fn.__doc__ else step_fn.__name__,
                status="executing",
            )
            try:
                output = step_fn()
                step.status = "completed"
                step.output = str(output) if output else "Done"
            except Exception as e:
                step.status = "failed"
                step.output = f"Error: {e}"

            step.timestamp = datetime.now()
            self.steps.append(step)

        return {
            "steps": self.steps,
            "result": self.result,
        }

    @abstractmethod
    def get_steps(self) -> list:
        """
        Return an ordered list of bound methods (callables) that form
        this branch's remediation pipeline.

        Example:
            def get_steps(self):
                return [
                    self.step_one,
                    self.step_two,
                    self.step_three,
                    self.step_four,
                ]
        """
        pass
