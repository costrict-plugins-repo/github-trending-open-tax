#!/usr/bin/env python3
"""
Sanity check computed tax data for math errors and anomalies.

Usage:
    python3 sanity_check.py <computed_data_dir>
"""

import json
import os
import sys
from datetime import datetime


def load_json(path):
    with open(path, 'r') as f:
        return json.load(f)


def check_math(tax, se, cap, credits_data):
    """Verify arithmetic consistency across computed data."""
    issues = []
    warnings = []

    gross = tax.get('gross_income', {})
    adjustments = tax.get('adjustments', {})
    agi = tax.get('agi', 0)
    taxable = tax.get('taxable_income', 0)
    deduction = tax.get('deduction_amount', 0)

    # Check AGI = gross - adjustments
    expected_agi = round(gross.get('total', 0) - adjustments.get('total', 0), 2)
    if abs(agi - expected_agi) > 0.01:
        issues.append({
            "type": "math_error",
            "field": "AGI",
            "expected": expected_agi,
            "actual": agi,
            "message": f"AGI mismatch: expected {expected_agi}, got {agi}",
        })

    # Check taxable income = AGI - deductions
    expected_taxable = max(0, round(agi - deduction, 2))
    if abs(taxable - expected_taxable) > 0.01:
        issues.append({
            "type": "math_error",
            "field": "taxable_income",
            "expected": expected_taxable,
            "actual": taxable,
            "message": f"Taxable income mismatch: expected {expected_taxable}, got {taxable}",
        })

    # Check SE tax deduction matches SE tax
    if se:
        se_tax = se.get('total_se_tax', 0)
        se_deduction = adjustments.get('se_tax_deduction', 0)
        expected_se_ded = round(se_tax * 0.5, 2)
        if se_tax > 0 and abs(se_deduction - expected_se_ded) > 1:
            warnings.append({
                "type": "consistency",
                "field": "se_tax_deduction",
                "message": f"SE tax deduction ({se_deduction}) doesn't match 50% of SE tax ({expected_se_ded})",
            })

    # Check effective tax rate is reasonable
    federal_tax = tax.get('federal_income_tax', 0)
    if gross.get('total', 0) > 0:
        eff_rate = federal_tax / gross['total'] * 100
        if eff_rate > 37:
            warnings.append({
                "type": "anomaly",
                "field": "effective_rate",
                "message": f"Effective tax rate of {eff_rate:.1f}% exceeds top marginal rate of 37%",
            })
        if gross['total'] > 50000 and eff_rate < 1:
            warnings.append({
                "type": "anomaly",
                "field": "effective_rate",
                "message": f"Very low effective rate ({eff_rate:.1f}%) for income of ${gross['total']:,.0f}",
            })

    # Check deduction reasonableness
    if tax.get('deduction_method') == 'itemized':
        if deduction > agi * 0.5 and agi > 50000:
            warnings.append({
                "type": "anomaly",
                "field": "deduction_amount",
                "message": f"Itemized deductions ({deduction:,.0f}) exceed 50% of AGI ({agi:,.0f})",
            })

    # Check capital losses aren't exceeding limit
    if cap:
        net_loss = cap.get('total_net_gain_loss', 0)
        deductible = cap.get('deductible_loss', 0)
        if net_loss < 0 and deductible < net_loss:
            # deductible_loss should be >= net_loss (less negative) due to $3k limit
            pass  # This is expected behavior
        if net_loss < -3000 and abs(deductible) > 3000:
            issues.append({
                "type": "limit_exceeded",
                "field": "capital_loss",
                "message": f"Deductible capital loss ({deductible}) exceeds $3,000 limit",
            })

    return issues, warnings


def check_missing_data(tax, computed_dir):
    """Check for expected but missing computed data files."""
    warnings = []
    gross = tax.get('gross_income', {})

    if gross.get('self_employment', 0) > 0:
        se_path = os.path.join(computed_dir, 'se_tax.json')
        if not os.path.exists(se_path):
            warnings.append({
                "type": "missing_data",
                "message": "Self-employment income found but se_tax.json not computed",
            })

    if gross.get('capital_gains_net', 0) != 0:
        cap_path = os.path.join(computed_dir, 'capital_gains.json')
        if not os.path.exists(cap_path):
            warnings.append({
                "type": "missing_data",
                "message": "Capital gains detected but capital_gains.json not computed",
            })

    credits_path = os.path.join(computed_dir, 'credits_and_final.json')
    if not os.path.exists(credits_path):
        warnings.append({
            "type": "missing_data",
            "message": "credits_and_final.json not found — credits may not be applied",
        })

    return warnings


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 sanity_check.py <computed_data_dir>", file=sys.stderr)
        sys.exit(1)

    computed_dir = sys.argv[1]

    # Load computed data
    tax_path = os.path.join(computed_dir, 'tax_computation.json')
    if not os.path.exists(tax_path):
        print("ERROR: tax_computation.json not found", file=sys.stderr)
        sys.exit(1)

    tax = load_json(tax_path)

    se = None
    se_path = os.path.join(computed_dir, 'se_tax.json')
    if os.path.exists(se_path):
        se = load_json(se_path)

    cap = None
    cap_path = os.path.join(computed_dir, 'capital_gains.json')
    if os.path.exists(cap_path):
        cap = load_json(cap_path)

    credits_data = None
    credits_path = os.path.join(computed_dir, 'credits_and_final.json')
    if os.path.exists(credits_path):
        credits_data = load_json(credits_path)

    # Run checks
    math_issues, math_warnings = check_math(tax, se, cap, credits_data)
    missing_warnings = check_missing_data(tax, computed_dir)

    all_issues = math_issues
    all_warnings = math_warnings + missing_warnings

    result = {
        "checked_at": datetime.now().isoformat(),
        "status": "PASS" if not all_issues else "FAIL",
        "issues": all_issues,
        "warnings": all_warnings,
        "issue_count": len(all_issues),
        "warning_count": len(all_warnings),
    }

    print(json.dumps(result, indent=2))

    if all_issues:
        print(f"\n{len(all_issues)} ISSUE(S) FOUND — review required", file=sys.stderr)
    elif all_warnings:
        print(f"\nPASS with {len(all_warnings)} warning(s)", file=sys.stderr)
    else:
        print("\nAll checks passed", file=sys.stderr)


if __name__ == '__main__':
    main()
