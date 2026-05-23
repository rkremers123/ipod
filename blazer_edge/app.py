"""
app.py — Blazer Edge: Portland Trail Blazers Basketball Intelligence Dashboard
"""

import datetime
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ---------------------------------------------------------------------------
# Page config — MUST be first Streamlit call
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Blazer Edge | Basketball Intelligence",
    page_icon="🔴",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Imports (local)
# ---------------------------------------------------------------------------
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from fetcher import get_player_stats, get_salary_data
from models import compute_bes, compute_contract_efficiency, compute_archetypes, analyze_trade

# ---------------------------------------------------------------------------
# Global CSS
# ---------------------------------------------------------------------------
st.markdown(
    """
<style>
    .main { background-color: #0a0a0a; }
    .stMetric {
        background: #1a1a1a;
        border-radius: 8px;
        padding: 12px;
        border-left: 3px solid #E03A3E;
    }
    h1, h2, h3 { color: #E03A3E; }
    .stDataFrame { font-size: 13px; }
    .blazer-badge {
        background: #E03A3E;
        color: white;
        padding: 3px 10px;
        border-radius: 12px;
        font-weight: bold;
        font-size: 12px;
    }
    .verdict-win { color: #00C851; font-weight: bold; font-size: 1.3em; }
    .verdict-loss { color: #E03A3E; font-weight: bold; font-size: 1.3em; }
    .verdict-fair { color: #FFD700; font-weight: bold; font-size: 1.3em; }
    section[data-testid="stSidebar"] { background-color: #111111; }
</style>
""",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Plotly chart defaults
# ---------------------------------------------------------------------------
CHART_DEFAULTS = dict(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
)

BLAZERS_RED = "#E03A3E"
BLAZERS_BLACK = "#000000"

ARCHETYPE_COLORS = {
    "Primary Creator": "#FF6B6B",
    "Defensive Anchor": "#4ECDC4",
    "Glass Eater": "#45B7D1",
    "3&D Wing": "#96CEB4",
    "Volume Scorer": "#FFEAA7",
    "Disruptor": "#DDA0DD",
    "Connector": "#98D8C8",
}


# ---------------------------------------------------------------------------
# Data loading (cached)
# ---------------------------------------------------------------------------
@st.cache_data(ttl=86400)
def load_data(season: str):
    df = get_player_stats(season)
    salary_df = get_salary_data()
    df = compute_bes(df)
    df = compute_contract_efficiency(df, salary_df)
    df, archetype_labels = compute_archetypes(df)
    return df, archetype_labels


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown(
        "<h1 style='color:#E03A3E; font-size:1.4em;'>🏀 BLAZER EDGE</h1>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='color:#888; font-size:0.8em;'>Basketball Intelligence Platform</p>",
        unsafe_allow_html=True,
    )
    st.divider()

    season = st.selectbox("Season", ["2024-25", "2023-24"], index=0)

    page = st.radio(
        "Navigation",
        [
            "League Intelligence",
            "Blazers Roster Analysis",
            "Trade Analyzer",
            "Player DNA (Archetypes)",
            "Contract Efficiency",
        ],
    )

    st.divider()
    st.markdown(
        "<p style='color:#555; font-size:0.75em;'>Built with Python · nba_api · scikit-learn · Blazer Edge v1.0</p>",
        unsafe_allow_html=True,
    )

# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------
with st.spinner("🏀 Fetching live NBA data..."):
    df, archetype_labels = load_data(season)

# Data freshness info
timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
st.info(f"Data sourced from NBA Stats API · Last updated: {timestamp} · {len(df)} players tracked")

# ===========================================================================
# PAGE 1: LEAGUE INTELLIGENCE
# ===========================================================================
if page == "League Intelligence":
    st.title(f"NBA League Intelligence — {season} Season")

    # Top metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Players Tracked", len(df))
    with col2:
        st.metric("League Avg BES", "50.0")
    with col3:
        top_player = df.nlargest(1, "BES")["PLAYER_NAME"].iloc[0]
        st.metric("Most Valuable Player", top_player)
    with col4:
        best_value = df.nlargest(1, "CONTRACT_EFFICIENCY")["PLAYER_NAME"].iloc[0]
        st.metric("Best Value Contract", best_value)

    st.divider()

    # ---- Salary vs BES scatter ----
    st.subheader("Player Value vs. Salary — Identifying Market Inefficiencies")

    plot_df = df.copy()
    plot_df["Salary ($M)"] = plot_df["SALARY_2425"] / 1_000_000
    plot_df["BES_fmt"] = plot_df["BES"].round(1)
    plot_df["Hover_Team"] = plot_df["TEAM_ABBREVIATION"].apply(
        lambda t: f"🔴 {t}" if t == "POR" else t
    )

    fig_scatter = px.scatter(
        plot_df,
        x="Salary ($M)",
        y="BES",
        color="MARKET_STATUS",
        size="MIN",
        size_max=18,
        hover_name="PLAYER_NAME",
        hover_data={
            "Hover_Team": True,
            "BES_fmt": True,
            "Salary ($M)": ":.1f",
            "MARKET_STATUS": True,
            "MIN": ":.1f",
            "PTS": ":.1f",
        },
        color_discrete_map={
            "Star": BLAZERS_RED,
            "Undervalued": "#00ff88",
            "Overpaid": "#ff6b35",
            "Market Rate": "#888888",
        },
        title="Player Value vs. Salary — Identifying Market Inefficiencies",
        labels={"BES": "Blazer Edge Score (BES)", "Salary ($M)": "2024-25 Salary ($M)"},
        **CHART_DEFAULTS,
    )

    # Fair-value reference line
    max_sal = plot_df["Salary ($M)"].max()
    x_ref = np.linspace(0, max_sal, 100)
    y_ref = (x_ref / max_sal) * 90 + 10  # rough diagonal

    fig_scatter.add_trace(
        go.Scatter(
            x=x_ref,
            y=y_ref,
            mode="lines",
            line=dict(dash="dash", color="rgba(255,255,255,0.3)", width=1),
            name="Fair Value Reference",
            hoverinfo="skip",
        )
    )
    fig_scatter.update_layout(height=520, legend=dict(orientation="h", yanchor="bottom", y=1.02))
    st.plotly_chart(fig_scatter, use_container_width=True)

    # ---- Filterable data table ----
    st.subheader("Player Explorer")

    status_filter = st.multiselect(
        "Filter by Market Status",
        options=["Star", "Undervalued", "Overpaid", "Market Rate"],
        default=["Star", "Undervalued", "Overpaid", "Market Rate"],
    )
    team_filter = st.text_input("Filter by Team (e.g. POR, LAL)", value="")

    table_df = df.copy()
    table_df = table_df[table_df["MARKET_STATUS"].isin(status_filter)]
    if team_filter.strip():
        table_df = table_df[
            table_df["TEAM_ABBREVIATION"].str.upper() == team_filter.strip().upper()
        ]

    table_df = table_df.sort_values("BES", ascending=False)
    table_df["Team"] = table_df["TEAM_ABBREVIATION"].apply(
        lambda t: f"🔴 {t}" if t == "POR" else t
    )
    table_df["Salary"] = table_df["SALARY_2425"].apply(lambda s: f"${s/1_000_000:.1f}M")
    table_df["BES"] = table_df["BES"].round(1)
    table_df["PTS"] = table_df["PTS"].round(1)
    table_df["MIN"] = table_df["MIN"].round(1)

    st.dataframe(
        table_df[["PLAYER_NAME", "Team", "BES", "Salary", "MARKET_STATUS", "MIN", "PTS"]].reset_index(drop=True),
        use_container_width=True,
        height=400,
    )


# ===========================================================================
# PAGE 2: BLAZERS ROSTER ANALYSIS
# ===========================================================================
elif page == "Blazers Roster Analysis":
    st.title("Portland Trail Blazers — Roster Intelligence")

    blazers_df = df[df["TEAM_ABBREVIATION"] == "POR"].copy()

    if blazers_df.empty:
        st.warning("No Blazers players found in current dataset. Using full league data as fallback.")
        blazers_df = df.head(10).copy()

    # ---- Top metrics ----
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        avg_bes = blazers_df["BES"].mean()
        st.metric("Team Avg BES", f"{avg_bes:.1f}", delta=f"{avg_bes - 50:.1f} vs avg")
    with col2:
        total_salary = blazers_df["SALARY_2425"].sum()
        st.metric("Roster Salary", f"${total_salary/1_000_000:.1f}M")
    with col3:
        best_asset = blazers_df.nlargest(1, "BES")["PLAYER_NAME"].iloc[0]
        st.metric("Best Asset", best_asset)
    with col4:
        biggest_need = blazers_df.nsmallest(1, "BES")["PLAYER_NAME"].iloc[0]
        st.metric("Biggest Need", biggest_need)

    st.divider()

    # ---- BES bar chart ----
    st.subheader("Roster Rankings by Blazer Edge Score")

    bbar = blazers_df.sort_values("BES", ascending=True).copy()
    bbar["Salary_Label"] = bbar["SALARY_2425"].apply(lambda s: f"${s/1_000_000:.1f}M")

    fig_bar = go.Figure(
        go.Bar(
            x=bbar["BES"],
            y=bbar["PLAYER_NAME"],
            orientation="h",
            text=bbar.apply(lambda r: f"BES: {r['BES']:.1f}  |  {r['Salary_Label']}", axis=1),
            textposition="outside",
            marker=dict(
                color=bbar["BES"],
                colorscale=[[0, "#2a0a0a"], [0.5, "#8B1A1A"], [1, BLAZERS_RED]],
                showscale=False,
            ),
        )
    )
    fig_bar.update_layout(
        height=max(350, len(bbar) * 45),
        xaxis_title="Blazer Edge Score",
        yaxis_title="",
        **CHART_DEFAULTS,
    )
    st.plotly_chart(fig_bar, use_container_width=True)

    # ---- Radar chart: Blazers vs league ----
    st.subheader("Team Profile — Blazers vs. League Average")

    league_off = df["OFF_RATING"].mean()
    league_def = df["DEF_RATING"].mean()
    league_ts = df["TS_PCT"].mean()
    league_ast = df["AST_PCT"].mean()

    bor = blazers_df["OFF_RATING"].mean()
    bdr = blazers_df["DEF_RATING"].mean()
    bts = blazers_df["TS_PCT"].mean()
    bast = blazers_df["AST_PCT"].mean()

    # Normalise 0-1 for radar
    def _radar_norm(val, mn, mx):
        if mx == mn:
            return 0.5
        return (val - mn) / (mx - mn)

    off_min, off_max = df["OFF_RATING"].min(), df["OFF_RATING"].max()
    def_min, def_max = df["DEF_RATING"].min(), df["DEF_RATING"].max()
    ts_min, ts_max = df["TS_PCT"].min(), df["TS_PCT"].max()
    ast_min, ast_max = df["AST_PCT"].min(), df["AST_PCT"].max()

    categories = ["Offense", "Defense\n(inverted)", "Shooting", "Playmaking"]

    blazers_vals = [
        _radar_norm(bor, off_min, off_max),
        1 - _radar_norm(bdr, def_min, def_max),  # lower DEF_RATING = better defence
        _radar_norm(bts, ts_min, ts_max),
        _radar_norm(bast, ast_min, ast_max),
    ]
    league_vals = [
        _radar_norm(league_off, off_min, off_max),
        1 - _radar_norm(league_def, def_min, def_max),
        _radar_norm(league_ts, ts_min, ts_max),
        _radar_norm(league_ast, ast_min, ast_max),
    ]

    fig_radar = go.Figure()
    fig_radar.add_trace(
        go.Scatterpolar(
            r=blazers_vals + [blazers_vals[0]],
            theta=categories + [categories[0]],
            fill="toself",
            name="Trail Blazers",
            line=dict(color=BLAZERS_RED),
            fillcolor="rgba(224,58,62,0.25)",
        )
    )
    fig_radar.add_trace(
        go.Scatterpolar(
            r=league_vals + [league_vals[0]],
            theta=categories + [categories[0]],
            fill="toself",
            name="League Average",
            line=dict(color="#888888"),
            fillcolor="rgba(136,136,136,0.15)",
        )
    )
    fig_radar.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 1]),
            bgcolor="rgba(0,0,0,0)",
        ),
        height=400,
        **CHART_DEFAULTS,
    )
    st.plotly_chart(fig_radar, use_container_width=True)

    # ---- Roster Gaps Heatmap ----
    st.subheader("Roster Gaps Analysis — League Percentile by Metric")

    heat_metrics = ["PTS", "AST", "REB", "STL", "BLK", "TS_PCT", "BES"]
    heat_data = []
    for _, row in blazers_df.iterrows():
        player_pcts = {}
        for m in heat_metrics:
            if m in df.columns:
                pct = (df[m] <= row[m]).sum() / len(df) * 100
                player_pcts[m] = round(pct, 1)
        heat_data.append({"Player": row["PLAYER_NAME"], **player_pcts})

    heat_df = pd.DataFrame(heat_data).set_index("Player")

    fig_heat = go.Figure(
        go.Heatmap(
            z=heat_df.values,
            x=heat_df.columns.tolist(),
            y=heat_df.index.tolist(),
            colorscale=[
                [0.0, "#8B0000"],
                [0.33, "#CC3300"],
                [0.5, "#888888"],
                [0.67, "#006633"],
                [1.0, "#00AA44"],
            ],
            zmin=0,
            zmax=100,
            text=heat_df.values.astype(int),
            texttemplate="%{text}th",
            showscale=True,
            colorbar=dict(title="Percentile"),
        )
    )
    fig_heat.update_layout(
        height=max(300, len(heat_df) * 40 + 80),
        xaxis_title="Metric",
        yaxis_title="",
        **CHART_DEFAULTS,
    )
    st.plotly_chart(fig_heat, use_container_width=True)

    # ---- Target Acquisitions ----
    st.subheader("Target Acquisitions — Affordable High-Value Players")

    targets = df[
        (df["TEAM_ABBREVIATION"] != "POR")
        & (df["BES"] > 55)
        & (df["SALARY_2425"] < 20_000_000)
        & (df["MARKET_STATUS"] == "Undervalued")
    ].copy()

    if targets.empty:
        # Relax criteria
        targets = df[
            (df["TEAM_ABBREVIATION"] != "POR")
            & (df["BES"] > 50)
            & (df["SALARY_2425"] < 20_000_000)
        ].nlargest(10, "BES")
    else:
        targets = targets.nlargest(10, "BES")

    targets["Salary"] = targets["SALARY_2425"].apply(lambda s: f"${s/1_000_000:.1f}M")
    targets["BES"] = targets["BES"].round(1)
    targets["Why Fit?"] = targets.apply(
        lambda r: f"{r['ARCHETYPE']} · {r['PTS']:.1f} PPG · {r['REB']:.1f} REB", axis=1
    )

    st.dataframe(
        targets[["PLAYER_NAME", "TEAM_ABBREVIATION", "BES", "Salary", "ARCHETYPE", "Why Fit?"]].reset_index(drop=True),
        use_container_width=True,
    )

    # ---- Rebuilding Trajectory ----
    st.subheader("Rebuilding Trajectory")

    scoot_bes = blazers_df[blazers_df["PLAYER_NAME"].str.contains("Scoot|Henderson", na=False)]["BES"]
    scoot_val = f"{scoot_bes.iloc[0]:.1f}" if not scoot_bes.empty else "N/A"

    best_bes_name = blazers_df.nlargest(1, "BES")["PLAYER_NAME"].iloc[0]
    best_bes_val = blazers_df.nlargest(1, "BES")["BES"].iloc[0]
    gap_metric = heat_df.min(axis=0).idxmin() if not heat_df.empty else "scoring"

    trajectory_text = f"""
**The Blazers are in Phase 2 of their rebuild** with a young core built around Scoot Henderson and Shaedon Sharpe.

The data reveals that **{best_bes_name}** (BES: {best_bes_val:.1f}) is the team's most productive player by composite metrics.
Scoot Henderson posts a BES of **{scoot_val}**, reflecting a developing point guard still acclimating to NBA pace and decision-making.

**Key priority:** The heatmap highlights that **{gap_metric}** is the area where the Blazers roster
ranks most consistently below league average. Targeting high-percentile performers in this category
via trade or free agency should be the front office's immediate focus.

Portland's cap situation provides flexibility, and with multiple first-round picks in coming drafts,
the franchise is well-positioned to accelerate this rebuild timeline — but patience with the young
core (especially Henderson and Sharpe) will be essential to maximizing long-term potential.
"""
    st.markdown(trajectory_text)


# ===========================================================================
# PAGE 3: TRADE ANALYZER
# ===========================================================================
elif page == "Trade Analyzer":
    st.title("Trade Analyzer — Value Assessment Engine")
    st.markdown(
        "Simulate trades and instantly see the BES-based value exchange, salary implications, and verdict."
    )

    por_players = sorted(
        df[df["TEAM_ABBREVIATION"] == "POR"]["PLAYER_NAME"].tolist()
    )
    all_teams = sorted(df["TEAM_ABBREVIATION"].unique().tolist())
    non_por_teams = [t for t in all_teams if t != "POR"]

    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown(f"### 🔴 Team A — Portland Trail Blazers")
        team1_sel = st.multiselect(
            "Select Blazers players to trade away",
            options=por_players,
            default=[por_players[0]] if por_players else [],
        )

        if team1_sel:
            t1_preview = df[df["PLAYER_NAME"].isin(team1_sel)][
                ["PLAYER_NAME", "BES", "SALARY_2425", "ARCHETYPE"]
            ].copy()
            t1_preview["BES"] = t1_preview["BES"].round(1)
            t1_preview["Salary"] = t1_preview["SALARY_2425"].apply(lambda s: f"${s/1_000_000:.1f}M")
            st.dataframe(t1_preview[["PLAYER_NAME", "BES", "Salary", "ARCHETYPE"]], use_container_width=True)

    with col_b:
        st.markdown("### ⚪ Team B — Other Team")
        other_team = st.selectbox("Select other team", options=non_por_teams, index=0)
        other_players = sorted(
            df[df["TEAM_ABBREVIATION"] == other_team]["PLAYER_NAME"].tolist()
        )
        team2_sel = st.multiselect(
            f"Select {other_team} players to receive",
            options=other_players,
            default=[other_players[0]] if other_players else [],
        )

        if team2_sel:
            t2_preview = df[df["PLAYER_NAME"].isin(team2_sel)][
                ["PLAYER_NAME", "BES", "SALARY_2425", "ARCHETYPE"]
            ].copy()
            t2_preview["BES"] = t2_preview["BES"].round(1)
            t2_preview["Salary"] = t2_preview["SALARY_2425"].apply(lambda s: f"${s/1_000_000:.1f}M")
            st.dataframe(t2_preview[["PLAYER_NAME", "BES", "Salary", "ARCHETYPE"]], use_container_width=True)

    st.divider()

    if st.button("🔍 Analyze Trade", type="primary", use_container_width=True):
        if not team1_sel and not team2_sel:
            st.warning("Select at least one player on each side to analyze.")
        else:
            result = analyze_trade(team1_sel, team2_sel, df)

            # Verdict colour
            verdict = result["verdict"]
            if verdict == "Fair Trade":
                verdict_class = "verdict-fair"
                verdict_icon = "⚖️"
            elif verdict == "Team A Wins":
                verdict_class = "verdict-win"
                verdict_icon = "✅"
            else:
                verdict_class = "verdict-loss"
                verdict_icon = "❌"

            st.markdown(
                f"<div class='{verdict_class}'>{verdict_icon} VERDICT: {verdict}</div>",
                unsafe_allow_html=True,
            )
            st.divider()

            c1, c2, c3, c4 = st.columns(4)
            with c1:
                st.metric("Portland BES Out", f"{result['team1_total_bes']:.1f}")
            with c2:
                st.metric("Portland BES In", f"{result['team2_total_bes']:.1f}",
                          delta=f"{result['bes_delta']:+.1f}")
            with c3:
                st.metric("Salary Out ($M)", f"${result['team1_total_salary']/1_000_000:.1f}M")
            with c4:
                sal_delta = result["salary_delta"]
                st.metric("Salary Delta", f"${abs(sal_delta)/1_000_000:.1f}M",
                          delta=f"{'More' if sal_delta > 0 else 'Less'} salary")

            # BES balance meter
            st.subheader("BES Balance")
            t1b = result["team1_total_bes"]
            t2b = result["team2_total_bes"]
            total = t1b + t2b if (t1b + t2b) > 0 else 1
            por_share = t1b / total

            fig_meter = go.Figure(
                go.Bar(
                    x=[por_share * 100, (1 - por_share) * 100],
                    y=[""],
                    orientation="h",
                    marker_color=[BLAZERS_RED, "#444444"],
                    text=[f"POR gives: {t1b:.1f} BES", f"POR receives: {t2b:.1f} BES"],
                    textposition="inside",
                )
            )
            fig_meter.update_layout(
                barmode="stack",
                height=100,
                showlegend=False,
                xaxis=dict(showticklabels=False, range=[0, 100]),
                margin=dict(l=10, r=10, t=10, b=10),
                **CHART_DEFAULTS,
            )
            st.plotly_chart(fig_meter, use_container_width=True)

            st.subheader("Analysis")
            st.write(result["analysis"])

            # Cap space impact
            st.subheader("Cap Space Impact")
            sal_delta = result["salary_delta"]
            current_payroll = df[df["TEAM_ABBREVIATION"] == "POR"]["SALARY_2425"].sum()
            tax_line = 165_000_000  # approx 2024-25 luxury tax
            new_payroll = current_payroll - result["team1_total_salary"] + result["team2_total_salary"]

            c5, c6, c7 = st.columns(3)
            with c5:
                st.metric("Current Payroll", f"${current_payroll/1_000_000:.1f}M")
            with c6:
                st.metric("Post-Trade Payroll", f"${new_payroll/1_000_000:.1f}M",
                          delta=f"${(new_payroll - current_payroll)/1_000_000:+.1f}M")
            with c7:
                headroom = tax_line - new_payroll
                st.metric("Tax Line Headroom", f"${max(headroom, 0)/1_000_000:.1f}M",
                          delta="Under tax" if headroom > 0 else "Over tax")


# ===========================================================================
# PAGE 4: PLAYER DNA (ARCHETYPES)
# ===========================================================================
elif page == "Player DNA (Archetypes)":
    st.title("Player DNA — Unsupervised Archetype Discovery")
    st.markdown(
        "Using K-means clustering on 9 performance dimensions reduced to 2D via PCA. "
        "Each cluster represents a fundamental player archetype discovered purely from data."
    )

    variance_explained = df["PCA_VARIANCE_EXPLAINED"].iloc[0] if "PCA_VARIANCE_EXPLAINED" in df.columns else 0.0

    # ---- PCA scatter ----
    fig_pca = px.scatter(
        df,
        x="PCA_1",
        y="PCA_2",
        color="ARCHETYPE",
        size="BES",
        size_max=20,
        hover_name="PLAYER_NAME",
        hover_data={
            "ARCHETYPE": True,
            "BES": ":.1f",
            "TEAM_ABBREVIATION": True,
            "PTS": ":.1f",
            "PCA_1": False,
            "PCA_2": False,
        },
        color_discrete_map=ARCHETYPE_COLORS,
        title=f"NBA Player Universe — 7 Fundamental Archetypes  |  PCA explains {variance_explained:.1f}% of variance",
        labels={"PCA_1": "Principal Component 1", "PCA_2": "Principal Component 2"},
        **CHART_DEFAULTS,
    )

    # Cluster centroids (stars)
    for archetype, color in ARCHETYPE_COLORS.items():
        subset = df[df["ARCHETYPE"] == archetype]
        if not subset.empty:
            cx = subset["PCA_1"].mean()
            cy = subset["PCA_2"].mean()
            fig_pca.add_trace(
                go.Scatter(
                    x=[cx],
                    y=[cy],
                    mode="markers",
                    marker=dict(symbol="star", size=16, color=color, line=dict(width=1.5, color="white")),
                    name=f"★ {archetype}",
                    hovertemplate=f"<b>{archetype}</b> centroid<extra></extra>",
                    showlegend=False,
                )
            )

    fig_pca.update_layout(height=580, legend=dict(orientation="h", yanchor="bottom", y=1.02))
    st.plotly_chart(fig_pca, use_container_width=True)

    # ---- Archetype breakdowns ----
    st.subheader("Archetype Profiles")
    archetype_cols = st.columns(2)
    col_idx = 0

    for archetype in sorted(df["ARCHETYPE"].unique()):
        subset = df[df["ARCHETYPE"] == archetype].copy()
        color = ARCHETYPE_COLORS.get(archetype, "#888888")
        with archetype_cols[col_idx % 2]:
            with st.expander(f"**{archetype}** — {len(subset)} players (Avg BES: {subset['BES'].mean():.1f})", expanded=False):
                top3 = subset.nlargest(3, "BES")[["PLAYER_NAME", "TEAM_ABBREVIATION", "BES", "PTS", "AST", "REB"]]
                top3["BES"] = top3["BES"].round(1)
                st.markdown(f"**Top players:**")
                st.dataframe(top3, use_container_width=True, hide_index=True)

                avg_stats = subset[["PTS", "AST", "REB", "STL", "BLK", "BES"]].mean().round(2)
                st.markdown("**Archetype averages:**")
                stat_cols = st.columns(len(avg_stats))
                for i, (stat, val) in enumerate(avg_stats.items()):
                    with stat_cols[i]:
                        st.metric(stat, f"{val:.1f}")
        col_idx += 1

    # ---- Comparable Players ----
    st.divider()
    st.subheader("Find Comparable Players")

    selected_player = st.selectbox(
        "Select a player to find comparables",
        options=sorted(df["PLAYER_NAME"].tolist()),
        index=0,
    )

    if selected_player:
        player_row = df[df["PLAYER_NAME"] == selected_player]
        if not player_row.empty:
            player_data = player_row.iloc[0]
            player_arch = player_data["ARCHETYPE"]
            player_pca1 = player_data["PCA_1"]
            player_pca2 = player_data["PCA_2"]

            # Euclidean distance in PCA space
            others = df[df["PLAYER_NAME"] != selected_player].copy()
            others["_dist"] = np.sqrt(
                (others["PCA_1"] - player_pca1) ** 2 + (others["PCA_2"] - player_pca2) ** 2
            )
            comps = others.nsmallest(5, "_dist")[
                ["PLAYER_NAME", "TEAM_ABBREVIATION", "ARCHETYPE", "BES", "PTS", "AST", "REB"]
            ].copy()
            comps["BES"] = comps["BES"].round(1)

            st.markdown(
                f"**{selected_player}** is a **{player_arch}** "
                f"(BES: {player_data['BES']:.1f}, {player_data['PTS']:.1f} PPG)"
            )
            st.markdown("**5 Most Similar Players (PCA distance):**")
            st.dataframe(comps.reset_index(drop=True), use_container_width=True)


# ===========================================================================
# PAGE 5: CONTRACT EFFICIENCY
# ===========================================================================
elif page == "Contract Efficiency":
    st.title("Contract Efficiency — Market Intelligence")
    st.markdown(
        "Identifying market inefficiencies: players whose production value exceeds "
        "their compensation, and vice versa."
    )

    # ---- Top 10 Undervalued / Top 10 Overpaid ----
    undervalued = df[df["MARKET_STATUS"] == "Undervalued"].nlargest(10, "CONTRACT_EFFICIENCY").copy()
    overpaid = df[df["MARKET_STATUS"] == "Overpaid"].nsmallest(10, "CONTRACT_EFFICIENCY").copy()

    # Fallback if not enough tagged
    if len(undervalued) < 5:
        undervalued = df.nlargest(10, "CONTRACT_EFFICIENCY").copy()
    if len(overpaid) < 5:
        overpaid = df.nsmallest(10, "CONTRACT_EFFICIENCY").copy()

    col_uv, col_op = st.columns(2)

    with col_uv:
        st.subheader("Top 10 Undervalued Players")
        undervalued["Sal_M"] = undervalued["SALARY_2425"] / 1_000_000
        undervalued["BES_r"] = undervalued["BES"].round(1)

        fig_uv = px.bar(
            undervalued.sort_values("CONTRACT_EFFICIENCY"),
            x="CONTRACT_EFFICIENCY",
            y="PLAYER_NAME",
            orientation="h",
            color="BES_r",
            color_continuous_scale=[[0, "#003300"], [1, "#00CC44"]],
            text=undervalued.sort_values("CONTRACT_EFFICIENCY").apply(
                lambda r: f"BES {r['BES']:.1f} | ${r['SALARY_2425']/1_000_000:.1f}M", axis=1
            ),
            title="Most Undervalued Contracts",
            labels={"CONTRACT_EFFICIENCY": "Contract Efficiency Percentile", "PLAYER_NAME": ""},
            **CHART_DEFAULTS,
        )
        fig_uv.update_layout(height=400, showlegend=False, coloraxis_showscale=False)
        st.plotly_chart(fig_uv, use_container_width=True)

    with col_op:
        st.subheader("Top 10 Overpaid Players")
        overpaid["Sal_M"] = overpaid["SALARY_2425"] / 1_000_000
        overpaid["BES_r"] = overpaid["BES"].round(1)

        fig_op = px.bar(
            overpaid.sort_values("CONTRACT_EFFICIENCY", ascending=False),
            x="CONTRACT_EFFICIENCY",
            y="PLAYER_NAME",
            orientation="h",
            color="BES_r",
            color_continuous_scale=[[0, "#CC0000"], [1, "#880000"]],
            text=overpaid.sort_values("CONTRACT_EFFICIENCY", ascending=False).apply(
                lambda r: f"BES {r['BES']:.1f} | ${r['SALARY_2425']/1_000_000:.1f}M", axis=1
            ),
            title="Most Overpaid Contracts",
            labels={"CONTRACT_EFFICIENCY": "Contract Efficiency Percentile", "PLAYER_NAME": ""},
            **CHART_DEFAULTS,
        )
        fig_op.update_layout(height=400, showlegend=False, coloraxis_showscale=False)
        st.plotly_chart(fig_op, use_container_width=True)

    st.divider()

    # ---- Value Per Dollar scatter ----
    st.subheader("Value Per Dollar Leaders")

    vpd_df = df.copy()
    vpd_df["Salary ($M)"] = vpd_df["SALARY_2425"] / 1_000_000
    vpd_df["Is_POR"] = vpd_df["TEAM_ABBREVIATION"] == "POR"
    vpd_df["Marker_Size"] = vpd_df["MIN"].clip(8, 38)

    fig_vpd = px.scatter(
        vpd_df[~vpd_df["Is_POR"]],
        x="Salary ($M)",
        y="BES",
        color="CONTRACT_EFFICIENCY",
        size="Marker_Size",
        size_max=15,
        hover_name="PLAYER_NAME",
        hover_data={"TEAM_ABBREVIATION": True, "BES": ":.1f", "CONTRACT_EFFICIENCY": ":.1f"},
        color_continuous_scale="RdYlGn",
        labels={"BES": "Blazer Edge Score", "CONTRACT_EFFICIENCY": "Efficiency Percentile"},
        title="Value Per Dollar — All Players (Blazers highlighted separately)",
        **CHART_DEFAULTS,
    )

    # Overlay Blazers
    por_vpd = vpd_df[vpd_df["Is_POR"]]
    fig_vpd.add_trace(
        go.Scatter(
            x=por_vpd["Salary ($M)"],
            y=por_vpd["BES"],
            mode="markers+text",
            marker=dict(symbol="diamond", size=14, color=BLAZERS_RED,
                        line=dict(width=2, color="white")),
            text=por_vpd["PLAYER_NAME"].str.split().str[-1],
            textposition="top center",
            textfont=dict(color=BLAZERS_RED, size=10),
            name="Trail Blazers",
            hovertemplate="<b>%{text}</b><br>BES: %{y:.1f}<br>Salary: $%{x:.1f}M<extra></extra>",
        )
    )
    fig_vpd.update_layout(height=500)
    st.plotly_chart(fig_vpd, use_container_width=True)

    # ---- Blazers Cap Efficiency ----
    st.subheader("Blazers Cap Efficiency — League Ranking")

    por_eff = df[df["TEAM_ABBREVIATION"] == "POR"][
        ["PLAYER_NAME", "BES", "SALARY_2425", "CONTRACT_EFFICIENCY", "MARKET_STATUS"]
    ].copy()
    por_eff = por_eff.sort_values("CONTRACT_EFFICIENCY", ascending=False)
    por_eff["League Percentile"] = por_eff["CONTRACT_EFFICIENCY"].round(1)
    por_eff["BES"] = por_eff["BES"].round(1)
    por_eff["Salary"] = por_eff["SALARY_2425"].apply(lambda s: f"${s/1_000_000:.1f}M")

    st.dataframe(
        por_eff[["PLAYER_NAME", "BES", "Salary", "League Percentile", "MARKET_STATUS"]].reset_index(drop=True),
        use_container_width=True,
    )

    # Worst contract cap opportunity
    if not por_eff.empty:
        worst = por_eff.iloc[-1]
        worst_sal = worst["SALARY_2425"]
        st.subheader("Cap Space Opportunity")
        st.markdown(
            f"Trading **{worst['PLAYER_NAME']}** (BES: {worst['BES']:.1f}, {worst['Salary']}) — "
            f"the Blazers' least efficient contract by value — would free up approximately "
            f"**${worst_sal/1_000_000:.1f}M** in cap flexibility, enabling pursuit of higher-impact "
            f"additions."
        )

    # Blazers efficiency bar chart
    fig_por_eff = px.bar(
        por_eff.sort_values("League Percentile"),
        x="League Percentile",
        y="PLAYER_NAME",
        orientation="h",
        color="League Percentile",
        color_continuous_scale=[[0, "#660000"], [0.5, "#888888"], [1, "#00AA44"]],
        text="League Percentile",
        title="Blazers Players — Contract Efficiency League Percentile",
        labels={"PLAYER_NAME": "", "League Percentile": "Contract Efficiency Percentile"},
        **CHART_DEFAULTS,
    )
    fig_por_eff.update_layout(height=max(300, len(por_eff) * 40 + 80), showlegend=False, coloraxis_showscale=False)
    st.plotly_chart(fig_por_eff, use_container_width=True)

# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------
st.divider()
st.markdown(
    "<p style='text-align:center; color:#555; font-size:0.8em;'>"
    "Built with Python · nba_api · scikit-learn · Blazer Edge v1.0 · "
    "Data sourced from NBA Stats API"
    "</p>",
    unsafe_allow_html=True,
)
