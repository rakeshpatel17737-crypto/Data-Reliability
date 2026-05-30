"""
AI-powered diagnosis using Groq (Llama 3).
Replaces the rule-based diagnoser when a Groq API key is configured.
"""

import json
import os

from groq import Groq


def diagnose_with_ai(
    issues: list[dict],
    last_snapshot: dict | None,
    df_sample: list[dict],
    source_name: str,
    file_path: str,
    api_key: str,
) -> list[dict]:
    client = Groq(api_key=api_key)
    context = _build_context(issues, last_snapshot, df_sample, source_name, file_path)

    prompt = f"""You are a data reliability expert. A monitoring system has detected problems in a data file.

Analyze the context below and for each issue provide:
1. A short, plain-English explanation of the most likely root cause (1-2 sentences)
2. A specific, actionable remediation step (1-2 sentences)

Be concrete — mention column names, row counts, and percentages where relevant.
Do NOT use jargon. Write as if explaining to someone who does not code.

=== DATA CONTEXT ===
{context}

=== DETECTED ISSUES ===
{json.dumps(issues, indent=2)}

Respond with a JSON array. Each element must correspond to one issue (same order) and contain:
- "likely_cause": string
- "suggested_action": string

Return only valid JSON — no markdown fences, no explanation outside the array."""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
    )
    raw = response.choices[0].message.content.strip()
    diagnoses = _parse_json(raw)

    for i, issue in enumerate(issues):
        if i < len(diagnoses):
            issue["likely_cause"] = diagnoses[i].get("likely_cause", "See data context for details")
            issue["suggested_action"] = diagnoses[i].get("suggested_action", "Review the data file manually")
        else:
            issue.setdefault("likely_cause", "AI diagnosis unavailable for this issue")
            issue.setdefault("suggested_action", "Review the data file manually")

    return issues


def _build_context(issues, last_snapshot, df_sample, source_name, file_path) -> str:
    parts = [f"Data source: {source_name}", f"File: {os.path.basename(file_path)}"]
    if last_snapshot:
        parts.append(f"Previous row count: {last_snapshot['row_count']}")
        parts.append(f"Previous columns: {', '.join(last_snapshot['column_names'])}")
        null_history = last_snapshot.get("null_rates", {})
        if null_history:
            parts.append(f"Previous null rates: {json.dumps(null_history)}")
        numeric_history = last_snapshot.get("numeric_stats", {})
        if numeric_history:
            parts.append(f"Previous numeric ranges: {json.dumps(numeric_history)}")
    else:
        parts.append("No previous snapshot — this is the first scan.")
    if df_sample:
        parts.append(f"Current data sample (first {len(df_sample)} rows): {json.dumps(df_sample)}")
    return "\n".join(parts)


def _parse_json(raw: str) -> list[dict]:
    try:
        clean = raw
        if "```" in clean:
            parts = clean.split("```")
            clean = parts[1] if len(parts) >= 2 else clean
            if clean.startswith("json"):
                clean = clean[4:]
        start = clean.find("[")
        end = clean.rfind("]") + 1
        if start != -1 and end > start:
            return json.loads(clean[start:end])
    except (json.JSONDecodeError, ValueError):
        pass
    return []
