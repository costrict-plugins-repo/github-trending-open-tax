#!/usr/bin/env python3
"""
Generate TurboTax or FreeTaxUSA CSV import files from computed tax data.

Usage:
    python3 generate_csv.py <computed_data_dir> <output_dir> --format turbotax
    python3 generate_csv.py <computed_data_dir> <output_dir> --format freetaxusa
"""

import argparse
import csv
import json
import os
import sys
from datetime import datetime


def load_json(path):
    with open(path, 'r') as f:
        return json.load(f)


def load_computed_data(computed_dir):
    """Load all computed JSON files and parsed tax data."""
    data = {}
    for name in ['tax_computation', 'se_tax', 'capital_gains', 'credits_and_final',
                  'crypto_lot_matching', 'crypto_income', 'final_tax_summary']:
        path = os.path.join(computed_dir, f'{name}.json')
        if os.path.exists(path):
            data[name] = load_json(path)

    # Also load parsed tax data for detailed per-employer/per-source breakdowns
    parsed_dir = os.path.join(os.path.dirname(computed_dir.rstrip(os.sep)), 'parsed')
    parsed_path = os.path.join(parsed_dir, 'tax_data.json')
    if os.path.exists(parsed_path):
        data['parsed_tax_data'] = load_json(parsed_path)

    return data


def generate_turbotax_csv(data, output_dir):
    """Generate TurboTax Online CSV import files."""
    os.makedirs(output_dir, exist_ok=True)

    # Income summary CSV
    tax = data.get('tax_computation', {})
    gross = tax.get('gross_income', {})

    income_rows = []
    if gross.get('wages', 0) > 0:
        income_rows.append(['W-2 Wages', f"{gross['wages']:.2f}"])
    if gross.get('self_employment', 0) > 0:
        income_rows.append(['Self-Employment Income', f"{gross['self_employment']:.2f}"])
    if gross.get('interest', 0) > 0:
        income_rows.append(['Interest Income', f"{gross['interest']:.2f}"])
    if gross.get('ordinary_dividends', 0) > 0:
        income_rows.append(['Ordinary Dividends', f"{gross['ordinary_dividends']:.2f}"])
    if gross.get('crypto_ordinary_income', 0) > 0:
        income_rows.append(['Crypto Ordinary Income', f"{gross['crypto_ordinary_income']:.2f}"])
    if gross.get('other', 0) > 0:
        income_rows.append(['Other Income', f"{gross['other']:.2f}"])

    income_path = os.path.join(output_dir, 'turbotax_income.csv')
    with open(income_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Category', 'Amount'])
        writer.writerows(income_rows)

    # Capital gains CSV (Form 8949 format for TurboTax)
    cap_gains = data.get('capital_gains', {})
    crypto_lots = data.get('crypto_lot_matching', {})

    all_transactions = []

    # From capital_gains computation
    # (These are summary-level; detailed transactions come from crypto lot matching)

    # From crypto lot matching
    for tx in crypto_lots.get('matched_transactions', []):
        all_transactions.append({
            'description': tx.get('description', ''),
            'date_acquired': tx.get('date_acquired', ''),
            'date_sold': tx.get('date_sold', ''),
            'proceeds': tx.get('proceeds', 0),
            'cost_basis': tx.get('cost_basis', 0),
            'adjustment_code': 'W' if tx.get('wash_sale_loss_disallowed', 0) > 0 else '',
            'adjustment_amount': tx.get('wash_sale_loss_disallowed', 0),
            'gain_loss': tx.get('gain_loss', 0),
        })

    if all_transactions:
        gains_path = os.path.join(output_dir, 'turbotax_gains.csv')
        with open(gains_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'Description', 'Date Acquired', 'Date Sold',
                'Proceeds', 'Cost Basis', 'Adjustment Code',
                'Adjustment Amount', 'Gain/Loss'
            ])
            for tx in all_transactions:
                writer.writerow([
                    tx['description'],
                    tx['date_acquired'] or '',
                    tx['date_sold'] or '',
                    f"{tx['proceeds']:.2f}",
                    f"{tx['cost_basis']:.2f}",
                    tx['adjustment_code'],
                    f"{tx['adjustment_amount']:.2f}" if tx['adjustment_amount'] else '',
                    f"{tx['gain_loss']:.2f}",
                ])

    # Summary CSV
    final = data.get('credits_and_final', {}).get('final_summary', {})
    summary_path = os.path.join(output_dir, 'turbotax_summary.csv')
    with open(summary_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Field', 'Value'])
        writer.writerow(['Filing Status', tax.get('filing_status', '')])
        writer.writerow(['AGI', f"{tax.get('agi', 0):.2f}"])
        writer.writerow(['Taxable Income', f"{tax.get('taxable_income', 0):.2f}"])
        writer.writerow(['Federal Income Tax', f"{final.get('federal_income_tax', 0):.2f}"])
        writer.writerow(['Total Tax', f"{final.get('total_tax_before_credits', 0):.2f}"])
        writer.writerow(['Total Credits', f"{final.get('nonrefundable_credits', 0) + final.get('refundable_credits', 0):.2f}"])
        writer.writerow(['Tax Withheld', f"{final.get('tax_withheld', 0):.2f}"])
        writer.writerow(['Amount Owed/Refund', f"{final.get('amount_owed_or_refund', 0):.2f}"])

    return [income_path, summary_path] + ([gains_path] if all_transactions else [])


def generate_freetaxusa_csv(data, output_dir):
    """Generate comprehensive FreeTaxUSA CSV import files.

    Reads from final_tax_summary.json and tax_data.json (parsed) to produce
    a complete CSV covering all income types, deductions, capital gains,
    withholding, and balance due/refund.
    """
    os.makedirs(output_dir, exist_ok=True)

    # Try to load final_tax_summary.json for the most complete data
    summary = data.get('final_tax_summary', {})
    parsed = data.get('parsed_tax_data', {})

    # Also fall back to intermediate computed files
    tax = data.get('tax_computation', {})
    gross_fallback = tax.get('gross_income', {})

    # Determine data sources
    gross = summary.get('gross_income', gross_fallback)
    adjustments = summary.get('adjustments_to_income', {})
    deductions = summary.get('deductions', parsed.get('deductions', {}))
    balance = summary.get('balance', {})
    payments = summary.get('payments_and_withholding', {})
    cap_detail = summary.get('capital_gains_detail', {})

    # --- Income CSV ---
    income_rows = [['section', 'field', 'source', 'amount']]

    # W-2 income (per employer from parsed data, or total from summary)
    w2_list = parsed.get('w2_income', [])
    if w2_list:
        for w2 in w2_list:
            employer = w2.get('employer', 'Employer')
            income_rows.append(['w2', 'wages', employer, f"{w2.get('wages', 0):.2f}"])
            income_rows.append(['w2', 'federal_withheld', employer, f"{w2.get('federal_withheld', 0):.2f}"])
            income_rows.append(['w2', 'ss_wages', employer, f"{w2.get('ss_wages', 0):.2f}"])
            income_rows.append(['w2', 'ss_tax_withheld', employer, f"{w2.get('ss_tax_withheld', 0):.2f}"])
            income_rows.append(['w2', 'medicare_wages', employer, f"{w2.get('medicare_wages', 0):.2f}"])
            income_rows.append(['w2', 'medicare_tax_withheld', employer, f"{w2.get('medicare_tax_withheld', 0):.2f}"])
            if w2.get('retirement_contributions', 0) > 0:
                income_rows.append(['w2', 'retirement_contributions', employer, f"{w2['retirement_contributions']:.2f}"])
            if w2.get('hsa_contributions', 0) > 0:
                income_rows.append(['w2', 'hsa_contributions', employer, f"{w2['hsa_contributions']:.2f}"])
    elif gross.get('w2_wages', gross.get('wages', 0)) > 0:
        wages = gross.get('w2_wages', gross.get('wages', 0))
        income_rows.append(['w2', 'wages', 'Total W-2 Wages', f"{wages:.2f}"])

    # Interest income
    for interest in parsed.get('interest_income', []):
        income_rows.append(['1099-INT', 'interest', interest.get('payer', 'Interest'), f"{interest.get('amount', 0):.2f}"])
    if not parsed.get('interest_income') and gross.get('interest_income', gross.get('interest', 0)) > 0:
        amt = gross.get('interest_income', gross.get('interest', 0))
        income_rows.append(['1099-INT', 'interest', 'Total Interest', f"{amt:.2f}"])

    # Dividend income
    for div in parsed.get('dividend_income', []):
        income_rows.append(['1099-DIV', 'ordinary_dividends', div.get('payer', 'Dividends'), f"{div.get('ordinary_dividends', 0):.2f}"])
        if div.get('qualified_dividends', 0) > 0:
            income_rows.append(['1099-DIV', 'qualified_dividends', div.get('payer', 'Dividends'), f"{div['qualified_dividends']:.2f}"])
    if not parsed.get('dividend_income') and gross.get('ordinary_dividends', 0) > 0:
        income_rows.append(['1099-DIV', 'ordinary_dividends', 'Total Dividends', f"{gross['ordinary_dividends']:.2f}"])

    # Capital gains summary
    if cap_detail:
        if cap_detail.get('short_term_gains_form_8949_box_A', 0) != 0:
            income_rows.append(['capital_gains', 'short_term_net', 'Form 8949 Box A',
                                f"{cap_detail['short_term_gains_form_8949_box_A']:.2f}"])
        if cap_detail.get('long_term_losses_form_8949_box_D', 0) != 0:
            income_rows.append(['capital_gains', 'long_term_net', 'Form 8949 Box D',
                                f"{cap_detail['long_term_losses_form_8949_box_D']:.2f}"])
        income_rows.append(['capital_gains', 'net_capital_gain', 'Schedule D Total',
                            f"{cap_detail.get('net_capital_gain', 0):.2f}"])

    # Crypto staking / ordinary income
    crypto_income = parsed.get('crypto_income', [])
    if crypto_income:
        total_staking = sum(c.get('fair_market_value_usd', 0) for c in crypto_income)
        income_rows.append(['other_income', 'crypto_staking_rewards', 'Schedule 1 Line 8z',
                            f"{total_staking:.2f}"])

    # Other income (1099-MISC, bonuses, etc.)
    for other in parsed.get('other_income', []):
        if other.get('type') == '1099-R':
            continue  # Handled separately via Form 8606
        income_rows.append(['other_income', other.get('type', 'other').lower(),
                            other.get('description', 'Other Income'),
                            f"{other.get('amount', 0):.2f}"])

    # IRA distribution (1099-R) — taxable amount only
    ira = parsed.get('ira_backdoor_roth', {})
    if ira.get('form_8606_required'):
        income_rows.append(['1099-R', 'gross_distribution', 'IRA Backdoor Roth Conversion',
                            f"{ira.get('conversion_amount', 0):.2f}"])
        income_rows.append(['1099-R', 'taxable_amount', 'IRA Backdoor Roth (Form 8606)',
                            f"{ira.get('taxable_conversion_amount', 0):.2f}"])

    income_path = os.path.join(output_dir, 'freetaxusa_income.csv')
    with open(income_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerows(income_rows)

    # --- Deductions & Adjustments CSV ---
    ded_rows = [['section', 'field', 'amount']]
    if adjustments.get('hsa_contributions_via_payroll', 0) > 0:
        ded_rows.append(['adjustment', 'hsa_contributions', f"{adjustments['hsa_contributions_via_payroll']:.2f}"])
    ded_rows.append(['deduction', 'method', deductions.get('method', 'standard')])
    std_ded = deductions.get('standard_deduction', summary.get('deductions', {}).get('standard_deduction', 0))
    if std_ded > 0:
        ded_rows.append(['deduction', 'standard_deduction', f"{std_ded:.2f}"])

    ded_path = os.path.join(output_dir, 'freetaxusa_deductions.csv')
    with open(ded_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerows(ded_rows)

    # --- Capital Gains Detail CSV (Form 8949 transactions) ---
    all_cap_tx = parsed.get('capital_transactions', [])
    crypto_lots = data.get('crypto_lot_matching', {})
    matched = crypto_lots.get('matched_transactions', [])
    all_cap_tx = all_cap_tx + matched

    gains_path = None
    if all_cap_tx:
        gains_path = os.path.join(output_dir, 'freetaxusa_gains.csv')
        with open(gains_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'Description of Property', 'Date Acquired', 'Date Sold',
                'Sales Price', 'Cost or Other Basis', 'Gain or Loss',
                'Holding Period', 'Form 8949 Box'
            ])
            for tx in all_cap_tx:
                writer.writerow([
                    tx.get('description', ''),
                    tx.get('date_acquired', '') or '',
                    tx.get('date_sold', '') or '',
                    f"{tx.get('proceeds', 0):.2f}",
                    f"{tx.get('cost_basis', 0):.2f}",
                    f"{tx.get('gain_loss', 0):.2f}",
                    tx.get('holding_period', ''),
                    tx.get('form_8949_box', ''),
                ])

    # --- Summary CSV ---
    summary_rows = [['field', 'value']]
    summary_rows.append(['filing_status', summary.get('filing_status', parsed.get('filing_status', ''))])
    summary_rows.append(['total_gross_income', f"{gross.get('total_gross_income', 0):.2f}"])
    summary_rows.append(['adjustments', f"{adjustments.get('total_adjustments', 0):.2f}"])
    summary_rows.append(['agi', f"{summary.get('adjusted_gross_income', 0):.2f}"])
    summary_rows.append(['taxable_income', f"{summary.get('taxable_income', 0):.2f}"])
    summary_rows.append(['federal_income_tax', f"{summary.get('tax_computation', {}).get('federal_income_tax', 0):.2f}"])
    summary_rows.append(['total_tax', f"{summary.get('total_tax', 0):.2f}"])
    summary_rows.append(['total_credits', f"{summary.get('credits', {}).get('total_credits', 0):.2f}"])
    summary_rows.append(['total_withheld', f"{payments.get('total_federal_withheld', 0):.2f}"])
    summary_rows.append(['total_payments', f"{payments.get('total_payments', 0):.2f}"])
    if balance.get('is_refund'):
        summary_rows.append(['refund', f"{abs(balance.get('amount_owed', 0)):.2f}"])
    else:
        summary_rows.append(['amount_owed', f"{balance.get('amount_owed', 0):.2f}"])
    summary_rows.append(['effective_tax_rate', f"{summary.get('effective_tax_rate_pct', 0):.2f}%"])
    summary_rows.append(['marginal_tax_rate', f"{summary.get('marginal_tax_rate_pct', 0)}%"])

    summary_path = os.path.join(output_dir, 'freetaxusa_summary.csv')
    with open(summary_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerows(summary_rows)

    paths = [income_path, ded_path, summary_path]
    if gains_path:
        paths.append(gains_path)
    return paths


def main():
    parser = argparse.ArgumentParser(description="Generate tax software CSV files")
    parser.add_argument("computed_dir", help="Directory with computed tax JSON files")
    parser.add_argument("output_dir", help="Directory to save CSV files")
    parser.add_argument("--format", choices=["turbotax", "freetaxusa"], default="turbotax",
                        help="Target software format (default: turbotax)")
    args = parser.parse_args()

    data = load_computed_data(args.computed_dir)

    if args.format == "turbotax":
        files = generate_turbotax_csv(data, args.output_dir)
    else:
        files = generate_freetaxusa_csv(data, args.output_dir)

    print(f"Generated {len(files)} CSV file(s):")
    for f in files:
        print(f"  {f}")


if __name__ == '__main__':
    main()
