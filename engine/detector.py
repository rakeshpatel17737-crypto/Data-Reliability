import pandas as pd


def run_checks(df: pd.DataFrame, last_snapshot: dict | None, rules: dict) -> list[dict]:
    """
    Compare the current data against the last snapshot and config rules.
    Returns a list of issues found. Each issue is a dict with 'type', 'severity', and 'detail'.
    """
    issues = []
    current_cols = set(df.columns)

    # --- Rule: required columns must be present ---
    required = set(rules.get("required_columns", []))
    missing_required = required - current_cols
    if missing_required:
        issues.append({
            "type": "missing_required_column",
            "severity": "critical",
            "detail": f"Required column(s) not found: {', '.join(sorted(missing_required))}",
            "columns": list(missing_required),
        })

    # --- Rule: minimum row count ---
    min_rows = rules.get("min_row_count", 1)
    if len(df) < min_rows:
        issues.append({
            "type": "low_row_count",
            "severity": "critical",
            "detail": f"Only {len(df)} rows found (minimum expected: {min_rows})",
            "current": len(df),
            "threshold": min_rows,
        })

    # --- Rule: null/missing value threshold ---
    max_null_pct = rules.get("max_null_percent", 10)
    for col in df.columns:
        null_pct = round(df[col].isna().mean() * 100, 2)
        if null_pct > max_null_pct:
            issues.append({
                "type": "high_null_rate",
                "severity": "warning",
                "detail": f"Column '{col}' has {null_pct}% missing values (limit: {max_null_pct}%)",
                "column": col,
                "null_percent": null_pct,
                "threshold": max_null_pct,
            })

    if last_snapshot is None:
        return issues

    prev_cols = set(last_snapshot["column_names"])

    # --- Schema drift: columns added or removed ---
    added = current_cols - prev_cols
    removed = prev_cols - current_cols
    if added:
        issues.append({
            "type": "schema_drift_added",
            "severity": "warning",
            "detail": f"New column(s) appeared since last check: {', '.join(sorted(added))}",
            "columns": list(added),
        })
    if removed:
        issues.append({
            "type": "schema_drift_removed",
            "severity": "critical",
            "detail": f"Column(s) disappeared since last check: {', '.join(sorted(removed))}",
            "columns": list(removed),
        })

    # --- Row count drop ---
    prev_rows = last_snapshot["row_count"]
    if prev_rows > 0:
        drop_pct = (prev_rows - len(df)) / prev_rows * 100
        if drop_pct > 20:
            issues.append({
                "type": "row_count_drop",
                "severity": "critical",
                "detail": f"Row count dropped {round(drop_pct)}% (was {prev_rows}, now {len(df)})",
                "previous": prev_rows,
                "current": len(df),
                "drop_percent": round(drop_pct, 1),
            })

    # --- Numeric anomaly: value outside historical range ---
    prev_stats = last_snapshot.get("numeric_stats", {})
    for col in df.select_dtypes(include="number").columns:
        if col not in prev_stats or df[col].isna().all():
            continue
        hist = prev_stats[col]
        if hist["min"] is None or hist["max"] is None:
            continue
        curr_min = float(df[col].min())
        curr_max = float(df[col].max())
        hist_range = hist["max"] - hist["min"]
        buffer = max(hist_range * 0.5, 1)
        if curr_min < hist["min"] - buffer or curr_max > hist["max"] + buffer:
            issues.append({
                "type": "numeric_anomaly",
                "severity": "warning",
                "detail": (
                    f"Column '{col}' values out of historical range. "
                    f"History: [{hist['min']}, {hist['max']}] | Now: [{curr_min}, {curr_max}]"
                ),
                "column": col,
                "historical_min": hist["min"],
                "historical_max": hist["max"],
                "current_min": curr_min,
                "current_max": curr_max,
            })

    return issues
