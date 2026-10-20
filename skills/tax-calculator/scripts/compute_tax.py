#!/usr/bin/env python3
"""
Main tax computation engine for Open Tax.

Reads parsed tax data, computes AGI, taxable income, and federal tax liability.

Usage:
    python3 compute_tax.py <parsed_data_dir> <output_dir>
"""

import json
import os
import sys
from datetime import datetime


def load_json(path):
    with open(path, 'r') as f:
        return json.load(f)


def load_all_parsed(parsed_dir):
    """Load and merge all parsed JSON files into a single tax profile."""
    profile = {
        "tax_year": 2025,
        "filing_status": "single",
        "w2_income": [],
        "self_employment_income": [],
        "interest_income": [],
        "dividend_income": [],
        "capital_transactions": [],
        "crypto_income": [],
        "other_income": [],
        "deductions": {"method": "standard"},
        "estimated_payments": [],
        "dependents": [],
    }

    for filename in sorted(os.listdir(parsed_dir)):
        if not filename.endswith('.json'):
            continue
        data = load_json(os.path.join(parsed_dir, filename))
        inner = data.get("data", data)

        for key in ["w2_income", "self_employment_income", "interest_income",
                     "dividend_income", "capital_transactions", "crypto_income",
                     "other_income", "estimated_payments", "dependents"]:
            if key in inner and isinstance(inner[key], list):
                profile[key].extend(inner[key])

        if "filing_status" in inner:
            profile["filing_status"] = inner["filing_status"]
        if "deductions" in inner and isinstance(inner["deductions"], dict):
            profile["deductions"].update(inner["deductions"])
        if "taxpayer" in inner:
            profile["taxpayer"] = inner["taxpayer"]

    return profile


def compute_gross_income(profile):
    """Compute total gross income from all sources."""
    result = {}

    # W-2 wages
    result["wages"] = sum(w.get("wages", 0) for w in profile["w2_income"])

    # Self-employment net income
    result["self_employment"] = sum(
        s.get("net_income", s.get("gross_income", 0) - s.get("expenses", 0))
        for s in profile["self_employment_income"]
    )

    # Interest
    result["interest"] = sum(i.get("amount", 0) for i in profile["interest_income"])

    # Ordinary dividends
    result["ordinary_dividends"] = sum(d.get("ordinary_dividends", 0) for d in profile["dividend_income"])

    # Capital gains (net)
    cap_gains = sum(t.get("gain_loss", 0) for t in profile.get("capital_transactions", []))
    result["capital_gains_net"] = round(cap_gains, 2)

    # Crypto ordinary income (staking, airdrops, mining)
    result["crypto_ordinary_income"] = sum(
        c.get("fair_market_value_usd", 0) for c in profile["crypto_income"]
    )

    # Other income
    result["other"] = sum(o.get("amount", 0) for o in profile["other_income"])

    result["total"] = sum(result.values())
    return result


def compute_adjustments(profile, gross_income):
    """Compute above-the-line adjustments to get AGI."""
    adjustments = {}
    deductions = profile.get("deductions", {})

    # Self-employment tax deduction (50% of SE tax)
    se_income = gross_income.get("self_employment", 0)
    if se_income > 0:
        net_se = se_income * 0.9235
        se_tax = min(net_se, 176100) * 0.153
        if net_se > 176100:
            se_tax = 176100 * 0.153 + (net_se - 176100) * 0.029
        adjustments["se_tax_deduction"] = round(se_tax * 0.5, 2)

    # HSA contributions — only non-W-2 contributions count as adjustments.
    # W-2 Box 12 code W contributions are already excluded from Box 1 wages,
    # so they must NOT be added here (that would double-deduct).
    hsa_non_w2 = deductions.get("hsa_contributions", 0)
    if hsa_non_w2 > 0:
        adjustments["hsa_contributions"] = hsa_non_w2

    # IRA contributions
    ira = deductions.get("ira_contributions", 0)
    if ira > 0:
        adjustments["ira_deduction"] = min(ira, 7000)  # 2025 limit

    # Student loan interest
    sli = deductions.get("student_loan_interest", 0)
    if sli > 0:
        adjustments["student_loan_interest"] = min(sli, 2500)

    # Educator expenses
    edu = deductions.get("educator_expenses", 0)
    if edu > 0:
        adjustments["educator_expenses"] = min(edu, 300)

    # Schedule 1-A (OBBBA 2025 — available even with standard deduction)
    sched_1a = deductions.get("schedule_1a", {})
    if sched_1a.get("qualified_tips", 0) > 0:
        adjustments["qualified_tips_exclusion"] = min(sched_1a["qualified_tips"], 25000)
    if sched_1a.get("overtime_pay", 0) > 0:
        adjustments["overtime_pay_deduction"] = min(sched_1a["overtime_pay"], 12500)
    if sched_1a.get("auto_loan_interest", 0) > 0:
        adjustments["auto_loan_interest"] = sched_1a["auto_loan_interest"]
    if sched_1a.get("senior_bonus"):
        adjustments["senior_bonus_deduction"] = 4000

    adjustments["total"] = round(sum(adjustments.values()), 2)
    return adjustments


def compute_taxable_income(profile, agi, deductions_data):
    """Compute taxable income after deductions."""
    filing_status = profile.get("filing_status", "single")
    deductions = profile.get("deductions", {})
    method = deductions.get("method", "standard")

    if method == "standard":
        std_ded = deductions_data["standard_deduction"].get(filing_status, 15750)

        # Additional for 65+ or blind
        taxpayer = profile.get("taxpayer", {})
        dob = taxpayer.get("date_of_birth")
        if dob:
            try:
                birth = datetime.strptime(dob, '%Y-%m-%d')
                age = (datetime(2025, 12, 31) - birth).days // 365
                if age >= 65:
                    married = filing_status in ("married_filing_jointly", "married_filing_separately")
                    std_ded += deductions_data["standard_deduction"]["additional_65_or_older"][
                        "married" if married else "single"
                    ]
            except (ValueError, TypeError):
                pass

        if taxpayer.get("is_blind"):
            married = filing_status in ("married_filing_jointly", "married_filing_separately")
            std_ded += deductions_data["standard_deduction"]["additional_blind"][
                "married" if married else "single"
            ]

        deduction_amount = std_ded
    else:
        # Itemized deductions
        salt = min(deductions.get("salt_paid", 0),
                   deductions_data["salt_deduction"]["cap"])
        mortgage = deductions.get("mortgage_interest", 0)
        charitable = deductions.get("charitable_cash", 0) + deductions.get("charitable_noncash", 0)
        medical = deductions.get("medical_expenses", 0)
        medical_deductible = max(0, medical - agi * 0.075)

        deduction_amount = salt + mortgage + charitable + medical_deductible

    taxable_income = max(0, agi - deduction_amount)
    return taxable_income, deduction_amount, method


def compute_tax_liability(taxable_income, filing_status, tax_tables):
    """Apply tax brackets to compute federal income tax."""
    brackets = tax_tables["brackets"].get(filing_status, tax_tables["brackets"]["single"])
    tax = 0.0

    for bracket in brackets:
        bracket_min = bracket["min"]
        bracket_max = bracket["max"]
        rate = bracket["rate"]

        if taxable_income <= bracket_min:
            break

        if bracket_max is None:
            taxable_in_bracket = taxable_income - bracket_min
        else:
            taxable_in_bracket = min(taxable_income, bracket_max) - bracket_min

        tax += taxable_in_bracket * rate

    return round(tax, 2)


def main():
    if len(sys.argv) < 3:
        print("Usage: python3 compute_tax.py <parsed_data_dir> <output_dir>", file=sys.stderr)
        sys.exit(1)

    parsed_dir = sys.argv[1]
    output_dir = sys.argv[2]

    # Find the data directory (relative to script location)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(script_dir, '..', '..', '..'))
    data_dir = os.path.join(project_root, 'data')

    tax_tables = load_json(os.path.join(data_dir, 'tax-tables-2025.json'))
    deductions_data = load_json(os.path.join(data_dir, 'deductions-2025.json'))

    # Load parsed data
    profile = load_all_parsed(parsed_dir)
    filing_status = profile.get("filing_status", "single")

    # Compute
    gross = compute_gross_income(profile)
    adjustments = compute_adjustments(profile, gross)
    agi = round(gross["total"] - adjustments["total"], 2)
    taxable_income, deduction_amount, deduction_method = compute_taxable_income(
        profile, agi, deductions_data
    )
    tax_liability = compute_tax_liability(taxable_income, filing_status, tax_tables)

    # Withholding
    total_withheld = sum(w.get("federal_withheld", 0) for w in profile["w2_income"])
    estimated_paid = sum(p.get("amount", 0) for p in profile["estimated_payments"])

    # Excess Social Security tax (multiple employers exceeding wage base)
    ss_wage_base = tax_tables.get("self_employment", {}).get("social_security_wage_base", 176100)
    total_ss_withheld = sum(w.get("ss_tax_withheld", 0) for w in profile["w2_income"])
    max_ss_tax = round(ss_wage_base * 0.062, 2)
    excess_ss_tax = round(max(0, total_ss_withheld - max_ss_tax), 2)

    total_payments = round(total_withheld + estimated_paid + excess_ss_tax, 2)

    # Build result
    result = {
        "tax_year": 2025,
        "filing_status": filing_status,
        "computed_at": datetime.now().isoformat(),
        "gross_income": gross,
        "adjustments": adjustments,
        "agi": agi,
        "deduction_method": deduction_method,
        "deduction_amount": deduction_amount,
        "taxable_income": taxable_income,
        "federal_income_tax": tax_liability,
        "self_employment_tax": 0,  # Computed by compute_se_tax.py
        "capital_gains_tax": 0,  # Computed by compute_cap_gains.py
        "niit": 0,  # Computed by compute_cap_gains.py
        "total_tax": tax_liability,
        "credits": {},  # Computed by compute_credits.py
        "total_credits": 0,
        "tax_withheld": total_withheld,
        "excess_ss_tax": excess_ss_tax,
        "estimated_payments": estimated_paid,
        "total_payments": total_payments,
        "amount_owed_or_refund": round(tax_liability - total_payments, 2),
        "effective_tax_rate": round(tax_liability / gross["total"] * 100, 2) if gross["total"] > 0 else 0,
    }

    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "tax_computation.json")

    with open(output_path, 'w') as f:
        json.dump(result, f, indent=2)

    print(json.dumps(result, indent=2))
    print(f"\nSaved to: {output_path}", file=sys.stderr)


if __name__ == '__main__':
    main()
