"""
src/database.py

SQLite persistence layer. This is the single place in the app that
talks to the database — the router, workflows, and Streamlit pages
never write raw SQL themselves, they call these functions.

We store CaseRecord as a row where the nested/complex fields
(classification, workflow_steps) are serialized to JSON text, since
SQLite has no native nested-object type. Reading a row back deserializes
that JSON into a real CaseRecord/ClassificationResult/WorkflowStep again.
"""

import sqlite3
import json
import os
from datetime import datetime
from contextlib import contextmanager

from src.models import CaseRecord, ClassificationResult, WorkflowStep

DATABASE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "cases.db")


@contextmanager
def get_connection():
    """Yields a connection with row access by column name, and always closes it."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    """Creates the cases table if it doesn't already exist. Safe to call every app start."""
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS cases (
                id TEXT PRIMARY KEY,
                raw_input TEXT NOT NULL,
                classification_json TEXT NOT NULL,
                workflow_steps_json TEXT NOT NULL,
                generated_response TEXT DEFAULT '',
                assigned_team TEXT DEFAULT '',
                status TEXT DEFAULT 'processing',
                sla_deadline TEXT,
                follow_up_at TEXT,
                is_escalated INTEGER DEFAULT 0,
                human_review_required INTEGER DEFAULT 0,
                created_at TEXT NOT NULL
            )
            """
        )


def insert_case(case: CaseRecord) -> None:
    """Inserts a new CaseRecord as a row."""
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO cases (
                id, raw_input, classification_json, workflow_steps_json,
                generated_response, assigned_team, status,
                sla_deadline, follow_up_at, is_escalated,
                human_review_required, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                case.id,
                case.raw_input,
                case.classification.model_dump_json(),
                json.dumps([step.model_dump(mode="json") for step in case.workflow_steps]),
                case.generated_response,
                case.assigned_team,
                case.status,
                case.sla_deadline.isoformat() if case.sla_deadline else None,
                case.follow_up_at.isoformat() if case.follow_up_at else None,
                int(case.is_escalated),
                int(case.human_review_required),
                case.created_at.isoformat(),
            ),
        )


def _row_to_case(row: sqlite3.Row) -> CaseRecord:
    """Deserializes one DB row back into a CaseRecord."""
    return CaseRecord(
        id=row["id"],
        raw_input=row["raw_input"],
        classification=ClassificationResult(**json.loads(row["classification_json"])),
        workflow_steps=[WorkflowStep(**s) for s in json.loads(row["workflow_steps_json"])],
        generated_response=row["generated_response"],
        assigned_team=row["assigned_team"],
        status=row["status"],
        sla_deadline=datetime.fromisoformat(row["sla_deadline"]) if row["sla_deadline"] else None,
        follow_up_at=datetime.fromisoformat(row["follow_up_at"]) if row["follow_up_at"] else None,
        is_escalated=bool(row["is_escalated"]),
        human_review_required=bool(row["human_review_required"]),
        created_at=datetime.fromisoformat(row["created_at"]),
    )


def get_case(case_id: str) -> CaseRecord | None:
    """Fetches a single case by id, or None if it doesn't exist."""
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM cases WHERE id = ?", (case_id,)).fetchone()
        return _row_to_case(row) if row else None


def get_all_cases(status: str | None = None) -> list[CaseRecord]:
    """Fetches all cases, optionally filtered by status (e.g. 'processing', 'resolved')."""
    with get_connection() as conn:
        if status:
            rows = conn.execute(
                "SELECT * FROM cases WHERE status = ? ORDER BY created_at DESC", (status,)
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM cases ORDER BY created_at DESC").fetchall()
        return [_row_to_case(row) for row in rows]


def get_cases_for_human_review() -> list[CaseRecord]:
    """Fetches all cases flagged for human review (low-confidence classifications)."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM cases WHERE human_review_required = 1 ORDER BY created_at DESC"
        ).fetchall()
        return [_row_to_case(row) for row in rows]


def update_case(case: CaseRecord) -> None:
    """Overwrites an existing case row with the current state of the CaseRecord."""
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE cases SET
                raw_input = ?, classification_json = ?, workflow_steps_json = ?,
                generated_response = ?, assigned_team = ?, status = ?,
                sla_deadline = ?, follow_up_at = ?, is_escalated = ?,
                human_review_required = ?
            WHERE id = ?
            """,
            (
                case.raw_input,
                case.classification.model_dump_json(),
                json.dumps([step.model_dump(mode="json") for step in case.workflow_steps]),
                case.generated_response,
                case.assigned_team,
                case.status,
                case.sla_deadline.isoformat() if case.sla_deadline else None,
                case.follow_up_at.isoformat() if case.follow_up_at else None,
                int(case.is_escalated),
                int(case.human_review_required),
                case.id,
            ),
        )


def delete_case(case_id: str) -> None:
    """Removes a case row (used rarely — mainly for test cleanup)."""
    with get_connection() as conn:
        conn.execute("DELETE FROM cases WHERE id = ?", (case_id,))