import pandas as pd
import os


def read_csv(path: str) -> pd.DataFrame:
    """Read a CSV file and return it as a table. Raises clear errors if file not found."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Could not find the file: {path}\nPlease check the path in config.yaml")
    try:
        df = pd.read_csv(path)
        return df
    except Exception as e:
        raise ValueError(f"Could not read '{path}' as a CSV file. Error: {e}")


def get_file_modified_time(path: str) -> float:
    """Returns when the file was last modified (used for diagnosis)."""
    if os.path.exists(path):
        return os.path.getmtime(path)
    return 0.0
