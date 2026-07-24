"""
pages/5_Human_Review.py

Queue for cases flagged for human review:
  - Low confidence classifications (< 0.7)
  - Escalation cases requiring supervisor approval
  - Classification failures

Allows operators to:
  - View AI's best guess and reasoning
  - Accept the classification and trigger the workflow
  - Override with a different classification
"""

import streamlit as st
from src.database import init_db, get_cases_for_human_review, update_case, get_all_cases
from src.router import process_request, BRANCH_MAP
from src.models import ClassificationResult, WorkflowStep
from datetime import datetime

init_db()

st.set_page_config(page_title="Human Review", page_icon="👁️", layout="wide")

st.markdown("# 👁️ Human Review Queue")
st.markdown("Cases flagged for manual review due to low AI confidence or escalation protocols.")

# Get cases needing review
review_cases = get_cases_for_human_review()

# Also get escalation cases that are paused
all_cases = get_all_cases()
paused_cases = [c for c in all_cases if c.status == "paused_for_review" and c not in review_cases]
review_cases.extend(paused_cases)

if not review_cases:
    st.success("🎉 No cases pending review! All caught up.")
    st.stop()

st.markdown(f"**{len(review_cases)}** case(s) awaiting human review")
st.markdown("---")

for i, case in enumerate(review_cases):
    type_icons = {
        "complaint": "🔴", "general_enquiry": "🟢",
        "service_request": "🟡", "escalation": "⚫",
    }
    icon = type_icons.get(case.classification.request_type, "⚪")
    label = case.classification.request_type.replace("_", " ").title()

    with st.container():
        st.markdown(f"### {icon} Case {case.id[:8]}...")

        # Show the original request
        st.markdown("**Original Request:**")
        st.text(case.raw_input[:500])

        # Show AI's best guess
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("AI Classification", label)
        col2.metric("Urgency", case.classification.urgency.upper())
        col3.metric("Confidence", f"{case.classification.confidence:.0%}")
        col4.metric("Status", case.status.replace("_", " ").title())

        st.markdown(f"**AI Reasoning:** {case.classification.reasoning}")

        # Show existing workflow steps if any
        if case.workflow_steps:
            st.markdown("**Steps Already Executed:**")
            for step in case.workflow_steps:
                status_icon = "✅" if step.status == "completed" else "❌"
                st.markdown(f"{status_icon} {step.action}: {step.output}")

        if case.generated_response:
            st.markdown("**Draft Response:**")
            st.info(case.generated_response)

        # ── Action Buttons ──────────────────────────────
        st.markdown("**Take Action:**")
        action_col1, action_col2 = st.columns(2)

        with action_col1:
            if st.button(f"✅ Accept AI Classification", key=f"accept_{i}"):
                # Accept the classification and run the workflow
                case.human_review_required = False
                case.status = "accepted_by_reviewer"
                case.workflow_steps.append(
                    WorkflowStep(
                        step_number=len(case.workflow_steps) + 1,
                        action="Human reviewer accepted AI classification",
                        status="completed",
                        output=f"Reviewer approved: {case.classification.request_type} ({case.classification.urgency})",
                        timestamp=datetime.now(),
                    )
                )
                update_case(case)
                st.success(f"Case {case.id[:8]} accepted and updated!")
                st.rerun()

        with action_col2:
            override_type = st.selectbox(
                "Override classification to:",
                options=["complaint", "general_enquiry", "service_request", "escalation"],
                format_func=lambda x: x.replace("_", " ").title(),
                key=f"override_select_{i}",
            )
            if st.button(f"🔄 Override & Reprocess", key=f"override_{i}"):
                # Update the classification and reprocess
                case.classification.request_type = override_type
                case.human_review_required = False
                case.workflow_steps.append(
                    WorkflowStep(
                        step_number=len(case.workflow_steps) + 1,
                        action=f"Human reviewer overrode classification to {override_type}",
                        status="completed",
                        output=f"Original: {label} -> Override: {override_type.replace('_', ' ').title()}",
                        timestamp=datetime.now(),
                    )
                )
                case.status = "overridden_by_reviewer"
                update_case(case)
                st.success(f"Case {case.id[:8]} overridden to {override_type.replace('_', ' ').title()}!")
                st.rerun()

        st.markdown("---")
