#!/usr/bin/env python3
"""
Parse W-2 text data into the Open Tax canonical JSON schema.

Usage:
    python3 parse_w2.py <input_file> <output_dir>
    cat w2_text.txt | python3 parse_w2.py - <output_dir>

Input: Plain text extracted from a W-2 form (by Claude's Read tool on PDF/image).
Output: JSON file conforming to the Open Tax schema's w2_income format.
"""

import json
import os
import re
import sys
from datetime import datetime


def parse_currency(value_str):
    """Parse a currency string like '$85,000.00' or '85000' into a float."""
    if not value_str:
        return 0.0
    cleaned = re.sub(r'[,$\s]', '', value_str.strip())
    try:
        return round(float(cleaned), 2)
    except ValueError:
        return 0.0


def extract_w2_fields(text):
    """Extract W-2 box values from text. Handles common OCR/text patterns."""
    w2 = {
        "employer": "",
        "employer_ein": "",
        "wages": 0.0,
        "federal_withheld": 0.0,
        "ss_wages": 0.0,
        "ss_tax_withheld": 0.0,
        "medicare_wages": 0.0,
        "medicare_tax_withheld": 0.0,
        "tips": 0.0,
        "state": "",
        "state_wages": 0.0,
        "state_tax_withheld": 0.0,
        "retirement_contributions": 0.0,
        "hsa_contributions": 0.0,
    }

    # Employer name — look for patterns like "c Employer's name" or "Employer name:"
    emp_match = re.search(
        r"(?:employer'?s?\s+name[,:\s]+|^c\s+)([A-Z][A-Za-z0-9\s&.,'-]+?)(?:\n|$|\d{2}-)",
        text, re.MULTILINE | re.IGNORECASE
    )
    if emp_match:
        w2["employer"] = emp_match.group(1).strip()

    # EIN — pattern like 12-3456789
    ein_match = re.search(r'\b(\d{2}-\d{7})\b', text)
    if ein_match:
        w2["employer_ein"] = ein_match.group(1)

    # Box patterns: "Box 1" or "1 Wages" followed by amount
    box_patterns = {
        "wages": [
            r'(?:box\s*1|1\s*wages[^0-9]*?)[\s:]+\$?([\d,]+\.?\d*)',
            r'wages,?\s*tips,?\s*other\s*comp[^0-9]*?\$?([\d,]+\.?\d*)',
        ],
        "federal_withheld": [
            r'(?:box\s*2|2\s*federal\s*income\s*tax)[^0-9]*?\$?([\d,]+\.?\d*)',
            r'federal\s*income\s*tax\s*withheld[^0-9]*?\$?([\d,]+\.?\d*)',
        ],
        "ss_wages": [
            r'(?:box\s*3|3\s*social\s*security\s*wages)[^0-9]*?\$?([\d,]+\.?\d*)',
            r'social\s*security\s*wages[^0-9]*?\$?([\d,]+\.?\d*)',
        ],
        "ss_tax_withheld": [
            r'(?:box\s*4|4\s*social\s*security\s*tax)[^0-9]*?\$?([\d,]+\.?\d*)',
            r'social\s*security\s*tax\s*withheld[^0-9]*?\$?([\d,]+\.?\d*)',
        ],
        "medicare_wages": [
            r'(?:box\s*5|5\s*medicare\s*wages)[^0-9]*?\$?([\d,]+\.?\d*)',
            r'medicare\s*wages\s*(?:and\s*)?tips[^0-9]*?\$?([\d,]+\.?\d*)',
        ],
        "medicare_tax_withheld": [
            r'(?:box\s*6|6\s*medicare\s*tax)[^0-9]*?\$?([\d,]+\.?\d*)',
            r'medicare\s*tax\s*withheld[^0-9]*?\$?([\d,]+\.?\d*)',
        ],
        "tips": [
            r'(?:box\s*7|7\s*social\s*security\s*tips)[^0-9]*?\$?([\d,]+\.?\d*)',
            r'social\s*security\s*tips[^0-9]*?\$?([\d,]+\.?\d*)',
        ],
        "state_wages": [
            r'(?:box\s*16|16\s*state\s*wages)[^0-9]*?\$?([\d,]+\.?\d*)',
            r'state\s*wages[^0-9]*?\$?([\d,]+\.?\d*)',
        ],
        "state_tax_withheld": [
            r'(?:box\s*17|17\s*state\s*income\s*tax)[^0-9]*?\$?([\d,]+\.?\d*)',
            r'state\s*income\s*tax[^0-9]*?\$?([\d,]+\.?\d*)',
        ],
    }

    for field, patterns in box_patterns.items():
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                w2[field] = parse_currency(match.group(1))
                break

    # State abbreviation
    state_match = re.search(r'(?:box\s*15|15\s*state)\s*[:\s]*([A-Z]{2})\b', text, re.IGNORECASE)
    if state_match:
        w2["state"] = state_match.group(1).upper()

    # Box 12 — retirement contributions (codes D, E, G, AA, BB)
    box12_patterns = [
        r'(?:12[a-d]?\s*)?(?:code\s*)?([D|E|G]|AA|BB)\s+\$?([\d,]+\.?\d*)',
        r'(?:401|403|457|TSP)[^0-9]*?\$?([\d,]+\.?\d*)',
    ]
    retirement_total = 0.0
    for pattern in box12_patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            if match.lastindex >= 2:
                retirement_total += parse_currency(match.group(2))
            else:
                retirement_total += parse_currency(match.group(1))
    w2["retirement_contributions"] = retirement_total

    # Box 12 code W — HSA contributions
    hsa_match = re.search(r'(?:code\s*)?W\s+\$?([\d,]+\.?\d*)', text, re.IGNORECASE)
    if hsa_match:
        w2["hsa_contributions"] = parse_currency(hsa_match.group(1))

    return w2


def main():
    if len(sys.argv) < 3:
        print("Usage: python3 parse_w2.py <input_file> <output_dir>", file=sys.stderr)
        print("  Use '-' for input_file to read from stdin", file=sys.stderr)
        sys.exit(1)

    input_file = sys.argv[1]
    output_dir = sys.argv[2]

    # Read input
    if input_file == '-':
        text = sys.stdin.read()
    else:
        with open(input_file, 'r') as f:
            text = f.read()

    # Parse
    w2_data = extract_w2_fields(text)

    # Write output
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    employer_slug = re.sub(r'[^a-z0-9]', '_', w2_data["employer"].lower())[:30] or "unknown"
    output_path = os.path.join(output_dir, f"w2_{employer_slug}_{timestamp}.json")

    output = {
        "source_type": "w2",
        "source_file": input_file if input_file != '-' else "stdin",
        "parsed_at": datetime.now().isoformat(),
        "data": w2_data,
        "needs_verification": True,
        "verification_notes": "Please verify all amounts match your W-2 form"
    }

    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2)

    print(json.dumps(output, indent=2))
    print(f"\nSaved to: {output_path}", file=sys.stderr)


if __name__ == '__main__':
    main()
