---
name: tax-crypto
description: |
  Process cryptocurrency and digital asset transactions for tax reporting.
  Performs FIFO lot matching, wash sale detection, income classification,
  and generates Form 8949-ready data. Called by the tax-wizard during compute phase.
user-invocable: false
allowed-tools: Bash, Read, Write
---

# Crypto Tax Processor

Process cryptocurrency and digital asset transactions for US federal tax reporting (tax year 2025).

## Scripts

### lot_matching.py — FIFO Lot Matching
```bash
python3 skills/tax-crypto/scripts/lot_matching.py <parsed_data_dir> <output_dir>
```
Reads parsed crypto transactions, applies FIFO (First In, First Out) cost basis method:
- Builds a per-asset lot pool from buy/receive transactions
- Matches sells against oldest lots first
- Computes cost basis, gain/loss, and holding period for each disposal
- Outputs Form 8949-ready capital transactions with `is_digital_asset: true`

### wash_sale_detector.py — Wash Sale Detection
```bash
python3 skills/tax-crypto/scripts/wash_sale_detector.py <computed_data_dir> <output_dir>
```
Scans matched transactions for potential wash sales:
- Checks for repurchases of the same asset within 30 days before/after a loss sale
- Flags affected transactions and computes disallowed loss amounts
- Note: Crypto wash sale rules are evolving — flags for review, not automatic adjustment

### income_classifier.py — Crypto Income Classification
```bash
python3 skills/tax-crypto/scripts/income_classifier.py <parsed_data_dir> <output_dir>
```
Classifies non-sale crypto events as ordinary income:
- Staking rewards → Schedule 1 / Other Income
- Airdrops → Schedule 1 / Other Income
- Mining → Schedule C (self-employment) or Other Income
- DeFi lending interest → Schedule B
- Computes total crypto ordinary income at FMV when received

## Reference Data
- Cost basis method: **FIFO** (default, per project rules)
- Per-wallet/account tracking: Required by Rev. Proc. 2024-28
- Form 8949 boxes: G/H/I (short-term digital), J/K/L (long-term digital)
- Tax rules reference: `skills/tax-crypto/references/crypto-tax-rules-2025.md`
