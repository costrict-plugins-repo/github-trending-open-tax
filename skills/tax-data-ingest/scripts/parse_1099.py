#!/usr/bin/env python3
"""
Parse 1099 form text data into the Open Tax canonical JSON schema.

Supports: 1099-NEC, 1099-MISC, 1099-INT, 1099-DIV, 1099-B, 1099-DA

Usage:
    python3 parse_1099.py <input_file> <output_dir> --type NEC
    python3 parse_1099.py <input_file> <output_dir> --type DIV
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime


def parse_currency(value_str):
    if not value_str:
        return 0.0
    cleaned = re.sub(r'[,$\s]', '', value_str.strip())
    try:
        return round(float(cleaned), 2)
    except ValueError:
        return 0.0


def parse_date(date_str):
    """Try common date formats and return YYYY-MM-DD."""
    if not date_str:
        return None
    date_str = date_str.strip()
    for fmt in ('%m/%d/%Y', '%m-%d-%Y', '%Y-%m-%d', '%m/%d/%y', '%b %d, %Y'):
        try:
            return datetime.strptime(date_str, fmt).strftime('%Y-%m-%d')
        except ValueError:
            continue
    return date_str


def find_amount(text, *patterns):
    """Search for amount using multiple regex patterns."""
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return parse_currency(match.group(1))
    return 0.0


def parse_1099_nec(text):
    """Parse 1099-NEC: Nonemployee Compensation."""
    payer = ""
    payer_match = re.search(r"(?:payer'?s?\s*name[:\s]+)(.+?)(?:\n|$)", text, re.IGNORECASE)
    if payer_match:
        payer = payer_match.group(1).strip()

    compensation = find_amount(
        text,
        r'(?:box\s*1|1\s*nonemployee\s*compensation)[^0-9]*?\$?([\d,]+\.?\d*)',
        r'nonemployee\s*compensation[^0-9]*?\$?([\d,]+\.?\d*)',
    )

    federal_withheld = find_amount(
        text,
        r'(?:box\s*4|4\s*federal\s*income\s*tax)[^0-9]*?\$?([\d,]+\.?\d*)',
    )

    return {
        "source_type": "1099-NEC",
        "data": {
            "self_employment_income": [{
                "description": f"1099-NEC from {payer}" if payer else "1099-NEC income",
                "payer": payer,
                "form_type": "1099-NEC",
                "gross_income": compensation,
                "expenses": 0,
                "net_income": compensation,
            }]
        },
        "federal_withheld": federal_withheld,
    }


def parse_1099_misc(text):
    """Parse 1099-MISC."""
    payer = ""
    payer_match = re.search(r"(?:payer'?s?\s*name[:\s]+)(.+?)(?:\n|$)", text, re.IGNORECASE)
    if payer_match:
        payer = payer_match.group(1).strip()

    rents = find_amount(text, r'(?:box\s*1|1\s*rents)[^0-9]*?\$?([\d,]+\.?\d*)')
    royalties = find_amount(text, r'(?:box\s*2|2\s*royalties)[^0-9]*?\$?([\d,]+\.?\d*)')
    other_income = find_amount(text, r'(?:box\s*3|3\s*other\s*income)[^0-9]*?\$?([\d,]+\.?\d*)')
    fishing_boat = find_amount(text, r'(?:box\s*5|5\s*fishing\s*boat)[^0-9]*?\$?([\d,]+\.?\d*)')
    medical = find_amount(text, r'(?:box\s*6|6\s*medical)[^0-9]*?\$?([\d,]+\.?\d*)')
    nec = find_amount(text, r'(?:box\s*7|7\s*nonemployee)[^0-9]*?\$?([\d,]+\.?\d*)')

    data = {"other_income": []}
    if rents > 0:
        data["other_income"].append({"type": "rental", "description": f"Rents from {payer}", "amount": rents})
    if royalties > 0:
        data["other_income"].append({"type": "royalty", "description": f"Royalties from {payer}", "amount": royalties})
    if other_income > 0:
        data["other_income"].append({"type": "other", "description": f"Other income from {payer}", "amount": other_income})
    if nec > 0:
        data["self_employment_income"] = [{
            "description": f"1099-MISC Box 7 from {payer}",
            "payer": payer,
            "form_type": "1099-MISC",
            "gross_income": nec,
            "expenses": 0,
            "net_income": nec,
        }]

    return {"source_type": "1099-MISC", "data": data}


def parse_1099_int(text):
    """Parse 1099-INT: Interest Income."""
    payer = ""
    payer_match = re.search(r"(?:payer'?s?\s*name[:\s]+)(.+?)(?:\n|$)", text, re.IGNORECASE)
    if payer_match:
        payer = payer_match.group(1).strip()

    interest = find_amount(
        text,
        r'(?:box\s*1|1\s*interest\s*income)[^0-9]*?\$?([\d,]+\.?\d*)',
        r'interest\s*income[^0-9]*?\$?([\d,]+\.?\d*)',
    )
    savings_bond = find_amount(text, r'(?:box\s*3)[^0-9]*?\$?([\d,]+\.?\d*)')
    federal_withheld = find_amount(text, r'(?:box\s*4)[^0-9]*?\$?([\d,]+\.?\d*)')
    tax_exempt = find_amount(text, r'(?:box\s*8)[^0-9]*?\$?([\d,]+\.?\d*)')

    return {
        "source_type": "1099-INT",
        "data": {
            "interest_income": [{
                "payer": payer,
                "amount": interest,
                "us_savings_bond_interest": savings_bond,
                "federal_tax_withheld": federal_withheld,
                "tax_exempt_interest": tax_exempt,
            }]
        },
    }


def parse_1099_div(text):
    """Parse 1099-DIV: Dividends and Distributions."""
    payer = ""
    payer_match = re.search(r"(?:payer'?s?\s*name[:\s]+)(.+?)(?:\n|$)", text, re.IGNORECASE)
    if payer_match:
        payer = payer_match.group(1).strip()

    ordinary = find_amount(
        text,
        r'(?:box\s*1a|1a\s*total\s*ordinary)[^0-9]*?\$?([\d,]+\.?\d*)',
        r'total\s*ordinary\s*dividends[^0-9]*?\$?([\d,]+\.?\d*)',
    )
    qualified = find_amount(
        text,
        r'(?:box\s*1b|1b\s*qualified)[^0-9]*?\$?([\d,]+\.?\d*)',
        r'qualified\s*dividends[^0-9]*?\$?([\d,]+\.?\d*)',
    )
    cap_gains = find_amount(text, r'(?:box\s*2a|2a\s*total\s*capital\s*gain)[^0-9]*?\$?([\d,]+\.?\d*)')
    federal_withheld = find_amount(text, r'(?:box\s*4)[^0-9]*?\$?([\d,]+\.?\d*)')
    foreign_tax = find_amount(text, r'(?:box\s*7|7\s*foreign\s*tax)[^0-9]*?\$?([\d,]+\.?\d*)')

    return {
        "source_type": "1099-DIV",
        "data": {
            "dividend_income": [{
                "payer": payer,
                "ordinary_dividends": ordinary,
                "qualified_dividends": qualified,
                "capital_gain_distributions": cap_gains,
                "federal_tax_withheld": federal_withheld,
                "foreign_tax_paid": foreign_tax,
            }]
        },
    }


def parse_1099_b(text):
    """Parse 1099-B: Proceeds from Broker and Barter Exchange Transactions."""
    transactions = []
    # Look for tabular data: description, date acquired, date sold, proceeds, cost basis
    # This is a simplified parser — real brokerage PDFs vary widely
    row_pattern = re.compile(
        r'(.{5,50}?)\s+'
        r'(\d{1,2}/\d{1,2}/\d{2,4}|VARIOUS)\s+'
        r'(\d{1,2}/\d{1,2}/\d{2,4})\s+'
        r'\$?([\d,]+\.?\d*)\s+'
        r'\$?([\d,]+\.?\d*)',
        re.IGNORECASE
    )

    for match in row_pattern.finditer(text):
        desc = match.group(1).strip()
        date_acquired = parse_date(match.group(2))
        date_sold = parse_date(match.group(3))
        proceeds = parse_currency(match.group(4))
        cost_basis = parse_currency(match.group(5))

        # Determine holding period
        holding = "short"
        if date_acquired and date_acquired != "VARIOUS":
            try:
                acq = datetime.strptime(date_acquired, '%Y-%m-%d')
                sold = datetime.strptime(date_sold, '%Y-%m-%d')
                if (sold - acq).days > 365:
                    holding = "long"
            except (ValueError, TypeError):
                pass

        transactions.append({
            "description": desc,
            "date_acquired": date_acquired or "VARIOUS",
            "date_sold": date_sold,
            "proceeds": proceeds,
            "cost_basis": cost_basis,
            "gain_loss": round(proceeds - cost_basis, 2),
            "holding_period": holding,
            "is_digital_asset": False,
            "basis_reported_to_irs": True,
        })

    return {
        "source_type": "1099-B",
        "data": {"capital_transactions": transactions},
        "transaction_count": len(transactions),
    }


def parse_1099_da(text):
    """Parse 1099-DA: Digital Asset Proceeds (new for 2025)."""
    transactions = []

    # 1099-DA fields: Box 1a (description), 1b (date acquired), 1c (date sold),
    # 1d (proceeds), 1e (cost basis - may be blank for 2025), 1f (gain/loss)
    row_pattern = re.compile(
        r'(.{3,40}?)\s+'
        r'(\d{1,2}/\d{1,2}/\d{2,4}|VARIOUS|N/A)\s+'
        r'(\d{1,2}/\d{1,2}/\d{2,4})\s+'
        r'\$?([\d,]+\.?\d*)\s*'
        r'(?:\$?([\d,]+\.?\d*))?',
        re.IGNORECASE
    )

    for match in row_pattern.finditer(text):
        desc = match.group(1).strip()
        date_acquired = parse_date(match.group(2))
        date_sold = parse_date(match.group(3))
        proceeds = parse_currency(match.group(4))
        cost_basis = parse_currency(match.group(5)) if match.group(5) else 0.0

        holding = "short"
        if date_acquired and date_acquired not in ("VARIOUS", "N/A"):
            try:
                acq = datetime.strptime(date_acquired, '%Y-%m-%d')
                sold = datetime.strptime(date_sold, '%Y-%m-%d')
                if (sold - acq).days > 365:
                    holding = "long"
            except (ValueError, TypeError):
                pass

        transactions.append({
            "description": desc,
            "date_acquired": date_acquired or "VARIOUS",
            "date_sold": date_sold,
            "proceeds": proceeds,
            "cost_basis": cost_basis,
            "gain_loss": round(proceeds - cost_basis, 2) if cost_basis else None,
            "holding_period": holding,
            "is_digital_asset": True,
            "basis_reported_to_irs": cost_basis > 0,
            "form_8949_box": f"{'G' if holding == 'short' else 'J'}" if cost_basis > 0 else f"{'I' if holding == 'short' else 'L'}",
        })

    return {
        "source_type": "1099-DA",
        "data": {"capital_transactions": transactions},
        "transaction_count": len(transactions),
        "note": "For 2025, brokers may report gross proceeds only. Cost basis may need to be provided by the taxpayer.",
    }


PARSERS = {
    "NEC": parse_1099_nec,
    "MISC": parse_1099_misc,
    "INT": parse_1099_int,
    "DIV": parse_1099_div,
    "B": parse_1099_b,
    "DA": parse_1099_da,
}


def main():
    parser = argparse.ArgumentParser(description="Parse 1099 forms into Open Tax schema")
    parser.add_argument("input_file", help="Path to text file (use '-' for stdin)")
    parser.add_argument("output_dir", help="Directory to save parsed JSON")
    parser.add_argument("--type", required=True, choices=PARSERS.keys(),
                        help="1099 variant type")
    args = parser.parse_args()

    if args.input_file == '-':
        text = sys.stdin.read()
    else:
        with open(args.input_file, 'r') as f:
            text = f.read()

    result = PARSERS[args.type](text)

    os.makedirs(args.output_dir, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_path = os.path.join(args.output_dir, f"1099_{args.type.lower()}_{timestamp}.json")

    output = {
        **result,
        "source_file": args.input_file if args.input_file != '-' else "stdin",
        "parsed_at": datetime.now().isoformat(),
        "needs_verification": True,
        "verification_notes": f"Please verify all 1099-{args.type} amounts match your form",
    }

    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2)

    print(json.dumps(output, indent=2))
    print(f"\nSaved to: {output_path}", file=sys.stderr)


if __name__ == '__main__':
    main()
