# 🤖 AI-Powered Incoming Request Processing Workflow

An intelligent prototype that automatically **receives**, **classifies**, and **processes** incoming customer requests through AI-powered remediation pipelines. Built for BPO/customer service operations teams.

![Python](https://img.shields.io/badge/Python-3.12+-blue?logo=python)
![Streamlit](https://img.shields.io/badge/Streamlit-1.45-red?logo=streamlit)
![Groq](https://img.shields.io/badge/Groq-Llama_3.3_70B-green?logo=meta)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## 🎯 What It Does

1. **Receives** customer requests (text, CSV, JSON, or email paste)
2. **Classifies** them using Groq's Llama 3.3 70B with JSON-mode structured output
3. **Routes** to one of 4 distinct remediation branches based on classification
4. **Executes** a multi-step workflow with 4 downstream actions per branch
5. **Generates** a tailored customer response using AI
6. **Logs** everything to an audit trail with full traceability

---

## 🔀 Branching Logic (4 Distinct Pipelines)

| Branch | Trigger | Strategy | Steps |
|--------|---------|----------|-------|
| 🔴 **Complaint** | Billing disputes, service issues, defects | Acknowledge + Escalate + Protect | 1. Generate empathetic acknowledgement → 2. Escalate to senior team → 3. Log as HIGH priority → 4. Set 2-hour follow-up |
| 🟢 **General Enquiry** | Questions, info requests, status checks | Answer + Resolve + Close | 1. Classify sub-topic → 2. Generate AI response → 3. Mark auto-responded → 4. Log as resolved |
| 🟡 **Service Request** | Account changes, cancellations, upgrades | Extract + Route + Confirm + Track | 1. Extract service details → 2. Route to department → 3. Generate confirmation → 4. Set SLA timer |
| ⚫ **Escalation** | Legal threats, repeated issues, safety | Flag + Acknowledge + Alert + Freeze | 1. Flag for human review → 2. Draft urgent acknowledgement → 3. Notify supervisor → 4. Pause auto-resolution |

### Confidence Gate
- Classification confidence ≥ 0.7 → auto-route to branch
- Classification confidence < 0.7 → route to **Human Review Queue** with AI's best guess visible

---

## 🏗️ Architecture

```
Customer Request (Text/CSV/JSON)
        │
        ▼
┌──────────────────────────────────────┐
│      Streamlit UI (app.py)           │
│  Submit / Batch / Dashboard / Audit  │
└──────────────┬───────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│      Router (router.py)              │
│  classify → confidence_check → route │
└──────────────┬───────────────────────┘
               │
        ┌──────┼──────┬──────────┐
        ▼      ▼      ▼          ▼
   Complaint Enquiry Service  Escalation
   (4 steps) (4 steps)(4 steps)(4 steps)
        │      │      │          │
        └──────┼──────┴──────────┘
               ▼
┌──────────────────────────────────────┐
│   Groq API (Llama 3.3 70B)          │
│   Classification + Response Gen      │
└──────────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│   SQLite (cases.db)                  │
│   Audit trail + case persistence     │
└──────────────────────────────────────┘
```

### Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **LLM** | Groq (Llama 3.3 70B) | Free tier, ultra-fast inference, JSON mode for structured classification |
| **Routing** | Code-first (Python dict) | Deterministic dispatch — LLM makes judgment, code handles plumbing |
| **Classification** | JSON mode + low temperature (0.1) | Guarantees valid JSON, consistent labels |
| **Response Gen** | Higher temperature (0.7) | Natural, empathetic tone for customer-facing text |
| **UI** | Streamlit | Rapid prototyping, built-in charts, free cloud deployment |
| **Database** | SQLite | Zero-config, file-based, audit trail + metrics |
| **Error Strategy** | Continue on step failure | A broken SLA timer shouldn't block response generation |

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Free Groq API key from [console.groq.com](https://console.groq.com)

### Setup

```bash
# Clone the repository
git clone https://github.com/Axxhit/ai-request-processor.git
cd ai-request-processor

# Install dependencies
pip install -r requirements.txt

# Configure API key
cp .env.example .env
# Edit .env and add your GROQ_API_KEY

# Run the application
streamlit run app.py
```

The app will be available at `http://localhost:8501`.

---

## 📂 Project Structure

```
├── app.py                         # Main Streamlit app (landing page)
├── requirements.txt               # Python dependencies
├── .env.example                   # API key template
├── .gitignore                     # Git exclusion rules
│
├── src/
│   ├── config.py                  # All settings, prompts, thresholds
│   ├── models.py                  # Pydantic data models
│   ├── database.py                # SQLite CRUD operations
│   ├── groq_client.py             # Groq API wrapper with retry logic
│   ├── classifier.py              # AI classification (JSON mode)
│   ├── response_generator.py      # AI response generation
│   ├── router.py                  # Central orchestrator
│   └── workflows/
│       ├── base.py                # Abstract workflow base class
│       ├── complaint.py           # 🔴 Complaint pipeline
│       ├── enquiry.py             # 🟢 Enquiry pipeline
│       ├── service_request.py     # 🟡 Service request pipeline
│       └── escalation.py          # ⚫ Escalation pipeline
│
├── pages/                         # Streamlit multi-page app
│   ├── 1_Submit_Request.py        # Single request intake
│   ├── 2_Batch_Processing.py      # CSV/JSON batch processing
│   ├── 3_Dashboard.py             # Analytics & metrics charts
│   ├── 4_Audit_Trail.py           # Searchable case history
│   └── 5_Human_Review.py          # Low-confidence review queue
│
├── data/
│   └── sample_requests.json       # 25 synthetic test requests
│
└── tests/
    └── test_classifier.py         # Classification accuracy tests
```

---

## 📊 UI Pages

| Page | Description |
|------|-------------|
| **🏠 Home** | Quick-submit widget, live metric cards |
| **📝 Submit Request** | Type/paste or pick from samples, full workflow visualization |
| **📁 Batch Processing** | Upload CSV/JSON or run all 25 samples with progress tracking |
| **📈 Dashboard** | Pie charts, bar charts, histograms with confidence threshold |
| **📋 Audit Trail** | Filterable table + expandable case details |
| **👁️ Human Review** | Accept or override AI classification for flagged cases |

---

## 🧪 Sample Requests (Built-in)

The app includes 25 pre-built test requests:
- **5 Complaints** — billing disputes, damaged products, rude staff
- **6 General Enquiries** — pricing, hours, shipping, return policy
- **6 Service Requests** — address change, plan upgrade, cancellation
- **4 Escalations** — legal threats, repeated issues, data loss
- **4 Edge Cases** — ambiguous requests, multi-type, vague language

---

## 🔧 Configuration

All tunable parameters are in [`src/config.py`](src/config.py):

| Setting | Default | Purpose |
|---------|---------|---------|
| `GROQ_MODEL` | `llama-3.3-70b-versatile` | LLM model for classification + generation |
| `GROQ_TEMPERATURE_CLASSIFY` | `0.1` | Low = deterministic classification |
| `GROQ_TEMPERATURE_GENERATE` | `0.7` | Higher = natural response writing |
| `CONFIDENCE_THRESHOLD` | `0.7` | Below this → human review queue |
| `SLA_TIMERS` | 24-72 hours | Per-service-type deadlines |
| `TEAM_ROUTING` | Configurable map | Maps request types to team names |

---

## 📋 Technology Stack

| Component | Technology | Why |
|-----------|-----------|-----|
| AI Engine | Groq API (Llama 3.3 70B) | Free, fast, structured JSON output |
| Frontend | Streamlit | Rapid prototyping, charts, free deployment |
| Backend | Python 3.12 | Type hints, pattern matching, modern syntax |
| Database | SQLite | Zero-config, file-based, portable |
| Validation | Pydantic | Type-safe models, automatic validation |
| Charts | Plotly | Interactive, dark-theme-compatible |

**Total cost: $0** — All services used are free tier.

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.
