# Document Checklist by Tax Situation

## Always Needed
- Government-issued ID (for verification, not parsed)
- Prior year tax return (optional, for comparison)

## W-2 Employment
- [ ] W-2 from each employer
- Key fields: Box 1 (wages), Box 2 (federal tax withheld), Box 3 (SS wages), Box 4 (SS tax), Box 5 (Medicare wages), Box 6 (Medicare tax), Box 12 (retirement contributions, HSA), Box 17 (state tax withheld)

## Self-Employment (1099-NEC / 1099-MISC)
- [ ] 1099-NEC from each client (Box 1: nonemployee compensation)
- [ ] 1099-MISC if applicable (Box 3: other income, Box 7: nonemployee comp for pre-2020)
- [ ] Records of business expenses (for Schedule C)

## Investment Income
- [ ] 1099-B or consolidated brokerage statement (stock/bond/fund sales)
- [ ] 1099-DIV (dividends — Box 1a: ordinary, Box 1b: qualified, Box 2a: capital gain distributions)
- [ ] 1099-INT (interest — Box 1: interest income, Box 3: savings bond interest)

## Crypto / Digital Assets
- [ ] 1099-DA from exchanges (new for 2025 — gross proceeds, may not have cost basis)
- [ ] Exchange transaction export CSV (Coinbase, Kraken, Gemini, etc.)
- [ ] DeFi/DEX records (Phantom wallet, Solscan export for Solana)
- [ ] Staking rewards records (date received, FMV at receipt)
- [ ] Airdrop records (date received, FMV at receipt)
- Note: DeFi/DEX trades and staking will NOT have 1099-DA — user must provide records

## Deductions (if itemizing)
- [ ] State/local tax payments or property tax bills (for SALT)
- [ ] Mortgage interest statement (Form 1098)
- [ ] Charitable contribution receipts
- [ ] Medical expense records (only deductible above 7.5% AGI)

## Schedule 1-A (new for 2025, even with standard deduction)
- [ ] W-2 showing tip income (for tips exclusion)
- [ ] W-2 showing overtime (for overtime deduction)
- [ ] Auto loan statement for US-assembled vehicle (for auto loan interest deduction)

## Credits
- [ ] Dependent information (name, SSN, date of birth, relationship)
- [ ] Form 1098-T (tuition statement, for education credits)
- [ ] Form 5498 (IRA contributions, for Saver's Credit)
- [ ] Records of estimated tax payments (dates and amounts)

## File Formats Supported
- **PDF**: Text-based PDFs are best. Scanned/image PDFs work but may need verification.
- **Images**: JPG, PNG of tax forms (Claude can read these)
- **CSV**: Exchange exports (Coinbase, Kraken, Gemini, Phantom)
- **JSON**: Pre-formatted data from other tools
