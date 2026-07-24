"""
pages/2_Batch_Processing.py

Processes multiple requests at once from:
  - CSV file upload (must have a 'text' column)
  - JSON file upload (list of objects with 'text' field)
  - The built-in sample dataset (25 requests)
"""

import streamlit as st
import pandas as pd
import json, os, time
from src.database import init_db
from src.router import process_request

init_db()

st.set_page_config(page_title="Batch Processing", page_icon="📁", layout="wide")

st.markdown("# 📁 Batch Processing")
st.markdown("Process multiple requests at once. Upload a CSV/JSON file or run the built-in sample dataset.")

tab1, tab2 = st.tabs(["📤 Upload File", "📋 Run Sample Dataset"])

requests_to_process = []

with tab1:
    uploaded = st.file_uploader("Upload CSV or JSON", type=["csv", "json"])
    if uploaded:
        try:
            if uploaded.name.endswith(".csv"):
                df = pd.read_csv(uploaded)
                if "text" not in df.columns:
                    st.error("CSV must have a `text` column.")
                else:
                    requests_to_process = df["text"].dropna().tolist()
                    st.success(f"Loaded {len(requests_to_process)} requests from CSV.")
            elif uploaded.name.endswith(".json"):
                data = json.load(uploaded)
                if isinstance(data, list):
                    requests_to_process = [
                        item.get("text", "") for item in data if item.get("text")
                    ]
                    st.success(f"Loaded {len(requests_to_process)} requests from JSON.")
                else:
                    st.error("JSON must be a list of objects with a `text` field.")
        except Exception as e:
            st.error(f"Error reading file: {e}")

with tab2:
    sample_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "sample_requests.json")
    try:
        with open(sample_path, "r") as f:
            samples = json.load(f)
        st.info(f"Sample dataset contains **{len(samples)}** requests across 4 types + edge cases.")

        # Show preview
        preview_df = pd.DataFrame([
            {"ID": s["id"], "Type": s.get("expected_request_type", "?"), "Text": s["text"][:80] + "..."}
            for s in samples
        ])
        st.dataframe(preview_df, use_container_width=True, hide_index=True)

        if st.button("🚀 Process All Samples", use_container_width=True):
            requests_to_process = [s["text"] for s in samples]
    except FileNotFoundError:
        st.warning("Sample data file not found at data/sample_requests.json")

# ── Process Batch ───────────────────────────────────────────
if requests_to_process:
    st.markdown("---")
    st.markdown(f"## Processing {len(requests_to_process)} Requests")

    progress = st.progress(0, text="Starting batch processing...")
    results = []

    for i, text in enumerate(requests_to_process):
        progress.progress(
            (i + 1) / len(requests_to_process),
            text=f"Processing request {i + 1}/{len(requests_to_process)}...",
        )
        try:
            case = process_request(text)
            results.append({
                "Case ID": case.id[:8] + "...",
                "Type": case.classification.request_type.replace("_", " ").title(),
                "Urgency": case.classification.urgency.upper(),
                "Confidence": f"{case.classification.confidence:.0%}",
                "Team": case.assigned_team,
                "Status": case.status.replace("_", " ").title(),
                "Response Preview": (case.generated_response[:80] + "...") if case.generated_response else "N/A",
            })
        except Exception as e:
            results.append({
                "Case ID": "ERROR",
                "Type": "Failed",
                "Urgency": "-",
                "Confidence": "-",
                "Team": "-",
                "Status": "Error",
                "Response Preview": str(e)[:80],
            })
        # Small delay to respect Groq rate limits (30 RPM free tier)
        time.sleep(2)

    progress.progress(1.0, text="Batch processing complete!")

    # ── Results Summary ─────────────────────────────────
    st.markdown("### Results Summary")

    results_df = pd.DataFrame(results)
    st.dataframe(results_df, use_container_width=True, hide_index=True)

    # ── Quick Stats ─────────────────────────────────────
    col1, col2, col3, col4 = st.columns(4)
    type_counts = results_df["Type"].value_counts()
    col1.metric("Total Processed", len(results))
    col2.metric("Successful", len([r for r in results if r["Status"] != "Error"]))
    col3.metric("Errors", len([r for r in results if r["Status"] == "Error"]))
    col4.metric("For Review", len([r for r in results if r["Status"] == "Pending Review"]))

    st.success(f"Batch complete! {len(results)} requests processed. View details in the **Audit Trail** page.")
