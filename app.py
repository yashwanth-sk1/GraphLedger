"""
GraphLedger — Cross-Bank, Crypto & NFT Transaction Intelligence
Rule-Based Graph Intelligence Prototype (synthetic demo only)

Run:
    pip install -r requirements.txt
    streamlit run app.py
"""
import os

import pandas as pd
import streamlit as st

import analytics as an
import graph_utils as gu
import ledger as lg

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, "data", "demo_transactions.csv")

st.set_page_config(page_title="GraphLedger", page_icon="🔐", layout="wide")

# ----------------------------------------------------------------------
# Styling
# ----------------------------------------------------------------------
st.markdown("""
<style>
.main-title {font-size: 36px; font-weight: 800; color:#123a63; margin-bottom:0;}
.sub {color:#5f6b76; font-size:16px; margin-top:2px;}
.pill {display:inline-block; padding:3px 10px; border-radius:999px; font-size:12px;
       font-weight:600; margin-right:6px; margin-bottom:6px;}
.pill-fiat {background:#e3edf7; color:#2d83bd;}
.pill-crypto {background:#f1e9fb; color:#7a4fd6;}
.pill-nft {background:#e4f6f3; color:#0f9d8c;}
.disclaimer {background:#fff8e6; border:1px solid #e8cf7a; border-radius:10px;
             padding:10px 14px; font-size:13px; color:#6b5a12;}
div[data-testid="stMetricValue"] {font-size: 24px;}
</style>
""", unsafe_allow_html=True)


@st.cache_data
def load_data():
    if not os.path.exists(DATA_PATH):
        import generate_data  # noqa: F401 — running the module writes the CSV
    raw = pd.read_csv(DATA_PATH)
    return an.normalize_transactions(raw)


df_all = load_data()

# ----------------------------------------------------------------------
# Header
# ----------------------------------------------------------------------
st.markdown('<div class="main-title">🔐 GraphLedger</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub">Cross-Bank, Cryptocurrency &amp; NFT Transaction Intelligence — '
    'Rule-Based Graph Intelligence Prototype</div>',
    unsafe_allow_html=True,
)
st.markdown(
    '<span class="pill pill-fiat">Bank Transfers</span>'
    '<span class="pill pill-crypto">Crypto Wallets &amp; Exchanges</span>'
    '<span class="pill pill-nft">NFT Marketplaces &amp; Assets</span>',
    unsafe_allow_html=True,
)
st.markdown(
    '<div class="disclaimer">⚠️ All entities, accounts, wallets, NFTs and prices in this '
    'prototype are <b>synthetic</b>. No real banking, cryptocurrency, or NFT data is used. '
    'Crypto/NFT valuations are fixed synthetic demo prices, not live market prices. The ledger '
    'below is a local SHA-256 hash-linked <b>prototype</b>, not a production blockchain.</div>',
    unsafe_allow_html=True,
)
st.write("")

# ----------------------------------------------------------------------
# Sidebar — filters & configurable thresholds (sections 18 & 26)
# ----------------------------------------------------------------------
st.sidebar.header("Filters")

asset_type_choice = st.sidebar.selectbox("Asset type", ["All", "Fiat", "Cryptocurrency", "NFT"])
entity_type_choice = st.sidebar.selectbox(
    "Entity type", ["All", "Bank Account", "Exchange", "Wallet", "NFT Marketplace", "NFT Asset"]
)
crypto_asset_choice = st.sidebar.selectbox("Crypto asset", ["All", "BTC", "ETH", "USDT", "USDC"])
scenario_choice = st.sidebar.selectbox(
    "Scenario", ["All"] + sorted(df_all.scenario.dropna().unique().tolist())
)

st.sidebar.divider()
st.sidebar.header("Detection thresholds")
rapid_hop_seconds = st.sidebar.slider("Rapid cross-bank/wallet hop window (sec)", 30, 600, 180, step=10)
cross_domain_window = st.sidebar.slider("Cross-domain correlation window (sec)", 60, 1800, 600, step=30)
nft_window = st.sidebar.slider("NFT rapid-trade window (sec)", 60, 900, 300, step=30)

st.sidebar.divider()
simulate = st.sidebar.button("🚨 Simulate Suspicious Network")

# ----------------------------------------------------------------------
# Apply filters
# ----------------------------------------------------------------------
d = df_all.copy()

ASSET_MAP = {"Fiat": "FIAT", "Cryptocurrency": "CRYPTO", "NFT": "NFT"}
if asset_type_choice != "All":
    d = d[d.asset_type == ASSET_MAP[asset_type_choice]]

ENTITY_MAP = {
    "Bank Account": "BANK_ACCOUNT", "Exchange": "CRYPTO_EXCHANGE", "Wallet": "CRYPTO_WALLET",
    "NFT Marketplace": "NFT_MARKETPLACE", "NFT Asset": "NFT_ASSET",
}
if entity_type_choice != "All":
    et = ENTITY_MAP[entity_type_choice]
    d = d[(d.source_type == et) | (d.destination_type == et)]

if crypto_asset_choice != "All":
    d = d[d.crypto_asset == crypto_asset_choice]

if scenario_choice != "All":
    d = d[d.scenario == scenario_choice]

if simulate:
    sim_rows = pd.DataFrame([
        {"tx_id": "SIM0001", "timestamp": pd.Timestamp("2026-06-23 10:00:00"),
         "chain_id": "SIM_CHAIN", "scenario": "cross_bank_layering",
         "transaction_type": "fiat_transfer", "asset_type": "FIAT",
         "source_entity": "AX_A03", "source_type": "BANK_ACCOUNT", "source_bank": "Axis Bank",
         "destination_entity": "YS_B02", "destination_type": "BANK_ACCOUNT", "destination_bank": "Yes Bank",
         "currency": "INR", "amount": 42000, "amount_inr": 42000},
        {"tx_id": "SIM0002", "timestamp": pd.Timestamp("2026-06-23 10:00:18"),
         "chain_id": "SIM_CHAIN", "scenario": "cross_bank_layering",
         "transaction_type": "fiat_transfer", "asset_type": "FIAT",
         "source_entity": "YS_B02", "source_type": "BANK_ACCOUNT", "source_bank": "Yes Bank",
         "destination_entity": "BOI_C02", "destination_type": "BANK_ACCOUNT", "destination_bank": "Bank of India",
         "currency": "INR", "amount": 41000, "amount_inr": 41000},
        {"tx_id": "SIM0003", "timestamp": pd.Timestamp("2026-06-23 10:00:40"),
         "chain_id": "SIM_CHAIN", "scenario": "cross_bank_layering",
         "transaction_type": "fiat_transfer", "asset_type": "FIAT",
         "source_entity": "BOI_C02", "source_type": "BANK_ACCOUNT", "source_bank": "Bank of India",
         "destination_entity": "CN_E02", "destination_type": "BANK_ACCOUNT", "destination_bank": "Canara Bank",
         "currency": "INR", "amount": 40000, "amount_inr": 40000},
    ])
    d = pd.concat([d, an.normalize_transactions(sim_rows)], ignore_index=True)
    st.warning("Simulated suspicious network injected: AX_A03 → YS_B02 → BOI_C02 → CN_E02", icon="🚨")

# ----------------------------------------------------------------------
# Run detectors once for the current filtered view
# ----------------------------------------------------------------------
alerts = an.run_all_detectors(
    d, rapid_hop_seconds=rapid_hop_seconds, crypto_hop_seconds=rapid_hop_seconds,
    nft_window_seconds=nft_window, cross_domain_window_seconds=cross_domain_window,
)
risk = an.calculate_risk_score(alerts)
suspicious_entities = {a["entity"] for a in alerts} | {
    e for a in alerts for e in a["path"].split(" → ")
}

# ----------------------------------------------------------------------
# Overview metrics (always visible, above the tabs)
# ----------------------------------------------------------------------
banks_seen = set(d.source_bank.dropna()) | set(d.destination_bank.dropna())
wallets_seen = set(d[d.source_type == "CRYPTO_WALLET"].source_entity) | \
    set(d[d.destination_type == "CRYPTO_WALLET"].destination_entity)
exchanges_seen = set(d[d.source_type == "CRYPTO_EXCHANGE"].source_entity) | \
    set(d[d.destination_type == "CRYPTO_EXCHANGE"].destination_entity)
nft_seen = set(d.nft_id.dropna())
crypto_volume_inr = d[d.asset_type == "CRYPTO"].amount_inr.sum()
nft_volume_inr = d[d.asset_type == "NFT"]["nft_sale_price_inr"].fillna(0).sum()

m1, m2, m3, m4, m5, m6 = st.columns(6)
m1.metric("Banks", len(banks_seen))
m2.metric("Wallets", len(wallets_seen))
m3.metric("Exchanges", len(exchanges_seen))
m4.metric("NFT Assets", len(nft_seen))
m5.metric("Transactions", len(d))
m6.metric("Alerts", len(alerts))

st.divider()

# ----------------------------------------------------------------------
# Tabs (section 21)
# ----------------------------------------------------------------------
tab_overview, tab_graph, tab_alerts, tab_crypto_nft, tab_investigation, tab_ledger = st.tabs(
    ["📊 Overview", "🕸️ Transaction Graph", "⚠️ Risk Alerts", "💎 Crypto & NFT Intelligence",
     "🔎 Investigation", "🔗 Ledger Verification"]
)

# ---- Overview ----
with tab_overview:
    c1, c2 = st.columns([1, 1])
    with c1:
        st.subheader("Total value moved")
        st.metric("Total transaction value (₹)", f"₹{d.amount_inr.sum():,.0f}")
        st.metric("Crypto volume (₹ equivalent)", f"₹{crypto_volume_inr:,.0f}")
        st.metric("NFT volume (₹ equivalent)", f"₹{nft_volume_inr:,.0f}")
    with c2:
        st.subheader("Risk Score")
        st.metric("Overall risk score", f"{risk['total']}/100")
        for k, v in risk["breakdown"].items():
            st.progress(min(v / an.COMPONENT_CAPS[k], 1.0) if an.COMPONENT_CAPS[k] else 0,
                        text=f"{k}: +{v} (cap {an.COMPONENT_CAPS[k]})")

    st.subheader("High-risk entities")
    if suspicious_entities:
        st.dataframe(pd.DataFrame({"Entity": sorted(suspicious_entities)}), hide_index=True,
                     use_container_width=True)
    else:
        st.info("No high-risk entities flagged for the current filters.")

# ---- Transaction Graph ----
with tab_graph:
    st.subheader("Unified Transaction Graph")
    st.caption("Bank accounts, crypto exchanges, crypto wallets, NFT marketplaces and NFT assets "
               "as one connected graph. Red nodes are involved in a detected risk signal.")
    g = gu.build_transaction_graph(d)
    fig = gu.render_graph(g, suspicious_entities)
    st.plotly_chart(fig, use_container_width=True)

# ---- Risk Alerts ----
with tab_alerts:
    st.subheader("⚠️ Risk Alerts")
    if not alerts:
        st.success("✓ No high-confidence pattern detected for the current filters.")
    else:
        for a in sorted(alerts, key=lambda x: x["score"], reverse=True):
            icon = "🚨" if a["severity"] == "HIGH" else "🟠"
            with st.expander(f"{icon} {a['severity']} — {a['type']}  ·  score {a['score']}"):
                st.write(f"**Path:** {a['path']}")
                if a["start_time"] is not None and a["end_time"] is not None:
                    st.write(f"**Time:** {a['start_time']} → {a['end_time']}  "
                             f"(**duration** {a['duration_seconds']}s)")
                cols = st.columns(4)
                cols[0].metric("Hops", a["hop_count"])
                cols[1].metric("Amount (₹)", f"{a['amount_inr']:,.0f}")
                cols[2].metric("Value velocity (₹/s)", f"{a['value_velocity']:,.1f}")
                cols[3].metric("Retention", f"{a['retention_percent']}%")
                st.write(f"**Assets involved:** {a['assets']}")
                st.write(f"**Reason:** {a['reason']}")
                st.write(f"**Evidence (tx IDs):** {', '.join(a['evidence'])}")

# ---- Crypto & NFT Intelligence ----
with tab_crypto_nft:
    st.subheader("Crypto & NFT Intelligence")
    crypto_df = d[d.asset_type == "CRYPTO"]
    nft_df = d[d.nft_id.notna()]

    cc1, cc2 = st.columns(2)
    with cc1:
        st.markdown("**Crypto transactions**")
        if crypto_df.empty:
            st.info("No crypto transactions in the current filter.")
        else:
            st.dataframe(
                crypto_df[["tx_id", "timestamp", "source_entity", "destination_entity",
                            "crypto_asset", "crypto_amount", "amount_inr", "scenario"]],
                hide_index=True, use_container_width=True,
            )
    with cc2:
        st.markdown("**NFT transactions**")
        if nft_df.empty:
            st.info("No NFT transactions in the current filter.")
        else:
            st.dataframe(
                nft_df[["tx_id", "timestamp", "nft_id", "nft_collection", "nft_marketplace",
                        "nft_sale_price_inr", "scenario"]],
                hide_index=True, use_container_width=True,
            )

    st.markdown("**Synthetic demo valuations used** (not live market prices)")
    price_table = pd.DataFrame([
        {"Asset": k, "Synthetic price (₹)": f"{v:,.2f}"}
        for k, v in {"BTC": 5_200_000.0, "ETH": 310_000.0, "USDT": 92.0, "USDC": 91.5}.items()
    ])
    st.dataframe(price_table, hide_index=True, use_container_width=True)

# ---- Investigation ----
with tab_investigation:
    st.subheader("🔎 Entity Investigation")
    all_entities = sorted(set(d.source_entity) | set(d.destination_entity))
    if not all_entities:
        st.info("No entities available for the current filters.")
    else:
        selected = st.selectbox("Select an entity", all_entities)
        entity_tx = d[(d.source_entity == selected) | (d.destination_entity == selected)].copy()
        entity_type = None
        match_out = d[d.source_entity == selected]
        match_in = d[d.destination_entity == selected]
        if len(match_out):
            entity_type = match_out.iloc[0].source_type
        elif len(match_in):
            entity_type = match_in.iloc[0].destination_type

        incoming = entity_tx[entity_tx.destination_entity == selected].amount_inr.sum()
        outgoing = entity_tx[entity_tx.source_entity == selected].amount_inr.sum()
        connections = len(set(entity_tx.source_entity) | set(entity_tx.destination_entity)) - 1
        first_seen = entity_tx.timestamp.min()
        last_seen = entity_tx.timestamp.max()
        span_seconds = an.calculate_time_delta(first_seen, last_seen) if len(entity_tx) > 1 else 0
        avg_interval = span_seconds / max(len(entity_tx) - 1, 1)
        tx_velocity = an.calculate_transaction_velocity(len(entity_tx), span_seconds)
        value_velocity = an.calculate_amount_velocity(entity_tx.amount_inr.sum(), span_seconds)

        st.write(f"**Entity type:** {gu.ENTITY_LABELS.get(entity_type, entity_type)}")
        a1, a2, a3 = st.columns(3)
        a1.metric("Incoming (₹)", f"{incoming:,.0f}")
        a2.metric("Outgoing (₹)", f"{outgoing:,.0f}")
        a3.metric("Connections", connections)
        b1, b2, b3 = st.columns(3)
        b1.metric("Tx velocity (per min)", f"{tx_velocity:.2f}")
        b2.metric("Value velocity (₹/s)", f"{value_velocity:,.1f}")
        b3.metric("Avg interval (s)", f"{avg_interval:,.0f}")
        st.caption(f"First seen: {first_seen}  ·  Last seen: {last_seen}")

        entity_risk_score = sum(a["score"] for a in alerts if selected in a["path"])
        st.metric("Entity-linked risk score", min(entity_risk_score, 100))

        st.markdown("**Transactions**")
        st.dataframe(
            entity_tx[["tx_id", "timestamp", "source_entity", "destination_entity",
                        "currency", "amount_inr", "transaction_type", "scenario"]],
            hide_index=True, use_container_width=True,
        )

        # Show the connected temporal path + velocity table if this entity starts a chain.
        seed_rows = d[d.source_entity == selected].sort_values("timestamp")
        if len(seed_rows):
            chain = an.find_cross_entity_chain(d, seed_rows.iloc[0], cross_domain_window)
            if chain.hop_count >= 1:
                st.markdown("**Connected transaction path**")
                st.write(chain.path_str)
                st.dataframe(an.build_velocity_table(chain, d), hide_index=True, use_container_width=True)

# ---- Ledger Verification ----
with tab_ledger:
    st.subheader("🔗 Tamper-Evident Ledger")
    st.info(
        "This prototype uses a local SHA-256 hash chain to demonstrate tamper-evident "
        "transaction provenance. A production deployment could migrate this layer to a "
        "permissioned DLT. This is **not** Hyperledger Fabric and **not** a live blockchain."
    )
    if st.button("Build / Verify Ledger"):
        chain = lg.build_ledger(d)
        valid = lg.verify_ledger(chain)
        if valid:
            st.success(f"✓ Ledger verified — {len(chain)} blocks valid. Hash chain is intact.")
        else:
            st.error("⚠ Ledger verification failed.")
        preview = [{
            "Block": i, "Tx ID": b["transaction"]["tx_id"],
            "Previous Hash": b["previous_hash"][:12] + "…", "Hash": b["hash"][:12] + "…",
        } for i, b in enumerate(chain[:12], 1)]
        st.dataframe(pd.DataFrame(preview), hide_index=True, use_container_width=True)

st.divider()
st.caption(
    "Prototype scope: synthetic data only, rule-based detection (not a trained ML model), "
    "and a local hash-linked ledger. Not connected to real banking rails, crypto exchanges, "
    "NFT marketplaces, or live blockchains."
)
