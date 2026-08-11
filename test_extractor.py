from pathlib import Path

from extractor import extract_bill_data, extract_pdf_text


SAMPLE = """
Industrial Electricity Bill
Consumer No: 1234567890
Meter Number: GJ-998877
Tariff Category: HT INDUSTRIAL
Billing Period: JUN 2026
Bill Date: 01/07/2026
Due Date: 18/07/2026
Sanctioned Load (KW): 450
Contract Demand (KVA): 500
Maximum Demand (KVA): 421.50
kWh: 68,420
kVAh: 70,250
Power Factor: 0.974
Fixed Charges: Rs. 83,500
Energy Charges: Rs. 547,360
Electricity Duty: Rs. 76,240
Arrears: Rs. 0
Total Amount Payable: Rs. 707,100
"""


def test_extract_bill_data():
    result = extract_bill_data(SAMPLE)

    assert result["account"]["consumer_number"] == "1234567890"
    assert result["load"]["contract_demand_kva"] == 500
    assert result["consumption"]["kwh"] == 68420
    assert result["consumption"]["power_factor"] == 0.974
    assert result["charges"]["total_amount"] == 707100


def test_extract_pgvcl_bill():
    bills = [
        (
            "S P METAL PGVCL.pdf", "88249048636", "PG-187327", 80, 54.64,
            11695, 10421, 7760, 53797, 9195.19, 101147.09,
        ),
        (
            "AMAR METAL PGVCL.pdf", "88249005520", "PG-177119", 37, 47.08,
            2467, 721, 6112.50, 11348.20, 2358.22, 25940.42,
        ),
    ]

    for (
        filename,
        consumer_number,
        meter_number,
        connected_load_hp,
        maximum_demand,
        kwh,
        reactive_import,
        fixed_charges,
        energy_charges,
        electricity_duty,
        total_amount,
    ) in bills:
        pdf_text, page_count = extract_pdf_text(Path(filename).read_bytes())
        result = extract_bill_data(pdf_text)

        assert page_count == 1
        assert result["account"] == {
            "consumer_number": consumer_number,
            "meter_number": meter_number,
            "tariff": "LTMD",
        }
        assert result["billing"] == {
            "billing_period": "APR,26",
            "bill_date": "23-04-2026",
            "due_date": "04-05-2026",
        }
        assert result["load"]["connected_load_hp"] == connected_load_hp
        assert result["load"]["maximum_demand_kva"] == maximum_demand
        assert result["consumption"]["kwh"] == kwh
        assert result["consumption"]["reactive_import_kvarh"] == reactive_import
        assert result["charges"]["fixed_charges"] == fixed_charges
        assert result["charges"]["energy_charges"] == energy_charges
        assert result["charges"]["electricity_duty"] == electricity_duty
        assert result["charges"]["arrears"] is None
        assert result["charges"]["total_amount"] == total_amount
