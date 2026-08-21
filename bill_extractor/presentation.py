"""Presentation-only formatting for the Streamlit preview table."""

import pandas as pd

from bill_extractor.models import BillRecord
from bill_extractor.schema import FIELDS


DISPLAY_LABELS = {
    "night_units_percent": "% of Total units (Night)",
    "tou_percent": "% of Total units (TOU)",
}


def display_dataframe(records: list[BillRecord]) -> pd.DataFrame:
    """Build an Arrow-safe string dataframe without changing extracted values."""
    rows: list[list[str]] = []
    for record in records:
        row: list[str] = []
        for field in FIELDS:
            value = record.values.get(field.key)
            if value is None:
                row.append("-")
            elif field.kind == "percent":
                row.append(f"{float(value):.2%}")
            else:
                row.append(str(value))
        rows.append(row)

    columns = [DISPLAY_LABELS.get(field.key, field.label) for field in FIELDS]
    frame = pd.DataFrame(rows, columns=columns)
    return frame.astype("string")
