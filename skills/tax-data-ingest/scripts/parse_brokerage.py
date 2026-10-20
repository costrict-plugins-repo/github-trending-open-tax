#!/usr/bin/env python3
"""
Parse consolidated brokerage statement text into the Open Tax canonical JSON schema.

Handles combined 1099-B, 1099-DIV, 1099-INT data from major brokerages.

Usage:
    python3 parse_brokerage.py <input_file> <output_dir>
"""

import json
import os
import re
import sys
from datetime import datetime


def parse_currency(value_str):
    if not value_str:
        return 0.0
    cleaned = re.sub(r'[,$\s]', '', value_str.strip())
    # Handle parentheses for negative numbers: (123.45) -> -123.45
    if cleaned.startswith('(') and cleaned.endswith(')'):
        cleaned = '-' + cleaned[1:-1]
    try:
        return round(float(cleaned), 2)
    except ValueError:
        return 0.0


def parse_date(date_str):
    if not date_str:
        return None
    date_str = date_str.strip()
    if date_str.upper() == "VARIOUS":
        return "VARIOUS"
    for fmt in ('%m/%d/%Y', '%m/%d/%y', '%m-%d-%Y', '%Y-%m-%d', '%b %d, %Y'):
        try:
            return datetime.strptime(date_str, fmt).strftime('%Y-%m-%d')
        except ValueError:
            continue
    return date_str


def extract_transactions(text):
    """Extract 1099-B capital gain/loss transactions from brokerage text."""
    transactions = []

    # Pattern for transaction rows (varies by broker, this handles common formats)
    # Description | Date Acquired | Date Sold | Proceeds | Cost Basis | Gain/Loss
    patterns = [
        # Standard tabular format
        re.compile(
            r'(.{5,60}?)\s+'
            r'(\d{1,2}/\d{1,2}/\d{2,4}|VARIOUS)\s+'
            r'(\d{1,2}/\d{1,2}/\d{2,4})\s+'
            r'\$?([\d,]+\.?\d*)\s+'
            r'\$?([\d,]+\.?\d*)\s+'
            r'[\($]?([\d,]+\.?\d*)\)?',
            re.IGNORECASE
        ),
    ]

    for pattern in patterns:
        for match in pattern.finditer(text):
            desc = match.group(1).strip()
            date_acquired = parse_date(match.group(2))
            date_sold = parse_date(match.group(3))
            proceeds = parse_currency(match.group(4))
            cost_basis = parse_currency(match.group(5))
            gain_loss = parse_currency(match.group(6))

            # Determine if gain or loss from context
            if ')' in match.group(6) or '-' in match.group(6):
                gain_loss = -abs(gain_loss)

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
                "gain_loss": gain_loss,
                "holding_period": holding,
                "is_digital_asset": False,
                "basis_reported_to_irs": True,
                "wash_sale_loss_disallowed": 0,
            })

    return transactions


def extract_summary_totals(text):
    """Extract summary dividend and interest totals from brokerage statement."""
    dividends = {
        "payer": "Brokerage",
        "ordinary_dividends": 0,
        "qualified_dividends": 0,
        "capital_gain_distributions": 0,
        "federal_tax_withheld": 0,
        "foreign_tax_paid": 0,
    }
    interest = {
        "payer": "Brokerage",
        "amount": 0,
        "federal_tax_withheld": 0,
        "tax_exempt_interest": 0,
    }

    # Dividend patterns
    ord_match = re.search(
        r'(?:total\s+)?ordinary\s+dividends[^0-9]*?\$?([\d,]+\.?\d*)',
        text, re.IGNORECASE
    )
    if ord_match:
        dividends["ordinary_dividends"] = parse_currency(ord_match.group(1))

    qual_match = re.search(
        r'qualified\s+dividends[^0-9]*?\$?([\d,]+\.?\d*)',
        text, re.IGNORECASE
    )
    if qual_match:
        dividends["qualified_dividends"] = parse_currency(qual_match.group(1))

    cap_match = re.search(
        r'(?:total\s+)?capital\s+gain\s+distributions?[^0-9]*?\$?([\d,]+\.?\d*)',
        text, re.IGNORECASE
    )
    if cap_match:
        dividends["capital_gain_distributions"] = parse_currency(cap_match.group(1))

    # Interest pattern
    int_match = re.search(
        r'(?:total\s+)?(?:taxable\s+)?interest\s+income[^0-9]*?\$?([\d,]+\.?\d*)',
        text, re.IGNORECASE
    )
    if int_match:
        interest["amount"] = parse_currency(int_match.group(1))

    return dividends, interest


def main():
    if len(sys.argv) < 3:
        print("Usage: python3 parse_brokerage.py <input_file> <output_dir>", file=sys.stderr)
        sys.exit(1)

    input_file = sys.argv[1]
    output_dir = sys.argv[2]

    if input_file == '-':
        text = sys.stdin.read()
    else:
        with open(input_file, 'r') as f:
            text = f.read()

    transactions = extract_transactions(text)
    dividends, interest = extract_summary_totals(text)

    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_path = os.path.join(output_dir, f"brokerage_{timestamp}.json")

    data = {"capital_transactions": transactions}
    if dividends["ordinary_dividends"] > 0 or dividends["qualified_dividends"] > 0:
        data["dividend_income"] = [dividends]
    if interest["amount"] > 0:
        data["interest_income"] = [interest]

    output = {
        "source_type": "brokerage_statement",
        "source_file": input_file if input_file != '-' else "stdin",
        "parsed_at": datetime.now().isoformat(),
        "data": data,
        "transaction_count": len(transactions),
        "needs_verification": True,
        "verification_notes": "Please verify transaction counts and totals match your brokerage statement",
    }

    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2)

    print(json.dumps(output, indent=2))
    print(f"\nSaved to: {output_path}", file=sys.stderr)


if __name__ == '__main__':
    main()
