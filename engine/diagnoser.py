import os
import time


def diagnose(issues: list[dict], last_snapshot: dict | None, file_path: str, file_modified_at: float) -> list[dict]:
    """
    For each detected issue, add a likely cause and a suggested action.
    Returns the same list with 'likely_cause' and 'suggested_action' added to each issue.
    """
    file_was_recently_modified = _file_recently_changed(last_snapshot, file_modified_at)

    for issue in issues:
        issue_type = issue["type"]

        if issue_type in ("schema_drift_removed", "missing_required_column"):
            if file_was_recently_modified:
                issue["likely_cause"] = "The source file was recently modified or re-exported"
                issue["suggested_action"] = (
                    f"Re-open the original source and make sure all required columns are present "
                    f"before re-exporting to '{os.path.basename(file_path)}'"
                )
            else:
                issue["likely_cause"] = "A column was accidentally deleted or renamed in the file"
                issue["suggested_action"] = "Open the file and check if the column was renamed or removed by mistake"

        elif issue_type == "schema_drift_added":
            issue["likely_cause"] = "New data or a new field was added to the source"
            issue["suggested_action"] = (
                "Verify the new column is intentional. If yes, update 'required_columns' in config.yaml"
            )

        elif issue_type == "low_row_count":
            if file_was_recently_modified:
                issue["likely_cause"] = "The file was recently overwritten, possibly with only partial data"
                issue["suggested_action"] = "Check if the file export/import job completed successfully"
            else:
                issue["likely_cause"] = "Rows may have been accidentally deleted from the file"
                issue["suggested_action"] = "Open the file and verify all expected records are present"

        elif issue_type == "row_count_drop":
            drop = issue.get("drop_percent", 0)
            if drop > 80:
                issue["likely_cause"] = "File appears nearly empty — possible failed export or accidental clear"
                issue["suggested_action"] = "Restore from the most recent backup or re-run the data export"
            else:
                issue["likely_cause"] = "A significant number of rows were removed or filtered out"
                issue["suggested_action"] = "Check if a data pipeline step is incorrectly filtering records"

        elif issue_type == "high_null_rate":
            col = issue.get("column", "unknown")
            null_pct = issue.get("null_percent", 0)
            if null_pct > 80:
                issue["likely_cause"] = f"Column '{col}' is almost entirely empty — possibly a failed data join or export"
                issue["suggested_action"] = f"Check the data source for column '{col}' and re-export if needed"
            else:
                issue["likely_cause"] = f"Some records are missing values for '{col}'"
                issue["suggested_action"] = (
                    f"Review the source data for '{col}'. "
                    "If auto_fix is enabled, missing values will be filled automatically."
                )

        elif issue_type == "numeric_anomaly":
            col = issue.get("column", "unknown")
            issue["likely_cause"] = f"Values in '{col}' are outside the range seen in previous scans"
            issue["suggested_action"] = (
                f"Verify if the change in '{col}' is expected (e.g., a legitimate spike or data entry error)"
            )

        else:
            issue["likely_cause"] = "Unknown — requires manual investigation"
            issue["suggested_action"] = "Review the data file and compare with the previous version"

    return issues


def _file_recently_changed(last_snapshot: dict | None, current_modified_at: float) -> bool:
    if last_snapshot is None:
        return False
    prev_modified = last_snapshot.get("file_modified_at", 0)
    return current_modified_at > prev_modified
