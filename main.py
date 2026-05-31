"""
DATA RELIABILITY SYSTEM
-----------------------
Run this file to start watching your data.

Usage:
  python main.py              ← runs on a schedule (as set in config.yaml)
  python main.py --once       ← runs a single check right now and exits
"""

import argparse
import sys
import time
import yaml

from apscheduler.schedulers.blocking import BlockingScheduler

from connectors.csv_connector import read_csv, get_file_modified_time
from storage.history import save_snapshot, get_last_snapshot
from engine.detector import run_checks
from engine.diagnoser import diagnose
from engine.remediator import auto_fix
from engine.predictor import predict
from alerting.slack_alert import send_all_clear, send_issues, send_error, send_prediction

try:
    from engine.ai_diagnoser import diagnose_with_ai
    _AI_AVAILABLE = True
except ImportError:
    _AI_AVAILABLE = False


def load_config(path="config.yaml") -> dict:
    with open(path, "r") as f:
        return yaml.safe_load(f)


def check_source(source: dict, slack_webhook: str, config: dict = None):
    name = source["name"]
    path = source["path"]
    rules = source.get("rules", {})
    should_auto_fix = source.get("auto_fix", False)

    print(f"  Checking: {name} ({path})")

    try:
        df = read_csv(path)
        file_mod_time = get_file_modified_time(path)
        last_snapshot = get_last_snapshot(name)

        issues = run_checks(df, last_snapshot, rules)

        if issues:
            api_key = (source.get("groq_api_key") or (config or {}).get("groq_api_key", "")
                       or source.get("gemini_api_key") or (config or {}).get("gemini_api_key", "")
                       or source.get("anthropic_api_key") or (config or {}).get("anthropic_api_key", ""))
            if _AI_AVAILABLE and api_key:
                print(f"    🤖 Using AI diagnosis for {name}...")
                df_sample = df.head(5).to_dict(orient="records")
                issues = diagnose_with_ai(issues, last_snapshot, df_sample, name, path, api_key)
            else:
                issues = diagnose(issues, last_snapshot, path, file_mod_time)
            fix_log = []
            if should_auto_fix:
                df, fix_log = auto_fix(df, issues, path)
            send_issues(slack_webhook, name, issues, fix_log)
        else:
            send_all_clear(slack_webhook, name, len(df))

        save_snapshot(name, df, file_mod_time)

        # --- PREDICTIVE CHECK (runs after every snapshot is saved) ---
        prediction = predict(name)
        score = prediction["health_score"]
        risk = prediction["risk_level"]
        print(f"    🔮 Health score: {score}/100  |  Risk: {risk.upper()}")
        if prediction["should_alert"]:
            print(f"    ⚠️  Pre-failure warning sent to Slack for {name}")
            send_prediction(slack_webhook, prediction)

    except Exception as e:
        print(f"  ❌ Error checking '{name}': {e}")
        send_error(slack_webhook, name, str(e))


def run_all_checks(config: dict):
    print(f"\n{'='*50}")
    print(f"Running data reliability checks...")
    print(f"{'='*50}")
    slack_url = config.get("slack_webhook_url", "")
    for source in config.get("data_sources", []):
        check_source(source, slack_url, config)
    print(f"Done.\n")


def main():
    parser = argparse.ArgumentParser(description="Data Reliability System")
    parser.add_argument("--once", action="store_true", help="Run checks once and exit")
    args = parser.parse_args()

    config = load_config()
    interval = config.get("check_interval_minutes", 30)

    if args.once:
        run_all_checks(config)
        return

    print(f"\n🚀 Data Reliability System started!")
    print(f"   Checks will run every {interval} minute(s).")
    print(f"   Press Ctrl+C to stop.\n")

    run_all_checks(config)

    scheduler = BlockingScheduler()
    scheduler.add_job(run_all_checks, "interval", minutes=interval, args=[config])
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        print("\nStopped. Goodbye!")


if __name__ == "__main__":
    main()
