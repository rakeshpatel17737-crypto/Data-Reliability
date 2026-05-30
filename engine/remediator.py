import os
import shutil
from datetime import datetime

import pandas as pd


def auto_fix(df: pd.DataFrame, issues: list[dict], file_path: str) -> tuple[pd.DataFrame, list[str]]:
    """
    Apply safe automatic fixes to the dataframe.
    Returns the fixed dataframe and a list of human-readable descriptions of what was fixed.
    """
    fix_log = []
    original_len = len(df)

    # Fix 1: Remove exact duplicate rows
    dupes = df.duplicated().sum()
    if dupes > 0:
        df = df.drop_duplicates()
        fix_log.append(f"Removed {dupes} duplicate row(s)")

    # Fix 2: Fill missing numeric values with the column median
    for col in df.select_dtypes(include="number").columns:
        null_count = df[col].isna().sum()
        if null_count > 0:
            median_val = df[col].median()
            df[col] = df[col].fillna(median_val)
            fix_log.append(f"Filled {null_count} missing value(s) in '{col}' with median ({median_val})")

    # Fix 3: Fill missing text values with "UNKNOWN"
    for col in df.select_dtypes(include="object").columns:
        null_count = df[col].isna().sum()
        if null_count > 0:
            df[col] = df[col].fillna("UNKNOWN")
            fix_log.append(f"Filled {null_count} missing text value(s) in '{col}' with 'UNKNOWN'")

    if fix_log:
        _backup_and_save(df, file_path)
        fix_log.append(f"Backup of original file saved before applying fixes")

    return df, fix_log


def _backup_and_save(df: pd.DataFrame, file_path: str):
    """Save a backup of the original file, then overwrite with the fixed version."""
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    base, ext = os.path.splitext(file_path)
    backup_path = f"{base}_backup_{timestamp}{ext}"
    shutil.copy2(file_path, backup_path)
    df.to_csv(file_path, index=False)
