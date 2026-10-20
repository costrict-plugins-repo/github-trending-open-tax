---
name: tax-calculator
description: |
  Compute federal tax liability from parsed tax data. Handles AGI calculation,
  taxable income, tax brackets, self-employment tax, capital gains, and credits.
  Called by the tax-wizard during the computation phase.
user-invocable: false
allowed-tools: Bash, Read, Write
---

# Tax Calculator

Compute federal tax liability from parsed data conforming to the Open Tax canonical schema.

## Scripts

### compute_tax.py — Main Tax Engine
```bash
python3 skills/tax-calculator/scripts/compute_tax.py <parsed_data_dir> <output_dir>
```
Reads all parsed JSON files, computes:
- Gross income (all sources)
- Above-the-line adjustments (IRA, HSA, student loan interest, SE tax deduction, Schedule 1-A)
- AGI (Adjusted Gross Income)
- Deductions (standard or itemized)
- Taxable income
- Tax liability (using brackets from `data/tax-tables-2025.json`)
- Effective tax rate

### compute_se_tax.py — Self-Employment Tax
```bash
python3 skills/tax-calculator/scripts/compute_se_tax.py <parsed_data_dir> <output_dir>
```
Computes Schedule SE for 1099-NEC/MISC income.

### compute_cap_gains.py — Capital Gains Tax
```bash
python3 skills/tax-calculator/scripts/compute_cap_gains.py <parsed_data_dir> <output_dir>
```
Computes capital gains/losses, applies $3,000 loss limit, NIIT.

### compute_credits.py — Tax Credits
```bash
python3 skills/tax-calculator/scripts/compute_credits.py <computed_data_dir> <output_dir>
```
Applies CTC, EITC, education credits. Computes final owed/refund.

## Reference Data
All tax rates and thresholds come from `data/tax-tables-2025.json`, `data/deductions-2025.json`, and `data/credits-2025.json`.
