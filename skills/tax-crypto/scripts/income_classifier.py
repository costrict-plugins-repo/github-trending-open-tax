#!/usr/bin/env python3
"""
Classify non-sale crypto events as ordinary income for tax reporting.

Categorizes staking rewards, airdrops, mining income, and DeFi lending
interest into the appropriate tax schedules.

Usage:
    python3 income_classifier.py <parsed_data_dir> <output_dir>
"""

import json
import os
import sys
from datetime import datetime


def load_json(path):
    with open(path, 'r') as f:
        return json.load(f)


# Maps crypto income types to their tax reporting schedule
SCHEDULE_MAP = {
    "staking": {"schedule": "Schedule 1", "line": "8z", "description": "Staking rewards"},
    "airdrop": {"schedule": "Schedule 1", "line": "8z", "description": "Airdrop income"},
    "mining": {"schedule": "Schedule C", "line": "1", "description": "Mining income (business)"},
    "lending": {"schedule": "Schedule B", "line": "1", "description": "DeFi lending interest"},
    "other": {"schedule": "Schedule 1", "line": "8z", "description": "Other crypto income"},
}


def classify_income(parsed_dir):
    """Collect and classify all crypto income events."""
    events = []

    for filename in sorted(os.listdir(parsed_dir)):
        if not filename.endswith('.json'):
            continue
        data = load_json(os.path.join(parsed_dir, filename))
        inner = data.get("data", data)

        for item in inner.get("crypto_income", []):
            income_type = item.get("type", "other").lower()
            if income_type not in SCHEDULE_MAP:
                income_type = "other"

            schedule_info = SCHEDULE_MAP[income_type]
            fmv = item.get("fair_market_value_usd", 0)

            events.append({
                "type": income_type,
                "asset": item.get("asset", "UNKNOWN"),
                "amount_received": item.get("amount_received", 0),
                "fair_market_value_usd": fmv,
                "date_received": item.get("date_received"),
                "source": item.get("source", ""),
                "tax_schedule": schedule_info["schedule"],
                "tax_line": schedule_info["line"],
                "tax_description": schedule_info["description"],
            })

    return events


def summarize_by_type(events):
    """Group and total income by type."""
    summary = {}
    for event in events:
        t = event["type"]
        if t not in summary:
            summary[t] = {
                "count": 0,
                "total_fmv_usd": 0,
                "schedule": event["tax_schedule"],
                "line": event["tax_line"],
            }
        summary[t]["count"] += 1
        summary[t]["total_fmv_usd"] = round(
            summary[t]["total_fmv_usd"] + event["fair_market_value_usd"], 2
        )
    return summary


def summarize_by_asset(events):
    """Group and total income by asset."""
    summary = {}
    for event in events:
        asset = event["asset"]
        if asset not in summary:
            summary[asset] = {"count": 0, "total_amount": 0, "total_fmv_usd": 0}
        summary[asset]["count"] += 1
        summary[asset]["total_amount"] = round(
            summary[asset]["total_amount"] + event["amount_received"], 8
        )
        summary[asset]["total_fmv_usd"] = round(
            summary[asset]["total_fmv_usd"] + event["fair_market_value_usd"], 2
        )
    return summary


def main():
    if len(sys.argv) < 3:
        print("Usage: python3 income_classifier.py <parsed_data_dir> <output_dir>", file=sys.stderr)
        sys.exit(1)

    parsed_dir = sys.argv[1]
    output_dir = sys.argv[2]

    events = classify_income(parsed_dir)
    total_income = round(sum(e["fair_market_value_usd"] for e in events), 2)

    # Determine if any mining income should be Schedule C vs hobby
    mining_events = [e for e in events if e["type"] == "mining"]
    mining_total = round(sum(e["fair_market_value_usd"] for e in mining_events), 2)

    result = {
        "computed_at": datetime.now().isoformat(),
        "total_crypto_income_usd": total_income,
        "event_count": len(events),
        "events": events,
        "by_type": summarize_by_type(events),
        "by_asset": summarize_by_asset(events),
    }

    if mining_total > 0:
        result["mining_note"] = (
            f"Mining income of ${mining_total:,.2f} detected. "
            "If mining is a business activity, report on Schedule C (self-employment tax applies). "
            "If hobby mining, report on Schedule 1 Line 8z (no SE tax). "
            "The classification depends on regularity, profit motive, and equipment investment."
        )

    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "crypto_income.json")

    with open(output_path, 'w') as f:
        json.dump(result, f, indent=2)

    print(json.dumps(result, indent=2))
    print(f"\nSaved to: {output_path}", file=sys.stderr)


if __name__ == '__main__':
    main()
