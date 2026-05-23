"""
models.py — Player value scoring, clustering, and trade analysis
"""

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans


# ---------------------------------------------------------------------------
# Blazer Edge Score (BES)
# ---------------------------------------------------------------------------

def compute_bes(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute the Blazer Edge Score — a composite player value metric on a
    0-100 scale where 50 ≈ league average.
    """
    df = df.copy()

    # 1. Minutes weight
    min_weight = np.clip(df["MIN"] / 30.0, 0.3, 1.0)

    # 2. Helper: safe min-max normalise
    def _norm(series: pd.Series) -> pd.Series:
        lo, hi = series.min(), series.max()
        if hi == lo:
            return pd.Series(0.5, index=series.index)
        return (series - lo) / (hi - lo)

    # 3. PIE score
    pie_col = df["PIE"].fillna(df["PIE"].median() if df["PIE"].notna().any() else 0.0)
    pie_norm = _norm(pie_col)

    # 4. Efficiency (TS%)
    ts_col = df["TS_PCT"].fillna(0.0)
    eff_norm = _norm(ts_col)

    # 5. Net rating (clip extreme values)
    net_col = df["NET_RATING"].fillna(0.0).clip(-20, 20)
    net_norm = _norm(net_col)

    # 6. Defensive score
    def_raw = df["STL_PCT"].fillna(0.0) + df["BLK_PCT"].fillna(0.0)
    def_norm = _norm(def_raw)

    # 7. Composite raw
    composite_raw = (
        0.35 * pie_norm
        + 0.25 * net_norm
        + 0.25 * eff_norm
        + 0.15 * def_norm
    )

    # 8. Apply minutes weight
    raw_bes = composite_raw * min_weight

    # 9. Scale to 0-100
    lo, hi = raw_bes.min(), raw_bes.max()
    if hi == lo:
        bes = pd.Series(50.0, index=df.index)
    else:
        bes = 100.0 * (raw_bes - lo) / (hi - lo)

    # 10. Clamp
    df["BES"] = bes.clip(0, 100)
    return df


# ---------------------------------------------------------------------------
# Contract Efficiency
# ---------------------------------------------------------------------------

def compute_contract_efficiency(
    df: pd.DataFrame, salary_df: pd.DataFrame
) -> pd.DataFrame:
    """
    Merge salary data and compute contract efficiency metrics.
    """
    df = df.copy()
    salary_df = salary_df.copy()

    # Normalise names for fuzzy merge
    salary_df["_name_norm"] = salary_df["PLAYER_NAME"].str.strip().str.lower()
    df["_name_norm"] = df["PLAYER_NAME"].str.strip().str.lower()

    salary_lookup = dict(
        zip(salary_df["_name_norm"], salary_df["SALARY_2425"])
    )

    def _lookup_salary(row):
        key = row["_name_norm"]
        if key in salary_lookup:
            return salary_lookup[key]
        # Estimate from BES
        return 2_000_000 + (row["BES"] / 100.0) * 20_000_000

    df["SALARY_2425"] = df.apply(_lookup_salary, axis=1)
    df.drop(columns=["_name_norm"], inplace=True)

    # Value per dollar
    df["VALUE_PER_DOLLAR"] = df["BES"] / (df["SALARY_2425"] / 1_000_000).clip(lower=0.5)

    # Percentile rank → CONTRACT_EFFICIENCY 0-100
    df["CONTRACT_EFFICIENCY"] = df["VALUE_PER_DOLLAR"].rank(pct=True) * 100

    # Market status
    def _market_status(row):
        sal = row["SALARY_2425"]
        bes = row["BES"]
        if bes > 70:
            return "Star"
        if sal > 20_000_000 and bes < 45:
            return "Overpaid"
        if sal < 10_000_000 and bes > 55:
            return "Undervalued"
        return "Market Rate"

    df["MARKET_STATUS"] = df.apply(_market_status, axis=1)
    return df


# ---------------------------------------------------------------------------
# Player Archetypes via K-Means + PCA
# ---------------------------------------------------------------------------

def compute_archetypes(df: pd.DataFrame) -> tuple:
    """
    Cluster players into 7 archetypes using K-Means on performance features,
    then project to 2D via PCA for visualisation.

    Returns (df_with_archetype_and_pca_coords, archetype_label_dict)
    """
    df = df.copy()

    feature_cols = [
        "USG_PCT", "AST_PCT", "OREB_PCT", "DREB_PCT",
        "STL_PCT", "BLK_PCT", "TOV_PCT", "TS_PCT", "FG3_PCT",
    ]

    # Fill missing values
    X = df[feature_cols].fillna(0).values

    # Standardise
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # PCA → 2D
    pca = PCA(n_components=2, random_state=42)
    X_pca = pca.fit_transform(X_scaled)
    variance_explained = float(pca.explained_variance_ratio_.sum() * 100)

    df["PCA_1"] = X_pca[:, 0]
    df["PCA_2"] = X_pca[:, 1]
    df["PCA_VARIANCE_EXPLAINED"] = variance_explained

    # K-Means
    n_clusters = 7
    km = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    df["CLUSTER"] = km.fit_predict(X_scaled)

    # Map cluster centers back to feature space for labelling
    centers = pd.DataFrame(
        scaler.inverse_transform(km.cluster_centers_),
        columns=feature_cols,
    )

    # Assign archetype labels by cluster center characteristics
    # (greedy: highest of each key metric wins that archetype)
    archetype_labels: dict = {}
    assigned: set = set()

    rules = [
        ("AST_PCT", "Primary Creator"),
        ("BLK_PCT", "Defensive Anchor"),
        ("OREB_PCT", "Glass Eater"),
        ("STL_PCT", "Disruptor"),
        ("USG_PCT", "Volume Scorer"),
        ("TS_PCT", "3&D Wing"),
    ]

    for col, label in rules:
        ranked = centers[col].sort_values(ascending=False)
        for cluster_id in ranked.index:
            if cluster_id not in assigned:
                archetype_labels[cluster_id] = label
                assigned.add(cluster_id)
                break

    # Remaining cluster → Connector
    for cluster_id in range(n_clusters):
        if cluster_id not in archetype_labels:
            archetype_labels[cluster_id] = "Connector"

    df["ARCHETYPE"] = df["CLUSTER"].map(archetype_labels)

    return df, archetype_labels


# ---------------------------------------------------------------------------
# Trade Analyzer
# ---------------------------------------------------------------------------

def analyze_trade(
    team1_players: list,
    team2_players: list,
    df: pd.DataFrame,
) -> dict:
    """
    Analyse a trade between two sets of players.
    team1 = Portland side, team2 = other team's side.

    Returns a dict with BES/salary comparisons and a verdict.
    """

    def _get_player_data(names: list) -> list:
        result = []
        for name in names:
            mask = df["PLAYER_NAME"].str.strip().str.lower() == name.strip().lower()
            match = df[mask]
            if not match.empty:
                row = match.iloc[0]
                result.append({
                    "name": row["PLAYER_NAME"],
                    "bes": round(float(row["BES"]), 1),
                    "salary": float(row["SALARY_2425"]),
                    "age_note": _age_note(row["BES"]),
                })
            else:
                result.append({
                    "name": name,
                    "bes": 40.0,
                    "salary": 5_000_000,
                    "age_note": "Unknown",
                })
        return result

    def _age_note(bes: float) -> str:
        if bes > 75:
            return "Star"
        if bes > 60:
            return "Solid starter"
        if bes > 45:
            return "Rotation player"
        return "Bench player"

    t1_data = _get_player_data(team1_players)
    t2_data = _get_player_data(team2_players)

    t1_bes = sum(p["bes"] for p in t1_data)
    t2_bes = sum(p["bes"] for p in t2_data)
    t1_sal = sum(p["salary"] for p in t1_data)
    t2_sal = sum(p["salary"] for p in t2_data)

    bes_delta = t2_bes - t1_bes  # positive = Portland (team1) gains
    sal_delta = t2_sal - t1_sal  # positive = Portland takes on more salary

    # Verdict
    bes_threshold = 5.0
    if abs(bes_delta) < bes_threshold:
        verdict = "Fair Trade"
    elif bes_delta > 0:
        verdict = "Team A Wins"   # Portland gets better players
    else:
        verdict = "Team B Wins"

    # Human-readable analysis
    if verdict == "Fair Trade":
        analysis = (
            f"This trade is relatively balanced in terms of player value, with a BES difference "
            f"of only {abs(bes_delta):.1f} points. "
            f"Portland {'takes on' if sal_delta > 0 else 'sheds'} "
            f"${abs(sal_delta/1_000_000):.1f}M in salary. "
            f"Consider long-term contract implications and player development trajectories."
        )
    elif verdict == "Team A Wins":
        analysis = (
            f"Portland comes out ahead, gaining {bes_delta:.1f} BES points of value. "
            f"The incoming players represent a meaningful upgrade in production. "
            f"Salary {'increases by' if sal_delta > 0 else 'decreases by'} "
            f"${abs(sal_delta/1_000_000):.1f}M — weigh cap flexibility against immediate value."
        )
    else:
        analysis = (
            f"Portland gives up {abs(bes_delta):.1f} BES points of value in this trade. "
            f"This may be justified if Portland is rebuilding and acquiring assets "
            f"(picks, cap relief). "
            f"Salary {'increases' if sal_delta > 0 else 'decreases'} by "
            f"${abs(sal_delta/1_000_000):.1f}M."
        )

    return {
        "team1_total_bes": round(t1_bes, 1),
        "team2_total_bes": round(t2_bes, 1),
        "team1_total_salary": t1_sal,
        "team2_total_salary": t2_sal,
        "bes_delta": round(bes_delta, 1),
        "salary_delta": sal_delta,
        "verdict": verdict,
        "team1_players": t1_data,
        "team2_players": t2_data,
        "analysis": analysis,
    }
