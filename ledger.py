"""
ledger.py
A local, tamper-evident SHA-256 hash-linked ledger prototype.

IMPORTANT WORDING: this is a "Tamper-Evident / DLT-inspired local ledger
prototype" — it is NOT Hyperledger Fabric, not a permissioned blockchain,
and not connected to any real chain. A production deployment could
migrate this layer to a real permissioned DLT; this module demonstrates
the integrity-verification concept only.
"""
import hashlib
import json

import pandas as pd


def _payload_for_row(r) -> dict:
    """Extended payload (section 25): includes entity types, crypto and
    NFT fields alongside the original bank fields, with graceful
    handling of missing values."""
    return {
        "tx_id": r.tx_id,
        "timestamp": str(r.timestamp),
        "source": r.source_entity,
        "source_type": r.source_type,
        "destination": r.destination_entity,
        "destination_type": r.destination_type,
        "amount": float(r.amount) if pd.notna(r.amount) else 0.0,
        "currency": r.currency if pd.notna(r.currency) else "INR",
        "crypto_asset": r.crypto_asset if pd.notna(r.crypto_asset) else None,
        "crypto_amount": float(r.crypto_amount) if pd.notna(r.crypto_amount) else None,
        "nft_id": r.nft_id if pd.notna(r.nft_id) else None,
        "transaction_type": r.transaction_type if pd.notna(r.transaction_type) else None,
    }


def build_ledger(df: pd.DataFrame) -> list:
    """Build a hash-linked chain of blocks over the (filtered) transaction
    set, in timestamp order."""
    prev = "GENESIS"
    ledger = []
    for _, r in df.sort_values("timestamp").iterrows():
        payload = _payload_for_row(r)
        block = {"previous_hash": prev, "transaction": payload}
        block_hash = hashlib.sha256(json.dumps(block, sort_keys=True).encode()).hexdigest()
        block["hash"] = block_hash
        ledger.append(block)
        prev = block_hash
    return ledger


def verify_ledger(ledger: list) -> bool:
    """Recompute each block's hash and confirm the chain of
    previous_hash references is unbroken."""
    check_prev = "GENESIS"
    for b in ledger:
        expected = hashlib.sha256(
            json.dumps({"previous_hash": b["previous_hash"], "transaction": b["transaction"]},
                       sort_keys=True).encode()
        ).hexdigest()
        if b["previous_hash"] != check_prev or expected != b["hash"]:
            return False
        check_prev = b["hash"]
    return True
