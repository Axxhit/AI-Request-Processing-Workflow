"""
pages/1_Submit_Request.py

Detailed request submission page with multiple input methods:
  - Free text input
  - Pre-loaded sample requests (for demo)
"""

import streamlit as st
from src.database import init_db
from src.router import process_request

init_db()

st.set_page_config(page_title="Submit Request", page_icon="📝", layout="wide")

st.markdown("# 📝 Submit a Request")
st.markdown("Enter a customer request below. The AI will classify it and execute the appropriate remediation workflow.")

# ── Input Method ────────────────────────────────────────────
tab1, tab2 = st.tabs(["✍️ Type / Paste", "📋 Sample Requests"])

with tab1:
    user_input = st.text_area(
        "Customer Request",
        height=180,
        placeholder="Paste or type the customer's message here...",
    )
    submit_btn = st.button("🚀 Process Request", key="submit_typed", use_container_width=True)

with tab2:
    import json, os
    sample_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "sample_requests.json")
    try:
        with open(sample_path, "r") as f:
            samples = json.load(f)
    except FileNotFoundError:
        samples = []
        st.warning("Sample data file not found.")

    if samples:
        # Group by expected type
        groups = {}
        for s in samples:
            t = s.get("expected_request_type", "unknown")
            groups.setdefault(t, []).append(s)

        type_icons = {
            "complaint": "🔴",
            "general_enquiry": "🟢",
            "service_request": "🟡",
            "escalation": "⚫",
        }

        selected_sample = None
        for req_type, items in groups.items():
            icon = type_icons.get(req_type, "⚪")
            st.markdown(f"**{icon} {req_type.replace('_', ' ').title()}**")
            for item in items:
                col1, col2 = st.columns([5, 1])
                with col1:
                    st.markdown(f"<small>{item['text'][:120]}...</small>" if len(item['text']) > 120 else f"<small>{item['text']}</small>", unsafe_allow_html=True)
                with col2:
                    if st.button("Use", key=f"sample_{item['id']}"):
                        selected_sample = item['text']
            st.markdown("---")

    submit_sample = False
    if selected_sample:
        st.text_area("Selected Request", value=selected_sample, height=100, disabled=True)
        submit_sample = st.button("🚀 Process Selected", key="submit_sample", use_container_width=True)

# ── Process ─────────────────────────────────────────────────
text_to_process = None
if submit_btn and user_input and user_input.strip():
    text_to_process = user_input.strip()
elif submit_sample and selected_sample:
    text_to_process = selected_sample

if text_to_process:
    st.markdown("---")
    st.markdown("## Processing Results")

    with st.spinner("🧠 Classifying with Llama 3.3 70B..."):
        case = process_request(text_to_process)

    # ── Classification Card ─────────────────────────────
    type_config = {
        "complaint":       ("🔴", "Complaint",       "#ef4444"),
        "general_enquiry": ("🟢", "General Enquiry", "#22c55e"),
        "service_request": ("🟡", "Service Request", "#eab308"),
        "escalation":      ("⚫", "Escalation",      "#6b7280"),
    }
    icon, label, color = type_config.get(
        case.classification.request_type,
        ("⚪", case.classification.request_type, "#94a3b8"),
    )

    st.markdown(f"### {icon} Classified as **{label}**")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Type", label)
    col2.metric("Urgency", case.classification.urgency.upper())
    col3.metric("Confidence", f"{case.classification.confidence:.0%}")
    col4.metric("Status", case.status.replace("_", " ").title())

    # ── Classification Details ──────────────────────────
    with st.expander("🧠 Classification Details", expanded=True):
        st.markdown(f"**Reasoning:** {case.classification.reasoning}")
        st.markdown(f"**Sub-topic:** {case.classification.sub_topic}")
        if case.classification.key_entities:
            st.markdown(f"**Key Entities:** {', '.join(case.classification.key_entities)}")
        st.markdown(f"**Assigned Team:** `{case.assigned_team}`")
        if case.follow_up_at:
            st.markdown(f"**Follow-up At:** {case.follow_up_at.strftime('%Y-%m-%d %H:%M')}")
        if case.sla_deadline:
            st.markdown(f"**SLA Deadline:** {case.sla_deadline.strftime('%Y-%m-%d %H:%M')}")

    # ── Workflow Steps Tracker ──────────────────────────
    st.markdown("### ⚙️ Remediation Workflow")
    for step in case.workflow_steps:
        if step.status == "completed":
            st.success(f"✅ **Step {step.step_number}:** {step.action}")
        elif step.status == "failed":
            st.error(f"❌ **Step {step.step_number}:** {step.action}")
        else:
            st.info(f"⏳ **Step {step.step_number}:** {step.action}")

        with st.expander(f"Step {step.step_number} — Output Details"):
            st.code(step.output, language=None)
            if step.timestamp:
                st.caption(f"Executed at {step.timestamp.strftime('%H:%M:%S.%f')[:-3]}")

    # ── Generated Response ──────────────────────────────
    if case.generated_response:
        st.markdown("### 📧 Generated Customer Response")
        st.info(case.generated_response)

    # ── Case Meta ───────────────────────────────────────
    st.markdown("---")
    col1, col2 = st.columns(2)
    col1.markdown(f"**Case ID:** `{case.id}`")
    col2.markdown(f"**Created:** {case.created_at.strftime('%Y-%m-%d %H:%M:%S')}")

    if case.human_review_required:
        st.warning("⚠️ This case has been flagged for **human review**. Visit the Human Review page to take action.")
