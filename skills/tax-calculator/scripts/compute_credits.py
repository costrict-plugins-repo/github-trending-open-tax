#!/usr/bin/env python3
"""
Apply tax credits and compute final owed/refund amount.

Reads the tax computation and applies CTC, EITC, education credits, etc.

Usage:
    python3 compute_credits.py <computed_data_dir> <output_dir>
"""

import json
import os
import sys
from datetime import datetime


def load_json(path):
    with open(path, 'r') as f:
        return json.load(f)


def compute_child_tax_credit(dependents, agi, filing_status, credits_data):
    """Compute Child Tax Credit for 2025."""
    ctc_config = credits_data["child_tax_credit"]
    max_per_child = ctc_config["max_per_child"]

    # Count qualifying children (under 17 with SSN)
    qualifying_children = 0
    for dep in dependents:
        if dep.get("qualifies_for_ctc", False):
            qualifying_children += 1
        elif dep.get("date_of_birth"):
            try:
                dob = datetime.strptime(dep["date_of_birth"], '%Y-%m-%d')
                age = (datetime(2025, 12, 31) - dob).days // 365
                if age < 17:
                    qualifying_children += 1
            except (ValueError, TypeError):
                pass

    if qualifying_children == 0:
        return {"qualifying_children": 0, "credit": 0, "refundable_portion": 0, "nonrefundable_portion": 0}

    total_ctc = qualifying_children * max_per_child

    # Phase-out
    threshold = ctc_config["phase_out"].get(filing_status, 200000)
    reduction_rate = ctc_config["phase_out"]["reduction_per_1000"]
    if agi > threshold:
        excess = agi - threshold
        reduction = (excess // 1000) * reduction_rate
        total_ctc = max(0, total_ctc - reduction)

    # Refundable portion (Additional Child Tax Credit)
    refundable = min(total_ctc, qualifying_children * ctc_config["refundable_portion"])

    return {
        "qualifying_children": qualifying_children,
        "credit": round(total_ctc, 2),
        "refundable_portion": round(refundable, 2),
        "nonrefundable_portion": round(total_ctc - refundable, 2),
    }


def compute_other_dependent_credit(dependents, credits_data):
    """Credit for dependents who don't qualify for CTC."""
    odc = credits_data.get("other_dependent_credit", {})
    max_per = odc.get("max_per_dependent", 500)

    qualifying = 0
    for dep in dependents:
        if not dep.get("qualifies_for_ctc", False):
            if dep.get("date_of_birth"):
                try:
                    dob = datetime.strptime(dep["date_of_birth"], '%Y-%m-%d')
                    age = (datetime(2025, 12, 31) - dob).days // 365
                    if age >= 17:
                        qualifying += 1
                except (ValueError, TypeError):
                    qualifying += 1
            else:
                qualifying += 1

    return {
        "qualifying_dependents": qualifying,
        "credit": round(qualifying * max_per, 2),
    }


def compute_final_summary(tax_computation, se_tax_data, cap_gains_data, credits_result):
    """Combine all computations into final summary."""
    federal_tax = tax_computation.get("federal_income_tax", 0)
    se_tax = se_tax_data.get("total_se_tax", 0) if se_tax_data else 0
    lt_tax = cap_gains_data.get("long_term_tax", 0) if cap_gains_data else 0
    niit = cap_gains_data.get("niit", 0) if cap_gains_data else 0

    total_tax = round(federal_tax + se_tax + lt_tax + niit, 2)

    # Apply nonrefundable credits (can reduce tax to zero but not below)
    nonrefundable = credits_result.get("total_nonrefundable", 0)
    tax_after_nonrefundable = max(0, total_tax - nonrefundable)

    # Apply refundable credits (can create a refund)
    refundable = credits_result.get("total_refundable", 0)

    # Payments
    withheld = tax_computation.get("tax_withheld", 0)
    estimated = tax_computation.get("estimated_payments", 0)

    amount_owed_or_refund = round(
        tax_after_nonrefundable - refundable - withheld - estimated, 2
    )

    gross = tax_computation.get("gross_income", {}).get("total", 0)
    effective_rate = round(total_tax / gross * 100, 2) if gross > 0 else 0

    return {
        "federal_income_tax": federal_tax,
        "self_employment_tax": se_tax,
        "long_term_capital_gains_tax": lt_tax,
        "net_investment_income_tax": niit,
        "total_tax_before_credits": total_tax,
        "nonrefundable_credits": nonrefundable,
        "tax_after_nonrefundable_credits": tax_after_nonrefundable,
        "refundable_credits": refundable,
        "tax_withheld": withheld,
        "estimated_payments": estimated,
        "amount_owed_or_refund": amount_owed_or_refund,
        "is_refund": amount_owed_or_refund < 0,
        "effective_tax_rate": effective_rate,
    }


def main():
    if len(sys.argv) < 3:
        print("Usage: python3 compute_credits.py <computed_data_dir> <output_dir>", file=sys.stderr)
        sys.exit(1)

    computed_dir = sys.argv[1]
    output_dir = sys.argv[2]

    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(script_dir, '..', '..', '..'))
    credits_data = load_json(os.path.join(project_root, 'data', 'credits-2025.json'))

    # Load computed data
    tax_computation = {}
    se_tax_data = None
    cap_gains_data = None
    dependents = []

    tax_path = os.path.join(computed_dir, 'tax_computation.json')
    if os.path.exists(tax_path):
        tax_computation = load_json(tax_path)

    se_path = os.path.join(computed_dir, 'se_tax.json')
    if os.path.exists(se_path):
        se_tax_data = load_json(se_path)

    cap_path = os.path.join(computed_dir, 'capital_gains.json')
    if os.path.exists(cap_path):
        cap_gains_data = load_json(cap_path)

    # Load dependents from parsed data or tax computation
    parsed_dir = os.path.join(os.path.dirname(computed_dir), 'parsed')
    if os.path.exists(parsed_dir):
        for filename in os.listdir(parsed_dir):
            if filename.endswith('.json'):
                data = load_json(os.path.join(parsed_dir, filename))
                inner = data.get("data", data)
                dependents.extend(inner.get("dependents", []))

    agi = tax_computation.get("agi", 0)
    filing_status = tax_computation.get("filing_status", "single")

    # Compute credits
    ctc = compute_child_tax_credit(dependents, agi, filing_status, credits_data)
    odc = compute_other_dependent_credit(dependents, credits_data)

    credits_result = {
        "child_tax_credit": ctc,
        "other_dependent_credit": odc,
        "total_nonrefundable": round(ctc["nonrefundable_portion"] + odc["credit"], 2),
        "total_refundable": ctc["refundable_portion"],
        "total_credits": round(ctc["credit"] + odc["credit"], 2),
    }

    # Final summary
    final = compute_final_summary(tax_computation, se_tax_data, cap_gains_data, credits_result)

    result = {
        "computed_at": datetime.now().isoformat(),
        "credits": credits_result,
        "final_summary": final,
    }

    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "credits_and_final.json")

    with open(output_path, 'w') as f:
        json.dump(result, f, indent=2)

    print(json.dumps(result, indent=2))
    print(f"\nSaved to: {output_path}", file=sys.stderr)


if __name__ == '__main__':
    main()
