#!/usr/bin/env python3
"""
Compute self-employment tax (Schedule SE) for 1099-NEC/MISC income.

Usage:
    python3 compute_se_tax.py <parsed_data_dir> <output_dir>
"""

import json
import os
import sys
from datetime import datetime


def load_json(path):
    with open(path, 'r') as f:
        return json.load(f)


def compute_se_tax(se_income, tax_tables):
    """Compute self-employment tax per Schedule SE."""
    se_config = tax_tables["self_employment"]

    # Step 1: Net earnings from self-employment
    # Multiply net SE income by 92.35% (equivalent of employer half)
    net_earnings = round(se_income * se_config["net_earnings_factor"], 2)

    if net_earnings < 400:
        return {
            "net_se_income": se_income,
            "net_earnings": net_earnings,
            "below_threshold": True,
            "total_se_tax": 0,
            "deductible_half": 0,
        }

    # Step 2: Social Security portion (12.4% up to wage base)
    ss_wage_base = se_config["social_security_wage_base"]
    ss_taxable = min(net_earnings, ss_wage_base)
    ss_tax = round(ss_taxable * se_config["social_security_rate"], 2)

    # Step 3: Medicare portion (2.9% on all net earnings)
    medicare_tax = round(net_earnings * se_config["medicare_rate"], 2)

    # Step 4: Additional Medicare tax (0.9% above threshold)
    # Note: threshold depends on filing status, but SE tax uses $200k single as default
    additional_medicare = 0
    additional_threshold = 200000  # Default for single
    if net_earnings > additional_threshold:
        additional_medicare = round(
            (net_earnings - additional_threshold) * se_config["additional_medicare_rate"], 2
        )

    total_se_tax = round(ss_tax + medicare_tax + additional_medicare, 2)
    deductible_half = round(total_se_tax * se_config["deductible_portion"], 2)

    return {
        "net_se_income": se_income,
        "net_earnings": net_earnings,
        "ss_taxable_earnings": ss_taxable,
        "ss_tax": ss_tax,
        "medicare_tax": medicare_tax,
        "additional_medicare_tax": additional_medicare,
        "total_se_tax": total_se_tax,
        "deductible_half": deductible_half,
        "below_threshold": False,
    }


def main():
    if len(sys.argv) < 3:
        print("Usage: python3 compute_se_tax.py <parsed_data_dir> <output_dir>", file=sys.stderr)
        sys.exit(1)

    parsed_dir = sys.argv[1]
    output_dir = sys.argv[2]

    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(script_dir, '..', '..', '..'))
    tax_tables = load_json(os.path.join(project_root, 'data', 'tax-tables-2025.json'))

    # Sum all self-employment income
    total_se = 0
    for filename in sorted(os.listdir(parsed_dir)):
        if not filename.endswith('.json'):
            continue
        data = load_json(os.path.join(parsed_dir, filename))
        inner = data.get("data", data)
        for item in inner.get("self_employment_income", []):
            net = item.get("net_income", item.get("gross_income", 0) - item.get("expenses", 0))
            total_se += net

    result = compute_se_tax(total_se, tax_tables)
    result["computed_at"] = datetime.now().isoformat()

    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "se_tax.json")

    with open(output_path, 'w') as f:
        json.dump(result, f, indent=2)

    print(json.dumps(result, indent=2))
    print(f"\nSaved to: {output_path}", file=sys.stderr)


if __name__ == '__main__':
    main()
