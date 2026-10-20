#!/usr/bin/env python3
"""
Generate TXF (Tax Exchange Format) file for TurboTax Desktop import.

Uses reference codes from data/txf-reference-codes.json.

Usage:
    python3 generate_txf.py <computed_data_dir> <output_dir>
"""

import json
import os
import sys
from datetime import datetime


def load_json(path):
    with open(path, 'r') as f:
        return json.load(f)


def format_date(date_str):
    """Convert YYYY-MM-DD to MM/DD/YYYY for TXF format."""
    if not date_str or date_str == "VARIOUS":
        return "VARIOUS"
    try:
        dt = datetime.strptime(date_str, '%Y-%m-%d')
        return dt.strftime('%m/%d/%Y')
    except (ValueError, TypeError):
        return date_str


def txf_code_for_box(box, txf_codes):
    """Map Form 8949 box to TXF reference code."""
    box_map = {
        "A": "short_term_basis_reported",
        "B": "short_term_basis_not_reported",
        "C": "short_term_no_1099b",
        "D": "long_term_basis_reported",
        "E": "long_term_basis_not_reported",
        "F": "long_term_no_1099b",
        "G": "short_term_digital_asset_reported",
        "H": "short_term_digital_asset_not_reported",
        "I": "short_term_digital_asset_no_1099",
        "J": "long_term_digital_asset_reported",
        "K": "long_term_digital_asset_not_reported",
        "L": "long_term_digital_asset_no_1099",
    }
    key = box_map.get(box, "short_term_basis_not_reported")
    return txf_codes["capital_gains_codes"].get(key, {}).get("code", 712)


def generate_txf_record(code, description, date_acquired, date_sold, proceeds, cost_basis,
                         adjustment_code="", adjustment_amount=0):
    """Generate a single TXF transaction record."""
    lines = []
    lines.append("TD")
    lines.append(f"N{code}")
    lines.append("C1")
    lines.append(f"L1 {description}")
    lines.append(f"D{format_date(date_acquired)}")
    lines.append(f"D{format_date(date_sold)}")
    lines.append(f"${proceeds:.2f}")
    lines.append(f"${cost_basis:.2f}")
    if adjustment_code and adjustment_amount:
        lines.append(f"L{adjustment_code}")
        lines.append(f"${adjustment_amount:.2f}")
    lines.append("^")
    return "\n".join(lines)


def main():
    if len(sys.argv) < 3:
        print("Usage: python3 generate_txf.py <computed_data_dir> <output_dir>", file=sys.stderr)
        sys.exit(1)

    computed_dir = sys.argv[1]
    output_dir = sys.argv[2]

    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(script_dir, '..', '..', '..'))
    txf_codes = load_json(os.path.join(project_root, 'data', 'txf-reference-codes.json'))

    # Collect all capital transactions
    transactions = []

    # From crypto lot matching
    crypto_path = os.path.join(computed_dir, 'crypto_lot_matching.json')
    if os.path.exists(crypto_path):
        crypto = load_json(crypto_path)
        for tx in crypto.get('matched_transactions', []):
            transactions.append(tx)

    # From parsed non-crypto transactions
    parsed_dir = os.path.join(os.path.dirname(computed_dir), 'parsed')
    if os.path.exists(parsed_dir):
        for filename in sorted(os.listdir(parsed_dir)):
            if not filename.endswith('.json'):
                continue
            data = load_json(os.path.join(parsed_dir, filename))
            inner = data.get("data", data)
            for tx in inner.get("capital_transactions", []):
                if not tx.get("is_digital_asset", False) and tx.get("cost_basis", 0) > 0:
                    transactions.append(tx)

    # Build TXF file
    txf_lines = []

    # Header
    txf_lines.append(txf_codes["header"]["version_line"])
    txf_lines.append(f"A{txf_codes['header']['software_line']}")
    txf_lines.append(f"D{datetime.now().strftime('%m/%d/%Y')}")
    txf_lines.append("^")

    # Income records
    tax_path = os.path.join(computed_dir, 'tax_computation.json')
    if os.path.exists(tax_path):
        tax = load_json(tax_path)
        gross = tax.get('gross_income', {})

        if gross.get('wages', 0) > 0:
            code = txf_codes["income_codes"]["wages_salaries_tips"]["code"]
            txf_lines.append("TD")
            txf_lines.append(f"N{code}")
            txf_lines.append("C1")
            txf_lines.append(f"L1 Total W-2 Wages")
            txf_lines.append(f"${gross['wages']:.2f}")
            txf_lines.append("^")

        if gross.get('interest', 0) > 0:
            code = txf_codes["income_codes"]["taxable_interest"]["code"]
            txf_lines.append("TD")
            txf_lines.append(f"N{code}")
            txf_lines.append("C1")
            txf_lines.append(f"L1 Total Interest Income")
            txf_lines.append(f"${gross['interest']:.2f}")
            txf_lines.append("^")

        if gross.get('ordinary_dividends', 0) > 0:
            code = txf_codes["income_codes"]["ordinary_dividends"]["code"]
            txf_lines.append("TD")
            txf_lines.append(f"N{code}")
            txf_lines.append("C1")
            txf_lines.append(f"L1 Total Ordinary Dividends")
            txf_lines.append(f"${gross['ordinary_dividends']:.2f}")
            txf_lines.append("^")

        if gross.get('self_employment', 0) > 0:
            code = txf_codes["income_codes"]["business_income"]["code"]
            txf_lines.append("TD")
            txf_lines.append(f"N{code}")
            txf_lines.append("C1")
            txf_lines.append(f"L1 Self-Employment Income")
            txf_lines.append(f"${gross['self_employment']:.2f}")
            txf_lines.append("^")

    # Capital gains records
    for tx in transactions:
        box = tx.get("form_8949_box", "B")
        if not box:
            is_digital = tx.get("is_digital_asset", False)
            holding = tx.get("holding_period", "short")
            basis_reported = tx.get("basis_reported_to_irs", False)
            if is_digital:
                box = "G" if holding == "short" and basis_reported else "H" if holding == "short" else "J" if basis_reported else "K"
            else:
                box = "A" if holding == "short" and basis_reported else "B" if holding == "short" else "D" if basis_reported else "E"

        code = txf_code_for_box(box, txf_codes)
        adj_code = tx.get("adjustment_code", "")
        adj_amount = tx.get("wash_sale_loss_disallowed", 0)

        record = generate_txf_record(
            code=code,
            description=tx.get("description", ""),
            date_acquired=tx.get("date_acquired", ""),
            date_sold=tx.get("date_sold", ""),
            proceeds=tx.get("proceeds", 0),
            cost_basis=tx.get("cost_basis", 0),
            adjustment_code=adj_code,
            adjustment_amount=adj_amount,
        )
        txf_lines.append(record)

    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "tax_data.txf")

    with open(output_path, 'w') as f:
        f.write("\n".join(txf_lines) + "\n")

    print(f"TXF file generated: {output_path}")
    print(f"  Income records + {len(transactions)} capital gains transaction(s)")


if __name__ == '__main__':
    main()
