"""
app.py — Main entry point for the Streamlit application.

This file sets up:
  1. Page configuration (title, icon, layout)
  2. Global CSS styling (dark theme, custom fonts, glassmorphism cards)
  3. The landing page with a quick-submit widget
  4. Sidebar navigation is auto-generated from the pages/ directory

Run with:  streamlit run app.py
"""

import streamlit as st
from src.database import init_db

# ── Page config (must be the first Streamlit call) ──────────
st.set_page_config(
    page_title="AI Request Processor",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Initialize database on every app start ──────────────────
init_db()

# ── Global CSS ──────────────────────────────────────────────
st.markdown("""
<style>
    /* ── Import Google Font ─────────────────────────── */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    /* ── Global font ────────────────────────────────── */
    html, body, [class*="st-"] {
        font-family: 'Inter', sans-serif;
    }

    /* ── Sidebar styling ────────────────────────────── */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0f0f23 0%, #1a1a3e 100%);
    }
    section[data-testid="stSidebar"] .stMarkdown p,
    section[data-testid="stSidebar"] .stMarkdown h1,
    section[data-testid="stSidebar"] .stMarkdown h2,
    section[data-testid="stSidebar"] .stMarkdown h3 {
        color: #e2e8f0;
    }

    /* ── Metric card styling ────────────────────────── */
    div[data-testid="stMetric"] {
        background: linear-gradient(135deg, #1e1e3f 0%, #2a2a5a 100%);
        border: 1px solid rgba(99, 102, 241, 0.2);
        border-radius: 12px;
        padding: 16px 20px;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
    }
    div[data-testid="stMetric"] label {
        color: #94a3b8 !important;
        font-size: 0.85rem !important;
    }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
        color: #f1f5f9 !important;
        font-weight: 700 !important;
    }

    /* ── Button styling ─────────────────────────────── */
    .stButton > button {
        background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.5rem 1.5rem;
        font-weight: 600;
        transition: all 0.3s ease;
        box-shadow: 0 2px 10px rgba(99, 102, 241, 0.3);
    }
    .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 20px rgba(99, 102, 241, 0.5);
    }

    /* ── Expander styling ───────────────────────────── */
    .streamlit-expanderHeader {
        font-weight: 600;
        color: #c7d2fe;
    }

    /* ── Success/Info/Error box styling ──────────────── */
    .stAlert > div {
        border-radius: 10px;
    }

    /* ── Tab styling ────────────────────────────────── */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px 8px 0 0;
        padding: 8px 20px;
        font-weight: 500;
    }

    /* ── Hide default hamburger and footer ──────────── */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# ── Sidebar ─────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🤖 AI Request Processor")
    st.markdown("---")
    st.markdown("""
    **Workflow Engine**

    Automatically classify and process
    incoming customer requests through
    AI-powered remediation pipelines.

    ---
    **Branches:**
    - 🔴 Complaint → Escalate
    - 🟢 Enquiry → Auto-resolve
    - 🟡 Service → Route & SLA
    - ⚫ Escalation → Supervisor
    ---
    """)

    st.markdown(
        "<small style='color: #64748b;'>Powered by Groq + Llama 3.3 70B</small>",
        unsafe_allow_html=True,
    )

# ── Landing Page ────────────────────────────────────────────
st.markdown("""
# 🤖 AI-Powered Request Processing Workflow

Automatically **classify**, **route**, and **remediate** incoming customer
requests through intelligent branching pipelines.
""")

# Quick stats from DB
from src.database import get_all_cases

all_cases = get_all_cases()
total = len(all_cases)
complaints = sum(1 for c in all_cases if c.classification.request_type == "complaint")
enquiries = sum(1 for c in all_cases if c.classification.request_type == "general_enquiry")
services = sum(1 for c in all_cases if c.classification.request_type == "service_request")
escalations = sum(1 for c in all_cases if c.classification.request_type == "escalation")
pending_review = sum(1 for c in all_cases if c.human_review_required)

col1, col2, col3, col4, col5, col6 = st.columns(6)
col1.metric("Total Processed", total)
col2.metric("🔴 Complaints", complaints)
col3.metric("🟢 Enquiries", enquiries)
col4.metric("🟡 Service Req.", services)
col5.metric("⚫ Escalations", escalations)
col6.metric("⚠️ Pending Review", pending_review)

st.markdown("---")

# ── Quick Submit Widget ─────────────────────────────────────
st.markdown("### ⚡ Quick Submit")
st.markdown("Paste a customer request below to process it instantly.")

quick_text = st.text_area(
    "Customer request text",
    height=120,
    placeholder="e.g. I was charged twice for my last order and nobody has refunded me...",
    label_visibility="collapsed",
)

if st.button("🚀 Process Request", use_container_width=True):
    if not quick_text.strip():
        st.warning("Please enter a request to process.")
    else:
        with st.spinner("Classifying and processing..."):
            from src.router import process_request

            case = process_request(quick_text)

        # ── Display result ──────────────────────────────
        st.markdown("---")

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

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Type", label)
        c2.metric("Urgency", case.classification.urgency.upper())
        c3.metric("Confidence", f"{case.classification.confidence:.0%}")
        c4.metric("Status", case.status.replace("_", " ").title())

        st.markdown(f"**AI Reasoning:** {case.classification.reasoning}")
        st.markdown(f"**Team:** {case.assigned_team}")
        if case.follow_up_at:
            st.markdown(f"**Follow-up:** {case.follow_up_at.strftime('%Y-%m-%d %H:%M')}")
        if case.sla_deadline:
            st.markdown(f"**SLA Deadline:** {case.sla_deadline.strftime('%Y-%m-%d %H:%M')}")

        # ── Workflow Steps ──────────────────────────────
        st.markdown("#### Remediation Steps")
        for step in case.workflow_steps:
            if step.status == "completed":
                st.success(f"✅ Step {step.step_number}: {step.action}")
            elif step.status == "failed":
                st.error(f"❌ Step {step.step_number}: {step.action}")
            else:
                st.info(f"⏳ Step {step.step_number}: {step.action}")
            with st.expander(f"Step {step.step_number} Details"):
                st.text(step.output)
                if step.timestamp:
                    st.caption(f"Executed at: {step.timestamp.strftime('%H:%M:%S')}")

        # ── Generated Response ──────────────────────────
        if case.generated_response:
            st.markdown("#### 📧 Generated Response")
            st.info(case.generated_response)

        st.markdown(f"*Case ID: `{case.id}`*")

st.markdown("---")
st.markdown(
    "📖 Use the **sidebar pages** for batch processing, dashboard analytics, "
    "full audit trail, and the human review queue."
)
