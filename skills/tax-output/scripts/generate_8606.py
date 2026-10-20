#!/usr/bin/env python3
"""
Generate Form 8606 (Nondeductible IRAs) CSV from computed tax data.

Produces a line-by-line CSV matching IRS Form 8606 for reporting:
- Nondeductible Traditional IRA contributions (Part I)
- Backdoor Roth conversions (Part II)

Usage:
    python3 generate_8606.py <computed_data_dir> <output_dir>
"""

import csv
import json
import os
import sys
from datetime import datetime


def load_json(path):
    with open(path, 'r') as f:
        return json.load(f)


FORM_8606_LINES = [
    ("1", "Nondeductible contributions to traditional IRAs for {tax_year}"),
    ("2", "Total basis in traditional IRAs from prior years (from last year's Form 8606, line 14)"),
    ("3", "Add lines 1 and 2"),
    ("4", "Contributions withdrawn between 1/1/{next_year} and 4/15/{next_year}"),
    ("5", "Subtract line 4 from line 3"),
    ("6", "Value of ALL traditional, SEP, and SIMPLE IRAs as of 12/31/{tax_year}"),
    ("7", "Distributions from traditional, SEP, and SIMPLE IRAs in {tax_year} (from 1099-R)"),
    ("8", "Net amount converted from traditional, SEP, and SIMPLE IRAs to Roth IRAs in {tax_year}"),
    ("9", "Add lines 6, 7, and 8"),
    ("10", "Divide line 5 by line 9. Enter as decimal (not percentage)"),
    ("11", "Multiply line 8 by line 10. Nontaxable portion of conversion"),
    ("12", "Multiply line 7 by line 10. Nontaxable portion of distributions"),
    ("13", "Taxable amount of distributions. Subtract line 12 from line 7"),
    ("14", "Total basis in traditional IRAs for {tax_year} and earlier years. Subtract lines 11 and 12 from line 3"),
    # Part II - Roth conversions
    ("16", "Roth IRA conversion amount (from line 8)"),
    ("17", "Taxable portion of Roth conversion. Subtract line 11 from line 16"),
    ("18", "Basis in Roth conversion. Equal to line 11"),
]


def generate_form_8606(computed_dir, output_dir):
    """Generate Form 8606 CSV from final_tax_summary.json."""
    os.makedirs(output_dir, exist_ok=True)

    # Load computed data
    summary_path = os.path.join(computed_dir, 'final_tax_summary.json')
    if not os.path.exists(summary_path):
        print("Error: final_tax_summary.json not found in computed directory.", file=sys.stderr)
        sys.exit(1)

    summary = load_json(summary_path)
    form_data = summary.get('form_8606_backdoor_roth', {})
    if not form_data:
        print("No Form 8606 data found in tax summary. Backdoor Roth not applicable.", file=sys.stderr)
        sys.exit(0)

    tax_year = summary.get('tax_year', 2025)
    next_year = tax_year + 1
    taxpayer = summary.get('taxpayer', {})

    # Map line numbers to computed values
    line_values = {
        "1": form_data.get('line_1_nondeductible_contributions', 0),
        "2": form_data.get('line_2_prior_year_basis', 0),
        "3": form_data.get('line_3_total_basis', 0),
        "4": form_data.get('line_4_contributions_withdrawn', 0),
        "5": form_data.get('line_5_basis_after_withdrawals', 0),
        "6": form_data.get('line_6_year_end_ira_value', 0),
        "7": form_data.get('line_7_distributions_1099r', 0),
        "8": form_data.get('line_8_conversions', 0),
        "9": form_data.get('line_9_total_distributions_plus_conversions', 0),
        "10": form_data.get('line_10_ratio_nontaxable', 0),
        "11": form_data.get('line_11_nontaxable_portion', 0),
        "12": 0,  # line 7 * line 10 (no non-conversion distributions here)
        "13": form_data.get('line_13_taxable_amount', 0),
        "14": form_data.get('line_14_total_ira_basis_carryforward', 0),
        "16": form_data.get('line_16_roth_conversion_amount', 0),
        "17": form_data.get('line_17_roth_conversion_taxable', 0),
        "18": form_data.get('line_18_roth_conversion_basis', 0),
    }

    # Compute line 12 if distributions exist
    if line_values["7"] > 0 and line_values["10"] > 0:
        line_values["12"] = round(line_values["7"] * line_values["10"], 2)
        line_values["13"] = round(line_values["7"] - line_values["12"], 2)

    # --- CSV output ---
    csv_path = os.path.join(output_dir, 'form_8606.csv')
    with open(csv_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Form 8606 — Nondeductible IRAs', '', ''])
        writer.writerow(['Tax Year', str(tax_year), ''])
        writer.writerow(['Taxpayer', taxpayer.get('name', ''), ''])
        writer.writerow(['SSN (last 4)', taxpayer.get('ssn_last_four', ''), ''])
        writer.writerow(['', '', ''])
        writer.writerow(['Line', 'Description', 'Amount'])

        # Part I header
        writer.writerow(['', 'PART I — Nondeductible Contributions and Basis', ''])

        for line_num, desc_template in FORM_8606_LINES:
            if line_num == "16":
                writer.writerow(['', '', ''])
                writer.writerow(['', 'PART II — Conversions from Traditional, SEP, or SIMPLE IRAs to Roth IRAs', ''])
            desc = desc_template.format(tax_year=tax_year, next_year=next_year)
            value = line_values.get(line_num, 0)
            # Line 10 is a ratio, format differently
            if line_num == "10":
                writer.writerow([line_num, desc, f"{value:.4f}"])
            else:
                writer.writerow([line_num, desc, f"{value:.2f}"])

    # --- JSON output (machine-readable) ---
    json_path = os.path.join(output_dir, 'form_8606.json')
    result = {
        "form": "8606",
        "title": "Nondeductible IRAs",
        "tax_year": tax_year,
        "generated_at": datetime.now().isoformat(),
        "taxpayer": taxpayer,
        "part_i": {
            f"line_{k}": v for k, v in line_values.items()
            if k not in ("16", "17", "18")
        },
        "part_ii": {
            "line_16_roth_conversion_amount": line_values["16"],
            "line_17_roth_conversion_taxable": line_values["17"],
            "line_18_roth_conversion_basis": line_values["18"],
        },
        "result_summary": {
            "nondeductible_contribution": line_values["1"],
            "conversion_amount": line_values["16"],
            "taxable_amount": line_values["17"],
            "basis_carried_forward": line_values["14"],
            "form_required": True,
        },
        "notes": [
            "This form must be filed with your tax return if you made nondeductible IRA contributions.",
            "Keep a copy for your records — you will need line 14 for next year's Form 8606.",
        ],
    }

    with open(json_path, 'w') as f:
        json.dump(result, f, indent=2)

    return csv_path, json_path


def main():
    if len(sys.argv) < 3:
        print("Usage: python3 generate_8606.py <computed_data_dir> <output_dir>", file=sys.stderr)
        sys.exit(1)

    computed_dir = sys.argv[1]
    output_dir = sys.argv[2]

    csv_path, json_path = generate_form_8606(computed_dir, output_dir)

    print(f"Form 8606 generated:")
    print(f"  CSV:  {csv_path}")
    print(f"  JSON: {json_path}")


if __name__ == '__main__':
    main()
