"""Paschim Gujarat Vij Company (PGVCL) parser."""

import re

from bill_extractor.providers.base import ProviderParser
from bill_extractor.utils import normalized_month, parse_number


class PGVCLParser(ProviderParser):
    name = "PGVCL"

    def matches(self, text: str) -> bool:
        return bool(re.search(r"Paschim\s+Gujarat\s+Vij\s+Company|PGVCL-Bill", text, re.I))

    @staticmethod
    def _amount(text: str, label: str) -> float | None:
        match = re.search(rf"{label}\s+(\d[\d,]*)\s+(\d{{1,2}})(?=\s|$)", text, re.I)
        if not match:
            return None
        return float(f"{int(match.group(1).replace(',', ''))}.{int(match.group(2)):02d}")

    def parse(self, text: str) -> dict[str, str | float | None]:
        values = self.record()
        month = re.search(r"E[\s\u2010-\u2015-]*ELECTRICITY\s+BILL\s*:\s*([A-Z]{3}\s*,\s*\d{2,4})", text, re.I)
        consumer = re.search(r"Consumer\s+No\.?\s*[:\-]?\s*(\d{6,})", text, re.I)
        meter = re.search(r"Meter\s+No\.?\s*[:\-]?\s*([A-Z0-9/-]{4,})", text, re.I)
        tariff = re.search(r"\b(LT[A-Z0-9-]+)\s+[A-Z]\s+\d+(?:\.\d+)?\s+\d+\s+[\d,]+\.\d+", text, re.I)
        load = re.search(
            r"Tariff\s+Meter\s+Chg\s+Code\s+H\.?p/K\.?V[\s\S]{0,220}?\bLT[A-Z0-9-]+\s+[A-Z]\s+(\d+(?:\.\d+)?)",
            text,
            re.I,
        )
        maximum = re.search(r"Max\s+Dem[^\n]*\n(?:[^\n]*\n){0,2}\s*(\d[\d,]*(?:\.\d+)?)", text, re.I)
        readings = re.search(
            r"Readings\s+KWH\s+Reactive\s+Import[\s\S]{0,500}?Difference\s+(\d[\d,]*(?:\.\d+)?)\s+(\d[\d,]*(?:\.\d+)?)",
            text,
            re.I,
        )
        values["billing_month"] = normalized_month(month.group(1)) if month else None
        values["customer_id"] = consumer.group(1) if consumer else None
        values["meter_number"] = meter.group(1) if meter else None
        values["tariff_category"] = tariff.group(1).upper() if tariff else None
        values["contract_demand"] = parse_number(load.group(1)) if load else None
        values["actual_max_demand"] = parse_number(maximum.group(1)) if maximum else None
        if readings:
            values["kwh_consumed"] = parse_number(readings.group(1))
        values["demand_charges"] = self._amount(text, r"Fixed\s+Chg")
        values["energy_charges"] = self._amount(text, r"Energy\s+Chg")
        values["electricity_duty"] = self._amount(text, r"Ed\s+Chg@\d+(?:\.\d+)?")
        values["total_payable"] = self._amount(text, r"Net\s+Bill\s+Amount\s+\(18-19\)")
        values["net_payable"] = values["total_payable"]
        return values
