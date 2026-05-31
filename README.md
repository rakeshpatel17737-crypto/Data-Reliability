# 🛡️ AI-Powered Data Reliability System

A data pipeline monitoring system that **predicts failures before they happen**, detects problems the moment they occur, and uses AI to explain why — all delivered to your Slack.

> Built as a learning project across multiple sessions, this system solves two problems no existing data reliability tool solves together.

---

## 🔥 What Makes This Different

| Existing tools (Great Expectations, Monte Carlo) | This project |
|---|---|
| Detect problems **after** they happen | Predicts problems **before** they happen |
| Generic error messages | AI-written root cause analysis |
| Complex setup | Run in 2 minutes locally or on Kaggle |

---

## 🧠 Two-Layer Architecture

```
Pipeline running normally
        ↓
🔮 Predictor watches trends silently every run
        ↓
Score drops → Pre-failure Slack warning sent
        ↓
You fix it before it breaks
        ↓
If missed → Detector catches the actual failure
        ↓
🤖 AI diagnoses why and tells you exactly what to do
```

---

## ✅ What It Detects

| Problem | Severity |
|---|---|
| Missing required column | 🔴 Critical |
| Low row count | 🔴 Critical |
| Row count drop >20% | 🔴 Critical |
| High null rate | 🟡 Warning |
| Schema drift (columns added/removed) | 🟡 Warning |
| Numeric anomaly | 🟡 Warning |

## 🔮 What It Predicts (across last 5 runs)

| Trend Signal | What It Means |
|---|---|
| Row count shrinking run-by-run | Data loss building up |
| Null rate creeping upward | Source quality degrading |
| Numeric mean drifting steadily | Values going out of range |

Each source gets a **Health Score (0–100)**:
- 🟢 80–100 — Healthy
- 🟡 50–79 — Warning, monitor closely
- 🔴 0–49 — Critical, failure likely soon

---

## 🤖 AI Diagnosis

When a problem is detected, the system sends it to **Groq (Llama 3)** which reads your actual data and writes a plain-English explanation:

> *"The 'email' column has a high percentage of missing values, likely due to incomplete data entry, as seen in customer 'C004' where the email is listed as NaN. Review the data entry process and verify email information for affected customers."*

---

## 🚀 How to Run

### Option 1 — Local (Mac/Linux)

**Setup (first time only):**
```bash
python3 -m venv venv
venv/bin/pip install -r requirements.txt
```

**Run once:**
```bash
venv/bin/python main.py --once
```

**Run on a schedule:**
```bash
venv/bin/python main.py
```
Press `Ctrl+C` to stop.

### Option 2 — Kaggle (no setup needed)

Upload `data_reliability_kaggle.ipynb` to [kaggle.com](https://kaggle.com) and run cells top to bottom.

---

## ⚙️ Configuration

Open `config.yaml` and fill in your details:

```yaml
slack_webhook_url: ""     # Get from api.slack.com/messaging/webhooks
groq_api_key: ""          # Get free key at console.groq.com

data_sources:
  - name: "My File"
    type: csv
    path: "/path/to/your/file.csv"
    auto_fix: true
    rules:
      max_null_percent: 5
      min_row_count: 10
      required_columns:
        - column_one
        - column_two
```

---

## 🔧 What It Auto-Fixes (when `auto_fix: true`)

- Removes exact duplicate rows
- Fills missing numbers with the column median
- Fills missing text with "UNKNOWN"
- Always saves a timestamped backup before changing anything

---

## 📂 Project Structure

```
config.yaml               ← Edit this. Controls everything.
main.py                   ← Run this to start.
data_reliability_kaggle.ipynb  ← Kaggle version (no setup needed)
sample_data/              ← Example CSV files for testing
connectors/
  csv_connector.py        ← Reads CSV files
engine/
  detector.py             ← Finds problems in current data
  diagnoser.py            ← Rule-based root cause analysis (fallback)
  ai_diagnoser.py         ← AI-powered diagnosis via Groq
  trend_analyzer.py       ← Detects deteriorating trends across runs
  predictor.py            ← Health score + pre-failure alerts
  remediator.py           ← Auto-fixes safe issues
alerting/
  slack_alert.py          ← Sends Slack messages
storage/
  history.py              ← Saves snapshots to SQLite database
```

---

## 🛠️ Built With

- **Python** — core language
- **Pandas** — data processing
- **SQLite** — stores historical snapshots
- **Groq (Llama 3)** — AI-powered diagnosis
- **Slack Webhooks** — real-time alerts
- **APScheduler** — runs checks on a schedule
