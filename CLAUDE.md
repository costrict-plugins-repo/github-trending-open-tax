# Open Tax — Claude Code Instructions

## What This Is

Open Tax is a free, open-source tax preparation plugin for Claude Code. It guides users through US federal tax filing by ingesting their documents, computing taxes, and generating output for TurboTax/FreeTaxUSA.

**IMPORTANT**: This is a tax preparation aid, NOT professional tax advice. Always display the disclaimer from `DISCLAIMER.md` at the start of every tax session.

## On Any Tax-Related Query

When a user asks about taxes, tax filing, W-2, 1099, capital gains, deductions, refunds, TurboTax, FreeTaxUSA, or any tax-related topic — invoke the `/open-tax:tax-wizard` skill to guide them through the process.

## Project Layout

- `skills/` — Modular skills (wizard, ingest, calculator, crypto, output, reviewer)
- `data/` — Tax reference tables (brackets, deductions, credits) as JSON
- `workspace/` — User's working directory (raw docs, parsed data, computed results, output files)
- `learnings/LEARNINGS.md` — Self-improvement log (read at session start, update on corrections)
- `agents/tax-preparer.md` — Agent definition for autonomous tax preparation

## Self-Improvement Loop

1. **At session start**: Read `learnings/LEARNINGS.md` for prior corrections and edge cases
2. **During processing**: After each phase (ingest, compute, review), verify results with the user
3. **On any correction**: Append the correction to `learnings/LEARNINGS.md` with today's date, what went wrong, and how it was fixed
4. **At session end**: Consolidate and deduplicate entries in LEARNINGS.md

## Key Rules

- All Python scripts use **stdlib only** — no pip dependencies
- All data flows through the canonical schema at `skills/tax-data-ingest/assets/schema.json`
- User documents go in `workspace/raw/`, parsed data in `workspace/parsed/`, results in `workspace/computed/`, exports in `workspace/output/`
- Tax reference data lives in `data/*.json` — always read these for current rates/thresholds
- Default cost basis method for crypto: **FIFO** (First In, First Out)
- Scope: **US federal taxes only**, tax year 2025
