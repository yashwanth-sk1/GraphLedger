# GraphLedger — Cross-Bank, Crypto & NFT Transaction Intelligence

**A working SIH26194 prototype** that follows the movement of value across
banks, cryptocurrency exchanges/wallets, and NFT marketplaces/assets as
**one unified temporal transaction graph** — not as isolated transactions.

> ⚠️ Everything here is synthetic. No real banking, cryptocurrency, or NFT
> data is used anywhere. Crypto/NFT prices are fixed synthetic demo
> valuations, not live market prices. The ledger is a local SHA-256
> hash-linked **prototype**, not a production blockchain or Hyperledger
> Fabric deployment.

## The story this prototype tells

A transaction can move from a bank account, to another bank, into a
crypto exchange, through several wallets, into an NFT marketplace,
through an NFT, back into crypto, and eventually back into the banking
system. GraphLedger connects these events into one temporal transaction
graph, measures transaction and value velocity at every hop, detects
suspicious cross-entity patterns, computes an explainable weighted risk
score, and preserves a tamper-evident record of the transaction history.

## IMPLEMENTED NOW

- **Unified cross-asset graph**: bank accounts, crypto exchanges, crypto
  wallets, NFT marketplaces and NFT assets as one connected NetworkX
  graph, rendered interactively with Plotly (color-coded by entity type,
  suspicious nodes highlighted).
- **Temporal chain detection** (`find_temporal_chain`, `find_cross_entity_chain`
  in `analytics.py`): follows destination→source links forward in time
  across *any* entity type, within a configurable time window, computing
  hop count, duration, entity/bank/wallet/exchange counts, retention %,
  and value velocity for every chain — not just a fixed 180-second
  same-domain check.
- **Transaction & value velocity** everywhere a chain is detected:
  transactions per minute, ₹ (or crypto) moved per second, computed via
  reusable helpers (`calculate_time_delta`, `calculate_transaction_velocity`,
  `calculate_amount_velocity`) rather than duplicated per rule.
- **Cross-bank layering detection**: multi-hop bank-only chains, reporting
  hop count, institutions crossed, elapsed time, and % of value retained.
- **Crypto multi-wallet velocity**: rapid wallet-to-wallet hops (BTC / ETH
  / USDT / USDC), with crypto-amount retention and wallet count.
- **Bank ↔ crypto movement**: chains that cross from banking into crypto
  infrastructure and (optionally) back.
- **Cross-ecosystem detection**: chains that touch all three domains
  (FIAT + CRYPTO + NFT) inside a configurable correlation window — the
  flagship "money moved through banks, crypto and an NFT sale" case.
- **NFT pattern detection**: repeated trading / wallet-cycling of the same
  NFT and rapid price escalation, labeled explicitly as a *pattern
  signal*, never as confirmed wash trading.
- **Circular transaction detection**: value that returns to its
  originating entity within the window.
- **Weighted, explainable 0–100 risk score** (`calculate_risk_score`):
  fixed, capped components (temporal velocity, cross-institution hops,
  value velocity, multi-wallet movement, cross-domain movement, NFT
  repeated trading, circularity), summed and shown as a breakdown — not
  an unbounded sum of ad-hoc points.
- **Configurable detection thresholds** exposed as sidebar sliders (rapid
  hop window, cross-domain correlation window, NFT rapid-trade window) —
  judges can change them live during the demo.
- **Six-tab UI**: Overview, Transaction Graph, Risk Alerts, Crypto & NFT
  Intelligence, Investigation, Ledger Verification.
- **Entity investigation panel**: incoming/outgoing value, connections,
  first/last seen, transaction velocity, value velocity, average
  interval, entity-linked risk score, and the connected transaction path
  with a per-hop time/amount velocity table.
- **Tamper-evident SHA-256 hash-linked ledger** (`ledger.py`), extended to
  carry entity types, crypto asset/amount, and NFT ID in its payload, with
  one-click build + verify.
- **"🚨 Simulate Suspicious Network"** button — injects a fresh 3-hop bank
  chain live for a strong closing demo beat.
- **Backward-compatible data loading** (`normalize_transactions`): an old
  bank-only CSV loads without crashing — missing columns get sensible
  defaults.
- **Synthetic dataset generator** (`generate_data.py`) covering 9 labeled
  scenarios: `normal`, `cross_bank_layering`, `smurfing`, `crypto_deposit`,
  `crypto_multi_wallet`, `bank_crypto_exit`, `nft_purchase`,
  `nft_price_escalation`, and the flagship `cross_ecosystem` chain.

## FUTURE ROADMAP (not implemented — say this out loud if asked)

- Migrate the hash-linked demo ledger to a real permissioned DLT
  (Hyperledger Fabric or a permissioned EVM chain).
- Replace the rule-based risk engine with a trained ML model / Graph
  Neural Network for anomaly detection.
- Real-time streaming ingestion instead of a static synthetic dataset.
- Real cross-institution privacy-preserving data sharing (hashing /
  commitments, potentially federated learning) so no raw PII ever needs
  to cross banks.
- Live crypto/NFT price feeds (today's prices are fixed synthetic demo
  values only).
- Graph algorithms beyond path-following: community detection for fraud
  rings, centrality measures for "hub" accounts.

**Never claimed as implemented:** real bank APIs, real crypto exchange
APIs, real NFT marketplace integration, a live blockchain, Hyperledger
Fabric, or a trained ML/AI model. The rule engine is explicitly a
"Rule-Based Graph Intelligence Prototype."

## Project structure

```
GraphLedger_Prototype/
├── app.py              # Streamlit UI — 6 tabs, filters, threshold sliders
├── analytics.py        # temporal/velocity helpers, chain detection, risk scoring
├── graph_utils.py       # unified cross-asset graph build + Plotly rendering
├── ledger.py             # SHA-256 hash-linked ledger (build + verify)
├── generate_data.py       # synthetic multi-domain dataset generator
├── requirements.txt
├── run.bat / run.sh         # one-command launch helpers
├── README.md                 # this file
├── CLAUDE.md                  # notes for Claude Code / AI pair-programming
├── AGENTS.md                    # same notes, tool-agnostic naming
├── DEMO_NOTES.txt                 # judge-facing talking points
└── data/
    └── demo_transactions.csv        # generated synthetic dataset
```

## Run it

```bash
pip install -r requirements.txt
python generate_data.py      # optional — app.py auto-generates if missing
streamlit run app.py
```

Windows: double-click `run.bat`. macOS/Linux: `bash run.sh`.

## Suggested demo flow (~4–5 minutes)

1. **Open the dashboard.** Point at the top metrics: banks, wallets,
   exchanges, NFT assets, transactions, alerts — "this is one unified
   view across three financial ecosystems, not three separate tools."
2. **Transaction Graph tab.** Show the color-coded legend (bank accounts,
   exchanges, wallets, NFT marketplaces, NFT assets) and the red
   suspicious nodes.
3. **Risk Alerts tab.** Open the "Cross-ecosystem rapid movement" alert —
   read out the path, duration, hop count, value velocity, and retention
   %. This is the strongest single alert in the dataset.
4. **Crypto & NFT Intelligence tab.** Show the crypto and NFT transaction
   tables and the synthetic price table (call out clearly: "synthetic
   demo valuations, not live prices").
5. **Investigation tab.** Pick a wallet from the multi-wallet chain, show
   its velocity numbers and the connected-path velocity table
   (time / amount / elapsed / cumulative).
6. **Ledger Verification tab.** Click "Build / Verify Ledger" — explain
   the hash chain and that a modified historical record breaks
   verification.
7. **Sidebar: move a threshold slider** (e.g. rapid-hop window) live and
   show an alert appear/disappear — "judges can test the detection logic
   themselves, right now."
8. **Simulate Suspicious Network button** for a live-injected pattern as
   the closing beat.

## Data & privacy note

All entities (banks, accounts, exchanges, wallets, NFT marketplaces, NFT
assets) and all transactions in `data/demo_transactions.csv` are
synthetic, generated by `generate_data.py` with a fixed random seed.
Nothing in this repository is derived from real personally identifiable
information, real account numbers, real wallet addresses, or real
transaction records.
# GraphLedger
