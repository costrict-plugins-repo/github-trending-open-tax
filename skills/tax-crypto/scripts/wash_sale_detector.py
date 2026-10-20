#!/usr/bin/env python3
"""
Detect potential wash sales in crypto transactions.

Scans lot-matched transactions for repurchases of the same asset within
30 days before or after a loss sale. Flags affected transactions.

Note: Crypto wash sale rules are not yet codified in statute as of 2025,
but may apply under proposed legislation. This flags for review only.

Usage:
    python3 wash_sale_detector.py <computed_data_dir> <output_dir>
"""

import json
import os
import sys
from datetime import datetime, timedelta


def load_json(path):
    with open(path, 'r') as f:
        return json.load(f)


def parse_date(date_str):
    if not date_str or date_str == "VARIOUS":
        return None
    try:
        return datetime.strptime(date_str, '%Y-%m-%d')
    except (ValueError, TypeError):
        return None


def detect_wash_sales(matched_transactions, buy_lots_by_asset):
    """
    Check each loss sale for a repurchase of the same asset within 30 days
    before or after the sale date.
    """
    flagged = []

    for tx in matched_transactions:
        if tx.get("gain_loss", 0) >= 0:
            continue  # Only losses can be wash sales

        asset = tx.get("description", "").upper()
        # Extract asset name from description like "Sell 0.5 BTC"
        parts = asset.split()
        asset_name = parts[-1] if parts else "UNKNOWN"

        sale_date = parse_date(tx.get("date_sold"))
        if not sale_date:
            continue

        window_start = sale_date - timedelta(days=30)
        window_end = sale_date + timedelta(days=30)

        # Check for repurchases in the window
        buys_in_window = []
        lots = buy_lots_by_asset.get(asset_name, [])
        for lot in lots:
            lot_date = parse_date(lot.get("date_acquired") or lot.get("date"))
            if not lot_date:
                continue
            if window_start <= lot_date <= window_end and lot_date != sale_date:
                buys_in_window.append({
                    "date": lot_date.strftime('%Y-%m-%d'),
                    "quantity": lot.get("quantity", 0),
                })

        # Also check other sell transactions (which imply prior buys)
        for other_tx in matched_transactions:
            if other_tx is tx:
                continue
            other_asset = other_tx.get("description", "").upper().split()
            other_name = other_asset[-1] if other_asset else ""
            if other_name != asset_name:
                continue

            # Check lots_matched for buy dates in window
            for lot in other_tx.get("lots_matched", []):
                lot_date = parse_date(lot.get("date_acquired"))
                if not lot_date:
                    continue
                if window_start <= lot_date <= window_end and lot_date != sale_date:
                    buys_in_window.append({
                        "date": lot_date.strftime('%Y-%m-%d'),
                        "quantity": lot.get("quantity", 0),
                    })

        if buys_in_window:
            loss_amount = abs(tx["gain_loss"])
            flagged.append({
                "description": tx.get("description"),
                "date_sold": tx.get("date_sold"),
                "loss_amount": loss_amount,
                "disallowed_loss": loss_amount,  # Conservative: flag full loss
                "repurchases_in_window": buys_in_window,
                "note": "Potential wash sale — crypto wash sale rules are evolving. Review with tax professional.",
            })

    return flagged


def main():
    if len(sys.argv) < 3:
        print("Usage: python3 wash_sale_detector.py <computed_data_dir> <output_dir>", file=sys.stderr)
        sys.exit(1)

    computed_dir = sys.argv[1]
    output_dir = sys.argv[2]

    # Load lot-matched data
    lot_path = os.path.join(computed_dir, "crypto_lot_matching.json")
    if not os.path.exists(lot_path):
        print("No crypto_lot_matching.json found. Run lot_matching.py first.", file=sys.stderr)
        sys.exit(1)

    lot_data = load_json(lot_path)
    matched = lot_data.get("matched_transactions", [])
    remaining = lot_data.get("remaining_lots", {})

    # Build buy lots map for cross-referencing
    buy_lots_by_asset = {}
    for asset, lots in remaining.items():
        buy_lots_by_asset[asset.upper()] = lots

    # Also extract buy lots from matched transactions
    for tx in matched:
        parts = tx.get("description", "").upper().split()
        asset_name = parts[-1] if parts else "UNKNOWN"
        if asset_name not in buy_lots_by_asset:
            buy_lots_by_asset[asset_name] = []
        for lot in tx.get("lots_matched", []):
            buy_lots_by_asset[asset_name].append(lot)

    flagged = detect_wash_sales(matched, buy_lots_by_asset)

    result = {
        "computed_at": datetime.now().isoformat(),
        "wash_sales_detected": len(flagged),
        "flagged_transactions": flagged,
        "total_disallowed_loss": round(sum(f["disallowed_loss"] for f in flagged), 2),
        "disclaimer": (
            "Crypto wash sale rules are not yet explicitly codified in US tax law as of 2025. "
            "These flags are for informational purposes. Consult a tax professional."
        ),
    }

    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "wash_sale_analysis.json")

    with open(output_path, 'w') as f:
        json.dump(result, f, indent=2)

    print(json.dumps(result, indent=2))
    print(f"\nSaved to: {output_path}", file=sys.stderr)


if __name__ == '__main__':
    main()
