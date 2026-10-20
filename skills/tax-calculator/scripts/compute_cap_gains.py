#!/usr/bin/env python3
"""
Compute capital gains/losses tax including NIIT.

Nets short-term and long-term gains/losses, applies the $3,000 loss limit,
and computes NIIT (Net Investment Income Tax) at 3.8%.

Usage:
    python3 compute_cap_gains.py <parsed_data_dir> <output_dir>
"""

import json
import os
import sys
from datetime import datetime


def load_json(path):
    with open(path, 'r') as f:
        return json.load(f)


def compute_capital_gains(transactions, filing_status, tax_tables):
    """Compute net capital gains/losses and tax."""

    short_term_gains = 0
    short_term_losses = 0
    long_term_gains = 0
    long_term_losses = 0

    for tx in transactions:
        gain = tx.get("gain_loss")
        if gain is None:
            gain = tx.get("proceeds", 0) - tx.get("cost_basis", 0)
        # Adjust for wash sales
        wash_disallowed = tx.get("wash_sale_loss_disallowed", 0)
        if wash_disallowed > 0 and gain < 0:
            gain += wash_disallowed

        holding = tx.get("holding_period", "short")
        if holding == "long":
            if gain >= 0:
                long_term_gains += gain
            else:
                long_term_losses += gain
        else:
            if gain >= 0:
                short_term_gains += gain
            else:
                short_term_losses += gain

    # Net within each category
    net_short_term = round(short_term_gains + short_term_losses, 2)
    net_long_term = round(long_term_gains + long_term_losses, 2)

    # Net across categories
    total_net = net_short_term + net_long_term

    # Apply $3,000 loss limit
    loss_limit = tax_tables["capital_gains"]["capital_loss_limit"]
    if filing_status == "married_filing_separately":
        loss_limit = tax_tables["capital_gains"]["capital_loss_limit_mfs"]

    deductible_loss = 0
    carryover_loss = 0
    if total_net < 0:
        deductible_loss = max(total_net, -loss_limit)
        carryover_loss = round(total_net - deductible_loss, 2)

    # Long-term capital gains tax rate
    lt_brackets = tax_tables["capital_gains"]["long_term"].get(
        filing_status, tax_tables["capital_gains"]["long_term"]["single"]
    )

    lt_tax = 0
    if net_long_term > 0:
        remaining = net_long_term
        for bracket in lt_brackets:
            if remaining <= 0:
                break
            bracket_min = bracket["min"]
            bracket_max = bracket["max"]
            rate = bracket["rate"]
            if bracket_max is None:
                taxable = remaining
            else:
                taxable = min(remaining, bracket_max - bracket_min)
            lt_tax += taxable * rate
            remaining -= taxable

    lt_tax = round(lt_tax, 2)

    # NIIT (3.8% on investment income above threshold)
    niit_config = tax_tables["capital_gains"]["net_investment_income_tax"]
    niit_threshold = niit_config["thresholds"].get(filing_status, 200000)
    niit = 0  # NIIT requires MAGI comparison, placeholder for integration

    return {
        "short_term": {
            "gains": round(short_term_gains, 2),
            "losses": round(short_term_losses, 2),
            "net": net_short_term,
        },
        "long_term": {
            "gains": round(long_term_gains, 2),
            "losses": round(long_term_losses, 2),
            "net": net_long_term,
        },
        "total_net_gain_loss": round(total_net, 2),
        "deductible_loss": deductible_loss,
        "carryover_loss": carryover_loss,
        "long_term_tax": lt_tax,
        "niit_threshold": niit_threshold,
        "niit": niit,
        "transaction_count": len(transactions),
    }


def main():
    if len(sys.argv) < 3:
        print("Usage: python3 compute_cap_gains.py <parsed_data_dir> <output_dir>", file=sys.stderr)
        sys.exit(1)

    parsed_dir = sys.argv[1]
    output_dir = sys.argv[2]

    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(script_dir, '..', '..', '..'))
    tax_tables = load_json(os.path.join(project_root, 'data', 'tax-tables-2025.json'))

    # Collect all capital transactions
    all_transactions = []
    filing_status = "single"

    for filename in sorted(os.listdir(parsed_dir)):
        if not filename.endswith('.json'):
            continue
        data = load_json(os.path.join(parsed_dir, filename))
        inner = data.get("data", data)
        all_transactions.extend(inner.get("capital_transactions", []))
        if "filing_status" in inner:
            filing_status = inner["filing_status"]

    result = compute_capital_gains(all_transactions, filing_status, tax_tables)
    result["computed_at"] = datetime.now().isoformat()
    result["filing_status"] = filing_status

    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "capital_gains.json")

    with open(output_path, 'w') as f:
        json.dump(result, f, indent=2)

    print(json.dumps(result, indent=2))
    print(f"\nSaved to: {output_path}", file=sys.stderr)


if __name__ == '__main__':
    main()
