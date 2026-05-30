# Data Reliability System

A tool that watches your data files, detects problems, explains why they happened, and alerts you on Slack.

---

## How to Start It

**Run once (check now and stop):**
```
venv/bin/python main.py --once
```

**Run on a schedule (keeps watching automatically):**
```
venv/bin/python main.py
```
Press `Ctrl+C` to stop.

---

## How to Set Up Slack Alerts

1. Go to https://api.slack.com/messaging/webhooks
2. Click "Create your Slack app" and follow the steps
3. Copy your Webhook URL (looks like: `https://hooks.slack.com/services/XXX/YYY/ZZZ`)
4. Open `config.yaml` and paste it next to `slack_webhook_url:`

Until you add a real URL, alerts will show as printed messages in the terminal instead.

---

## How to Watch Your Own Files

Open `config.yaml` and add your file under `data_sources`:

```yaml
data_sources:
  - name: "My File"        ← any name you want
    type: csv
    path: "/path/to/your/file.csv"
    auto_fix: true         ← set to false if you don't want automatic fixes
    rules:
      max_null_percent: 5
      min_row_count: 10
      required_columns:
        - column_one
        - column_two
```

---

## What It Detects

| Problem | What It Means |
|---|---|
| 🔴 Missing required column | A column you said must exist has disappeared |
| 🔴 Low row count | Fewer rows than expected — possible data loss |
| 🔴 Row count drop | Big drop since last check — possible partial overwrite |
| 🟡 High null rate | Too many empty/blank values in a column |
| 🟡 Schema drift | Columns added or removed since last check |
| 🟡 Numeric anomaly | Numbers outside the range seen in previous checks |

---

## What It Auto-Fixes (when `auto_fix: true`)

- Removes exact duplicate rows
- Fills missing numbers with the column average
- Fills missing text with "UNKNOWN"
- Always saves a backup before changing anything

---

## Project Files

```
config.yaml        ← Edit this. Controls everything.
main.py            ← Run this to start.
sample_data/       ← Example CSV files for testing
connectors/        ← Code that reads your files
engine/            ← Detection, diagnosis, and fix logic
alerting/          ← Slack messaging
storage/           ← Saves history to a local database
```
