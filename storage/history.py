import json
import sqlite3
import os
from datetime import datetime

import pandas as pd

DB_PATH = "reliability_history.db"


def _get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_name TEXT NOT NULL,
            captured_at TEXT NOT NULL,
            row_count INTEGER,
            column_names TEXT,
            null_rates TEXT,
            numeric_stats TEXT,
            file_modified_at REAL
        )
    """)
    conn.commit()
    return conn


def save_snapshot(source_name: str, df: pd.DataFrame, file_modified_at: float = 0.0):
    """Save a statistical snapshot of the current state of a data source."""
    column_names = list(df.columns)
    null_rates = {col: round(df[col].isna().mean() * 100, 2) for col in df.columns}

    numeric_stats = {}
    for col in df.select_dtypes(include="number").columns:
        numeric_stats[col] = {
            "min": float(df[col].min()) if not df[col].isna().all() else None,
            "max": float(df[col].max()) if not df[col].isna().all() else None,
            "mean": round(float(df[col].mean()), 4) if not df[col].isna().all() else None,
        }

    conn = _get_conn()
    conn.execute(
        """INSERT INTO snapshots
           (source_name, captured_at, row_count, column_names, null_rates, numeric_stats, file_modified_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            source_name,
            datetime.utcnow().isoformat(),
            len(df),
            json.dumps(column_names),
            json.dumps(null_rates),
            json.dumps(numeric_stats),
            file_modified_at,
        ),
    )
    conn.commit()
    conn.close()


def get_last_snapshot(source_name: str) -> dict | None:
    """Retrieve the most recent snapshot for a data source."""
    conn = _get_conn()
    row = conn.execute(
        "SELECT * FROM snapshots WHERE source_name = ? ORDER BY id DESC LIMIT 1",
        (source_name,),
    ).fetchone()
    conn.close()

    if not row:
        return None

    return {
        "id": row[0],
        "source_name": row[1],
        "captured_at": row[2],
        "row_count": row[3],
        "column_names": json.loads(row[4]),
        "null_rates": json.loads(row[5]),
        "numeric_stats": json.loads(row[6]),
        "file_modified_at": row[7],
    }
