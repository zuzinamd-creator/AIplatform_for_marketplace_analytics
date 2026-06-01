import io
from typing import Any

import pandas as pd


def load_file_to_dataframe(filename: str, content: bytes) -> pd.DataFrame:
    """Load CSV or Excel report into a pandas DataFrame."""
    lower = filename.lower()
    buffer = io.BytesIO(content)

    if lower.endswith(".csv"):
        return pd.read_csv(buffer)
    if lower.endswith((".xlsx", ".xls")):
        return pd.read_excel(buffer)
    raise ValueError(f"Unsupported file format: {filename}")


def dataframe_to_raw_records(df: pd.DataFrame, max_rows: int = 5000) -> dict[str, Any]:
    """Serialize DataFrame sample for JSONB storage (MVP raw snapshot)."""
    limited = df.head(max_rows)
    return {
        "columns": list(limited.columns.astype(str)),
        "row_count": int(len(df)),
        "sample_rows": limited.fillna("").astype(str).to_dict(orient="records"),
    }
