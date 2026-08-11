"""Small parsing helpers shared by provider adapters."""

import re
from collections.abc import Iterable


NUMBER_TOKEN = r"[+-]?(?:\d[\d,]*(?:\.\d+)?|\.\d+)-?"


def first_match(text: str, patterns: Iterable[str], group: int = 1) -> str | None:
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE)
        if match:
            return " ".join(match.group(group).split()).strip(" :-")
    return None


def parse_number(value: str | None) -> float | None:
    if value is None:
        return None
    cleaned = value.replace(",", "").replace("₹", "").replace("R", "").strip()
    negative = cleaned.endswith("-")
    cleaned = cleaned.rstrip("-")
    try:
        number = float(cleaned)
    except ValueError:
        return None
    return -number if negative else number


def number_match(text: str, patterns: Iterable[str], group: int = 1) -> float | None:
    return parse_number(first_match(text, patterns, group))


def safe_divide(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator in (None, 0):
        return None
    return numerator / denominator


def sum_known(*values: float | None) -> float | None:
    known = [value for value in values if value is not None]
    return sum(known) if known else None


def normalized_month(value: str | None) -> str | None:
    if not value:
        return None
    compact = re.sub(r"\s+", "-", value.strip().upper())
    match = re.search(r"([A-Z]{3,9})[-,](\d{2,4})", compact)
    if not match:
        return value.strip().upper()
    month = match.group(1)[:3]
    year = match.group(2)
    if len(year) == 2:
        year = f"20{year}"
    return f"{month}-{year}"
