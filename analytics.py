"""
analytics.py
Temporal / velocity feature calculations, chain (path) detection across
banks + crypto + NFT entities, and the weighted risk-scoring engine for
GraphLedger.

Kept separate from app.py so the detection logic is unit-testable and
app.py stays focused on the Streamlit UI.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

# ----------------------------------------------------------------------
# Configurable time windows (section 18 — exposed as sliders in the UI)
# ----------------------------------------------------------------------
DEFAULT_RAPID_HOP_SECONDS = 180
DEFAULT_CRYPTO_RAPID_HOP_SECONDS = 180
DEFAULT_NFT_RAPID_TRADE_SECONDS = 300
DEFAULT_VELOCITY_WINDOW_SECONDS = 300
DEFAULT_CROSS_DOMAIN_WINDOW_SECONDS = 600
DEFAULT_MAX_CHAIN_HOPS = 8

ENTITY_DOMAIN = {
    "BANK": "FIAT", "BANK_ACCOUNT": "FIAT",
    "CRYPTO_EXCHANGE": "CRYPTO", "CRYPTO_WALLET": "CRYPTO",
    "NFT_MARKETPLACE": "NFT", "NFT_ASSET": "NFT",
}

REQUIRED_COLUMNS = [
    "tx_id", "timestamp", "chain_id", "scenario", "transaction_type", "asset_type",
    "source_entity", "source_type", "source_bank",
    "destination_entity", "destination_type", "destination_bank",
    "currency", "amount", "amount_inr",
    "crypto_asset", "crypto_amount", "crypto_price_inr",
    "nft_id", "nft_collection", "nft_marketplace", "nft_sale_price_inr",
    "channel", "parent_tx_id", "block_reference",
]


# ----------------------------------------------------------------------
# Section 30 — backward compatibility with the old bank-only schema
# ----------------------------------------------------------------------
def normalize_transactions(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure every expected column exists, filling sensible defaults so
    an older (bank-only) CSV never crashes the new app."""
    d = df.copy()

    # Old schema used source_account / destination_account directly.
    if "source_entity" not in d.columns and "source_account" in d.columns:
        d["source_entity"] = d["source_account"]
    if "destination_entity" not in d.columns and "destination_account" in d.columns:
        d["destination_entity"] = d["destination_account"]

    for col in REQUIRED_COLUMNS:
        if col not in d.columns:
            d[col] = None

    d["source_type"] = d["source_type"].fillna("BANK_ACCOUNT")
    d["destination_type"] = d["destination_type"].fillna("BANK_ACCOUNT")
    d["asset_type"] = d["asset_type"].fillna("FIAT")
    d["transaction_type"] = d["transaction_type"].fillna("fiat_transfer")
    d["currency"] = d["currency"].fillna("INR")
    d["amount"] = pd.to_numeric(d["amount"], errors="coerce").fillna(0.0)
    d["amount_inr"] = pd.to_numeric(d["amount_inr"], errors="coerce")
    d["amount_inr"] = d["amount_inr"].fillna(d["amount"])
    d["scenario"] = d["scenario"].fillna("normal")
    d["timestamp"] = pd.to_datetime(d["timestamp"], errors="coerce")
    d = d.dropna(subset=["timestamp", "source_entity", "destination_entity"])
    return d


# ----------------------------------------------------------------------
# Reusable time / velocity helpers (section 5 & 6)
# ----------------------------------------------------------------------
def calculate_time_delta(t1: pd.Timestamp, t2: pd.Timestamp) -> float:
    """Seconds between two timestamps (t2 - t1), always >= 0 for valid chains."""
    return max((t2 - t1).total_seconds(), 0.0)


def calculate_transaction_velocity(count: int, window_seconds: float) -> float:
    """Transactions per minute for a given count within a time window."""
    if window_seconds <= 0:
        return float(count)
    return count / (window_seconds / 60.0)


def calculate_amount_velocity(total_value: float, duration_seconds: float) -> float:
    """Value moved per second. Guards against divide-by-zero for
    same-timestamp / single-transaction chains."""
    if duration_seconds <= 0:
        return float(total_value)
    return total_value / duration_seconds


# ----------------------------------------------------------------------
# Chain (path) object
# ----------------------------------------------------------------------
@dataclass
class TemporalChain:
    chain_id: str
    tx_ids: list = field(default_factory=list)
    entities: list = field(default_factory=list)     # ordered path of entity IDs
    entity_types: list = field(default_factory=list)  # ordered path of entity types
    domains: set = field(default_factory=set)          # {"FIAT","CRYPTO","NFT"}
    start_time: pd.Timestamp = None
    end_time: pd.Timestamp = None
    starting_value_inr: float = 0.0
    ending_value_inr: float = 0.0
    total_value_inr: float = 0.0
    hop_amounts_inr: list = field(default_factory=list)
    nft_ids: set = field(default_factory=set)
    assets: set = field(default_factory=set)
    scenario_labels: set = field(default_factory=set)

    @property
    def duration_seconds(self) -> float:
        if self.start_time is None or self.end_time is None:
            return 0.0
        return calculate_time_delta(self.start_time, self.end_time)

    @property
    def hop_count(self) -> int:
        return len(self.tx_ids)

    @property
    def entity_count(self) -> int:
        return len(set(self.entities))

    @property
    def bank_count(self) -> int:
        return len({e for e, t in zip(self.entities, self.entity_types) if t in ("BANK", "BANK_ACCOUNT")})

    @property
    def wallet_count(self) -> int:
        return len({e for e, t in zip(self.entities, self.entity_types) if t == "CRYPTO_WALLET"})

    @property
    def exchange_count(self) -> int:
        return len({e for e, t in zip(self.entities, self.entity_types) if t == "CRYPTO_EXCHANGE"})

    @property
    def retention_percent(self) -> float:
        if self.starting_value_inr <= 0:
            return 100.0
        return round((self.ending_value_inr / self.starting_value_inr) * 100, 1)

    @property
    def loss_percent(self) -> float:
        return round(100 - self.retention_percent, 1)

    @property
    def value_velocity_inr_per_sec(self) -> float:
        return round(calculate_amount_velocity(self.total_value_inr, self.duration_seconds), 2)

    @property
    def transaction_velocity_per_min(self) -> float:
        return round(calculate_transaction_velocity(self.hop_count, self.duration_seconds), 2)

    @property
    def crosses_domain(self) -> bool:
        return len(self.domains) >= 2

    @property
    def is_circular(self) -> bool:
        return len(self.entities) >= 2 and self.entities[0] == self.entities[-1]

    @property
    def path_str(self) -> str:
        return " → ".join(self.entities)


# ----------------------------------------------------------------------
# find_temporal_chain / find_cross_entity_chain (section 5)
# ----------------------------------------------------------------------
def find_temporal_chain(df: pd.DataFrame, start_tx_row, max_gap_seconds: float,
                         max_hops: int = DEFAULT_MAX_CHAIN_HOPS) -> TemporalChain:
    """Follow destination(A) -> source(B) links forward in time, as long as
    each hop starts within max_gap_seconds of the previous hop ending.
    Works across any entity type (bank account, wallet, exchange, NFT
    marketplace) — this is what makes it a *cross-entity* chain too."""
    d = df.sort_values("timestamp")
    chain = TemporalChain(chain_id=f"path_{start_tx_row.tx_id}")

    current = start_tx_row
    visited_tx = set()
    while current is not None and len(chain.tx_ids) < max_hops:
        if current.tx_id in visited_tx:
            break
        visited_tx.add(current.tx_id)

        if chain.start_time is None:
            chain.start_time = current.timestamp
            chain.entities.append(current.source_entity)
            chain.entity_types.append(current.source_type)
            chain.starting_value_inr = current.amount_inr or 0.0

        chain.tx_ids.append(current.tx_id)
        chain.entities.append(current.destination_entity)
        chain.entity_types.append(current.destination_type)
        chain.end_time = current.timestamp
        chain.ending_value_inr = current.amount_inr or 0.0
        chain.total_value_inr += current.amount_inr or 0.0
        chain.hop_amounts_inr.append(current.amount_inr or 0.0)
        chain.domains.add(ENTITY_DOMAIN.get(current.source_type, "FIAT"))
        chain.domains.add(ENTITY_DOMAIN.get(current.destination_type, "FIAT"))
        if pd.notna(current.nft_id):
            chain.nft_ids.add(current.nft_id)
        if pd.notna(current.crypto_asset):
            chain.assets.add(current.crypto_asset)
        if pd.notna(current.scenario):
            chain.scenario_labels.add(current.scenario)

        # find the next hop: a transaction that starts at current's destination,
        # within max_gap_seconds after current's timestamp.
        window_end = current.timestamp + pd.Timedelta(seconds=max_gap_seconds)
        candidates = d[
            (d.source_entity == current.destination_entity)
            & (d.timestamp > current.timestamp)
            & (d.timestamp <= window_end)
            & (~d.tx_id.isin(visited_tx))
        ]
        current = candidates.iloc[0] if len(candidates) else None

    return chain


def find_cross_entity_chain(df: pd.DataFrame, start_tx_row,
                             window_seconds: float = DEFAULT_CROSS_DOMAIN_WINDOW_SECONDS,
                             max_hops: int = DEFAULT_MAX_CHAIN_HOPS) -> TemporalChain:
    """Same traversal as find_temporal_chain but with the wider window
    typically used for cross-domain (bank -> crypto -> NFT) correlation."""
    return find_temporal_chain(df, start_tx_row, window_seconds, max_hops)


# ----------------------------------------------------------------------
# Alert object
# ----------------------------------------------------------------------
def make_alert(alert_type, severity, score, entity, path, reason, chain: TemporalChain,
               evidence=None):
    return {
        "type": alert_type,
        "severity": severity,
        "score": score,
        "entity": entity,
        "path": path,
        "reason": reason,
        "start_time": chain.start_time,
        "end_time": chain.end_time,
        "duration_seconds": round(chain.duration_seconds, 1),
        "hop_count": chain.hop_count,
        "amount_inr": round(chain.total_value_inr, 2),
        "assets": ", ".join(sorted(chain.assets)) if chain.assets else "INR",
        "value_velocity": chain.value_velocity_inr_per_sec,
        "retention_percent": chain.retention_percent,
        "evidence": chain.tx_ids,
    }


# ----------------------------------------------------------------------
# Detection rules (section 16), grouped by domain (section 33)
# ----------------------------------------------------------------------
def detect_bank_patterns(df: pd.DataFrame, rapid_hop_seconds=DEFAULT_RAPID_HOP_SECONDS):
    """Rapid cross-bank hops, multi-hop layering, repeated incoming (smurfing)."""
    alerts = []
    bank_df = df[df.source_type == "BANK_ACCOUNT"]

    for _, r in bank_df.iterrows():
        chain = find_temporal_chain(df, r, rapid_hop_seconds)
        stays_in_banking = all(t == "BANK_ACCOUNT" for t in chain.entity_types)
        if chain.hop_count >= 2 and chain.bank_count >= 2 and stays_in_banking:
            alerts.append(make_alert(
                "Cross-bank velocity chain", "HIGH" if chain.hop_count >= 3 else "MEDIUM",
                min(15, 5 * chain.hop_count), chain.entities[0], chain.path_str,
                f"{chain.hop_count}-hop cross-bank movement across {chain.bank_count} institutions "
                f"in {chain.duration_seconds:.0f} seconds. {chain.retention_percent}% of the original "
                f"amount remained in the chain.",
                chain,
            ))

    # Repeated incoming activity / smurfing signal.
    counts = bank_df.groupby(["destination_type", "destination_entity"]).size().reset_index(name="count")
    for _, r in counts[counts["count"] >= 4].iterrows():
        sub = bank_df[bank_df.destination_entity == r.destination_entity]
        chain = TemporalChain(chain_id=f"smurf_{r.destination_entity}")
        chain.entities = [r.destination_entity]
        chain.entity_types = [r.destination_type]
        chain.start_time = sub.timestamp.min()
        chain.end_time = sub.timestamp.max()
        chain.total_value_inr = sub.amount_inr.sum()
        chain.starting_value_inr = chain.total_value_inr
        chain.ending_value_inr = chain.total_value_inr
        chain.tx_ids = sub.tx_id.tolist()
        alerts.append(make_alert(
            "Repeated incoming activity (smurfing signal)", "MEDIUM", 10,
            r.destination_entity, f"Multiple senders → {r.destination_entity}",
            f"{int(r['count'])} incoming transactions detected for this account in the dataset.",
            chain,
        ))
    return alerts


def detect_crypto_patterns(df: pd.DataFrame, rapid_hop_seconds=DEFAULT_CRYPTO_RAPID_HOP_SECONDS):
    """Multi-wallet crypto velocity, and bank<->crypto exit/entry chains."""
    alerts = []
    wallet_df = df[df.source_type == "CRYPTO_WALLET"]

    for _, r in wallet_df.iterrows():
        chain = find_temporal_chain(df, r, rapid_hop_seconds)
        stays_in_crypto = all(t in ("CRYPTO_WALLET", "CRYPTO_EXCHANGE") for t in chain.entity_types)
        if chain.hop_count >= 2 and chain.wallet_count >= 2 and stays_in_crypto:
            alerts.append(make_alert(
                "Multi-wallet crypto velocity", "HIGH" if chain.hop_count >= 3 else "MEDIUM",
                min(15, 5 * chain.hop_count), chain.entities[0], chain.path_str,
                f"Rapid multi-wallet movement: {chain.hop_count} hops across {chain.wallet_count} "
                f"wallets in {chain.duration_seconds:.0f} seconds. "
                f"{chain.retention_percent}% of the original value remained in the chain.",
                chain,
            ))

    # Bank -> crypto -> bank exit/entry chains (wider window, crosses domain).
    bank_entry_df = df[df.source_type == "BANK_ACCOUNT"]
    for _, r in bank_entry_df.iterrows():
        chain = find_cross_entity_chain(df, r, DEFAULT_CROSS_DOMAIN_WINDOW_SECONDS)
        if chain.crosses_domain and "CRYPTO" in chain.domains and chain.hop_count >= 2:
            alerts.append(make_alert(
                "Bank-to-crypto movement", "HIGH", 12,
                chain.entities[0], chain.path_str,
                f"Value moved from banking into cryptocurrency infrastructure and back across "
                f"{chain.hop_count} hops in {chain.duration_seconds:.0f} seconds.",
                chain,
            ))
    return alerts


def detect_nft_patterns(df: pd.DataFrame, rapid_trade_seconds=DEFAULT_NFT_RAPID_TRADE_SECONDS):
    """Repeated NFT trading / wallet cycling and rapid price escalation."""
    alerts = []
    nft_df = df[df.nft_id.notna()].sort_values("timestamp")
    if nft_df.empty:
        return alerts

    for nft_id, grp in nft_df.groupby("nft_id"):
        grp = grp.sort_values("timestamp")
        if len(grp) < 2:
            continue
        prices = grp["nft_sale_price_inr"].fillna(grp["amount_inr"]).tolist()
        wallets = pd.unique(grp[["source_entity", "destination_entity"]].values.ravel())
        first_ts, last_ts = grp.timestamp.iloc[0], grp.timestamp.iloc[-1]
        duration = calculate_time_delta(first_ts, last_ts)

        is_cycling = len(set(wallets)) <= max(2, len(grp))
        price_escalated = len(prices) >= 2 and prices[-1] > prices[0] * 2

        chain = TemporalChain(chain_id=f"nft_{nft_id}")
        chain.entities = list(wallets)
        chain.entity_types = ["CRYPTO_WALLET"] * len(wallets)
        chain.start_time, chain.end_time = first_ts, last_ts
        chain.starting_value_inr = prices[0] if prices else 0
        chain.ending_value_inr = prices[-1] if prices else 0
        chain.total_value_inr = sum(prices)
        chain.tx_ids = grp.tx_id.tolist()
        chain.nft_ids = {nft_id}

        if duration <= rapid_trade_seconds and len(grp) >= 2:
            change_pct = round(((prices[-1] - prices[0]) / prices[0]) * 100, 1) if prices[0] else 0
            reason_bits = [f"{nft_id} traded {len(grp)} times across {len(set(wallets))} wallets "
                            f"in {duration:.0f} seconds"]
            if price_escalated:
                reason_bits.append(f"price rose {change_pct}% across trades")
            if is_cycling:
                reason_bits.append("wallets involved repeat/cycle")
            alerts.append(make_alert(
                "Potential NFT wash-trading pattern" if (is_cycling and price_escalated)
                else "Rapid NFT price escalation across repeated trades",
                "HIGH", 10, nft_id, " → ".join(chain.entities),
                ". ".join(reason_bits) + ". This is a pattern signal, not confirmation of wash trading.",
                chain,
            ))
    return alerts


def detect_cross_ecosystem_patterns(df: pd.DataFrame,
                                     window_seconds=DEFAULT_CROSS_DOMAIN_WINDOW_SECONDS):
    """Chains that touch all three domains: FIAT, CRYPTO, and NFT."""
    alerts = []
    seeds = df[df.source_type == "BANK_ACCOUNT"]
    for _, r in seeds.iterrows():
        chain = find_cross_entity_chain(df, r, window_seconds, max_hops=10)
        if chain.domains >= {"FIAT", "CRYPTO", "NFT"}:
            alerts.append(make_alert(
                "Cross-ecosystem rapid movement", "HIGH", 15,
                chain.entities[0], chain.path_str,
                f"Value moved across banking, cryptocurrency and NFT entities within a "
                f"{chain.duration_seconds:.0f}-second window ({chain.hop_count} hops, "
                f"{chain.bank_count} bank(s), {chain.wallet_count} wallet(s)). "
                f"Retention: {chain.retention_percent}%.",
                chain,
            ))
    return alerts


def detect_circular_patterns(df: pd.DataFrame, window_seconds=DEFAULT_CROSS_DOMAIN_WINDOW_SECONDS):
    """Value that returns to its starting entity within the window."""
    alerts = []
    for _, r in df.iterrows():
        chain = find_temporal_chain(df, r, window_seconds, max_hops=6)
        if chain.is_circular and chain.hop_count >= 2:
            alerts.append(make_alert(
                "Circular transaction pattern", "MEDIUM", 8,
                chain.entities[0], chain.path_str,
                f"Value returned to its originating entity after {chain.hop_count} hops "
                f"in {chain.duration_seconds:.0f} seconds.",
                chain,
            ))
    return alerts


# ----------------------------------------------------------------------
# Weighted, explainable risk score (section 17)
# ----------------------------------------------------------------------
COMPONENT_CAPS = {
    "Temporal velocity": 20,
    "Cross-institution hops": 15,
    "Amount / value velocity": 15,
    "Multi-wallet movement": 15,
    "Cross-domain movement": 15,
    "NFT repeated trading": 10,
    "Circularity / repetition": 10,
}


def calculate_risk_score(alerts: list) -> dict:
    """Map raw alerts into the fixed weighted components above, cap each
    component, and sum for a deterministic 0-100 score with a breakdown."""
    buckets = {k: 0 for k in COMPONENT_CAPS}

    for a in alerts:
        t = a["type"]
        if t == "Cross-bank velocity chain":
            buckets["Temporal velocity"] += min(a["score"], 10)
            buckets["Cross-institution hops"] += min(a["hop_count"] * 3, 10)
        elif t == "Repeated incoming activity (smurfing signal)":
            buckets["Circularity / repetition"] += 6
        elif t == "Multi-wallet crypto velocity":
            buckets["Multi-wallet movement"] += min(a["score"], 15)
            buckets["Temporal velocity"] += 5
        elif t == "Bank-to-crypto movement":
            buckets["Cross-domain movement"] += 10
        elif "NFT" in t:
            buckets["NFT repeated trading"] += min(a["score"], 10)
        elif t == "Cross-ecosystem rapid movement":
            buckets["Cross-domain movement"] += 15
            buckets["Amount / value velocity"] += min(abs(a["value_velocity"]) / 50, 15)
        elif t == "Circular transaction pattern":
            buckets["Circularity / repetition"] += 8

    for k in buckets:
        buckets[k] = int(min(buckets[k], COMPONENT_CAPS[k]))

    total = min(sum(buckets.values()), 100)
    return {"breakdown": buckets, "total": total}


def run_all_detectors(df: pd.DataFrame, rapid_hop_seconds=DEFAULT_RAPID_HOP_SECONDS,
                       crypto_hop_seconds=DEFAULT_CRYPTO_RAPID_HOP_SECONDS,
                       nft_window_seconds=DEFAULT_NFT_RAPID_TRADE_SECONDS,
                       cross_domain_window_seconds=DEFAULT_CROSS_DOMAIN_WINDOW_SECONDS) -> list:
    """Run every detector and de-duplicate on (type, path)."""
    if df.empty:
        return []
    alerts = []
    alerts += detect_bank_patterns(df, rapid_hop_seconds)
    alerts += detect_crypto_patterns(df, crypto_hop_seconds)
    alerts += detect_nft_patterns(df, nft_window_seconds)
    alerts += detect_cross_ecosystem_patterns(df, cross_domain_window_seconds)
    alerts += detect_circular_patterns(df, cross_domain_window_seconds)

    seen, out = set(), []
    for a in alerts:
        key = (a["type"], a["path"])
        if key not in seen:
            seen.add(key)
            out.append(a)
    return out


def build_velocity_table(chain: TemporalChain, df: pd.DataFrame) -> pd.DataFrame:
    """Small time/amount velocity table for a chain, for the UI (section 24)."""
    sub = df[df.tx_id.isin(chain.tx_ids)].sort_values("timestamp")
    rows_out = []
    cumulative = 0.0
    prev_ts = None
    for _, r in sub.iterrows():
        elapsed = calculate_time_delta(prev_ts, r.timestamp) if prev_ts is not None else 0.0
        cumulative += r.amount_inr or 0.0
        rows_out.append({
            "Time": r.timestamp.strftime("%H:%M:%S"),
            "Transaction": f"{r.source_entity} → {r.destination_entity}",
            "Amount (₹)": round(r.amount_inr or 0.0, 2),
            "Elapsed (s)": round(elapsed, 1),
            "Cumulative (₹)": round(cumulative, 2),
        })
        prev_ts = r.timestamp
    return pd.DataFrame(rows_out)
