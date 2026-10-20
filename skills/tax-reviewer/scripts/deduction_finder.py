#!/usr/bin/env python3
"""
Analyze computed tax data to find potentially missed deductions and credits.

Usage:
    python3 deduction_finder.py <computed_data_dir>
"""

import json
import os
import sys
from datetime import datetime


def load_json(path):
    with open(path, 'r') as f:
        return json.load(f)


def find_suggestions(tax, se, credits_data, deductions_ref, credits_ref):
    """Analyze tax profile and suggest missed deductions/credits."""
    suggestions = []
    gross = tax.get('gross_income', {})
    adjustments = tax.get('adjustments', {})
    agi = tax.get('agi', 0)
    filing_status = tax.get('filing_status', 'single')
    deduction_method = tax.get('deduction_method', 'standard')
    deduction_amount = tax.get('deduction_amount', 0)

    # Standard vs. Itemized comparison
    std_amount = deductions_ref.get('standard_deduction', {}).get(filing_status, 15750)
    if deduction_method == 'standard':
        suggestions.append({
            "category": "deductions",
            "priority": "info",
            "title": "Standard Deduction Selected",
            "detail": (
                f"You're taking the standard deduction of ${std_amount:,.0f}. "
                "If your itemizable expenses (SALT, mortgage interest, charitable, medical) "
                f"exceed ${std_amount:,.0f}, itemizing may save you money."
            ),
        })
    elif deduction_method == 'itemized' and deduction_amount < std_amount:
        suggestions.append({
            "category": "deductions",
            "priority": "high",
            "title": "Standard Deduction May Be Better",
            "detail": (
                f"Your itemized deductions (${deduction_amount:,.0f}) are less than "
                f"the standard deduction (${std_amount:,.0f}). Switching to standard "
                f"could save ${std_amount - deduction_amount:,.0f} in deductions."
            ),
        })

    # IRA contribution room
    if 'ira_deduction' not in adjustments and gross.get('total', 0) > 0:
        suggestions.append({
            "category": "retirement",
            "priority": "medium",
            "title": "Traditional IRA Contribution",
            "detail": (
                "No IRA deduction found. You may be able to deduct up to $7,000 "
                "($8,000 if 50+) for traditional IRA contributions made by April 15, 2026."
            ),
        })

    # HSA contribution room
    if 'hsa_contributions' not in adjustments and gross.get('wages', 0) > 0:
        suggestions.append({
            "category": "retirement",
            "priority": "low",
            "title": "HSA Contributions",
            "detail": (
                "No HSA contributions detected. If you have a high-deductible health plan, "
                "you can deduct up to $4,300 (self) or $8,550 (family) in HSA contributions."
            ),
        })

    # Schedule 1-A deductions (new for 2025)
    if gross.get('wages', 0) > 0:
        if 'qualified_tips_exclusion' not in adjustments:
            suggestions.append({
                "category": "schedule_1a",
                "priority": "low",
                "title": "Qualified Tips Exclusion (New 2025)",
                "detail": (
                    "If you receive tips in a traditionally tipped occupation, "
                    "you may exclude up to $25,000 from income under the new Schedule 1-A."
                ),
            })
        if 'overtime_pay_deduction' not in adjustments:
            suggestions.append({
                "category": "schedule_1a",
                "priority": "low",
                "title": "Overtime Pay Deduction (New 2025)",
                "detail": (
                    "If you earn overtime pay, you may deduct up to $12,500 "
                    "under the new Schedule 1-A provisions."
                ),
            })

    # Senior bonus
    if 'senior_bonus_deduction' not in adjustments:
        suggestions.append({
            "category": "schedule_1a",
            "priority": "low",
            "title": "Senior Bonus Deduction (New 2025)",
            "detail": (
                "Taxpayers 65+ taking the standard deduction get an additional "
                "$4,000 deduction. If you're 65+, make sure your date of birth is included."
            ),
        })

    # QBI deduction for self-employed
    if gross.get('self_employment', 0) > 0:
        se_income = gross['self_employment']
        threshold = 197300 if filing_status == 'single' else 394600
        if agi < threshold:
            potential_qbi = round(se_income * 0.20, 2)
            suggestions.append({
                "category": "deductions",
                "priority": "high",
                "title": "Qualified Business Income (QBI) Deduction",
                "detail": (
                    f"With self-employment income of ${se_income:,.0f} and AGI below "
                    f"the ${threshold:,.0f} threshold, you may qualify for a QBI deduction "
                    f"of up to ${potential_qbi:,.0f} (20% of qualified business income)."
                ),
            })

    # Student loan interest
    if 'student_loan_interest' not in adjustments:
        suggestions.append({
            "category": "adjustments",
            "priority": "low",
            "title": "Student Loan Interest",
            "detail": (
                "No student loan interest deduction found. If you paid student loan interest, "
                "you can deduct up to $2,500 above-the-line."
            ),
        })

    # Education credits
    credits_detail = credits_data.get('credits', {}) if credits_data else {}
    if credits_detail.get('total_credits', 0) == 0 or not credits_detail:
        aotc_limit = credits_ref.get('education_credits', {}).get('american_opportunity', {})
        aotc_phase_out = aotc_limit.get('magi_phase_out', {}).get(filing_status, {})
        if aotc_phase_out and agi < aotc_phase_out.get('end', 90000):
            suggestions.append({
                "category": "credits",
                "priority": "medium",
                "title": "Education Credits",
                "detail": (
                    "No education credits claimed. If you or a dependent paid for higher education, "
                    "you may qualify for the American Opportunity Credit (up to $2,500/student) "
                    "or Lifetime Learning Credit (up to $2,000)."
                ),
            })

    # Estimated tax payments check
    final = credits_data.get('final_summary', {}) if credits_data else {}
    owed = final.get('amount_owed_or_refund', 0)
    if owed > 1000:
        suggestions.append({
            "category": "planning",
            "priority": "medium",
            "title": "Consider Estimated Tax Payments",
            "detail": (
                f"You owe ${owed:,.0f}. If this is typical, consider making quarterly "
                "estimated payments to avoid underpayment penalties next year."
            ),
        })
    elif owed < -3000:
        suggestions.append({
            "category": "planning",
            "priority": "low",
            "title": "Adjust Withholding",
            "detail": (
                f"You're getting a refund of ${abs(owed):,.0f}. Consider adjusting your "
                "W-4 withholding to keep more money in each paycheck."
            ),
        })

    return suggestions


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 deduction_finder.py <computed_data_dir>", file=sys.stderr)
        sys.exit(1)

    computed_dir = sys.argv[1]

    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(script_dir, '..', '..', '..'))

    tax_path = os.path.join(computed_dir, 'tax_computation.json')
    if not os.path.exists(tax_path):
        print("ERROR: tax_computation.json not found", file=sys.stderr)
        sys.exit(1)

    tax = load_json(tax_path)
    deductions_ref = load_json(os.path.join(project_root, 'data', 'deductions-2025.json'))
    credits_ref = load_json(os.path.join(project_root, 'data', 'credits-2025.json'))

    se = None
    se_path = os.path.join(computed_dir, 'se_tax.json')
    if os.path.exists(se_path):
        se = load_json(se_path)

    credits_data = None
    credits_path = os.path.join(computed_dir, 'credits_and_final.json')
    if os.path.exists(credits_path):
        credits_data = load_json(credits_path)

    suggestions = find_suggestions(tax, se, credits_data, deductions_ref, credits_ref)

    result = {
        "analyzed_at": datetime.now().isoformat(),
        "suggestion_count": len(suggestions),
        "suggestions": suggestions,
    }

    print(json.dumps(result, indent=2))

    high = [s for s in suggestions if s['priority'] == 'high']
    medium = [s for s in suggestions if s['priority'] == 'medium']
    if high:
        print(f"\n{len(high)} HIGH priority suggestion(s) found", file=sys.stderr)
    if medium:
        print(f"{len(medium)} MEDIUM priority suggestion(s) found", file=sys.stderr)


if __name__ == '__main__':
    main()
