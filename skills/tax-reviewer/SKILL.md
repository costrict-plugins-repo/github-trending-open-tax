---
name: tax-reviewer
description: |
  Review computed tax data for errors, anomalies, and missed deductions.
  Runs sanity checks on math and reasonableness, then suggests potential
  deductions the user may have missed. Called by the tax-wizard during review phase.
user-invocable: false
allowed-tools: Bash, Read, Write
---

# Tax Reviewer

Review computed tax data for correctness and optimization opportunities.

## Scripts

### sanity_check.py — Validation & Anomaly Detection
```bash
python3 skills/tax-reviewer/scripts/sanity_check.py <computed_data_dir>
```
Runs checks on computed tax data:
- Math verification (AGI = gross - adjustments, taxable = AGI - deductions, etc.)
- Reasonable ranges (effective rate, deduction-to-income ratios)
- Missing data warnings (expected forms not found)
- Cross-check consistency (SE deduction matches SE tax, etc.)

### deduction_finder.py — Missed Deduction Suggestions
```bash
python3 skills/tax-reviewer/scripts/deduction_finder.py <computed_data_dir>
```
Analyzes the tax profile to suggest potentially missed deductions and credits:
- Standard vs. itemized comparison
- Retirement contribution room (IRA, HSA)
- Education credits eligibility
- QBI deduction applicability
- Schedule 1-A deductions (tips, overtime, auto loan, senior bonus)
