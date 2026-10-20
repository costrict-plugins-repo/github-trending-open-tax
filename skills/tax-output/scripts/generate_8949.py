#!/usr/bin/env python3
"""
Generate Form 8949-formatted CSV from computed capital gains data.

Groups transactions by Form 8949 box (A-F for traditional assets,
G-L for digital assets) and produces summary totals for Schedule D.

Usage:
    python3 generate_8949.py <computed_data_dir> <output_dir>
"""

import csv
import json
import os
import sys
from datetime import datetime


def load_json(path):
    with open(path, 'r') as f:
        return json.load(f)


BOX_DESCRIPTIONS = {
    "A": "Short-term, basis reported to IRS",
    "B": "Short-term, basis NOT reported to IRS",
    "C": "Short-term, no 1099-B",
    "D": "Long-term, basis reported to IRS",
    "E": "Long-term, basis NOT reported to IRS",
    "F": "Long-term, no 1099-B",
    "G": "Short-term digital asset, basis reported",
    "H": "Short-term digital asset, basis NOT reported",
    "I": "Short-term digital asset, no 1099",
    "J": "Long-term digital asset, basis reported",
    "K": "Long-term digital asset, basis NOT reported",
    "L": "Long-term digital asset, no 1099",
}


def determine_box(tx):
    """Determine Form 8949 box for a transaction."""
    if tx.get("form_8949_box"):
        return tx["form_8949_box"]

    is_digital = tx.get("is_digital_asset", False)
    holding = tx.get("holding_period", "short")
    basis_reported = tx.get("basis_reported_to_irs", False)

    if is_digital:
        if holding == "short":
            return "G" if basis_reported else "H"
        else:
            return "J" if basis_reported else "K"
    else:
        if holding == "short":
            return "A" if basis_reported else "B"
        else:
            return "D" if basis_reported else "E"


def collect_all_transactions(data):
    """Collect transactions from all computed sources."""
    transactions = []

    # From crypto lot matching
    crypto = data.get("crypto_lot_matching", {})
    for tx in crypto.get("matched_transactions", []):
        transactions.append(tx)

    # From capital gains computation (non-crypto)
    cap = data.get("capital_gains", {})
    # capital_gains.json has summary data, not individual transactions
    # Individual non-crypto transactions would come from parsed data

    return transactions


def main():
    if len(sys.argv) < 3:
        print("Usage: python3 generate_8949.py <computed_data_dir> <output_dir>", file=sys.stderr)
        sys.exit(1)

    computed_dir = sys.argv[1]
    output_dir = sys.argv[2]

    data = {}
    for name in ['capital_gains', 'crypto_lot_matching', 'wash_sale_analysis']:
        path = os.path.join(computed_dir, f'{name}.json')
        if os.path.exists(path):
            data[name] = load_json(path)

    # Also check parsed dir for non-crypto capital transactions
    parsed_dir = os.path.join(os.path.dirname(computed_dir), 'parsed')
    if os.path.exists(parsed_dir):
        for filename in sorted(os.listdir(parsed_dir)):
            if not filename.endswith('.json'):
                continue
            parsed = load_json(os.path.join(parsed_dir, filename))
            inner = parsed.get("data", parsed)
            for tx in inner.get("capital_transactions", []):
                if not tx.get("is_digital_asset", False) and tx.get("cost_basis", 0) > 0:
                    if "non_crypto_transactions" not in data:
                        data["non_crypto_transactions"] = []
                    data["non_crypto_transactions"].append(tx)

    transactions = collect_all_transactions(data)
    transactions.extend(data.get("non_crypto_transactions", []))

    # Apply wash sale adjustments
    wash = data.get("wash_sale_analysis", {})
    wash_map = {}
    for flagged in wash.get("flagged_transactions", []):
        key = f"{flagged.get('description')}_{flagged.get('date_sold')}"
        wash_map[key] = flagged.get("disallowed_loss", 0)

    for tx in transactions:
        key = f"{tx.get('description')}_{tx.get('date_sold')}"
        if key in wash_map:
            tx["wash_sale_loss_disallowed"] = wash_map[key]
            tx["adjustment_code"] = "W"

    # Group by box
    by_box = {}
    for tx in transactions:
        box = determine_box(tx)
        if box not in by_box:
            by_box[box] = []
        by_box[box].append(tx)

    os.makedirs(output_dir, exist_ok=True)

    # Write per-box CSV files
    files_written = []
    schedule_d_summary = []

    for box in sorted(by_box.keys()):
        txs = by_box[box]
        filename = f"form_8949_box_{box}.csv"
        filepath = os.path.join(output_dir, filename)

        with open(filepath, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                '(a) Description of property',
                '(b) Date acquired',
                '(c) Date sold or disposed of',
                '(d) Proceeds (sales price)',
                '(e) Cost or other basis',
                '(f) Code(s) from instructions',
                '(g) Amount of adjustment',
                '(h) Gain or (loss)',
            ])
            total_proceeds = 0
            total_basis = 0
            total_adjustment = 0
            total_gain = 0

            for tx in txs:
                proceeds = tx.get('proceeds', 0)
                basis = tx.get('cost_basis', 0)
                wash_adj = tx.get('wash_sale_loss_disallowed', 0)
                adj_code = tx.get('adjustment_code', '')
                gain = tx.get('gain_loss', proceeds - basis)
                if wash_adj > 0:
                    gain += wash_adj  # Adjust for disallowed wash sale loss

                total_proceeds += proceeds
                total_basis += basis
                total_adjustment += wash_adj
                total_gain += gain

                writer.writerow([
                    tx.get('description', ''),
                    tx.get('date_acquired', '') or '',
                    tx.get('date_sold', '') or '',
                    f"{proceeds:.2f}",
                    f"{basis:.2f}",
                    adj_code,
                    f"{wash_adj:.2f}" if wash_adj > 0 else '',
                    f"{gain:.2f}",
                ])

            # Totals row
            writer.writerow([
                f'TOTALS — Box {box}: {BOX_DESCRIPTIONS.get(box, "")}',
                '', '',
                f"{total_proceeds:.2f}",
                f"{total_basis:.2f}",
                '',
                f"{total_adjustment:.2f}" if total_adjustment > 0 else '',
                f"{total_gain:.2f}",
            ])

        files_written.append(filepath)
        schedule_d_summary.append({
            "box": box,
            "description": BOX_DESCRIPTIONS.get(box, ""),
            "transaction_count": len(txs),
            "total_proceeds": round(total_proceeds, 2),
            "total_cost_basis": round(total_basis, 2),
            "total_adjustments": round(total_adjustment, 2),
            "total_gain_loss": round(total_gain, 2),
        })

    # Write Schedule D summary
    summary = {
        "generated_at": datetime.now().isoformat(),
        "total_transactions": len(transactions),
        "boxes": schedule_d_summary,
        "files": [os.path.basename(f) for f in files_written],
    }

    summary_path = os.path.join(output_dir, "form_8949_summary.json")
    with open(summary_path, 'w') as f:
        json.dump(summary, f, indent=2)

    print(json.dumps(summary, indent=2))
    print(f"\nGenerated {len(files_written)} Form 8949 CSV file(s)", file=sys.stderr)
    for fp in files_written:
        print(f"  {fp}", file=sys.stderr)


if __name__ == '__main__':
    main()
