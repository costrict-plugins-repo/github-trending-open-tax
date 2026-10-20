# Open Tax

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![GitHub Sponsors](https://img.shields.io/badge/Sponsor-%E2%9D%A4-white)](https://github.com/sponsors/tugberkgoc)

Free, open-source US federal tax preparation assistant for AI coding tools.

Open Tax guides you through an interview about your tax situation, ingests your documents (W-2, 1099s, crypto exports, brokerage statements), computes your federal tax summary, and outputs data ready to plug into TurboTax or FreeTaxUSA.

> **Disclaimer**: This is a tax preparation aid, not professional tax advice. See [DISCLAIMER.md](DISCLAIMER.md) for full legal notice.

## Quick Start

### Option 1: Install as a Claude Code Plugin

```bash
claude plugin add --from https://github.com/tugberkgoc/open-tax
```

Then invoke from any project:

```
> /open-tax:tax-wizard
```

### Option 2: Clone and Use as a Project

```bash
git clone https://github.com/tugberkgoc/open-tax.git
cd open-tax
claude
```

Then just ask about your taxes:

```
> I need to file my taxes
```

### Option 3: Works with Any AI Coding Tool

Thanks to the `AGENTS.md` standard, Open Tax also works with Cursor, GitHub Copilot, Gemini CLI, OpenAI Codex, and any tool that supports the [Agent Skills](https://agentskills.io) spec. Just clone the repo and open it in your tool of choice.

### What Happens

The tax wizard will:
1. Ask about your filing status, income sources, and deductions
2. Tell you which documents to provide
3. Parse your documents automatically (PDFs, images, CSVs)
4. Compute your federal tax summary
5. Run sanity checks and suggest missed deductions
6. Generate files ready for TurboTax or FreeTaxUSA

### Available Skills

| Skill | Command | Description |
|-------|---------|-------------|
| Tax Wizard | `/open-tax:tax-wizard` | Main entry point — guided interview and full workflow |
| Data Ingest | *(internal)* | Parses W-2, 1099, crypto CSV, brokerage statements |
| Calculator | *(internal)* | Computes AGI, brackets, SE tax, capital gains, credits |
| Crypto | *(internal)* | FIFO lot matching, wash sale detection, income classification |
| Output | *(internal)* | Generates CSV, TXF, Form 8949, Form 8606, reports |
| Reviewer | *(internal)* | Sanity checks, deduction finder, anomaly detection |

## What's Supported

### Tax Year
- **2025** (includes One Big Beautiful Bill Act changes)

### Income Types
- W-2 wages
- 1099-NEC / 1099-MISC (self-employment)
- 1099-INT (interest)
- 1099-DIV (dividends, qualified dividends)
- 1099-B (stock/investment sales)
- 1099-DA (digital assets — new for 2025)
- Crypto exchange CSVs (Coinbase, Kraken, Phantom)

### Computations
- Federal tax brackets (all filing statuses)
- Standard deduction + Schedule 1-A deductions (tips, overtime, auto loan interest, senior bonus)
- Self-employment tax (Schedule SE)
- Capital gains/losses (short-term and long-term)
- Crypto lot matching (FIFO default)
- Net Investment Income Tax (NIIT)
- Child Tax Credit ($2,200/child for 2025)
- SALT deduction (capped at $40,000 for 2025)

### Output Formats
- TurboTax-compatible CSV
- FreeTaxUSA-compatible CSV
- TXF format (TurboTax Desktop import)
- Human-readable summary report

## Project Structure

```
open-tax/
├── skills/
│   ├── tax-wizard/          # Main entry point — guided interview
│   ├── tax-data-ingest/     # Document parsing (W-2, 1099, crypto CSV)
│   ├── tax-calculator/      # Tax computation engine
│   ├── tax-crypto/          # Crypto-specific processing
│   ├── tax-output/          # Export to tax software
│   └── tax-reviewer/        # Sanity checks + deduction finder
├── data/                    # Tax reference tables (JSON)
├── workspace/               # Your working directory (gitignored)
├── learnings/               # Self-improvement log
└── agents/                  # Agent definitions
```

## Privacy

All processing happens **locally on your machine**. No tax documents, personal information, or financial data is sent anywhere. The `workspace/` directory is gitignored by default.

## Cross-Platform Compatibility

Open Tax follows the [Agent Skills](https://agentskills.io) open standard and works with:
- Claude Code
- OpenAI Codex
- Cursor
- GitHub Copilot
- Gemini CLI
- Any tool supporting AGENTS.md

## Roadmap

Open Tax is growing from a tax filing tool into a **year-round financial assistant** — like having a personal tax agency that helps you plan, optimize, and file with confidence.

### Near-Term
- [ ] **Multi-state tax support** — State income tax computation and filing for all 50 states
- [ ] **Married Filing Jointly / Head of Household** — Full support for all filing statuses with spouse income merging
- [ ] **Itemized deductions (Schedule A)** — Mortgage interest, charitable donations, medical expenses
- [ ] **Estimated quarterly payments** — Compute and track quarterly estimated tax payments (Form 1040-ES)
- [ ] **Prior year import** — Import last year's return data for year-over-year comparison
- [ ] **More broker integrations** — Fidelity, Schwab, Vanguard, E-Trade CSV/OFX parsing

### Mid-Term
- [ ] **Year-round tax planning** — "Should I max out my 401(k)?" "What's the tax impact of selling these shares?"
- [ ] **Life event guidance** — Marriage, new job, freelancing, home purchase, having a child — how each changes your tax picture
- [ ] **Deduction tracking** — Real-time tracking of deductible expenses throughout the year with receipt capture
- [ ] **Tax-loss harvesting alerts** — Monitor portfolio for tax-loss harvesting opportunities before year-end
- [ ] **Withholding optimizer** — Analyze current withholding and recommend W-4 adjustments to avoid underpayment or overpayment
- [ ] **Retirement planning integration** — Roth conversion ladders, RMD calculations, backdoor Roth optimization

### Long-Term Vision
- [ ] **Full consultancy mode** — Proactive AI tax advisor that monitors your financial activity and suggests actions throughout the year
- [ ] **Audit preparation** — Organized documentation, red flag detection, and IRS correspondence drafting
- [ ] **Business tax support** — Schedule C, LLC, S-Corp, partnership returns
- [ ] **International tax** — Foreign income, FBAR, Form 8938, tax treaty benefits
- [ ] **Multi-year tax optimization** — Income shifting, Roth conversion strategies, capital gain timing across tax years
- [ ] **Browser automation for filing** — Automated entry into FreeTaxUSA, TurboTax, and IRS Direct File
- [ ] **Community tax rules engine** — Crowdsourced, version-controlled tax rules that stay up to date with IRS changes

### Completed
- [x] Tax wizard interview flow
- [x] W-2, 1099-INT, 1099-DIV, 1099-B, 1099-R, 1099-MISC, 1099-NEC parsing
- [x] Federal tax computation (single filer, standard deduction)
- [x] Capital gains/losses (Form 8949, Schedule D)
- [x] Crypto tax support with FIFO lot matching
- [x] Backdoor Roth IRA (Form 8606)
- [x] Excess Social Security tax (multiple employers)
- [x] FreeTaxUSA CSV export and browser automation
- [x] Tax reviewer with sanity checks and deduction finder
- [x] Self-improvement learnings system

## Contributing

Contributions welcome! Please read [DISCLAIMER.md](DISCLAIMER.md) and ensure any tax calculations are verified against IRS publications.

## Support

If you find Open Tax helpful, consider [sponsoring the project](https://github.com/sponsors/tugberkgoc).

## License

[MIT](LICENSE) -- see [DISCLAIMER.md](DISCLAIMER.md) for tax-specific legal notices.
