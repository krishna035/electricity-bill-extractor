from pathlib import Path

from openpyxl import load_workbook
import pytest

from bill_extractor.export import export_excel
from bill_extractor.schema import FIELDS
from bill_extractor.service import InputFile, extract_files


DATA = Path("data")


def extract(filename: str):
    path = DATA / filename
    return extract_files([InputFile(path.name, path.read_bytes())], use_ocr=False)


def test_schema_matches_reference_workbook():
    workbook = load_workbook(DATA / "Angiplast_Bill_Analysis.xlsx", read_only=True)
    headers = [cell.value for cell in workbook["Angiplast"][1]][: len(FIELDS)]

    assert len(FIELDS) == 58
    assert headers == [field.label for field in FIELDS]


def test_ugvcl_merged_bill_matches_reference_readings():
    records = extract("Angiplast_UGVCL-INVOICES 2025-26 Merge.pdf")
    by_month = {record.values["billing_month"]: record for record in records}
    workbook = load_workbook(DATA / "Angiplast_Bill_Analysis.xlsx", data_only=True, read_only=True)
    sheet = workbook["Angiplast"]

    assert len(records) == 12
    for row in range(2, 14):
        month = sheet.cell(row, 1).value
        assert by_month[month].values["kwh_consumed"] == sheet.cell(row, 9).value
        assert by_month[month].values["total_consumption_charges"] == pytest.approx(sheet.cell(row, 38).value)

    april = by_month["APR-2025"].values
    assert april["customer_id"] == "65500"
    assert april["meter_number"] == "GHBD1806"
    assert april["solar_generation_units"] == 37920
    assert april["solar_setoff_units"] == 423
    assert april["solar_export_units"] == 5003
    assert april["solar_banking_units"] == 32917
    assert april["calculated_adjustment"] == 22648.10
    assert april["total_payable"] == 424939.03


def test_ugvcl_combines_multirow_adjustments():
    may = {record.values["billing_month"]: record for record in extract("Angiplast_UGVCL-INVOICES 2025-26 Merge.pdf")}["MAY-2025"].values

    assert may["solar_setoff_units"] == 2300
    assert may["solar_export_units"] == 18318
    assert may["solar_banking_units"] == 71442
    assert may["solar_generation_units"] == 89760
    assert may["security_deposit_interest"] == -115233.75
    assert may["other_credits"] == -975.24


def test_torrent_power_parser():
    record = extract("Torrent Bill Marking_260810_174038.pdf")[0]
    values = record.values

    assert record.provider == "Torrent Power"
    assert values["billing_month"] == "JAN-2026"
    assert values["customer_id"] == "100358213"
    assert values["contract_demand"] == 900
    assert values["actual_max_demand"] == 612
    assert values["billing_demand"] == 765
    assert values["kwh_consumed"] == 249690
    assert values["fuel_surcharge"] == 1003612.58
    assert values["electricity_duty"] == 359765.81
    assert values["solar_generation_units"] == 37805
    assert values["solar_net_billed_units"] == 249139
    assert values["total_payable"] == 2779320
    assert not record.warnings


def test_excel_export_uses_reference_headers_and_missing_marker():
    records = extract_files(
        [InputFile("S P METAL PGVCL.pdf", Path("S P METAL PGVCL.pdf").read_bytes())],
        use_ocr=False,
    )
    workbook = load_workbook(filename=__import__("io").BytesIO(export_excel(records)), data_only=True)
    sheet = workbook["Extracted Bills"]

    assert [cell.value for cell in sheet[1]] == [field.label for field in FIELDS]
    tariff_column = next(index for index, field in enumerate(FIELDS, 1) if field.key == "tariff_category")
    solar_column = next(index for index, field in enumerate(FIELDS, 1) if field.key == "solar_generation_units")
    assert sheet.cell(2, tariff_column).value == "LTMD"
    assert sheet.cell(2, solar_column).value == "-"


def test_percentage_columns_use_excel_percentage_format():
    records = extract("Angiplast_UGVCL-INVOICES 2025-26 Merge.pdf")
    workbook = load_workbook(filename=__import__("io").BytesIO(export_excel(records)), data_only=True)
    sheet = workbook["Extracted Bills"]
    solar_export_column = next(
        index for index, field in enumerate(FIELDS, 1) if field.key == "solar_export_percent"
    )

    assert sheet.cell(2, solar_export_column).value == pytest.approx(0.131935654)
    assert sheet.cell(2, solar_export_column).number_format == "0.00%"


def test_photographed_bill_and_adjustment_are_merged():
    filenames = ["1000371676.jpg", "1000371677.jpg"]
    records = extract_files(
        [InputFile(name, (DATA / name).read_bytes()) for name in filenames],
        use_ocr=True,
    )

    assert len(records) == 1
    record = records[0]
    values = record.values
    assert record.provider == "UGVCL"
    assert values["billing_month"] == "MAY-2025"
    assert values["customer_id"] == "65500"
    assert values["tariff_category"] == "HTP-I"
    assert values["kwh_consumed"] == 52176
    assert values["solar_generation_units"] == 89760
    assert values["solar_setoff_units"] == 2300
    assert values["solar_export_units"] == 18318
    assert values["solar_banking_units"] == 71442
    assert values["net_payable"] == 295385.72
    assert values["total_payable"] == 295385.72
    assert not record.warnings
