#!/usr/bin/env python3
"""
FIFO lot matching for cryptocurrency transactions.

Builds per-asset lot pools from buy/receive events, matches sells against
oldest lots first, and computes cost basis and gain/loss for each disposal.

Usage:
    python3 lot_matching.py <parsed_data_dir> <output_dir>
"""

import json
import os
import sys
from datetime import datetime


def load_json(path):
    with open(path, 'r') as f:
        return json.load(f)


def parse_date(date_str):
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, '%Y-%m-%d')
    except (ValueError, TypeError):
        return None


def holding_period(acquired_date, sold_date):
    """Determine if holding period is short or long term."""
    if not acquired_date or not sold_date:
        return "short"
    acq = parse_date(acquired_date)
    sold = parse_date(sold_date)
    if not acq or not sold:
        return "short"
    delta = (sold - acq).days
    return "long" if delta > 365 else "short"


def form_8949_box(holding, basis_reported):
    """Determine Form 8949 box for digital assets."""
    if holding == "short":
        if basis_reported:
            return "G"
        return "H"
    else:
        if basis_reported:
            return "J"
        return "K"


def collect_transactions(parsed_dir):
    """Collect all crypto buy/sell/income transactions from parsed files."""
    buys = []   # [{asset, quantity, price_per_unit, date, source}]
    sells = []  # [{asset, quantity, proceeds, date, description}]

    for filename in sorted(os.listdir(parsed_dir)):
        if not filename.endswith('.json'):
            continue
        data = load_json(os.path.join(parsed_dir, filename))
        inner = data.get("data", data)

        for tx in inner.get("capital_transactions", []):
            if not tx.get("is_digital_asset", False):
                continue

            qty = tx.get("quantity", 0)
            if qty <= 0:
                continue

            # If cost_basis is already set and nonzero, this was pre-matched
            if tx.get("cost_basis", 0) > 0 and tx.get("gain_loss") is not None:
                continue

            sells.append({
                "asset": tx.get("asset", tx.get("description", "UNKNOWN")),
                "quantity": qty,
                "proceeds": tx.get("proceeds", 0),
                "date_sold": tx.get("date_sold"),
                "date_acquired": tx.get("date_acquired"),
                "description": tx.get("description", ""),
                "basis_reported_to_irs": tx.get("basis_reported_to_irs", False),
            })

        # Buys come from purchase events (not directly in schema, but inferred
        # from crypto CSV parsing where type=trade and it's a buy)
        # Also, income events create cost basis lots at FMV
        for inc in inner.get("crypto_income", []):
            fmv = inc.get("fair_market_value_usd", 0)
            amt = inc.get("amount_received", 0)
            if amt > 0:
                buys.append({
                    "asset": inc.get("asset", "UNKNOWN"),
                    "quantity": amt,
                    "price_per_unit": fmv / amt if amt > 0 else 0,
                    "total_cost": fmv,
                    "date": inc.get("date_received"),
                    "source": inc.get("source", "income"),
                })

    return buys, sells


def load_buy_lots(parsed_dir):
    """Load explicit buy lots from parsed data (from buy transactions in CSVs)."""
    lots = []

    for filename in sorted(os.listdir(parsed_dir)):
        if not filename.endswith('.json'):
            continue
        data = load_json(os.path.join(parsed_dir, filename))

        # Look for buy_lots array (produced by crypto CSV parser for buys)
        buy_lots = data.get("data", data).get("crypto_buy_lots", [])
        for lot in buy_lots:
            lots.append({
                "asset": lot.get("asset", "UNKNOWN"),
                "quantity": lot.get("quantity", 0),
                "price_per_unit": lot.get("price_per_unit", 0),
                "total_cost": lot.get("total_cost", 0),
                "date": lot.get("date"),
                "source": lot.get("source", "purchase"),
            })

    return lots


def fifo_match(buys, sells):
    """Apply FIFO lot matching: match sells against oldest buy lots per asset."""
    # Group buys by asset, sorted by date (oldest first = FIFO)
    lot_pools = {}
    for buy in buys:
        asset = buy["asset"].upper()
        if asset not in lot_pools:
            lot_pools[asset] = []
        lot_pools[asset].append({
            "quantity_remaining": buy["quantity"],
            "price_per_unit": buy.get("price_per_unit", 0),
            "total_cost": buy.get("total_cost", 0),
            "date": buy.get("date"),
            "source": buy.get("source", ""),
        })

    # Sort each pool by date (FIFO)
    for asset in lot_pools:
        lot_pools[asset].sort(key=lambda x: x["date"] or "0000-00-00")

    matched = []
    unmatched_sells = []

    for sell in sells:
        asset = sell["asset"].upper()
        pool = lot_pools.get(asset, [])
        qty_to_match = sell["quantity"]
        proceeds = sell["proceeds"]
        price_per_unit_sold = proceeds / qty_to_match if qty_to_match > 0 else 0

        total_cost_basis = 0
        lots_used = []
        earliest_acquired = None

        for lot in pool:
            if qty_to_match <= 0:
                break
            if lot["quantity_remaining"] <= 0:
                continue

            used = min(lot["quantity_remaining"], qty_to_match)
            if lot["total_cost"] > 0 and lot["quantity_remaining"] > 0:
                cost = (lot["total_cost"] / (lot["quantity_remaining"] + used - used)) * used
                # Simpler: use price_per_unit
                cost = lot["price_per_unit"] * used
            else:
                cost = lot["price_per_unit"] * used

            total_cost_basis += cost
            lot["quantity_remaining"] -= used
            qty_to_match -= used

            lots_used.append({
                "date_acquired": lot["date"],
                "quantity": round(used, 8),
                "cost": round(cost, 2),
            })

            if earliest_acquired is None or (lot["date"] and (earliest_acquired is None or lot["date"] < earliest_acquired)):
                earliest_acquired = lot["date"]

        total_cost_basis = round(total_cost_basis, 2)
        gain_loss = round(proceeds - total_cost_basis, 2)

        hp = holding_period(earliest_acquired, sell["date_sold"])
        box = form_8949_box(hp, sell.get("basis_reported_to_irs", False))

        tx = {
            "description": sell["description"],
            "date_acquired": earliest_acquired if len(lots_used) == 1 else "VARIOUS",
            "date_sold": sell["date_sold"],
            "proceeds": proceeds,
            "cost_basis": total_cost_basis,
            "gain_loss": gain_loss,
            "holding_period": hp,
            "is_digital_asset": True,
            "basis_reported_to_irs": sell.get("basis_reported_to_irs", False),
            "form_8949_box": box,
            "wash_sale_loss_disallowed": 0,
            "lots_matched": lots_used,
        }

        if qty_to_match > 0:
            tx["unmatched_quantity"] = round(qty_to_match, 8)
            tx["warning"] = f"Could not match {qty_to_match} units — missing buy lots"
            unmatched_sells.append(tx)

        matched.append(tx)

    # Remaining lots (unsold)
    remaining_lots = {}
    for asset, pool in lot_pools.items():
        remaining = [l for l in pool if l["quantity_remaining"] > 0]
        if remaining:
            remaining_lots[asset] = [{
                "quantity": round(l["quantity_remaining"], 8),
                "price_per_unit": l["price_per_unit"],
                "date_acquired": l["date"],
            } for l in remaining]

    return matched, remaining_lots, unmatched_sells


def main():
    if len(sys.argv) < 3:
        print("Usage: python3 lot_matching.py <parsed_data_dir> <output_dir>", file=sys.stderr)
        sys.exit(1)

    parsed_dir = sys.argv[1]
    output_dir = sys.argv[2]

    # Collect all buy and sell transactions
    income_lots, sells = collect_transactions(parsed_dir)
    purchase_lots = load_buy_lots(parsed_dir)
    all_buys = purchase_lots + income_lots

    if not sells:
        print("No crypto sell transactions found.", file=sys.stderr)
        result = {
            "computed_at": datetime.now().isoformat(),
            "method": "FIFO",
            "matched_transactions": [],
            "remaining_lots": {},
            "warnings": [],
            "total_proceeds": 0,
            "total_cost_basis": 0,
            "total_gain_loss": 0,
        }
    else:
        matched, remaining, unmatched = fifo_match(all_buys, sells)

        total_proceeds = round(sum(t["proceeds"] for t in matched), 2)
        total_basis = round(sum(t["cost_basis"] for t in matched), 2)
        total_gl = round(sum(t["gain_loss"] for t in matched), 2)

        warnings = []
        for t in unmatched:
            warnings.append(t.get("warning", "Unmatched sell transaction"))

        result = {
            "computed_at": datetime.now().isoformat(),
            "method": "FIFO",
            "matched_transactions": matched,
            "remaining_lots": remaining,
            "warnings": warnings,
            "summary": {
                "total_transactions": len(matched),
                "total_proceeds": total_proceeds,
                "total_cost_basis": total_basis,
                "total_gain_loss": total_gl,
                "short_term_gain": round(sum(t["gain_loss"] for t in matched if t["holding_period"] == "short"), 2),
                "long_term_gain": round(sum(t["gain_loss"] for t in matched if t["holding_period"] == "long"), 2),
                "unmatched_sells": len(unmatched),
            },
        }

    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "crypto_lot_matching.json")

    with open(output_path, 'w') as f:
        json.dump(result, f, indent=2)

    print(json.dumps(result, indent=2))
    print(f"\nSaved to: {output_path}", file=sys.stderr)


if __name__ == '__main__':
    main()
