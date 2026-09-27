"""
generate_data.py
Builds the synthetic dataset for GraphLedger: Cross-Bank, Crypto & NFT
Transaction Intelligence.

Everything here is synthetic. Nothing is derived from real banking,
crypto, or NFT transaction data. Crypto/NFT prices are fixed synthetic
demo values, not live market prices.

Run directly, or it auto-runs from app.py if the CSV is missing:
    python generate_data.py
"""
import os
import random
from datetime import datetime, timedelta

import pandas as pd

random.seed(42)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)
OUT_PATH = os.path.join(DATA_DIR, "demo_transactions.csv")

# ----------------------------------------------------------------------
# Synthetic universe of entities
# ----------------------------------------------------------------------
BANKS = ["Axis Bank", "Yes Bank", "Bank of India", "ICICI Bank", "Canara Bank"]
BANK_ACCOUNTS = {
    "Axis Bank": ["AX_A01", "AX_A02", "AX_A03", "AX_A04"],
    "Yes Bank": ["YS_B01", "YS_B02", "YS_B03", "YS_B04"],
    "Bank of India": ["BOI_C01", "BOI_C02", "BOI_C03", "BOI_C04"],
    "ICICI Bank": ["IC_D01", "IC_D02", "IC_D03"],
    "Canara Bank": ["CN_E01", "CN_E02", "CN_E03"],
}

CRYPTO_EXCHANGES = ["ExchangeAlpha_Synthetic", "ExchangeBeta_Synthetic", "ExchangeGamma_Synthetic"]
CRYPTO_WALLETS = [f"WALLET_{i:04d}" for i in range(1, 21)]

# Fixed synthetic demo valuations (NOT live market prices).
CRYPTO_PRICES_INR = {
    "BTC": 5_200_000.0,
    "ETH": 310_000.0,
    "USDT": 92.0,
    "USDC": 91.5,
}

NFT_MARKETPLACES = ["MarketplaceOne_Synthetic", "MarketplaceTwo_Synthetic"]
NFT_COLLECTIONS = ["SyntheticApes", "PixelDeeds", "GhostGrid"]
NFT_ASSETS = [f"NFT_{i:03d}" for i in range(1, 11)]

CHANNEL = "UPI"

COLUMNS = [
    "tx_id", "timestamp", "chain_id", "scenario", "transaction_type", "asset_type",
    "source_entity", "source_type", "source_bank",
    "destination_entity", "destination_type", "destination_bank",
    "currency", "amount", "amount_inr",
    "crypto_asset", "crypto_amount", "crypto_price_inr",
    "nft_id", "nft_collection", "nft_marketplace", "nft_sale_price_inr",
    "channel", "parent_tx_id", "block_reference",
]

_tx_counter = 0


def _next_tx_id():
    global _tx_counter
    _tx_counter += 1
    return f"TX{_tx_counter:04d}"


def _row(ts, scenario, transaction_type, asset_type,
         source_entity, source_type, destination_entity, destination_type,
         currency="INR", amount=0.0, amount_inr=0.0,
         source_bank=None, destination_bank=None,
         crypto_asset=None, crypto_amount=None, crypto_price_inr=None,
         nft_id=None, nft_collection=None, nft_marketplace=None, nft_sale_price_inr=None,
         chain_id=None, parent_tx_id=None):
    return {
        "tx_id": _next_tx_id(),
        "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S"),
        "chain_id": chain_id,
        "scenario": scenario,
        "transaction_type": transaction_type,
        "asset_type": asset_type,
        "source_entity": source_entity, "source_type": source_type, "source_bank": source_bank,
        "destination_entity": destination_entity, "destination_type": destination_type,
        "destination_bank": destination_bank,
        "currency": currency, "amount": float(amount), "amount_inr": float(amount_inr),
        "crypto_asset": crypto_asset, "crypto_amount": crypto_amount, "crypto_price_inr": crypto_price_inr,
        "nft_id": nft_id, "nft_collection": nft_collection, "nft_marketplace": nft_marketplace,
        "nft_sale_price_inr": nft_sale_price_inr,
        "channel": CHANNEL, "parent_tx_id": parent_tx_id, "block_reference": None,
    }


rows = []
start = datetime(2026, 6, 14, 14, 0, 0)

# ------------------------------------------------------------------
# A. Normal background bank transactions
# ------------------------------------------------------------------
for i in range(24):
    sb = random.choice(BANKS)
    db = random.choice([b for b in BANKS if b != sb])
    sa = random.choice(BANK_ACCOUNTS[sb])
    da = random.choice(BANK_ACCOUNTS[db])
    amt = random.choice([500, 750, 1000, 1200, 1500, 2000, 2500, 3000, 4000, 5000, 7500, 10000])
    ts = start + timedelta(minutes=random.randint(0, 6 * 24 * 60))
    rows.append(_row(
        ts, "normal", "fiat_transfer", "FIAT",
        sa, "BANK_ACCOUNT", da, "BANK_ACCOUNT",
        currency="INR", amount=amt, amount_inr=amt,
        source_bank=sb, destination_bank=db,
    ))

# ------------------------------------------------------------------
# B. Cross-bank layering chain (4 hops, ~1 minute)
# ------------------------------------------------------------------
chain_id = "CHAIN_BANK_LAYERING_01"
t0 = datetime(2026, 6, 15, 16, 51, 0)
hops = [
    ("AX_A01", "Axis Bank", "YS_B01", "Yes Bank", 50000, 0),
    ("YS_B01", "Yes Bank", "BOI_C01", "Bank of India", 49000, 12),
    ("BOI_C01", "Bank of India", "IC_D01", "ICICI Bank", 48000, 23),
    ("IC_D01", "ICICI Bank", "CN_E01", "Canara Bank", 47000, 31),
]
prev_id = None
for sa, sb, da, db, amt, sec in hops:
    r = _row(
        t0 + timedelta(seconds=sec), "cross_bank_layering", "fiat_transfer", "FIAT",
        sa, "BANK_ACCOUNT", da, "BANK_ACCOUNT",
        currency="INR", amount=amt, amount_inr=amt,
        source_bank=sb, destination_bank=db,
        chain_id=chain_id, parent_tx_id=prev_id,
    )
    rows.append(r)
    prev_id = r["tx_id"]

# ------------------------------------------------------------------
# C. Smurfing pattern (fan-in)
# ------------------------------------------------------------------
smurf_t0 = datetime(2026, 6, 17, 11, 0, 0)
for k, amt in enumerate([18000, 17000, 16000, 15000]):
    rows.append(_row(
        smurf_t0 + timedelta(seconds=k), "smurfing", "fiat_transfer", "FIAT",
        f"AX_A0{2 + (k % 2)}", "BANK_ACCOUNT", "YS_B03", "BANK_ACCOUNT",
        currency="INR", amount=amt, amount_inr=amt,
        source_bank="Axis Bank", destination_bank="Yes Bank",
    ))

# ------------------------------------------------------------------
# D. Crypto deposit: bank -> exchange -> wallet
# ------------------------------------------------------------------
dep_t0 = datetime(2026, 6, 18, 9, 0, 0)
chain_id = "CHAIN_CRYPTO_DEPOSIT_01"
r1 = _row(
    dep_t0, "crypto_deposit", "fiat_to_crypto", "CRYPTO",
    "BOI_C02", "BANK_ACCOUNT", "ExchangeAlpha_Synthetic", "CRYPTO_EXCHANGE",
    currency="INR", amount=92000, amount_inr=92000,
    source_bank="Bank of India",
    crypto_asset="USDT", crypto_amount=1000.0, crypto_price_inr=CRYPTO_PRICES_INR["USDT"],
    chain_id=chain_id,
)
rows.append(r1)
r2 = _row(
    dep_t0 + timedelta(seconds=40), "crypto_deposit", "crypto_transfer", "CRYPTO",
    "ExchangeAlpha_Synthetic", "CRYPTO_EXCHANGE", "WALLET_0001", "CRYPTO_WALLET",
    currency="USDT", amount=1000.0, amount_inr=1000.0 * CRYPTO_PRICES_INR["USDT"],
    crypto_asset="USDT", crypto_amount=990.0, crypto_price_inr=CRYPTO_PRICES_INR["USDT"],
    chain_id=chain_id, parent_tx_id=r1["tx_id"],
)
rows.append(r2)

# ------------------------------------------------------------------
# E. Multi-wallet crypto velocity chain (ETH, 3 hops, <1 minute)
# ------------------------------------------------------------------
chain_id = "CHAIN_CRYPTO_MULTIWALLET_01"
wt0 = datetime(2026, 6, 18, 10, 0, 0)
eth_hops = [
    ("WALLET_0002", "WALLET_0003", 2.50, 0),
    ("WALLET_0003", "WALLET_0004", 2.45, 15),
    ("WALLET_0004", "WALLET_0005", 2.40, 31),
]
prev_id = None
for wa, wb, amt, sec in eth_hops:
    r = _row(
        wt0 + timedelta(seconds=sec), "crypto_multi_wallet", "crypto_transfer", "CRYPTO",
        wa, "CRYPTO_WALLET", wb, "CRYPTO_WALLET",
        currency="ETH", amount=amt, amount_inr=amt * CRYPTO_PRICES_INR["ETH"],
        crypto_asset="ETH", crypto_amount=amt, crypto_price_inr=CRYPTO_PRICES_INR["ETH"],
        chain_id=chain_id, parent_tx_id=prev_id,
    )
    rows.append(r)
    prev_id = r["tx_id"]

# ------------------------------------------------------------------
# F. Bank -> exchange -> wallet -> exchange -> bank (crypto exit)
# ------------------------------------------------------------------
chain_id = "CHAIN_BANK_CRYPTO_EXIT_01"
et0 = datetime(2026, 6, 19, 15, 30, 0)
seq = [
    ("IC_D02", "BANK_ACCOUNT", "ICICI Bank", "ExchangeBeta_Synthetic", "CRYPTO_EXCHANGE", None,
     "fiat_to_crypto", "FIAT", "INR", 60000, 60000, None, None, 0),
    ("ExchangeBeta_Synthetic", "CRYPTO_EXCHANGE", None, "WALLET_0006", "CRYPTO_WALLET", None,
     "crypto_transfer", "CRYPTO", "USDT", 640.0, 640.0 * CRYPTO_PRICES_INR["USDT"], "USDT", 640.0, 18),
    ("WALLET_0006", "CRYPTO_WALLET", None, "ExchangeGamma_Synthetic", "CRYPTO_EXCHANGE", None,
     "crypto_transfer", "CRYPTO", "USDT", 635.0, 635.0 * CRYPTO_PRICES_INR["USDT"], "USDT", 635.0, 33),
    ("ExchangeGamma_Synthetic", "CRYPTO_EXCHANGE", None, "CN_E02", "BANK_ACCOUNT", "Canara Bank",
     "crypto_to_fiat", "FIAT", "INR", 57000, 57000, None, None, 52),
]
prev_id = None
for sa, sty, sbank, da, dty, dbank, ttype, atype, cur, amt, amt_inr, casset, camt, sec in seq:
    r = _row(
        et0 + timedelta(seconds=sec), "bank_crypto_exit", ttype, atype,
        sa, sty, da, dty, currency=cur, amount=amt, amount_inr=amt_inr,
        source_bank=sbank, destination_bank=dbank,
        crypto_asset=casset, crypto_amount=camt,
        crypto_price_inr=CRYPTO_PRICES_INR.get(casset) if casset else None,
        chain_id=chain_id, parent_tx_id=prev_id,
    )
    rows.append(r)
    prev_id = r["tx_id"]

# ------------------------------------------------------------------
# G. NFT purchase (wallet -> marketplace -> NFT -> wallet)
# ------------------------------------------------------------------
chain_id = "CHAIN_NFT_PURCHASE_01"
nt0 = datetime(2026, 6, 20, 12, 0, 0)
r = _row(
    nt0, "nft_purchase", "nft_purchase", "NFT",
    "WALLET_0007", "CRYPTO_WALLET", "WALLET_0008", "CRYPTO_WALLET",
    currency="ETH", amount=0.4, amount_inr=0.4 * CRYPTO_PRICES_INR["ETH"],
    crypto_asset="ETH", crypto_amount=0.4, crypto_price_inr=CRYPTO_PRICES_INR["ETH"],
    nft_id="NFT_001", nft_collection="SyntheticApes", nft_marketplace="MarketplaceOne_Synthetic",
    nft_sale_price_inr=0.4 * CRYPTO_PRICES_INR["ETH"],
    chain_id=chain_id,
)
rows.append(r)

# ------------------------------------------------------------------
# H. NFT repeated trading / wash-trading-like pattern
#    Same NFT cycles between 3 connected wallets, rising price, short gaps
# ------------------------------------------------------------------
chain_id = "CHAIN_NFT_WASH_01"
wtime = datetime(2026, 6, 21, 18, 0, 0)
wash_hops = [
    ("WALLET_0009", "WALLET_0010", 10000, 0),
    ("WALLET_0010", "WALLET_0011", 50000, 20),
    ("WALLET_0011", "WALLET_0009", 150000, 45),
]
prev_id = None
for wa, wb, price, sec in wash_hops:
    r = _row(
        wtime + timedelta(seconds=sec), "nft_price_escalation", "nft_transfer", "NFT",
        wa, "CRYPTO_WALLET", wb, "CRYPTO_WALLET",
        currency="INR", amount=price, amount_inr=price,
        nft_id="NFT_002", nft_collection="PixelDeeds", nft_marketplace="MarketplaceTwo_Synthetic",
        nft_sale_price_inr=price,
        chain_id=chain_id, parent_tx_id=prev_id,
    )
    rows.append(r)
    prev_id = r["tx_id"]

# ------------------------------------------------------------------
# I. Flagship cross-ecosystem demo scenario:
#    Bank -> Bank -> Exchange -> Wallet -> Wallet -> Wallet ->
#    NFT Marketplace -> NFT -> Wallet -> Exchange -> Bank
# ------------------------------------------------------------------
chain_id = "CHAIN_CROSS_ECOSYSTEM_DEMO_01"
ct0 = datetime(2026, 6, 22, 9, 0, 0)
prev_id = None
step_defs = [
    dict(sec=0, ttype="fiat_transfer", atype="FIAT", sa="CN_E03", sty="BANK_ACCOUNT", sbank="Canara Bank",
         da="AX_A04", dty="BANK_ACCOUNT", dbank="Axis Bank", cur="INR", amt=100000, amt_inr=100000),
    dict(sec=14, ttype="fiat_to_crypto", atype="CRYPTO", sa="AX_A04", sty="BANK_ACCOUNT", sbank="Axis Bank",
         da="ExchangeAlpha_Synthetic", dty="CRYPTO_EXCHANGE", dbank=None, cur="INR", amt=98000, amt_inr=98000,
         casset="USDT", camt=98000 / CRYPTO_PRICES_INR["USDT"]),
    dict(sec=29, ttype="crypto_transfer", atype="CRYPTO", sa="ExchangeAlpha_Synthetic", sty="CRYPTO_EXCHANGE",
         sbank=None, da="WALLET_0012", dty="CRYPTO_WALLET", dbank=None, cur="USDT", amt=1030.0,
         amt_inr=1030.0 * CRYPTO_PRICES_INR["USDT"], casset="USDT", camt=1030.0),
    dict(sec=44, ttype="crypto_transfer", atype="CRYPTO", sa="WALLET_0012", sty="CRYPTO_WALLET", sbank=None,
         da="WALLET_0013", dty="CRYPTO_WALLET", dbank=None, cur="USDT", amt=1020.0,
         amt_inr=1020.0 * CRYPTO_PRICES_INR["USDT"], casset="USDT", camt=1020.0),
    dict(sec=59, ttype="crypto_transfer", atype="CRYPTO", sa="WALLET_0013", sty="CRYPTO_WALLET", sbank=None,
         da="WALLET_0014", dty="CRYPTO_WALLET", dbank=None, cur="USDT", amt=1010.0,
         amt_inr=1010.0 * CRYPTO_PRICES_INR["USDT"], casset="USDT", camt=1010.0),
    dict(sec=80, ttype="nft_purchase", atype="NFT", sa="WALLET_0014", sty="CRYPTO_WALLET", sbank=None,
         da="MarketplaceOne_Synthetic", dty="NFT_MARKETPLACE", dbank=None, cur="INR", amt=93000, amt_inr=93000,
         nft_id="NFT_003", nft_collection="GhostGrid", nft_mkt="MarketplaceOne_Synthetic", nft_price=93000),
    dict(sec=95, ttype="nft_transfer", atype="NFT", sa="MarketplaceOne_Synthetic", sty="NFT_MARKETPLACE",
         sbank=None, da="WALLET_0015", dty="CRYPTO_WALLET", dbank=None, cur="INR", amt=0, amt_inr=0,
         nft_id="NFT_003", nft_collection="GhostGrid", nft_mkt="MarketplaceOne_Synthetic"),
    dict(sec=110, ttype="crypto_transfer", atype="CRYPTO", sa="WALLET_0015", sty="CRYPTO_WALLET", sbank=None,
         da="ExchangeGamma_Synthetic", dty="CRYPTO_EXCHANGE", dbank=None, cur="USDT", amt=995.0,
         amt_inr=995.0 * CRYPTO_PRICES_INR["USDT"], casset="USDT", camt=995.0),
    dict(sec=133, ttype="crypto_to_fiat", atype="FIAT", sa="ExchangeGamma_Synthetic", sty="CRYPTO_EXCHANGE",
         sbank=None, da="BOI_C03", dty="BANK_ACCOUNT", dbank="Bank of India", cur="INR", amt=90600, amt_inr=90600),
]
for step in step_defs:
    r = _row(
        ct0 + timedelta(seconds=step["sec"]), "cross_ecosystem", step["ttype"], step["atype"],
        step["sa"], step["sty"], step["da"], step["dty"],
        currency=step["cur"], amount=step["amt"], amount_inr=step["amt_inr"],
        source_bank=step.get("sbank"), destination_bank=step.get("dbank"),
        crypto_asset=step.get("casset"), crypto_amount=step.get("camt"),
        crypto_price_inr=CRYPTO_PRICES_INR.get(step.get("casset")) if step.get("casset") else None,
        nft_id=step.get("nft_id"), nft_collection=step.get("nft_collection"),
        nft_marketplace=step.get("nft_mkt"), nft_sale_price_inr=step.get("nft_price"),
        chain_id=chain_id, parent_tx_id=prev_id,
    )
    rows.append(r)
    prev_id = r["tx_id"]

# ------------------------------------------------------------------
# Build, sort, save
# ------------------------------------------------------------------
df = pd.DataFrame(rows, columns=COLUMNS).sort_values("timestamp").reset_index(drop=True)
df.to_csv(OUT_PATH, index=False)

if __name__ == "__main__":
    print(f"Wrote {len(df)} synthetic transactions to {OUT_PATH}")
    print("Scenarios included:", sorted(df.scenario.unique().tolist()))
