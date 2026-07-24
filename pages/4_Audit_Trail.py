"""
pages/4_Audit_Trail.py

Full searchable, filterable log of all processed cases.
Shows every case with its classification, workflow steps, and response.
"""

import streamlit as st
import pandas as pd
from src.database import init_db, get_all_cases

init_db()

st.set_page_config(page_title="Audit Trail", page_icon="📋", layout="wide")

st.markdown("# 📋 Audit Trail")
st.markdown("Complete log of all processed requests with classification decisions and actions taken.")

cases = get_all_cases()

if not cases:
    st.info("No cases processed yet.")
    st.stop()

# ── Filters ─────────────────────────────────────────────────
col1, col2, col3 = st.columns(3)
with col1:
    type_filter = st.multiselect(
        "Filter by Type",
        options=["complaint", "general_enquiry", "service_request", "escalation"],
        default=None,
        format_func=lambda x: x.replace("_", " ").title(),
    )
with col2:
    urgency_filter = st.multiselect(
        "Filter by Urgency",
        options=["low", "medium", "high", "critical"],
        default=None,
        format_func=lambda x: x.upper(),
    )
with col3:
    status_filter = st.multiselect(
        "Filter by Status",
        options=list(set(c.status for c in cases)),
        default=None,
        format_func=lambda x: x.replace("_", " ").title(),
    )

# Apply filters
filtered = cases
if type_filter:
    filtered = [c for c in filtered if c.classification.request_type in type_filter]
if urgency_filter:
    filtered = [c for c in filtered if c.classification.urgency in urgency_filter]
if status_filter:
    filtered = [c for c in filtered if c.status in status_filter]

st.markdown(f"Showing **{len(filtered)}** of {len(cases)} cases")

# ── Summary Table ───────────────────────────────────────────
table_data = []
for c in filtered:
    type_icons = {
        "complaint": "🔴", "general_enquiry": "🟢",
        "service_request": "🟡", "escalation": "⚫",
    }
    icon = type_icons.get(c.classification.request_type, "⚪")
    table_data.append({
        "Case ID": c.id[:8] + "...",
        "Type": f"{icon} {c.classification.request_type.replace('_', ' ').title()}",
        "Urgency": c.classification.urgency.upper(),
        "Confidence": f"{c.classification.confidence:.0%}",
        "Team": c.assigned_team,
        "Status": c.status.replace("_", " ").title(),
        "Created": c.created_at.strftime("%Y-%m-%d %H:%M"),
    })

if table_data:
    st.dataframe(pd.DataFrame(table_data), use_container_width=True, hide_index=True)

# ── Expandable Case Details ─────────────────────────────────
st.markdown("---")
st.markdown("### Case Details")

for case in filtered:
    type_icons = {
        "complaint": "🔴", "general_enquiry": "🟢",
        "service_request": "🟡", "escalation": "⚫",
    }
    icon = type_icons.get(case.classification.request_type, "⚪")
    label = case.classification.request_type.replace("_", " ").title()

    with st.expander(
        f"{icon} {label} — {case.id[:8]}... — "
        f"{case.classification.urgency.upper()} — {case.status.replace('_', ' ').title()}"
    ):
        st.markdown(f"**Original Request:**")
        st.text(case.raw_input)

        st.markdown("**Classification:**")
        col1, col2, col3 = st.columns(3)
        col1.markdown(f"Type: `{case.classification.request_type}`")
        col2.markdown(f"Urgency: `{case.classification.urgency}`")
        col3.markdown(f"Confidence: `{case.classification.confidence:.2f}`")
        st.markdown(f"Reasoning: *{case.classification.reasoning}*")

        st.markdown("**Workflow Steps:**")
        for step in case.workflow_steps:
            status_icon = "✅" if step.status == "completed" else "❌" if step.status == "failed" else "⏳"
            st.markdown(f"{status_icon} **Step {step.step_number}:** {step.action}")
            st.markdown(f"   ↳ {step.output}")

        if case.generated_response:
            st.markdown("**Generated Response:**")
            st.info(case.generated_response)

        st.caption(f"Case ID: {case.id} | Created: {case.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
