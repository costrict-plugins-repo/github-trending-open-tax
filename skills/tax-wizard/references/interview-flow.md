# Interview Decision Tree

This document maps user answers to the documents and skills needed.

## Filing Status -> Documents

| Filing Status | Additional Questions |
|---|---|
| Single | Standard flow |
| Married Filing Jointly | Spouse income sources? Spouse W-2s? |
| Married Filing Separately | Only taxpayer's income |
| Head of Household | Qualifying person? (child or dependent) |
| Qualifying Surviving Spouse | Dependent child? Year spouse died? |

## Income Source -> Documents Needed -> Skills Used

| Income Source | Documents | Parsing Script | Calculator Script |
|---|---|---|---|
| W-2 wages | W-2 (PDF/image) | parse_w2.py | compute_tax.py |
| Self-employment | 1099-NEC, 1099-MISC (PDF) | parse_1099.py | compute_tax.py + compute_se_tax.py |
| Stock/bond sales | 1099-B, brokerage statement (PDF) | parse_brokerage.py | compute_cap_gains.py |
| Crypto trades | 1099-DA (PDF), exchange CSV | parse_crypto_csv.py, parse_1099.py | lot_matching.py + compute_cap_gains.py |
| Crypto staking/airdrops | Exchange records, wallet history | parse_crypto_csv.py | classify_income.py (ordinary income) |
| Interest income | 1099-INT (PDF) | parse_1099.py | compute_tax.py |
| Dividends | 1099-DIV (PDF) | parse_1099.py | compute_tax.py + compute_cap_gains.py (qualified) |
| Rental income | Schedule E data (manual entry) | — | compute_tax.py |
| Retirement distributions | 1099-R (PDF) | parse_1099.py | compute_tax.py |

## Deduction Decision Logic

```
IF total_itemized > standard_deduction[filing_status]:
    RECOMMEND itemize
ELSE:
    RECOMMEND standard deduction
    CHECK Schedule 1-A eligibility:
        - Tips? -> qualified_tips_exclusion (up to $25,000)
        - Overtime? -> qualified_overtime_pay (up to $12,500)
        - Auto loan? -> auto_loan_interest
        - Age 65+? -> senior_bonus_deduction ($4,000)
```

## Credit Eligibility Flow

```
IF children_under_17 > 0:
    APPLY child_tax_credit ($2,500/child, phase out at $200k/$400k)
IF other_dependents > 0:
    APPLY other_dependent_credit ($500/dependent)
IF education_expenses > 0 AND student_in_first_4_years:
    APPLY american_opportunity_credit (up to $2,500)
ELSE IF education_expenses > 0:
    APPLY lifetime_learning_credit (up to $2,000)
IF earned_income < threshold AND investment_income < $11,600:
    CHECK earned_income_credit eligibility
```
