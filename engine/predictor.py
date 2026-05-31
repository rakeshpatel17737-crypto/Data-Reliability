"""
Failure Predictor
-----------------
Takes trend warnings and converts them into a single Pipeline Health Score
with a predicted failure window and a plain-English risk summary.
"""

from engine.trend_analyzer import analyze_trends


# Points deducted per warning type
SEVERITY_PENALTY = {
    "critical": 30,
    "warning": 15,
}

SIGNAL_LABELS = {
    "row_count_trend":    "📉 Row count shrinking",
    "null_rate_trend":    "🕳️  Null rate rising",
    "numeric_mean_drift": "📊 Numeric values drifting",
    "run_gap_trend":      "⏱️  Runs getting slower",
}


def predict(source_name: str) -> dict:
    """
    Returns a prediction dict:
      - health_score  : 0–100 (100 = perfectly healthy)
      - risk_level    : 'healthy' | 'warning' | 'critical'
      - warnings      : list of trend warnings
      - summary       : plain-English summary string
      - should_alert  : True if a pre-failure Slack alert should be sent
    """
    warnings = analyze_trends(source_name)

    # Calculate health score
    score = 100
    for w in warnings:
        score -= SEVERITY_PENALTY.get(w["severity"], 10)
    score = max(0, score)

    # Determine risk level
    if score >= 80:
        risk_level = "healthy"
    elif score >= 50:
        risk_level = "warning"
    else:
        risk_level = "critical"

    # Build plain-English summary
    summary = _build_summary(source_name, score, risk_level, warnings)

    return {
        "source_name": source_name,
        "health_score": score,
        "risk_level": risk_level,
        "warnings": warnings,
        "summary": summary,
        "should_alert": risk_level in ("warning", "critical"),
    }


def _build_summary(source_name, score, risk_level, warnings) -> str:
    if not warnings:
        return f"✅ {source_name} looks healthy — no concerning trends detected."

    emoji = "🔴" if risk_level == "critical" else "🟡"
    lines = [
        f"{emoji} *{source_name}* — Health Score: {score}/100  |  Risk: {risk_level.upper()}",
        "",
        "*Trend warnings detected:*",
    ]
    for w in warnings:
        label = SIGNAL_LABELS.get(w["signal"], w["signal"])
        lines.append(f"  • {label}: {w['description']}")

    lines.append("")
    if risk_level == "critical":
        lines.append(
            "🚨 *Prediction:* This pipeline is showing multiple deteriorating signals. "
            "A failure is likely within the next few runs if no action is taken."
        )
    else:
        lines.append(
            "⚠️ *Prediction:* Early warning signs detected. "
            "Monitor closely — if the trend continues, a failure may occur soon."
        )

    return "\n".join(lines)
