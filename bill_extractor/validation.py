"""Cross-field checks that flag likely extraction errors."""

from bill_extractor.models import BillRecord


def validate(record: BillRecord) -> None:
    values = record.values

    def numeric(key: str) -> float | None:
        value = values.get(key)
        return float(value) if isinstance(value, (int, float)) else None

    kwh = numeric("kwh_consumed")
    setoff = numeric("solar_setoff_units")
    net = numeric("solar_net_billed_units")
    if kwh is not None and setoff is not None and net is not None and abs((kwh - setoff) - net) > 1:
        record.warnings.append("Solar net billed units do not equal kWh minus set-off units.")

    generation = numeric("solar_generation_units")
    export = numeric("solar_export_units")
    banking = numeric("solar_banking_units")
    if all(value is not None for value in (generation, export, banking)):
        if abs(float(generation) - float(export) - float(banking)) > 1:
            record.warnings.append("Solar generation does not equal export plus banking units.")

    found = sum(value is not None for value in values.values())
    if found < 12:
        record.warnings.append(f"Only {found} of {len(values)} fields were populated; review this layout.")
