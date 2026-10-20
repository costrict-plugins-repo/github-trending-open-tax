# Contributing to Open Tax

Thanks for your interest in contributing! Open Tax aims to become a year-round financial assistant that helps everyone prepare and optimize their taxes with AI.

## How to Contribute

### Report Issues
- Found a tax calculation bug? Open an issue with the expected vs. actual result
- Include which IRS publication or form you're referencing
- Never include personal tax data in issues — use example numbers

### Add Features
Check the [Roadmap](README.md#roadmap) for ideas. Some great first contributions:

- **Add a new state** — Create `data/state-taxes/<state>.json` with brackets and rules
- **Add a broker format** — Add CSV/PDF parsing for Fidelity, Schwab, Vanguard, etc.
- **Add a filing status** — Extend compute_tax.py for MFJ, MFS, HoH, QSS
- **Add a deduction** — Implement Schedule A itemized deductions
- **Add a credit** — Implement education credits, EITC, etc.
- **Improve a skill** — Better interview questions, smarter deduction suggestions

### Code Standards

- **Python stdlib only** — No pip dependencies. This keeps installation frictionless.
- **All data flows through the schema** — See `skills/tax-data-ingest/assets/schema.json`
- **Tax reference data is separate from logic** — Rates and thresholds go in `data/*.json`, not hardcoded in scripts
- **Verify against IRS publications** — Every calculation must cite the relevant IRS form, publication, or revenue procedure
- **Test with realistic examples** — Use plausible but fictional tax scenarios

### Project Structure

```
open-tax/
├── .claude-plugin/         # Claude Code plugin manifest
├── skills/                 # Modular skills (each has SKILL.md + scripts/)
│   ├── tax-wizard/         # Main entry point — guided interview
│   ├── tax-data-ingest/    # Document parsing
│   ├── tax-calculator/     # Tax computation engine
│   ├── tax-crypto/         # Crypto-specific processing
│   ├── tax-output/         # Export generators
│   └── tax-reviewer/       # Sanity checks + deduction finder
├── data/                   # Tax reference tables (JSON) — update yearly
├── workspace/              # User's working directory (gitignored)
├── learnings/              # Edge cases and corrections log
└── agents/                 # Agent definitions (AGENTS.md compatible)
```

### Adding a New Skill

1. Create a directory under `skills/` (e.g., `skills/tax-planner/`)
2. Add a `SKILL.md` with YAML frontmatter:
   ```yaml
   ---
   name: tax-planner
   description: |
     Year-round tax planning and optimization suggestions.
   user-invocable: true
   allowed-tools: Bash, Read, Write
   ---
   ```
3. Add your scripts in `skills/tax-planner/scripts/`
4. Add reference docs in `skills/tax-planner/references/` if needed
5. Update the wizard to call your skill when appropriate

### Updating Tax Year Data

When a new tax year's numbers are released (usually in November via IRS Revenue Procedures):

1. Update `data/tax-tables-{year}.json` — Brackets, rates, SS wage base
2. Update `data/deductions-{year}.json` — Standard deduction amounts
3. Update `data/credits-{year}.json` — Credit amounts and phase-outs
4. Update `skills/tax-calculator/references/tax-rules-{year}.md`
5. Test against known IRS examples

### Privacy Rules

- **Never commit personal tax data** — The `workspace/` directory is gitignored
- **Use fictional examples** — If you need test data, use clearly fake names and numbers
- **Learnings must be generic** — Edge cases in `learnings/LEARNINGS.md` should describe the pattern, not specific user data

## Getting Help

- Open a [GitHub Discussion](https://github.com/tugberkgoc/open-tax/discussions) for questions
- Tag issues with `good-first-issue` for beginner-friendly tasks
- Check `learnings/LEARNINGS.md` for known edge cases and gotchas

## License

By contributing, you agree that your contributions will be licensed under the [MIT License](LICENSE).
