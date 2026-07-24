"""
pages/3_Dashboard.py

Analytics dashboard showing:
  - Summary metrics cards
  - Request volume by type (pie chart)
  - Urgency distribution (bar chart)
  - Status breakdown (donut chart)
  - Processing timeline
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from src.database import init_db, get_all_cases

init_db()

st.set_page_config(page_title="Dashboard", page_icon="📈", layout="wide")

st.markdown("# 📈 Analytics Dashboard")

cases = get_all_cases()

if not cases:
    st.info("No cases processed yet. Submit some requests first!")
    st.stop()

# ── Build DataFrame ─────────────────────────────────────────
data = []
for c in cases:
    data.append({
        "id": c.id[:8],
        "type": c.classification.request_type.replace("_", " ").title(),
        "urgency": c.classification.urgency.upper(),
        "confidence": c.classification.confidence,
        "status": c.status.replace("_", " ").title(),
        "team": c.assigned_team,
        "escalated": c.is_escalated,
        "review": c.human_review_required,
        "created": c.created_at,
    })
df = pd.DataFrame(data)

# ── Metric Cards ────────────────────────────────────────────
st.markdown("### Overview")
col1, col2, col3, col4, col5, col6 = st.columns(6)

col1.metric("Total Cases", len(df))
col2.metric("🔴 Complaints", len(df[df["type"] == "Complaint"]))
col3.metric("🟢 Enquiries", len(df[df["type"] == "General Enquiry"]))
col4.metric("🟡 Service Req.", len(df[df["type"] == "Service Request"]))
col5.metric("⚫ Escalations", len(df[df["type"] == "Escalation"]))
col6.metric("⚠️ Pending Review", len(df[df["review"] == True]))

avg_confidence = df["confidence"].mean()
resolved = len(df[df["status"] == "Resolved"])
auto_rate = (resolved / len(df) * 100) if len(df) > 0 else 0

col_a, col_b, col_c = st.columns(3)
col_a.metric("Avg Confidence", f"{avg_confidence:.0%}")
col_b.metric("Auto-Resolved", f"{resolved}")
col_c.metric("Auto-Resolution Rate", f"{auto_rate:.0f}%")

st.markdown("---")

# ── Charts Row 1 ────────────────────────────────────────────
chart1, chart2 = st.columns(2)

with chart1:
    st.markdown("#### Request Volume by Type")
    type_counts = df["type"].value_counts().reset_index()
    type_counts.columns = ["Type", "Count"]
    color_map = {
        "Complaint": "#ef4444",
        "General Enquiry": "#22c55e",
        "Service Request": "#eab308",
        "Escalation": "#6b7280",
    }
    fig = px.pie(
        type_counts,
        values="Count",
        names="Type",
        color="Type",
        color_discrete_map=color_map,
        hole=0.4,
    )
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="#e2e8f0",
        showlegend=True,
        margin=dict(t=20, b=20, l=20, r=20),
    )
    st.plotly_chart(fig, use_container_width=True)

with chart2:
    st.markdown("#### Urgency Distribution")
    urgency_counts = df["urgency"].value_counts().reset_index()
    urgency_counts.columns = ["Urgency", "Count"]
    urgency_order = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    urgency_colors = {
        "LOW": "#22c55e",
        "MEDIUM": "#eab308",
        "HIGH": "#f97316",
        "CRITICAL": "#ef4444",
    }
    fig2 = px.bar(
        urgency_counts,
        x="Urgency",
        y="Count",
        color="Urgency",
        color_discrete_map=urgency_colors,
        category_orders={"Urgency": urgency_order},
    )
    fig2.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="#e2e8f0",
        showlegend=False,
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=True, gridcolor="rgba(148,163,184,0.1)"),
        margin=dict(t=20, b=20, l=20, r=20),
    )
    st.plotly_chart(fig2, use_container_width=True)

# ── Charts Row 2 ────────────────────────────────────────────
chart3, chart4 = st.columns(2)

with chart3:
    st.markdown("#### Status Breakdown")
    status_counts = df["status"].value_counts().reset_index()
    status_counts.columns = ["Status", "Count"]
    fig3 = px.pie(
        status_counts,
        values="Count",
        names="Status",
        hole=0.5,
        color_discrete_sequence=px.colors.qualitative.Set2,
    )
    fig3.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="#e2e8f0",
        margin=dict(t=20, b=20, l=20, r=20),
    )
    st.plotly_chart(fig3, use_container_width=True)

with chart4:
    st.markdown("#### Team Assignment")
    team_counts = df["team"].value_counts().reset_index()
    team_counts.columns = ["Team", "Count"]
    fig4 = px.bar(
        team_counts,
        x="Count",
        y="Team",
        orientation="h",
        color_discrete_sequence=["#8b5cf6"],
    )
    fig4.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="#e2e8f0",
        showlegend=False,
        xaxis=dict(showgrid=True, gridcolor="rgba(148,163,184,0.1)"),
        yaxis=dict(showgrid=False),
        margin=dict(t=20, b=20, l=20, r=20),
    )
    st.plotly_chart(fig4, use_container_width=True)

# ── Confidence Distribution ─────────────────────────────────
st.markdown("#### Confidence Score Distribution")
fig5 = px.histogram(
    df,
    x="confidence",
    nbins=20,
    color_discrete_sequence=["#6366f1"],
    labels={"confidence": "Confidence Score"},
)
fig5.add_vline(x=0.7, line_dash="dash", line_color="#ef4444",
               annotation_text="Threshold (0.7)", annotation_position="top right")
fig5.update_layout(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font_color="#e2e8f0",
    xaxis=dict(showgrid=False),
    yaxis=dict(showgrid=True, gridcolor="rgba(148,163,184,0.1)", title="Count"),
    margin=dict(t=40, b=20, l=20, r=20),
)
st.plotly_chart(fig5, use_container_width=True)
