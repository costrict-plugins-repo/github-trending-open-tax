# Exchange & Broker CSV Formats

## Coinbase

**Export path**: Coinbase.com > Taxes > Generate Tax Report > Download CSV

| Column | Description |
|--------|-------------|
| Timestamp | ISO 8601 format (2025-01-15T14:30:00Z) |
| Transaction Type | Buy, Sell, Send, Receive, Staking Income, Learning Reward, etc. |
| Asset | BTC, ETH, SOL, etc. |
| Quantity Transacted | Amount of crypto |
| Spot Price at Transaction | USD price per unit at time of transaction |
| Subtotal | USD value before fees |
| Total (inclusive of fees and/or spread) | USD value including fees |
| Fees and/or Spread | Fee amount in USD |
| Notes | Additional context |

## Kraken

**Export path**: Kraken.com > History > Export

| Column | Description |
|--------|-------------|
| txid | Transaction ID |
| refid | Reference ID |
| time | Timestamp (YYYY-MM-DD HH:MM:SS) |
| type | trade, deposit, withdrawal, staking, etc. |
| subtype | Additional type info |
| aclass | Asset class |
| asset | Asset code (XXBT = BTC, XETH = ETH) |
| amount | Transaction amount (negative = outflow) |
| fee | Fee amount |
| balance | Running balance |

## Gemini

**Export path**: Gemini.com > Account > Statements & History > Download

| Column | Description |
|--------|-------------|
| Date | MM/DD/YYYY HH:MM:SS format |
| Type | Buy, Sell, Credit, Debit |
| Symbol | Trading pair (BTCUSD, ETHUSD) |
| Specification | Market, Limit |
| Trading Fee (USD) | Fee in USD |
| USD Amount | USD value |
| BTC Amount (or asset) | Crypto amount |

## Phantom Wallet (Solana)

Phantom does not have a built-in CSV export. Users should use:
- **Step Finance** (step.finance) — connect wallet, export transactions
- **Solscan** (solscan.io) — search wallet address, export CSV

### Solscan CSV Format

| Column | Description |
|--------|-------------|
| Signature | Transaction signature/hash |
| Time | Unix timestamp or ISO format |
| Action | Transfer, Swap, Stake, etc. |
| From | Sender address |
| To | Receiver address |
| Amount | Token amount |
| Token | Token symbol or mint address |

## TurboTax Universal CSV Template

For importing crypto transactions into TurboTax:

| Column | Required | Description |
|--------|----------|-------------|
| Date | Yes | YYYY-MM-DD HH:mm:ss (UTC) |
| Type | Yes | Buy, Sell, Trade, Income, etc. |
| Sent Asset | Conditional | Asset sent |
| Sent Amount | Conditional | Amount sent |
| Sent Asset Market Value | Conditional | USD value of sent asset |
| Received Asset | Conditional | Asset received |
| Received Amount | Conditional | Amount received |
| Received Asset Market Value | Conditional | USD value of received asset |
| Fee Asset | Optional | Asset used for fee |
| Fee Amount | Optional | Fee amount |
| Fee Market Value | Optional | USD value of fee |
| Description | Optional | Free text |
| Transaction Hash | Optional | On-chain hash |
| Transaction ID | Optional | Exchange ID |

**Limit**: 2,250 transactions per file. For more, split into multiple files or use summary totals.
