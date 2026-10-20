---
name: tax-data-ingest
description: |
  Parse tax documents (W-2, 1099 variants, crypto exchange CSVs, brokerage statements)
  into the canonical Open Tax JSON schema. Called by the tax-wizard during ingestion phase.
user-invocable: false
allowed-tools: Bash, Read, Write, Glob
---

# Tax Data Ingest

Parse tax documents and output canonical JSON conforming to `assets/schema.json`.

## How to Use

### W-2 Documents
```bash
python3 skills/tax-data-ingest/scripts/parse_w2.py <input_file> <output_dir>
```
Input: Text extracted from a W-2 (pass via stdin or file path)
Output: JSON file in output_dir with W-2 fields mapped to schema

### 1099 Documents (all variants)
```bash
python3 skills/tax-data-ingest/scripts/parse_1099.py <input_file> <output_dir> --type [NEC|MISC|INT|DIV|B|DA]
```
Input: Text extracted from a 1099 form
Output: JSON file with fields mapped per variant type

### Crypto Exchange CSVs
```bash
python3 skills/tax-data-ingest/scripts/parse_crypto_csv.py <csv_file> <output_dir> --exchange [coinbase|kraken|gemini|phantom|generic]
```
Input: CSV export from a crypto exchange
Output: JSON with capital_transactions and crypto_income arrays

### Brokerage Statements
```bash
python3 skills/tax-data-ingest/scripts/parse_brokerage.py <input_file> <output_dir>
```
Input: Text extracted from a consolidated brokerage statement (1099-B/DIV/INT combined)
Output: JSON with capital_transactions, dividend_income, and interest_income

## Important Notes

- Claude can read PDFs and images directly with the Read tool — use that first, then pass extracted text to these scripts
- All output must conform to `assets/schema.json`
- When in doubt about a parsed value, flag it for user verification
- Store parsed output in `workspace/parsed/`
