---
name: tax-preparer
description: |
  Autonomous agent that processes tax documents and computes a complete
  federal tax return. Use when documents are in workspace/raw/ and user
  wants the full pipeline run without step-by-step interaction.
---

# Tax Preparer Agent

An autonomous agent that processes tax documents and computes a complete federal tax return.

## When to Use

Use this agent when the user has already placed their tax documents in `workspace/raw/` and wants to run the full pipeline without step-by-step interaction.

## Agent Flow

```
1. Read learnings/LEARNINGS.md for prior corrections
2. Scan workspace/raw/ for all documents
3. Ingest: Parse each document → workspace/parsed/
4. Compute: Run tax calculations → workspace/computed/
5. Review: Sanity check + deduction finder
6. Output: Generate all export formats → workspace/output/
7. Present summary to user
```

## Detailed Steps

### 1. Initialize
- Read `learnings/LEARNINGS.md`
- Read `DISCLAIMER.md` and present disclaimer to user
- Scan `workspace/raw/` to identify all documents

### 2. Ingest Documents
For each file in `workspace/raw/`:

```bash
# W-2 PDFs/images
python3 skills/tax-data-ingest/scripts/parse_w2.py <file> workspace/parsed/

# 1099 variants
python3 skills/tax-data-ingest/scripts/parse_1099.py <file> workspace/parsed/ --type NEC|INT|DIV|MISC|B

# Brokerage statements
python3 skills/tax-data-ingest/scripts/parse_brokerage.py <file> workspace/parsed/

# Crypto exchange CSVs
python3 skills/tax-data-ingest/scripts/parse_crypto_csv.py <file> workspace/parsed/ --exchange coinbase|kraken|generic
```

### 3. Compute Taxes
Run in order:

```bash
# Main tax engine (AGI, taxable income, brackets)
python3 skills/tax-calculator/scripts/compute_tax.py workspace/parsed/ workspace/computed/

# Self-employment tax (if applicable)
python3 skills/tax-calculator/scripts/compute_se_tax.py workspace/parsed/ workspace/computed/

# Crypto lot matching (if applicable)
python3 skills/tax-crypto/scripts/lot_matching.py workspace/parsed/ workspace/computed/

# Crypto income classification (if applicable)
python3 skills/tax-crypto/scripts/income_classifier.py workspace/parsed/ workspace/computed/

# Capital gains tax
python3 skills/tax-calculator/scripts/compute_cap_gains.py workspace/parsed/ workspace/computed/

# Wash sale detection (if crypto present)
python3 skills/tax-crypto/scripts/wash_sale_detector.py workspace/computed/ workspace/computed/

# Credits and final summary
python3 skills/tax-calculator/scripts/compute_credits.py workspace/computed/ workspace/computed/
```

### 4. Review
```bash
python3 skills/tax-reviewer/scripts/sanity_check.py workspace/computed/
python3 skills/tax-reviewer/scripts/deduction_finder.py workspace/computed/
```

### 5. Generate Output
```bash
# TurboTax CSV
python3 skills/tax-output/scripts/generate_csv.py workspace/computed/ workspace/output/ --format turbotax

# FreeTaxUSA CSV
python3 skills/tax-output/scripts/generate_csv.py workspace/computed/ workspace/output/ --format freetaxusa

# Form 8949 CSV (if capital gains present)
python3 skills/tax-output/scripts/generate_8949.py workspace/computed/ workspace/output/

# TXF file (TurboTax Desktop)
python3 skills/tax-output/scripts/generate_txf.py workspace/computed/ workspace/output/

# Human-readable summary
python3 skills/tax-output/scripts/generate_report.py workspace/computed/ workspace/output/
```

### 6. Present Results
Show the user:
- Federal tax summary (income, deductions, tax, credits, owed/refund)
- Any review warnings or issues
- Missed deduction suggestions
- List of generated output files

### 7. Record Learnings
If any corrections were made during processing, append to `learnings/LEARNINGS.md`.

## Error Handling

- If a parse script fails, skip that document and warn the user
- If computed values fail sanity checks, present the issues before generating output
- Always verify critical numbers (AGI, total tax, refund/owed) with the user before finalizing

## Constraints

- Python stdlib only — no pip dependencies
- US federal taxes only, tax year 2025
- Default crypto cost basis: FIFO
- All data must conform to `skills/tax-data-ingest/assets/schema.json`
