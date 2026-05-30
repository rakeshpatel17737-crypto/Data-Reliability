import json
import requests
from datetime import datetime


SEVERITY_EMOJI = {
    "critical": "🔴",
    "warning":  "🟡",
    "info":     "🔵",
}


def send_all_clear(webhook_url: str, source_name: str, row_count: int):
    """Send a green 'all good' message to Slack."""
    if not _is_real_webhook(webhook_url):
        print(f"[Slack] ✅ All checks passed for '{source_name}' ({row_count} rows) — no Slack URL configured")
        return
    _post(webhook_url, {
        "text": f"✅ *{source_name}* — All checks passed | {row_count} rows | {_now()}"
    })


def send_issues(webhook_url: str, source_name: str, issues: list[dict], fix_log: list[str]):
    """Send a detailed Slack alert for detected issues."""
    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"⚠️ Data Issues Found: {source_name}"}
        },
        {
            "type": "context",
            "elements": [{"type": "mrkdwn", "text": f"Checked at {_now()} • {len(issues)} issue(s) found"}]
        },
        {"type": "divider"},
    ]

    for issue in issues:
        emoji = SEVERITY_EMOJI.get(issue.get("severity", "warning"), "🟡")
        section_text = f"{emoji} *{issue['detail']}*"
        if "likely_cause" in issue:
            section_text += f"\n*Likely cause:* {issue['likely_cause']}"
        if "suggested_action" in issue:
            section_text += f"\n*What to do:* {issue['suggested_action']}"

        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": section_text}
        })
        blocks.append({"type": "divider"})

    if fix_log:
        fixes_text = "\n".join(f"• {f}" for f in fix_log)
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"🔧 *Auto-fixes applied:*\n{fixes_text}"}
        })

    message = {"blocks": blocks, "text": f"⚠️ {len(issues)} issue(s) found in {source_name}"}

    if not _is_real_webhook(webhook_url):
        print(f"\n[Slack Preview — no webhook configured]\n")
        for issue in issues:
            emoji = SEVERITY_EMOJI.get(issue.get("severity", "warning"), "🟡")
            print(f"  {emoji} {issue['detail']}")
            if "likely_cause" in issue:
                print(f"     Likely cause: {issue['likely_cause']}")
            if "suggested_action" in issue:
                print(f"     What to do:   {issue['suggested_action']}")
        if fix_log:
            print(f"\n  🔧 Auto-fixes applied:")
            for f in fix_log:
                print(f"     • {f}")
        print()
        return

    _post(webhook_url, message)


def send_error(webhook_url: str, source_name: str, error: str):
    """Send an error alert to Slack when the tool itself fails."""
    msg = f"🔴 *Error checking '{source_name}'*\n```{error}```\n_Check that the file path in config.yaml is correct._"
    if not _is_real_webhook(webhook_url):
        print(f"[Slack] ERROR for '{source_name}': {error}")
        return
    _post(webhook_url, {"text": msg})


def _post(webhook_url: str, payload: dict):
    try:
        resp = requests.post(webhook_url, data=json.dumps(payload), headers={"Content-Type": "application/json"}, timeout=10)
        if resp.status_code != 200:
            print(f"[Slack] Warning: message not delivered (HTTP {resp.status_code}): {resp.text}")
    except Exception as e:
        print(f"[Slack] Could not send message: {e}")


def _is_real_webhook(url: str) -> bool:
    return url.startswith("https://hooks.slack.com/services/") and "YOUR" not in url


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
