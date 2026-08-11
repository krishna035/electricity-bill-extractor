"""Backward-compatible API for integrations using the original prototype."""

import re
from io import BytesIO
from typing import Any

import fitz

from bill_extractor.providers import PARSERS
from bill_extractor.utils import NUMBER_TOKEN, first_match, number_match


def extract_pdf_text(pdf_bytes: bytes) -> tuple[str, int]:
    """Extract selectable text from a PDF byte string."""
    with fitz.open(stream=BytesIO(pdf_bytes), filetype="pdf") as document:
        return "\n".join(page.get_text("text", sort=True) for page in document), document.page_count


GENERIC_TEXT_PATTERNS = {
    "consumer_number": [r"(?:consumer|customer|account|service)\s*(?:no|number|id)?\s*[:\-]?\s*([A-Z0-9/\-]{4,})"],
    "meter_number": [r"meter\s*(?:no|number)?\s*[:\-]?\s*([A-Z0-9/\-]{4,})"],
    "tariff": [r"(?:tariff|category)\s*(?:code|category)?\s*[:\-]?\s*([A-Z0-9][A-Z0-9 /\-]{1,30})"],
    "billing_period": [r"(?:billing|bill)\s*(?:period|month)\s*[:\-]?\s*([A-Z0-9 /\-.]{4,30})"],
    "bill_date": [r"(?:bill|invoice)\s*date\s*[:\-]?\s*(\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4})"],
    "due_date": [r"(?:due|payment)\s*date\s*[:\-]?\s*(\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4})"],
}

GENERIC_NUMBER_PATTERNS = {
    "sanctioned_load_kw": [rf"sanctioned\s*load(?:\s*\(?kw\)?)?\s*[:\-]?\s*({NUMBER_TOKEN})"],
    "contract_demand_kva": [rf"contract(?:ed)?\s*demand(?:\s*\(?kva\)?)?\s*[:\-]?\s*({NUMBER_TOKEN})"],
    "maximum_demand_kva": [rf"(?:maximum|max|recorded|billing)\s*demand(?:\s*\(?kva\)?)?\s*[:\-]?\s*({NUMBER_TOKEN})"],
    "kwh": [rf"(?:units\s*consumed|consumption)?\s*kwh\s*[:\-]?\s*({NUMBER_TOKEN})", rf"^\s*kwh\s*[:\-]?\s*({NUMBER_TOKEN})"],
    "kvah": [rf"(?:units\s*consumed|consumption)?\s*kvah\s*[:\-]?\s*({NUMBER_TOKEN})"],
    "power_factor": [rf"(?:average\s*)?(?:power\s*factor|p\.?f\.?)\s*[:\-]?\s*({NUMBER_TOKEN})"],
    "fixed_charges": [rf"(?:fixed|demand)\s*charges?\s*[:\-]?\s*(?:rs\.?|inr|₹)?\s*({NUMBER_TOKEN})"],
    "energy_charges": [rf"energy\s*charges?\s*[:\-]?\s*(?:rs\.?|inr|₹)?\s*({NUMBER_TOKEN})"],
    "electricity_duty": [rf"(?:electricity\s*)?duty\s*[:\-]?\s*(?:rs\.?|inr|₹)?\s*({NUMBER_TOKEN})"],
    "arrears": [rf"(?:previous\s*)?arrears?\s*[:\-]?\s*(?:rs\.?|inr|₹)?\s*({NUMBER_TOKEN})"],
    "total_amount": [rf"(?:net|total|bill)\s*(?:amount|payable|due)\s*[:\-]?\s*(?:rs\.?|inr|₹)?\s*({NUMBER_TOKEN})", rf"amount\s*payable\s*[:\-]?\s*(?:rs\.?|inr|₹)?\s*({NUMBER_TOKEN})"],
}


def extract_bill_data(text: str) -> dict[str, Any]:
    """Return the original nested response shape for backward compatibility."""
    parser = next((candidate for candidate in PARSERS if candidate.matches(text)), None)
    canonical = parser.parse(text) if parser else {}
    identity = {key: first_match(text, patterns) for key, patterns in GENERIC_TEXT_PATTERNS.items()}
    numbers = {key: number_match(text, patterns) for key, patterns in GENERIC_NUMBER_PATTERNS.items()}

    if parser:
        identity.update(
            consumer_number=canonical.get("customer_id"),
            meter_number=canonical.get("meter_number"),
            tariff=canonical.get("tariff_category"),
            billing_period=(
                canonical.get("billing_month").replace("-20", ",")
                if parser.name == "PGVCL" and canonical.get("billing_month")
                else canonical.get("billing_month")
            ),
        )
        numbers.update(
            contract_demand_kva=canonical.get("contract_demand"),
            maximum_demand_kva=canonical.get("actual_max_demand"),
            kwh=canonical.get("kwh_consumed"),
            fixed_charges=canonical.get("demand_charges"),
            energy_charges=canonical.get("energy_charges"),
            electricity_duty=canonical.get("electricity_duty"),
            arrears=canonical.get("outstanding_arrears"),
            total_amount=canonical.get("total_payable"),
        )

    connected_load = None
    reactive_import = None
    if parser and parser.name == "PGVCL":
        connected_load = canonical.get("contract_demand")
        maximum = canonical.get("actual_max_demand")
        due = re.search(r"Last\s+Date\s+For[\s\S]{0,180}?Payment\s+(\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4})", text, re.I)
        bill = re.search(r"(?:Bill|Issue)\s*Date\s*[:\-]?\s*(\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4})", text, re.I)
        readings = re.search(r"Readings\s+KWH\s+Reactive\s+Import[\s\S]{0,500}?Difference\s+\d[\d,]*(?:\.\d+)?\s+(\d[\d,]*(?:\.\d+)?)", text, re.I)
        identity["due_date"] = due.group(1) if due else identity["due_date"]
        identity["bill_date"] = bill.group(1) if bill else identity["bill_date"]
        reactive_import = float(readings.group(1).replace(",", "")) if readings else None
        numbers["maximum_demand_kva"] = maximum

    found = sum(value is not None for value in (*identity.values(), *numbers.values()))
    warnings = []
    if len(text.strip()) < 100:
        warnings.append("Very little text was extracted. The document may require OCR.")
    if numbers["total_amount"] is None:
        warnings.append("Total payable amount was not detected.")
    return {
        "source": {"filename": None, "page_count": None},
        "account": {key: identity[key] for key in ("consumer_number", "meter_number", "tariff")},
        "billing": {key: identity[key] for key in ("billing_period", "bill_date", "due_date")},
        "load": {
            "sanctioned_load_kw": numbers["sanctioned_load_kw"],
            "contract_demand_kva": numbers["contract_demand_kva"],
            "maximum_demand_kva": numbers["maximum_demand_kva"],
            "connected_load_hp": connected_load,
        },
        "consumption": {
            "kwh": numbers["kwh"],
            "kvah": numbers["kvah"],
            "power_factor": numbers["power_factor"],
            "reactive_import_kvarh": reactive_import,
        },
        "charges": {
            "fixed_charges": numbers["fixed_charges"],
            "energy_charges": numbers["energy_charges"],
            "electricity_duty": numbers["electricity_duty"],
            "arrears": numbers["arrears"],
            "total_amount": numbers["total_amount"],
            "currency": "INR",
        },
        "extraction": {"fields_found": found, "fields_checked": 18, "coverage_percent": round(found / 18 * 100, 1)},
        "warnings": warnings,
    }
