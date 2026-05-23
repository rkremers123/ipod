"""
fetcher.py — NBA API data fetching with caching and fallback simulation
"""

import os
import time
import pickle
import datetime
import numpy as np
import pandas as pd

CACHE_DIR = os.path.join(os.path.dirname(__file__), ".cache")
os.makedirs(CACHE_DIR, exist_ok=True)

CACHE_TTL_HOURS = 24


def _cache_path(name: str) -> str:
    return os.path.join(CACHE_DIR, f"{name}.pkl")


def _load_cache(name: str):
    path = _cache_path(name)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "rb") as f:
            cached = pickle.load(f)
        age = datetime.datetime.now() - cached["timestamp"]
        if age.total_seconds() < CACHE_TTL_HOURS * 3600:
            return cached["data"]
    except Exception:
        pass
    return None


def _save_cache(name: str, data):
    path = _cache_path(name)
    try:
        with open(path, "wb") as f:
            pickle.dump({"timestamp": datetime.datetime.now(), "data": data}, f)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Salary data (hardcoded approximate 2024-25 values)
# ---------------------------------------------------------------------------

SALARY_DATA = {
    "Stephen Curry": 55760000,
    "LeBron James": 51415938,
    "Kevin Durant": 51179890,
    "Nikola Jokic": 47607350,
    "Giannis Antetokounmpo": 45640084,
    "Joel Embiid": 47607350,
    "Jayson Tatum": 34500000,
    "Damian Lillard": 49205800,
    "Luka Doncic": 43031160,
    "Devin Booker": 36016200,
    "Bam Adebayo": 32600490,
    "Anthony Davis": 43219440,
    "Kawhi Leonard": 48787980,
    "Paul George": 48787980,
    "Zion Williamson": 37094502,
    "Ja Morant": 33000040,
    "Trae Young": 37100000,
    "Donovan Mitchell": 35277000,
    "Tyrese Haliburton": 26000000,
    "De'Aaron Fox": 30351500,
    "Darius Garland": 37096500,
    "Karl-Anthony Towns": 33833400,
    "Rudy Gobert": 41000000,
    "Anthony Edwards": 10396680,
    "Cade Cunningham": 26200000,
    "Evan Mobley": 10899480,
    "Franz Wagner": 8421000,
    "Scottie Barnes": 7400000,
    "Paolo Banchero": 10280400,
    "Jalen Brunson": 24000000,
    "Fred VanVleet": 42978840,
    "Anfernee Simons": 24375000,
    "Jerami Grant": 21000000,
    "Scoot Henderson": 10050120,
    "Deandre Ayton": 32608696,
    "Shaedon Sharpe": 5200000,
    "Toumani Camara": 1900000,
    "Jabari Walker": 1900000,
    "Robert Williams": 12000000,
    "Deni Avdija": 13000000,
    "Malcolm Brogdon": 22000000,
    "OG Anunoby": 36000000,
    "Julius Randle": 28235380,
    "RJ Barrett": 22600000,
    "Pascal Siakam": 37967448,
    "Tyrese Maxey": 13500000,
    "De'Anthony Melton": 8000000,
    "Kyle Lowry": 29700000,
    "Jimmy Butler": 48798750,
    "Tyler Herro": 29050000,
    "Duncan Robinson": 18000000,
    "Draymond Green": 22273974,
    "Klay Thompson": 43219440,
    "Andrew Wiggins": 23250000,
    "Jordan Poole": 28000000,
    "Chris Paul": 30800000,
    "Demar DeRozan": 27285714,
    "Zach LaVine": 43000000,
    "Nikola Vucevic": 20000000,
    "Coby White": 5400000,
    "Brandon Ingram": 36016200,
    "CJ McCollum": 32428082,
    "Jonas Valanciunas": 13500000,
    "Herb Jones": 12000000,
    "Jaylen Brown": 29600000,
    "Marcus Smart": 20000000,
    "Al Horford": 10500000,
    "Grant Williams": 13000000,
    "Jarrett Allen": 20000000,
    "Caris LeVert": 12000000,
    "Lauri Markkanen": 21600000,
    "Jordan Clarkson": 12750000,
    "Mike Conley": 8000000,
    "Bogdan Bogdanovic": 18000000,
    "John Collins": 26000000,
    "Clint Capela": 13000000,
    "Dejounte Murray": 25000000,
    "Jalen Johnson": 4800000,
    "James Harden": 35640000,
    "Russell Westbrook": 3600000,
    "Kristaps Porzingis": 36016200,
    "Jrue Holiday": 36861707,
    "Khris Middleton": 33200000,
    "Brook Lopez": 13000000,
    "Bobby Portis": 11500000,
    "Patrick Beverley": 3600000,
    "Desmond Bane": 23600000,
    "Jaren Jackson Jr": 24590750,
    "Dillon Brooks": 20000000,
    "Vince Williams": 2500000,
    "Ivica Zubac": 10000000,
    "Nicolas Batum": 3500000,
    "Brandon Clarke": 9500000,
    "D'Angelo Russell": 18000000,
    "Austin Reaves": 13000000,
    "Rui Hachimura": 17000000,
    "Luguentz Dort": 12900000,
    "Shai Gilgeous-Alexander": 33393450,
    "SGA": 33393450,
    "Josh Giddey": 5000000,
    "Aaron Wiggins": 2000000,
    "Isaiah Hartenstein": 16000000,
    "Josh Hart": 12960000,
    "Donte DiVincenzo": 9000000,
    "Mitchell Robinson": 14500000,
    "Precious Achiuwa": 5200000,
    "Dennis Schroder": 13000000,
    "Cam Johnson": 15400000,
    "Mikal Bridges": 18000000,
    "Ben Simmons": 37893408,
    "Spencer Dinwiddie": 9500000,
    "Seth Curry": 8000000,
    "Dorian Finney-Smith": 13000000,
    "Wendell Carter": 14700000,
    "Cole Anthony": 13500000,
    "Markelle Fultz": 16000000,
    "Jonathan Isaac": 17000000,
    "Hamidou Diallo": 4000000,
    "Kevin Huerter": 16000000,
    "Myles Turner": 18000000,
    "Buddy Hield": 10000000,
    "Isaiah Jackson": 4000000,
    "Victor Wembanyama": 12215640,
    "Keldon Johnson": 19000000,
    "Devin Vassell": 16000000,
    "Tre Jones": 7000000,
}


def get_salary_data() -> pd.DataFrame:
    """Return salary DataFrame with PLAYER_NAME and SALARY_2425 columns."""
    rows = [{"PLAYER_NAME": name, "SALARY_2425": salary}
            for name, salary in SALARY_DATA.items()]
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Simulated data fallback
# ---------------------------------------------------------------------------

REAL_PLAYERS = [
    ("Stephen Curry", "GSW"),
    ("LeBron James", "LAL"),
    ("Kevin Durant", "PHX"),
    ("Nikola Jokic", "DEN"),
    ("Giannis Antetokounmpo", "MIL"),
    ("Joel Embiid", "PHI"),
    ("Jayson Tatum", "BOS"),
    ("Damian Lillard", "MIL"),
    ("Luka Doncic", "DAL"),
    ("Devin Booker", "PHX"),
    ("Bam Adebayo", "MIA"),
    ("Anthony Davis", "LAL"),
    ("Ja Morant", "MEM"),
    ("Trae Young", "ATL"),
    ("Donovan Mitchell", "CLE"),
    ("Tyrese Haliburton", "IND"),
    ("Shai Gilgeous-Alexander", "OKC"),
    ("Anthony Edwards", "MIN"),
    ("Cade Cunningham", "DET"),
    ("Evan Mobley", "CLE"),
    ("Paolo Banchero", "ORL"),
    ("Victor Wembanyama", "SAS"),
    ("Franz Wagner", "ORL"),
    ("Scottie Barnes", "TOR"),
    ("Jalen Brunson", "NYK"),
    # Blazers
    ("Anfernee Simons", "POR"),
    ("Jerami Grant", "POR"),
    ("Scoot Henderson", "POR"),
    ("Deandre Ayton", "POR"),
    ("Shaedon Sharpe", "POR"),
    ("Toumani Camara", "POR"),
    ("Jabari Walker", "POR"),
    ("Robert Williams", "POR"),
    ("Deni Avdija", "POR"),
    # More real players
    ("Jaylen Brown", "BOS"),
    ("Jrue Holiday", "BOS"),
    ("Al Horford", "BOS"),
    ("Darius Garland", "CLE"),
    ("Karl-Anthony Towns", "NYK"),
    ("Julius Randle", "NYK"),
    ("OG Anunoby", "NYK"),
    ("Jalen Brunson", "NYK"),
    ("Pascal Siakam", "IND"),
    ("Myles Turner", "IND"),
    ("Desmond Bane", "MEM"),
    ("Jaren Jackson Jr", "MEM"),
    ("Rudy Gobert", "MIN"),
    ("Lauri Markkanen", "UTA"),
    ("Zach LaVine", "CHI"),
    ("Fred VanVleet", "HOU"),
]

# Player-specific realistic stats overrides
PLAYER_STAT_OVERRIDES = {
    "Nikola Jokic": dict(PIE=0.250, PTS=27.4, AST=9.0, REB=12.4, STL=1.4, BLK=0.9, NET_RATING=12.0, USG_PCT=0.295, TS_PCT=0.665, OFF_RATING=125.0, DEF_RATING=113.0, AST_PCT=0.415, OREB_PCT=0.10, DREB_PCT=0.28, MIN=34.0),
    "Stephen Curry": dict(PIE=0.220, PTS=28.4, AST=6.0, REB=4.5, STL=1.2, BLK=0.4, NET_RATING=10.0, USG_PCT=0.320, TS_PCT=0.680, OFF_RATING=122.0, DEF_RATING=112.0, AST_PCT=0.30, FG3_PCT=0.422, MIN=33.0),
    "Giannis Antetokounmpo": dict(PIE=0.240, PTS=31.8, AST=6.0, REB=11.5, STL=1.1, BLK=1.2, NET_RATING=8.0, USG_PCT=0.340, TS_PCT=0.620, OFF_RATING=120.0, DEF_RATING=112.0, MIN=35.0),
    "Victor Wembanyama": dict(PIE=0.190, PTS=23.8, AST=3.5, REB=10.3, STL=1.2, BLK=3.6, NET_RATING=4.0, USG_PCT=0.275, TS_PCT=0.580, OFF_RATING=116.0, DEF_RATING=112.0, BLK_PCT=0.12, MIN=32.0),
    "LeBron James": dict(PIE=0.210, PTS=25.7, AST=8.3, REB=7.3, STL=1.3, BLK=0.5, NET_RATING=6.0, USG_PCT=0.285, TS_PCT=0.610, OFF_RATING=118.0, DEF_RATING=112.0, MIN=35.0),
    "Luka Doncic": dict(PIE=0.215, PTS=32.4, AST=9.8, REB=9.0, STL=1.4, BLK=0.5, NET_RATING=5.0, USG_PCT=0.360, TS_PCT=0.590, OFF_RATING=117.0, DEF_RATING=112.0, MIN=36.0),
    "Joel Embiid": dict(PIE=0.220, PTS=34.7, AST=5.6, REB=11.0, STL=1.0, BLK=1.7, NET_RATING=9.0, USG_PCT=0.370, TS_PCT=0.640, OFF_RATING=122.0, DEF_RATING=113.0, MIN=34.0),
    "Jayson Tatum": dict(PIE=0.175, PTS=26.9, AST=4.9, REB=8.1, STL=1.0, BLK=0.6, NET_RATING=7.0, USG_PCT=0.300, TS_PCT=0.590, OFF_RATING=120.0, DEF_RATING=113.0, MIN=36.0),
    "Shai Gilgeous-Alexander": dict(PIE=0.210, PTS=30.1, AST=6.2, REB=5.5, STL=2.0, BLK=0.9, NET_RATING=11.0, USG_PCT=0.330, TS_PCT=0.640, OFF_RATING=122.0, DEF_RATING=111.0, STL_PCT=0.027, MIN=33.0),
    "Devin Booker": dict(PIE=0.165, PTS=27.1, AST=6.9, REB=4.5, STL=0.9, BLK=0.3, NET_RATING=3.0, USG_PCT=0.295, TS_PCT=0.600, OFF_RATING=117.0, DEF_RATING=114.0, MIN=34.0),
    "Anthony Edwards": dict(PIE=0.165, PTS=25.9, AST=5.1, REB=5.4, STL=1.3, BLK=0.5, NET_RATING=6.0, USG_PCT=0.310, TS_PCT=0.570, OFF_RATING=118.0, DEF_RATING=112.0, MIN=35.0),
    "Damian Lillard": dict(PIE=0.165, PTS=24.3, AST=7.4, REB=4.4, STL=0.9, BLK=0.3, NET_RATING=2.0, USG_PCT=0.305, TS_PCT=0.600, OFF_RATING=116.0, DEF_RATING=114.0, FG3_PCT=0.385, MIN=34.0),
    # Blazers
    "Anfernee Simons": dict(PIE=0.130, PTS=21.5, AST=4.2, REB=3.5, STL=0.9, BLK=0.3, NET_RATING=-5.0, USG_PCT=0.270, TS_PCT=0.570, OFF_RATING=111.0, DEF_RATING=116.0, FG3_PCT=0.380, MIN=32.0),
    "Scoot Henderson": dict(PIE=0.110, PTS=15.7, AST=6.0, REB=3.9, STL=1.1, BLK=0.3, NET_RATING=-7.0, USG_PCT=0.220, TS_PCT=0.520, OFF_RATING=108.0, DEF_RATING=115.0, AST_PCT=0.30, MIN=29.0),
    "Deandre Ayton": dict(PIE=0.140, PTS=17.0, AST=1.7, REB=10.5, STL=0.7, BLK=1.0, NET_RATING=-6.0, USG_PCT=0.200, TS_PCT=0.595, OFF_RATING=109.0, DEF_RATING=115.0, OREB_PCT=0.115, DREB_PCT=0.24, MIN=31.0),
    "Shaedon Sharpe": dict(PIE=0.120, PTS=18.3, AST=2.8, REB=3.5, STL=1.0, BLK=0.4, NET_RATING=-6.5, USG_PCT=0.255, TS_PCT=0.565, OFF_RATING=110.0, DEF_RATING=116.5, FG3_PCT=0.370, MIN=31.0),
    "Jerami Grant": dict(PIE=0.130, PTS=15.8, AST=2.2, REB=4.2, STL=1.0, BLK=0.9, NET_RATING=-5.5, USG_PCT=0.230, TS_PCT=0.555, OFF_RATING=109.0, DEF_RATING=114.5, MIN=30.0),
    "Deni Avdija": dict(PIE=0.120, PTS=14.4, AST=4.5, REB=5.5, STL=1.2, BLK=0.5, NET_RATING=-5.0, USG_PCT=0.195, TS_PCT=0.545, OFF_RATING=110.0, DEF_RATING=115.0, MIN=30.0),
    "Robert Williams": dict(PIE=0.130, PTS=9.5, AST=1.2, REB=8.8, STL=0.6, BLK=2.2, NET_RATING=-4.0, USG_PCT=0.140, TS_PCT=0.620, OFF_RATING=111.0, DEF_RATING=115.0, BLK_PCT=0.09, OREB_PCT=0.14, MIN=24.0),
    "Toumani Camara": dict(PIE=0.105, PTS=9.2, AST=2.1, REB=4.8, STL=1.3, BLK=0.5, NET_RATING=-6.0, USG_PCT=0.155, TS_PCT=0.540, OFF_RATING=108.5, DEF_RATING=114.5, MIN=24.0),
    "Jabari Walker": dict(PIE=0.095, PTS=7.5, AST=1.8, REB=5.5, STL=0.8, BLK=0.6, NET_RATING=-8.0, USG_PCT=0.145, TS_PCT=0.510, OFF_RATING=107.0, DEF_RATING=115.0, MIN=20.0),
}


def _generate_simulated_data() -> pd.DataFrame:
    """Generate realistic simulated NBA player data when API fails."""
    rng = np.random.default_rng(42)

    rows = []
    pid = 1000

    for name, team in REAL_PLAYERS:
        overrides = PLAYER_STAT_OVERRIDES.get(name, {})
        gp = int(rng.integers(40, 75))
        min_val = float(overrides.get("MIN", rng.uniform(18, 36)))
        pts = float(overrides.get("PTS", rng.uniform(6, 30)))
        ast = float(overrides.get("AST", rng.uniform(0.5, 9)))
        reb = float(overrides.get("REB", rng.uniform(2, 11)))
        oreb = float(overrides.get("OREB", rng.uniform(0.3, 3.5)))
        dreb = reb - oreb
        stl = float(overrides.get("STL", rng.uniform(0.4, 2.0)))
        blk = float(overrides.get("BLK", rng.uniform(0.2, 3.5)))
        tov = float(overrides.get("TOV", rng.uniform(0.8, 4.0)))
        fg_pct = float(overrides.get("FG_PCT", rng.uniform(0.42, 0.58)))
        fg3_pct = float(overrides.get("FG3_PCT", rng.uniform(0.32, 0.42)))
        ft_pct = float(overrides.get("FT_PCT", rng.uniform(0.70, 0.90)))
        fga = pts / max(fg_pct * 2, 0.01)
        fta = pts * rng.uniform(0.1, 0.4)
        usg = float(overrides.get("USG_PCT", rng.uniform(0.14, 0.35)))
        ts_pct = float(overrides.get("TS_PCT", rng.uniform(0.50, 0.65)))
        net_rating = float(overrides.get("NET_RATING", rng.uniform(-10, 12)))
        off_rating = float(overrides.get("OFF_RATING", 110 + net_rating * 0.5 + rng.uniform(-3, 3)))
        def_rating = off_rating - net_rating
        pie = float(overrides.get("PIE", rng.uniform(0.08, 0.22)))
        ast_pct = float(overrides.get("AST_PCT", rng.uniform(0.08, 0.40)))
        oreb_pct = float(overrides.get("OREB_PCT", rng.uniform(0.02, 0.14)))
        dreb_pct = float(overrides.get("DREB_PCT", rng.uniform(0.10, 0.30)))
        stl_pct = float(overrides.get("STL_PCT", rng.uniform(0.01, 0.03)))
        blk_pct = float(overrides.get("BLK_PCT", rng.uniform(0.01, 0.10)))
        tov_pct = float(overrides.get("TOV_PCT", rng.uniform(0.08, 0.20)))
        e_off = off_rating + rng.uniform(-1, 1)
        e_def = def_rating + rng.uniform(-1, 1)
        e_net = e_off - e_def

        rows.append({
            "PLAYER_ID": pid, "PLAYER_NAME": name, "TEAM_ABBREVIATION": team,
            "GP": gp, "MIN": min_val, "PTS": pts, "AST": ast, "REB": reb,
            "OREB": oreb, "DREB": dreb, "STL": stl, "BLK": blk, "TOV": tov,
            "FG_PCT": fg_pct, "FG3_PCT": fg3_pct, "FT_PCT": ft_pct,
            "FGA": fga, "FTA": fta,
            "USG_PCT": usg, "TS_PCT": ts_pct,
            "NET_RATING": net_rating, "OFF_RATING": off_rating, "DEF_RATING": def_rating,
            "PIE": pie, "AST_PCT": ast_pct, "OREB_PCT": oreb_pct, "DREB_PCT": dreb_pct,
            "STL_PCT": stl_pct, "BLK_PCT": blk_pct, "TOV_PCT": tov_pct,
            "E_OFF_RATING": e_off, "E_DEF_RATING": e_def, "E_NET_RATING": e_net,
        })
        pid += 1

    # Generate ~150 additional generic players
    teams = ["ATL", "BOS", "BKN", "CHA", "CHI", "CLE", "DAL", "DEN", "DET",
             "GSW", "HOU", "IND", "LAC", "LAL", "MEM", "MIA", "MIL", "MIN",
             "NOP", "NYK", "OKC", "ORL", "PHI", "PHX", "POR", "SAC", "SAS",
             "TOR", "UTA", "WAS"]

    for i in range(1, 166):
        team = teams[i % len(teams)]
        gp = int(rng.integers(10, 75))
        min_val = float(rng.uniform(8, 34))
        pts = float(rng.uniform(2, 22))
        ast = float(rng.uniform(0.3, 7))
        reb = float(rng.uniform(1, 9))
        oreb = float(rng.uniform(0.2, 3))
        dreb = reb - oreb
        stl = float(rng.uniform(0.2, 1.8))
        blk = float(rng.uniform(0.1, 2.0))
        tov = float(rng.uniform(0.5, 3.5))
        fg_pct = float(rng.uniform(0.38, 0.56))
        fg3_pct = float(rng.uniform(0.28, 0.40))
        ft_pct = float(rng.uniform(0.65, 0.88))
        fga = pts / max(fg_pct * 2, 0.01)
        fta = pts * rng.uniform(0.1, 0.35)
        usg = float(rng.uniform(0.10, 0.28))
        ts_pct = float(rng.uniform(0.48, 0.62))
        net_rating = float(rng.uniform(-12, 8))
        off_rating = float(110 + net_rating * 0.5 + rng.uniform(-3, 3))
        def_rating = off_rating - net_rating
        pie = float(rng.uniform(0.05, 0.17))
        ast_pct = float(rng.uniform(0.05, 0.30))
        oreb_pct = float(rng.uniform(0.01, 0.12))
        dreb_pct = float(rng.uniform(0.08, 0.25))
        stl_pct = float(rng.uniform(0.005, 0.025))
        blk_pct = float(rng.uniform(0.005, 0.08))
        tov_pct = float(rng.uniform(0.08, 0.20))
        e_off = off_rating + rng.uniform(-1, 1)
        e_def = def_rating + rng.uniform(-1, 1)
        e_net = e_off - e_def

        rows.append({
            "PLAYER_ID": pid, "PLAYER_NAME": f"Player_{i:03d}", "TEAM_ABBREVIATION": team,
            "GP": gp, "MIN": min_val, "PTS": pts, "AST": ast, "REB": reb,
            "OREB": oreb, "DREB": dreb, "STL": stl, "BLK": blk, "TOV": tov,
            "FG_PCT": fg_pct, "FG3_PCT": fg3_pct, "FT_PCT": ft_pct,
            "FGA": fga, "FTA": fta,
            "USG_PCT": usg, "TS_PCT": ts_pct,
            "NET_RATING": net_rating, "OFF_RATING": off_rating, "DEF_RATING": def_rating,
            "PIE": pie, "AST_PCT": ast_pct, "OREB_PCT": oreb_pct, "DREB_PCT": dreb_pct,
            "STL_PCT": stl_pct, "BLK_PCT": blk_pct, "TOV_PCT": tov_pct,
            "E_OFF_RATING": e_off, "E_DEF_RATING": e_def, "E_NET_RATING": e_net,
        })
        pid += 1

    df = pd.DataFrame(rows)
    df = df[df["GP"] >= 10].reset_index(drop=True)
    return df


# ---------------------------------------------------------------------------
# API fetching
# ---------------------------------------------------------------------------

def _fetch_player_stats_from_api(season: str) -> pd.DataFrame:
    """Attempt to fetch from nba_api; raises on any failure."""
    from nba_api.stats.endpoints import leaguedashplayerstats

    base = leaguedashplayerstats.LeagueDashPlayerStats(
        season=season,
        measure_type_detailed_defense="Base",
        per_mode_simple="PerGame",
        timeout=30,
    )
    base_df = base.get_data_frames()[0]
    time.sleep(0.6)

    adv = leaguedashplayerstats.LeagueDashPlayerStats(
        season=season,
        measure_type_detailed_defense="Advanced",
        per_mode_simple="PerGame",
        timeout=30,
    )
    adv_df = adv.get_data_frames()[0]
    time.sleep(0.6)

    # Merge: drop duplicate columns from advanced except key
    adv_cols = [c for c in adv_df.columns if c not in base_df.columns or c == "PLAYER_ID"]
    merged = base_df.merge(adv_df[adv_cols], on="PLAYER_ID", how="left")
    merged = merged[merged["GP"] >= 10].reset_index(drop=True)

    # Ensure expected columns exist
    for col in ["USG_PCT", "TS_PCT", "NET_RATING", "OFF_RATING", "DEF_RATING",
                "PIE", "AST_PCT", "OREB_PCT", "DREB_PCT", "STL_PCT", "BLK_PCT", "TOV_PCT",
                "E_OFF_RATING", "E_DEF_RATING", "E_NET_RATING"]:
        if col not in merged.columns:
            merged[col] = 0.0

    # Ensure FG3_PCT exists
    if "FG3_PCT" not in merged.columns:
        merged["FG3_PCT"] = 0.35

    return merged


def get_player_stats(season: str = "2024-25") -> pd.DataFrame:
    """
    Fetch player stats for the given season with caching.
    Falls back to simulated data on any error.
    """
    cache_key = f"player_stats_{season}"
    cached = _load_cache(cache_key)
    if cached is not None:
        return cached

    try:
        df = _fetch_player_stats_from_api(season)
        _save_cache(cache_key, df)
        return df
    except Exception:
        df = _generate_simulated_data()
        # Don't cache simulated data (try fresh next time)
        return df


def get_team_stats(season: str = "2024-25") -> pd.DataFrame:
    """Fetch team stats with caching, fallback to simulated."""
    cache_key = f"team_stats_{season}"
    cached = _load_cache(cache_key)
    if cached is not None:
        return cached

    try:
        from nba_api.stats.endpoints import leaguedashteamstats
        ts = leaguedashteamstats.LeagueDashTeamStats(
            season=season,
            measure_type_detailed_defense="Base",
            per_mode_simple="PerGame",
            timeout=30,
        )
        df = ts.get_data_frames()[0]
        _save_cache(cache_key, df)
        return df
    except Exception:
        # Minimal simulated team stats
        teams = ["ATL", "BOS", "BKN", "CHA", "CHI", "CLE", "DAL", "DEN", "DET",
                 "GSW", "HOU", "IND", "LAC", "LAL", "MEM", "MIA", "MIL", "MIN",
                 "NOP", "NYK", "OKC", "ORL", "PHI", "PHX", "POR", "SAC", "SAS",
                 "TOR", "UTA", "WAS"]
        rng = np.random.default_rng(42)
        rows = []
        for team in teams:
            rows.append({
                "TEAM_ABBREVIATION": team,
                "GP": 82,
                "W": int(rng.integers(20, 62)),
                "PTS": float(rng.uniform(108, 122)),
                "REB": float(rng.uniform(42, 48)),
                "AST": float(rng.uniform(23, 30)),
            })
        return pd.DataFrame(rows)
