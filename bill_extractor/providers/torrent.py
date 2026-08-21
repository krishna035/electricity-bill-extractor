"""Torrent Power industrial bill parser."""

import re

from bill_extractor.providers.base import ProviderParser
from bill_extractor.utils import NUMBER_TOKEN, normalized_month, parse_number, sum_known


class TorrentParser(ProviderParser):
    name = "Torrent Power"

    def matches(self, text: str) -> bool:
        return bool(re.search(r"Torrent\s+Power", text, re.I))

    def parse(self, text: str) -> dict[str, str | float | None]:
        values = self.record()
        self._parse_header(text, values)
        self._parse_meter(text, values)
        self._parse_charges(text, values)
        self._parse_solar(text, values)
        return values

    @staticmethod
    def _find(text: str, pattern: str, group: int = 1) -> str | None:
        match = re.search(pattern, text, re.I | re.M)
        return " ".join(match.group(group).split()) if match else None

    def _parse_header(self, text: str, values: dict[str, str | float | None]) -> None:
        contract = self._find(text, rf"CONTRACT\s+DEMAND[\s\S]{{0,100}}?({NUMBER_TOKEN})\s*KW")
        month_tariff = re.search(r"([A-Z]{3,9}\s+\d{4})\s+([A-Z]+\d+)\b", text, re.I)
        billing_line = next(
            (line for line in text.splitlines() if re.search(rf"{NUMBER_TOKEN}\s*KW", line) and re.search(r"\d{1,2}/\d{1,2}/\d{2}", line)),
            "",
        )
        billing_match = re.search(rf"({NUMBER_TOKEN})\s*KW", billing_line)
        customer_matches = re.findall(r"\b\d{8,}\b", billing_line)
        power_factor = self._find(
            text,
            rf"Registered\s+Mobile[^\n]*?\s({NUMBER_TOKEN})\s+\d{{1,2}}/\d{{1,2}}/\d{{2}}",
        )
        values["contract_demand"] = parse_number(contract)
        values["billing_demand"] = parse_number(billing_match.group(1)) if billing_match else None
        values["customer_id"] = customer_matches[-1] if customer_matches else None
        if month_tariff:
            values["billing_month"] = normalized_month(month_tariff.group(1))
            values["tariff_category"] = month_tariff.group(2).upper()
        pf = parse_number(power_factor)
        values["average_power_factor"] = pf / 100 if pf is not None and pf > 1 else pf

    def _parse_meter(self, text: str, values: dict[str, str | float | None]) -> None:
        values["meter_number"] = self._find(text, r"Meter\s+No\.?\s*:\s*([A-Z0-9/-]+)")
        units = re.search(
            rf"^\s*Units\s+({NUMBER_TOKEN})\s+({NUMBER_TOKEN})\s+({NUMBER_TOKEN})\s+"
            rf"({NUMBER_TOKEN})\s+({NUMBER_TOKEN})",
            text,
            re.I | re.M,
        )
        if units:
            values["actual_max_demand"] = parse_number(units.group(1))
            values["kwh_consumed"] = parse_number(units.group(2))
            values["tou_kwh"] = parse_number(units.group(3))
            values["night_units"] = parse_number(units.group(5))
            values["night_concession_units"] = parse_number(units.group(5))

    def _amount(self, text: str, label: str) -> float | None:
        value = self._find(text, rf"^\s*{label}\s+({NUMBER_TOKEN})(?:\s|$)")
        return parse_number(value)

    def _parse_charges(self, text: str, values: dict[str, str | float | None]) -> None:
        values["energy_charges"] = self._amount(text, r"Energy\s+charges\s*\(A\)")
        values["demand_charges"] = self._amount(text, r"Fixed\s+demand\s+charges\s*\(B\)")
        values["excess_demand_charges"] = self._amount(text, r"Excess\s+demand\s+charges")
        base_fppas = self._amount(text, r"Base\s+FPPAS[^\n]*\(C\)")
        additional_fppas_text = self._find(
            text,
            rf"FPPAS\s+charges\s+@\s+{NUMBER_TOKEN}%\s+of\s+\(A\+B\+C\)\s+({NUMBER_TOKEN})",
        )
        additional_fppas = parse_number(additional_fppas_text)
        values["fuel_surcharge"] = sum_known(base_fppas, additional_fppas)
        values["tou_charges"] = self._amount(text, r"TOU\s+charges")
        values["power_factor_adjustment"] = self._amount(text, r"Power\s+Factor\s+adjustment\s+charges")
        values["night_rebate"] = self._amount(text, r"NTC\s+rebate")
        total_energy = self._find(text, rf"Total\s+energy\s+charges\s+({NUMBER_TOKEN})")
        values["total_energy_charges"] = parse_number(total_energy)
        values["total_consumption_charges"] = values["total_energy_charges"]
        duty = self._find(
            text,
            rf"Total\s+government\s+duty\s+@\s+{NUMBER_TOKEN}%\s+({NUMBER_TOKEN})",
        )
        values["electricity_duty"] = parse_number(duty)
        banking = self._find(
            text,
            rf"Banking\s+charges\s+\(Solar\s+generation\s+unit-Excess\s+solar\s+unit\)\s+@\s+Rs\.\s*{NUMBER_TOKEN}\s+({NUMBER_TOKEN})",
        )
        values["solar_banking_charges"] = parse_number(banking)
        credit = self._amount(text, r"Credit")
        values["solar_credit"] = -abs(credit) if credit is not None else None
        values["previous_dues"] = self._amount(text, r"Previous\s+dues")
        values["wheeling_charges"] = self._amount(text, r"Wheeling\s+charges")
        values["delayed_payment_charges"] = self._amount(text, r"Delay\s+payment\s+charges")
        values["net_payable"] = self._amount(text, r"Amount\s+due")
        bill_amount = self._find(
            text,
            rf"B\s*I\s*L\s*L\s+A\s*M\s*O\s*U\s*N\s*T\s*:\s*R\s*({NUMBER_TOKEN})",
        )
        values["total_payable"] = (
            values["net_payable"]
            if values["net_payable"] is not None
            else parse_number(bill_amount)
        )
        values["current_month_bill"] = sum_known(
            values["total_consumption_charges"], values["electricity_duty"]
        )

    @staticmethod
    def _parse_solar(text: str, values: dict[str, str | float | None]) -> None:
        note = re.search(
            rf"Solar\s+generation\s+units\s+are\s*:\s*({NUMBER_TOKEN})\s*,\s*Net\s+billed\s+units-\s*({NUMBER_TOKEN})",
            text,
            re.I,
        )
        if note:
            values["solar_generation_units"] = parse_number(note.group(1))
            values["solar_net_billed_units"] = parse_number(note.group(2))
        setoff = re.search(rf"Solar\s+Setoff\s+Units\s+({NUMBER_TOKEN})", text, re.I)
        if setoff:
            values["solar_setoff_units"] = parse_number(setoff.group(1))
        export = re.search(rf"for\s+({NUMBER_TOKEN})\s+excess\s+Solar", text, re.I)
        if export:
            values["solar_export_units"] = parse_number(export.group(1))
        if values["solar_generation_units"] is not None and values["solar_export_units"] is not None:
            values["solar_banking_units"] = (
                float(values["solar_generation_units"]) - float(values["solar_export_units"])
            )
