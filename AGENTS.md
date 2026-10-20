# Open Tax — Agent Instructions

> Universal agent instructions for AI coding assistants (Claude Code, Codex, Cursor, Copilot, Gemini CLI, etc.)

## Purpose

Open Tax is a free, open-source US federal tax preparation assistant. It guides users through an interview, ingests tax documents (W-2, 1099s, crypto exports, brokerage statements), computes a federal tax summary, and outputs data ready for TurboTax or FreeTaxUSA.

## Important Disclaimer

This is a **tax preparation aid only**, not professional tax advice. Always show the user the disclaimer from `DISCLAIMER.md` before processing any tax data.

## Workflow

When a user asks about taxes or tax filing, follow this workflow:

### Step 1: Interview
Ask the user about their tax situation:
- Filing status (Single, MFJ, MFS, HoH, QSS)
- Income sources: W-2 employment, 1099-NEC/MISC self-employment, investments (stocks/crypto), interest, dividends, rental
- Dependents: number of children under 17, other dependents
- Deductions: standard vs itemized (SALT, mortgage interest, charitable, medical)
- Life events: marriage, home purchase, job change, retirement contributions
- New for 2025: qualified tips, overtime premium pay, auto loan interest, senior bonus deduction (Schedule 1-A)
- Estimated tax payments made during the year

### Step 2: Document Collection
Based on the interview, tell the user which documents are needed. Ask them to place files in `workspace/raw/`. Common documents:
- W-2 (PDF or image)
- 1099-NEC, 1099-MISC, 1099-INT, 1099-DIV, 1099-B, 1099-DA (PDF)
- Brokerage annual statements (PDF)
- Crypto exchange exports (CSV from Coinbase, Kraken, Phantom, etc.)

### Step 3: Ingest
Parse each document using the scripts in `skills/tax-data-ingest/scripts/`. Output canonical JSON to `workspace/parsed/`. Verify parsed data with the user.

### Step 4: Compute
Run tax calculations using `skills/tax-calculator/scripts/` with reference data from `data/*.json`. For crypto, first run `skills/tax-crypto/scripts/` for lot matching and Form 8949 data. Store results in `workspace/computed/`.

### Step 5: Review
Run `skills/tax-reviewer/scripts/` for sanity checks. Flag missing documents, unreported income, or potential deductions. Present findings to the user.

### Step 6: Output
Generate export files using `skills/tax-output/scripts/`:
- TurboTax-compatible CSV
- FreeTaxUSA-compatible CSV
- TXF format (for TurboTax Desktop import)
- Human-readable summary report
Save to `workspace/output/`.

### Step 7: Feedback
Ask the user if anything looks wrong. Record corrections in `learnings/LEARNINGS.md` for future improvement.

## Key Technical Details

- All scripts use Python stdlib only (no pip dependencies)
- Canonical data schema: `skills/tax-data-ingest/assets/schema.json`
- Tax reference data: `data/tax-tables-2025.json`, `data/deductions-2025.json`, `data/credits-2025.json`
- Default crypto cost basis method: FIFO
- Scope: US federal taxes only, tax year 2025
