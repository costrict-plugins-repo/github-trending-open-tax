# Tax Form Field Maps

## W-2: Wage and Tax Statement

| Box | Field | Schema Mapping |
|-----|-------|---------------|
| 1 | Wages, tips, other compensation | `w2_income[].wages` |
| 2 | Federal income tax withheld | `w2_income[].federal_withheld` |
| 3 | Social security wages | `w2_income[].ss_wages` |
| 4 | Social security tax withheld | `w2_income[].ss_tax_withheld` |
| 5 | Medicare wages and tips | `w2_income[].medicare_wages` |
| 6 | Medicare tax withheld | `w2_income[].medicare_tax_withheld` |
| 7 | Social security tips | `w2_income[].tips` |
| 8 | Allocated tips | `w2_income[].tips` (add to box 7) |
| 12 | Codes D/E/G/AA/BB | `w2_income[].retirement_contributions` |
| 12 | Code W | `w2_income[].hsa_contributions` |
| 15 | State | `w2_income[].state` |
| 16 | State wages | `w2_income[].state_wages` |
| 17 | State income tax | `w2_income[].state_tax_withheld` |

## 1099-NEC: Nonemployee Compensation

| Box | Field | Schema Mapping |
|-----|-------|---------------|
| 1 | Nonemployee compensation | `self_employment_income[].gross_income` |
| 4 | Federal income tax withheld | (track separately) |

## 1099-INT: Interest Income

| Box | Field | Schema Mapping |
|-----|-------|---------------|
| 1 | Interest income | `interest_income[].amount` |
| 3 | Interest on US savings bonds | `interest_income[].us_savings_bond_interest` |
| 4 | Federal income tax withheld | `interest_income[].federal_tax_withheld` |
| 8 | Tax-exempt interest | `interest_income[].tax_exempt_interest` |

## 1099-DIV: Dividends and Distributions

| Box | Field | Schema Mapping |
|-----|-------|---------------|
| 1a | Total ordinary dividends | `dividend_income[].ordinary_dividends` |
| 1b | Qualified dividends | `dividend_income[].qualified_dividends` |
| 2a | Total capital gain distributions | `dividend_income[].capital_gain_distributions` |
| 4 | Federal income tax withheld | `dividend_income[].federal_tax_withheld` |
| 7 | Foreign tax paid | `dividend_income[].foreign_tax_paid` |

## 1099-B: Proceeds from Broker Transactions

| Column | Schema Mapping |
|--------|---------------|
| 1a Description of property | `capital_transactions[].description` |
| 1b Date acquired | `capital_transactions[].date_acquired` |
| 1c Date sold | `capital_transactions[].date_sold` |
| 1d Proceeds | `capital_transactions[].proceeds` |
| 1e Cost or other basis | `capital_transactions[].cost_basis` |
| 1g Wash sale loss disallowed | `capital_transactions[].wash_sale_loss_disallowed` |

## 1099-DA: Digital Asset Proceeds (New for 2025)

| Box | Field | Schema Mapping |
|-----|-------|---------------|
| 1a | Description of digital asset | `capital_transactions[].description` |
| 1b | Date acquired | `capital_transactions[].date_acquired` |
| 1c | Date of disposition | `capital_transactions[].date_sold` |
| 1d | Proceeds | `capital_transactions[].proceeds` |
| 1e | Cost basis | `capital_transactions[].cost_basis` (may be blank for 2025) |
| 1f | Gain or loss | `capital_transactions[].gain_loss` |

**Note for 2025**: Brokers are required to report gross proceeds (Box 1d) but cost basis (Box 1e) is NOT required until 2026. Users may need to provide their own cost basis records.
