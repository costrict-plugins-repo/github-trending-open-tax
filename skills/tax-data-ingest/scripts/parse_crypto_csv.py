#!/usr/bin/env python3
"""
Parse crypto exchange CSV exports into the Open Tax canonical JSON schema.

Supports: Coinbase, Kraken, Gemini, Phantom/Solscan, and generic formats.

Usage:
    python3 parse_crypto_csv.py <csv_file> <output_dir> --exchange coinbase
    python3 parse_crypto_csv.py <csv_file> <output_dir> --exchange generic
"""

import argparse
import csv
import json
import os
import sys
from datetime import datetime


def parse_date(date_str):
    if not date_str:
        return None
    date_str = date_str.strip()
    for fmt in (
        '%Y-%m-%dT%H:%M:%SZ', '%Y-%m-%dT%H:%M:%S.%fZ',
        '%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M:%S UTC',
        '%Y-%m-%d', '%m/%d/%Y', '%m/%d/%Y %H:%M:%S',
        '%m-%d-%Y', '%b %d, %Y',
    ):
        try:
            return datetime.strptime(date_str, fmt).strftime('%Y-%m-%d')
        except ValueError:
            continue
    return date_str


def parse_float(val):
    if not val:
        return 0.0
    try:
        return round(float(str(val).replace(',', '').replace('$', '').strip()), 8)
    except (ValueError, TypeError):
        return 0.0


def classify_transaction(tx_type):
    """Classify a transaction type string into standard categories."""
    tx_type = (tx_type or "").lower().strip()

    trade_types = ["buy", "sell", "trade", "swap", "convert", "exchange"]
    income_types = ["staking", "reward", "interest", "earn", "airdrop", "fork",
                    "mining", "referral", "bonus", "cashback", "learning"]
    send_receive = ["send", "receive", "transfer", "deposit", "withdrawal"]

    for t in trade_types:
        if t in tx_type:
            return "trade"
    for t in income_types:
        if t in tx_type:
            return "income"
    for t in send_receive:
        if t in tx_type:
            return "transfer"
    return "unknown"


# --- Exchange-specific parsers ---

def parse_coinbase(rows):
    """Parse Coinbase transaction CSV."""
    transactions = []
    income_events = []

    for row in rows:
        tx_type = classify_transaction(row.get("Transaction Type", row.get("Type", "")))
        asset = row.get("Asset", row.get("Currency", ""))
        amount = parse_float(row.get("Quantity Transacted", row.get("Amount", 0)))
        usd_amount = parse_float(row.get("Spot Price at Transaction", row.get("USD Amount", 0)))
        total = parse_float(row.get("Total (inclusive of fees and/or spread)", row.get("Subtotal", 0)))
        fees = parse_float(row.get("Fees and/or Spread", row.get("Fees", 0)))
        timestamp = row.get("Timestamp", row.get("Date", ""))
        date = parse_date(timestamp)

        if tx_type == "trade":
            # Sells generate capital transactions
            if "sell" in row.get("Transaction Type", row.get("Type", "")).lower():
                transactions.append({
                    "description": f"Sell {amount} {asset}",
                    "date_sold": date,
                    "date_acquired": None,  # To be determined by lot matching
                    "proceeds": total if total else usd_amount * amount,
                    "cost_basis": 0,  # To be determined by lot matching
                    "is_digital_asset": True,
                    "basis_reported_to_irs": False,
                    "asset": asset,
                    "quantity": amount,
                })
        elif tx_type == "income":
            income_type = row.get("Transaction Type", row.get("Type", "")).lower()
            category = "staking"
            if "airdrop" in income_type:
                category = "airdrop"
            elif "mining" in income_type:
                category = "mining"
            elif "interest" in income_type or "earn" in income_type:
                category = "lending"

            income_events.append({
                "type": category,
                "asset": asset,
                "amount_received": amount,
                "fair_market_value_usd": total if total else usd_amount * amount,
                "date_received": date,
                "source": "Coinbase",
            })

    return transactions, income_events


def parse_kraken(rows):
    """Parse Kraken ledger CSV."""
    transactions = []
    income_events = []

    for row in rows:
        tx_type = classify_transaction(row.get("type", row.get("txtype", "")))
        asset = row.get("asset", row.get("pair", ""))
        amount = abs(parse_float(row.get("amount", 0)))
        fee = parse_float(row.get("fee", 0))
        timestamp = row.get("time", row.get("timestamp", ""))
        date = parse_date(timestamp)

        if tx_type == "trade":
            if parse_float(row.get("amount", 0)) < 0:  # Sell
                transactions.append({
                    "description": f"Sell {amount} {asset}",
                    "date_sold": date,
                    "date_acquired": None,
                    "proceeds": amount,
                    "cost_basis": 0,
                    "is_digital_asset": True,
                    "basis_reported_to_irs": False,
                    "asset": asset,
                    "quantity": amount,
                })
        elif tx_type == "income":
            income_events.append({
                "type": "staking",
                "asset": asset,
                "amount_received": amount,
                "fair_market_value_usd": 0,  # Kraken may not include USD value
                "date_received": date,
                "source": "Kraken",
            })

    return transactions, income_events


def parse_generic(rows):
    """Parse generic CSV with flexible column matching."""
    transactions = []
    income_events = []

    # Try to detect columns
    if not rows:
        return transactions, income_events

    headers = {k.lower().strip(): k for k in rows[0].keys()}

    def get_col(row, *candidates):
        for c in candidates:
            for h_lower, h_orig in headers.items():
                if c.lower() in h_lower:
                    val = row.get(h_orig, "")
                    if val:
                        return val
        return ""

    for row in rows:
        tx_type = classify_transaction(get_col(row, "type", "transaction", "action"))
        asset = get_col(row, "asset", "currency", "coin", "token", "symbol")
        amount = parse_float(get_col(row, "amount", "quantity", "qty", "volume"))
        usd = parse_float(get_col(row, "usd", "total", "value", "price", "fiat"))
        date = parse_date(get_col(row, "date", "time", "timestamp"))

        if tx_type == "trade":
            transactions.append({
                "description": f"Trade {amount} {asset}",
                "date_sold": date,
                "date_acquired": None,
                "proceeds": usd,
                "cost_basis": 0,
                "is_digital_asset": True,
                "basis_reported_to_irs": False,
                "asset": asset,
                "quantity": amount,
            })
        elif tx_type == "income":
            income_events.append({
                "type": "staking",
                "asset": asset,
                "amount_received": amount,
                "fair_market_value_usd": usd,
                "date_received": date,
                "source": "exchange",
            })

    return transactions, income_events


EXCHANGE_PARSERS = {
    "coinbase": parse_coinbase,
    "kraken": parse_kraken,
    "gemini": parse_generic,  # Gemini uses a similar format
    "phantom": parse_generic,
    "solscan": parse_generic,
    "generic": parse_generic,
}


def main():
    parser = argparse.ArgumentParser(description="Parse crypto exchange CSVs")
    parser.add_argument("csv_file", help="Path to CSV file")
    parser.add_argument("output_dir", help="Directory to save parsed JSON")
    parser.add_argument("--exchange", default="generic",
                        choices=EXCHANGE_PARSERS.keys(),
                        help="Exchange format (default: generic)")
    args = parser.parse_args()

    with open(args.csv_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    parse_fn = EXCHANGE_PARSERS[args.exchange]
    transactions, income_events = parse_fn(rows)

    os.makedirs(args.output_dir, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_path = os.path.join(args.output_dir, f"crypto_{args.exchange}_{timestamp}.json")

    output = {
        "source_type": f"crypto_csv_{args.exchange}",
        "source_file": args.csv_file,
        "parsed_at": datetime.now().isoformat(),
        "data": {
            "capital_transactions": transactions,
            "crypto_income": income_events,
        },
        "transaction_count": len(transactions),
        "income_event_count": len(income_events),
        "needs_verification": True,
        "verification_notes": (
            "Please verify transaction counts and amounts. "
            "Cost basis will be determined during lot matching phase (FIFO). "
            "DeFi/DEX transactions not on exchanges must be added manually."
        ),
    }

    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2)

    print(json.dumps(output, indent=2))
    print(f"\nSaved to: {output_path}", file=sys.stderr)
    print(f"Transactions: {len(transactions)}, Income events: {len(income_events)}", file=sys.stderr)


if __name__ == '__main__':
    main()
