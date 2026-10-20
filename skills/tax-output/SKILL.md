---
name: tax-output
description: |
  Generate export files from computed tax data. Supports TurboTax CSV,
  FreeTaxUSA CSV, TXF (TurboTax Desktop), Form 8949 CSV, and human-readable
  summary reports. Called by the tax-wizard during the output phase.
user-invocable: false
allowed-tools: Bash, Read, Write
---

# Tax Output Generator

Generate export files from computed tax data for import into tax filing software.

## Scripts

### generate_csv.py — TurboTax / FreeTaxUSA CSV
```bash
python3 skills/tax-output/scripts/generate_csv.py <computed_data_dir> <output_dir> --format turbotax
python3 skills/tax-output/scripts/generate_csv.py <computed_data_dir> <output_dir> --format freetaxusa
```
Generates CSV files for import into TurboTax Online or FreeTaxUSA:
- Income summary (W-2, 1099, etc.)
- Capital gains/losses
- Deductions and credits

### generate_8949.py — Form 8949 CSV
```bash
python3 skills/tax-output/scripts/generate_8949.py <computed_data_dir> <output_dir>
```
Generates Form 8949-formatted CSV for capital gains reporting:
- Grouped by Box (A-F for traditional, G-L for digital assets)
- Includes wash sale adjustments
- Summary totals per box for Schedule D

### generate_txf.py — TXF File (TurboTax Desktop)
```bash
python3 skills/tax-output/scripts/generate_txf.py <computed_data_dir> <output_dir>
```
Generates TXF (Tax Exchange Format) file for TurboTax Desktop import.

### generate_8606.py — Form 8606 (Nondeductible IRAs / Backdoor Roth)
```bash
python3 skills/tax-output/scripts/generate_8606.py <computed_data_dir> <output_dir>
```
Generates Form 8606 output for nondeductible IRA contributions and backdoor Roth conversions:
- CSV with line-by-line Form 8606 values (Part I and Part II)
- JSON machine-readable version with result summary
- Required when `form_8606_required: true` in parsed tax data

### generate_report.py — Human-Readable Summary
```bash
python3 skills/tax-output/scripts/generate_report.py <computed_data_dir> <output_dir>
```
Generates a Markdown summary report with all computed values.

## Reference Data
- TXF codes: `data/txf-reference-codes.json`
