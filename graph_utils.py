"""
graph_utils.py
Builds the unified cross-asset transaction graph (bank accounts, crypto
exchanges, crypto wallets, NFT marketplaces, NFT assets) and renders it
with Plotly for an interactive, judge-friendly view.
"""
import networkx as nx
import plotly.graph_objects as go
import pandas as pd

ENTITY_COLORS = {
    "BANK_ACCOUNT": "#2d83bd",
    "CRYPTO_EXCHANGE": "#7a4fd6",
    "CRYPTO_WALLET": "#e08a2b",
    "NFT_MARKETPLACE": "#0f9d8c",
    "NFT_ASSET": "#c23f7a",
}
ENTITY_LABELS = {
    "BANK_ACCOUNT": "Bank Account",
    "CRYPTO_EXCHANGE": "Crypto Exchange",
    "CRYPTO_WALLET": "Crypto Wallet",
    "NFT_MARKETPLACE": "NFT Marketplace",
    "NFT_ASSET": "NFT Asset",
}
SUSPICIOUS_COLOR = "#d0393f"


def build_transaction_graph(df: pd.DataFrame) -> nx.DiGraph:
    """Build the unified directed graph. Every edge keeps its transaction
    metadata (amount, currency, asset, timestamp, type, tx_id)."""
    g = nx.DiGraph()
    for _, r in df.iterrows():
        g.add_node(r.source_entity, entity_type=r.source_type)
        g.add_node(r.destination_entity, entity_type=r.destination_type)
        g.add_edge(
            r.source_entity, r.destination_entity,
            tx_id=r.tx_id, amount=r.amount, amount_inr=r.amount_inr,
            currency=r.currency, transaction_type=r.transaction_type,
            asset_type=r.asset_type, timestamp=r.timestamp, scenario=r.scenario,
        )
    return g


def render_graph(g: nx.DiGraph, suspicious_entities: set):
    """Return a Plotly figure of the graph, colored by entity type, with
    suspicious nodes highlighted in red and a legend."""
    if g.number_of_nodes() == 0:
        fig = go.Figure()
        fig.update_layout(title="No transactions in the current filter.")
        return fig

    pos = nx.spring_layout(g, seed=7, k=0.9)

    edge_x, edge_y = [], []
    for u, v in g.edges():
        x0, y0 = pos[u]
        x1, y1 = pos[v]
        edge_x += [x0, x1, None]
        edge_y += [y0, y1, None]

    edge_trace = go.Scatter(
        x=edge_x, y=edge_y, mode="lines",
        line=dict(width=1, color="rgba(120,130,140,0.45)"),
        hoverinfo="none", showlegend=False,
    )

    fig = go.Figure(data=[edge_trace])

    # One trace per entity type so a legend appears automatically.
    for etype, color in ENTITY_COLORS.items():
        nodes = [n for n, d in g.nodes(data=True) if d.get("entity_type") == etype]
        if not nodes:
            continue
        node_colors = [SUSPICIOUS_COLOR if n in suspicious_entities else color for n in nodes]
        fig.add_trace(go.Scatter(
            x=[pos[n][0] for n in nodes], y=[pos[n][1] for n in nodes],
            mode="markers+text", text=nodes, textposition="top center",
            textfont=dict(size=9),
            marker=dict(size=16, color=node_colors, line=dict(width=1, color="white")),
            name=ENTITY_LABELS[etype],
            hovertext=[f"{n}<br>{ENTITY_LABELS[etype]}" for n in nodes],
            hoverinfo="text",
        ))

    fig.update_layout(
        showlegend=True, legend=dict(orientation="h", yanchor="bottom", y=-0.15),
        margin=dict(l=10, r=10, t=10, b=10),
        xaxis=dict(showgrid=False, zeroline=False, visible=False),
        yaxis=dict(showgrid=False, zeroline=False, visible=False),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        height=520,
    )
    return fig
