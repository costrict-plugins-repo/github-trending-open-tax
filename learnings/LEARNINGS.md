# Open Tax — Learnings Log

This file tracks corrections, edge cases, and best practices discovered during tax preparation sessions. It is read at the start of every session and updated whenever a mistake is found or a new edge case is encountered.

## Parsing Corrections
<!-- Format: - [YYYY-MM-DD] Description of what was parsed wrong and how it was fixed -->

## Calculation Corrections
<!-- Format: - [YYYY-MM-DD] Description of the calculation error and the correct approach -->

- [2026-04-02] **HSA double-deduction**: When HSA contributions are made via payroll (W-2 Box 12 code W), they are already excluded from Box 1 wages. Do NOT take them as an additional above-the-line adjustment — this double-deducts the HSA. To verify: check if Box 3 (SS wages) = Box 1 + 401(k) contributions. If so, Box 1 already excludes the HSA. Only take HSA as an above-the-line deduction if the contribution was made directly (not through payroll).

- [2026-04-02] **Excess Social Security tax with multiple employers**: When a taxpayer has two or more W-2s and combined Social Security wages exceed the annual wage base ($176,100 for 2025), the excess SS tax withheld must be calculated and claimed as a payment on Schedule 3, Line 11 → Form 1040, Line 25d. Formula: (total SS tax withheld) - (wage base × 6.2%).

- [2026-04-02] **Capital gains must be included in gross income**: Always incorporate the net capital gain/loss from capital transactions into the gross income computation. Do not leave capital_gains_net as a placeholder — compute it from the capital_transactions array during the main compute phase.

- [2026-04-03] **Verify standard deduction amounts against IRS guidance**: Always cross-reference standard deduction amounts in data files against the IRS Revenue Procedure for the applicable tax year (e.g., Rev. Proc. 2024-40 for TY2025). Even small discrepancies (e.g., $750) at a 24% marginal rate can cause ~$180 errors in the final amount owed.

- [2026-04-03] **FreeTaxUSA auto-calculates excess Social Security tax**: When two W-2s have combined SS wages exceeding the wage base, FreeTaxUSA automatically calculates the excess SS tax credit and includes it in total payments. No manual entry needed on Schedule 3.

- [2026-04-03] **FreeTaxUSA auto-generates Form 8606 for backdoor Roth**: When you enter a nondeductible traditional IRA contribution + report the 1099-R conversion + enter $0 year-end IRA balance and $0 prior basis, FreeTaxUSA generates Form 8606 automatically. The taxable portion is correctly calculated.

## User Preferences
<!-- Format: - [YYYY-MM-DD] Preference description (e.g., preferred broker format, filing method) -->
<!-- Preferences are per-user and should not be committed to git. -->

## Edge Cases
<!-- Format: - [YYYY-MM-DD] Description of the unusual situation and how it was handled -->

- [2026-04-02] **Backdoor Roth with partial-year contribution**: If a taxpayer contributes less than the full IRA limit to a traditional IRA and converts the entire balance to Roth, with $0 year-end traditional IRA balance and no pre-tax IRA funds, the pro-rata rule results in 100% nontaxable conversion. Form 8606 is required to document the non-deductible basis.

- [2026-04-02] **Crypto staking reported on 1099-MISC (not 1099-NEC)**: Some brokerages (e.g., Robinhood) report crypto staking rewards on 1099-MISC Box 3 rather than 1099-NEC. This income should be reported as ordinary income on Schedule 1, Line 8z — not as self-employment income.

- [2026-04-03] **1099-MISC payer address validation**: FreeTaxUSA requires Payer Name, Address, and City when entering 1099-MISC data. If these fields are left blank, the form will fail validation. Always parse payer information from the source document.
