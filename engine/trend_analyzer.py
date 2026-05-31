"""
Trend Analyzer
--------------
Looks at the last N snapshots for a data source and detects
gradual warning signals that a pipeline is heading toward failure.
"""

import json
import sqlite3
from datetime import datetime

DB_PATH = "reliability_history.db"
LOOKBACK = 5   # number of recent snapshots to analyze


def get_recent_snapshots(source_name: str, n: int = LOOKBACK) -> list[dict]:
    """Fetch the last N snapshots for a source, oldest first."""
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        """SELECT id, source_name, captured_at, row_count, column_names,
                  null_rates, numeric_stats, file_modified_at
           FROM snapshots
           WHERE source_name = ?
           ORDER BY id DESC
           LIMIT ?""",
        (source_name, n),
    ).fetchall()
    conn.close()

    snapshots = []
    for row in reversed(rows):   # oldest → newest
        snapshots.append({
            "id": row[0],
            "source_name": row[1],
            "captured_at": row[2],
            "row_count": row[3],
            "column_names": json.loads(row[4]),
            "null_rates": json.loads(row[5]),
            "numeric_stats": json.loads(row[6]),
            "file_modified_at": row[7],
        })
    return snapshots


def analyze_trends(source_name: str) -> list[dict]:
    """
    Analyze recent snapshots and return a list of trend warnings.
    Each warning has: signal, severity, trend, description
    """
    snapshots = get_recent_snapshots(source_name)
    if len(snapshots) < 2:
        return []   # not enough history to detect trends

    warnings = []

    # --- 1. ROW COUNT TREND ---
    row_counts = [s["row_count"] for s in snapshots]
    row_trend = _calc_trend(row_counts)
    if row_trend < -0.05:   # shrinking more than 5% per run on average
        total_drop = round((row_counts[0] - row_counts[-1]) / max(row_counts[0], 1) * 100, 1)
        warnings.append({
            "signal": "row_count_trend",
            "severity": "critical" if row_trend < -0.15 else "warning",
            "trend": round(row_trend * 100, 1),
            "values": row_counts,
            "description": (
                f"Row count has been shrinking across the last {len(snapshots)} runs "
                f"(from {row_counts[0]} → {row_counts[-1]}, total drop: {total_drop}%). "
                f"Average change per run: {round(row_trend * 100, 1)}%."
            ),
        })

    # --- 2. NULL RATE TREND (per column) ---
    all_cols = set()
    for s in snapshots:
        all_cols.update(s["null_rates"].keys())

    for col in all_cols:
        null_series = [s["null_rates"].get(col, 0) for s in snapshots]
        if max(null_series) == 0:
            continue   # always clean, skip
        null_trend = _calc_trend(null_series)
        if null_trend > 2.0:   # null rate rising more than 2 percentage points per run
            warnings.append({
                "signal": "null_rate_trend",
                "severity": "critical" if null_trend > 5.0 else "warning",
                "column": col,
                "trend": round(null_trend, 1),
                "values": null_series,
                "description": (
                    f"Null rate in column '{col}' has been rising across the last {len(snapshots)} runs "
                    f"({null_series[0]}% → {null_series[-1]}%). "
                    f"Average increase per run: +{round(null_trend, 1)} percentage points."
                ),
            })

    # --- 3. NUMERIC MEAN DRIFT (per column) ---
    all_numeric_cols = set()
    for s in snapshots:
        all_numeric_cols.update(s["numeric_stats"].keys())

    for col in all_numeric_cols:
        means = []
        for s in snapshots:
            stat = s["numeric_stats"].get(col)
            if stat and stat.get("mean") is not None:
                means.append(stat["mean"])

        if len(means) < 3:
            continue

        mean_trend = _calc_trend(means)
        baseline = means[0]
        if baseline == 0:
            continue
        drift_pct = abs(mean_trend / baseline) * 100

        if drift_pct > 10:   # mean drifting more than 10% per run
            direction = "rising" if mean_trend > 0 else "falling"
            warnings.append({
                "signal": "numeric_mean_drift",
                "severity": "critical" if drift_pct > 25 else "warning",
                "column": col,
                "trend": round(mean_trend, 4),
                "values": means,
                "description": (
                    f"Average value of '{col}' is steadily {direction} "
                    f"({round(means[0], 2)} → {round(means[-1], 2)} over {len(means)} runs). "
                    f"Drift rate: {round(drift_pct, 1)}% per run."
                ),
            })

    # --- 4. RUN GAP TREND (source arriving later each time) ---
    timestamps = [
        datetime.fromisoformat(s["captured_at"]) for s in snapshots
    ]
    if len(timestamps) >= 3:
        gaps_minutes = [
            (timestamps[i+1] - timestamps[i]).total_seconds() / 60
            for i in range(len(timestamps) - 1)
        ]
        gap_trend = _calc_trend(gaps_minutes)
        if gap_trend > 5:   # gaps growing more than 5 min per run
            warnings.append({
                "signal": "run_gap_trend",
                "severity": "warning",
                "trend": round(gap_trend, 1),
                "values": [round(g, 1) for g in gaps_minutes],
                "description": (
                    f"Time between runs is increasing (last gaps: "
                    f"{', '.join(str(round(g,1))+'min' for g in gaps_minutes[-3:])}). "
                    f"The data source may be slowing down."
                ),
            })

    return warnings


def _calc_trend(values: list[float]) -> float:
    """
    Returns the average change per step (linear slope).
    Positive = rising, Negative = falling.
    Uses simple linear regression slope.
    """
    n = len(values)
    if n < 2:
        return 0.0
    x_mean = (n - 1) / 2
    y_mean = sum(values) / n
    numerator = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values))
    denominator = sum((i - x_mean) ** 2 for i in range(n))
    if denominator == 0:
        return 0.0
    return numerator / denominator
