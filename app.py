import streamlit as st
import pandas as pd
import numpy as np
import requests
import math
import glob
import os
from datetime import datetime, timedelta, date
from urllib.parse import quote
import xml.etree.ElementTree as ET

# ============================================================
# MONITOR NFL — V8
#
# CAMBIOS IMPORTANTES:
# 1) El backtest ya NO usa Elo como sustituto de V6.
# 2) Busca predicciones históricas V6 en CSV.
# 3) La calibración se hace sobre EL FAVORITO DEL MODELO.
# 4) El resultado histórico se cruza con nflverse.
# 5) Si no existe un archivo histórico V6, NO inventa resultados.
# 6) Se mantienen las predicciones actuales 2026.
# 7) El backtest histórico muestra accuracy, Brier, log loss,
#    calibración, resultados por temporada y selección.
# 8) V8 calibra las probabilidades V6 con datos históricos.
# 9) La calibración del backtest usa leave-one-season-out para evitar leakage.
# 10) Las probabilidades actuales 2026 usan la calibración entrenada en todo el histórico.
#
# ARCHIVOS V6 ACEPTADOS:
#   nfl_v6_predictions_2019.csv
#   nfl_v6_predictions_2020.csv
#   ...
#   nfl_v6_predictions_2025.csv
#
# También acepta:
#   nfl_v6_predictions_historical.csv
#   nfl_v6_predictions.csv
#
# COLUMNAS MÍNIMAS PARA HISTÓRICO:
#   team
#   opponent_team
#   model_prob
#   date / game_date / gameday
#
# Si el archivo tiene season, se usa directamente.
# ============================================================

st.set_page_config(
    page_title="Monitor NFL",
    page_icon="🏈",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ============================================================
# CONFIGURACIÓN
# ============================================================

V6_FILE = "nfl_v6_predictions_2026.csv"

NFLVERSE_SCHEDULE_URL = (
    "https://github.com/nflverse/nflverse-data/"
    "releases/download/schedules/schedules.csv"
)

KALSHI_BASE = (
    "https://external-api.kalshi.com/"
    "trade-api/v2/events/"
)

WINDOW_DAYS = 7

OFFICIAL_PROB = 0.63
DIAGNOSTIC_PROB = 0.60
MIN_EDGE = 0.08
MAX_EDGE = 0.20

HISTORICAL_PATTERNS = [
    "nfl_v6_predictions_*.csv",
    "nfl_v6_predictions*.csv",
    "*v6*predictions*.csv",
]

# ============================================================
# PRETEMPORADA 2026
# ============================================================

PRESEASON = [
    ("2026-08-13", "DET", "CIN", "PRE1"),
    ("2026-08-13", "GB",  "PIT", "PRE1"),
    ("2026-08-13", "IND", "NE", "PRE1"),
    ("2026-08-13", "LAC", "HOU", "PRE1"),
    ("2026-08-13", "TEN", "SF", "PRE1"),
    ("2026-08-14", "ARI", "LV", "PRE1"),
    ("2026-08-14", "DEN", "ATL", "PRE1"),
    ("2026-08-14", "TB", "NYJ", "PRE1"),
    ("2026-08-14", "MIA", "WAS", "PRE1"),
    ("2026-08-15", "CAR", "BUF", "PRE1"),
    ("2026-08-15", "CLE", "CHI", "PRE1"),
    ("2026-08-15", "MIN", "NYG", "PRE1"),
    ("2026-08-15", "LAR", "KC", "PRE1"),
    ("2026-08-15", "JAX", "NO", "PRE1"),
    ("2026-08-15", "PHI", "BAL", "PRE1"),
    ("2026-08-16", "DAL", "SEA", "PRE1"),
    ("2026-08-20", "LV", "HOU", "PRE2"),
    ("2026-08-20", "SF", "LAC", "PRE2"),
    ("2026-08-21", "NYJ", "PIT", "PRE2"),
    ("2026-08-21", "CAR", "JAX", "PRE2"),
    ("2026-08-21", "GB", "DEN", "PRE2"),
    ("2026-08-22", "WAS", "DET", "PRE2"),
    ("2026-08-22", "BUF", "CLE", "PRE2"),
    ("2026-08-22", "ATL", "IND", "PRE2"),
    ("2026-08-22", "BAL", "MIN", "PRE2"),
    ("2026-08-22", "NO", "LAR", "PRE2"),
    ("2026-08-22", "NYG", "MIA", "PRE2"),
    ("2026-08-22", "CHI", "CIN", "PRE2"),
    ("2026-08-22", "PHI", "NE", "PRE2"),
    ("2026-08-22", "KC", "TB", "PRE2"),
    ("2026-08-22", "DAL", "ARI", "PRE2"),
    ("2026-08-23", "SEA", "TEN", "PRE2"),
    ("2026-08-27", "PIT", "BUF", "PRE3"),
    ("2026-08-27", "NE", "CLE", "PRE3"),
    ("2026-08-27", "SF", "LV", "PRE3"),
    ("2026-08-27", "LAR", "LAC", "PRE3"),
    ("2026-08-28", "ATL", "MIA", "PRE3"),
    ("2026-08-28", "HOU", "CAR", "PRE3"),
    ("2026-08-28", "WAS", "BAL", "PRE3"),
    ("2026-08-28", "NYG", "NYJ", "PRE3"),
    ("2026-08-28", "TB", "JAX", "PRE3"),
    ("2026-08-28", "NO", "DAL", "PRE3"),
    ("2026-08-28", "ARI", "GB", "PRE3"),
    ("2026-08-28", "SEA", "KC", "PRE3"),
    ("2026-08-28", "CIN", "PHI", "PRE3"),
    ("2026-08-28", "MIN", "DEN", "PRE3"),
    ("2026-08-29", "DET", "IND", "PRE3"),
    ("2026-08-29", "CHI", "TEN", "PRE3"),
]

# ============================================================
# NOMBRES
# ============================================================

TEAM_NAMES = {
    "ARI": "Arizona Cardinals", "ATL": "Atlanta Falcons",
    "BAL": "Baltimore Ravens", "BUF": "Buffalo Bills",
    "CAR": "Carolina Panthers", "CHI": "Chicago Bears",
    "CIN": "Cincinnati Bengals", "CLE": "Cleveland Browns",
    "DAL": "Dallas Cowboys", "DEN": "Denver Broncos",
    "DET": "Detroit Lions", "GB": "Green Bay Packers",
    "HOU": "Houston Texans", "IND": "Indianapolis Colts",
    "JAX": "Jacksonville Jaguars", "KC": "Kansas City Chiefs",
    "LAC": "Los Angeles Chargers", "LAR": "Los Angeles Rams",
    "LV": "Las Vegas Raiders", "MIA": "Miami Dolphins",
    "MIN": "Minnesota Vikings", "NE": "New England Patriots",
    "NO": "New Orleans Saints", "NYG": "New York Giants",
    "NYJ": "New York Jets", "PHI": "Philadelphia Eagles",
    "PIT": "Pittsburgh Steelers", "SEA": "Seattle Seahawks",
    "SF": "San Francisco 49ers", "TB": "Tampa Bay Buccaneers",
    "TEN": "Tennessee Titans", "WAS": "Washington Commanders",
}

ALIASES = {
    "AZ": "ARI", "JAC": "JAX", "JACKSONVILLE": "JAX",
    "LAS VEGAS": "LV", "OAK": "LV", "LA": "LAR",
    "LOS ANGELES RAMS": "LAR", "LOS ANGELES CHARGERS": "LAC",
    "WASHINGTON": "WAS", "WASHINGTON COMMANDERS": "WAS",
    "NEW ENGLAND": "NE", "NEW ORLEANS": "NO",
    "NEW YORK GIANTS": "NYG", "NEW YORK JETS": "NYJ",
    "TAMPA BAY": "TB", "GREEN BAY": "GB", "KANSAS CITY": "KC",
    "SAN FRANCISCO": "SF", "SEATTLE": "SEA", "TENNESSEE": "TEN",
}

# ============================================================
# UTILIDADES
# ============================================================

def norm_team(x):
    if x is None or pd.isna(x):
        return ""
    x = str(x).strip().upper()
    return ALIASES.get(x, x)


def fnum(x):
    try:
        if x is None or pd.isna(x):
            return None
        return float(x)
    except Exception:
        return None


def probability_to_american(p):
    if p is None:
        return None
    p = max(0.001, min(0.999, float(p)))
    if p >= 0.5:
        return int(round(-100 * p / (1 - p)))
    return int(round(100 * (1 - p) / p))


def make_ticker(date_str, away, home):
    try:
        d = datetime.strptime(str(date_str)[:10], "%Y-%m-%d")
        code = d.strftime("%y%b%d").upper()
        return f"KXNFLGAME-{code}{away}{home}"
    except Exception:
        return ""


def find_column(df, names):
    lookup = {str(c).lower().strip(): c for c in df.columns}
    for name in names:
        if name.lower() in lookup:
            return lookup[name.lower()]
    return None


def normalize_probability_series(series):
    vals = pd.to_numeric(series, errors="coerce")
    # Soporta 0.63 y 63.
    if vals.dropna().size:
        q95 = vals.dropna().quantile(0.95)
        if q95 > 1.5:
            vals = vals / 100.0
    return vals.clip(0.001, 0.999)


# ============================================================
# CARGAR V6 ACTUAL
# ============================================================

@st.cache_data(ttl=300)
def load_v6():
    try:
        return pd.read_csv(V6_FILE), None
    except Exception as e:
        return None, str(e)


def build_team_probs(v6):
    if v6 is None or "team" not in v6.columns or "model_prob" not in v6.columns:
        return {}

    data = {}
    for _, row in v6.iterrows():
        team = norm_team(row.get("team"))
        p = fnum(row.get("model_prob"))
        if team and p is not None:
            if p > 1:
                p /= 100
            if 0.01 <= p <= 0.99:
                data.setdefault(team, []).append(p)

    return {team: float(np.median(values)) for team, values in data.items()}


# ============================================================
# PRESEASON MODEL
# ============================================================

def preseason_probability(away, home, team_probs):
    ap = team_probs.get(away)
    hp = team_probs.get(home)

    if ap is None and hp is None:
        return 0.50, "LOW", "NO V6 DATA"

    if ap is not None and hp is None:
        p_home = 0.50 + (0.50 - ap) * 0.20
        return max(0.25, min(0.75, p_home)), "LOW", "AWAY ONLY"

    if ap is None and hp is not None:
        p_home = 0.50 + (0.50 - hp) * 0.20
        return max(0.25, min(0.75, p_home)), "LOW", "HOME ONLY"

    strength = hp - ap
    p_home = 0.50 + strength * 0.55 + 0.015
    p_home = max(0.25, min(0.75, p_home))
    return p_home, "MEDIUM", "BOTH TEAMS"


def get_preseason_games():
    return [
        {
            "game_id": f"{d}_{a}_{h}",
            "date": d,
            "away": a,
            "home": h,
            "type": "PRE",
            "week": w,
        }
        for d, a, h, w in PRESEASON
    ]


# ============================================================
# KALSHI
# ============================================================

def get_kalshi_event(ticker):
    if not ticker:
        return None, [], "NO TICKER"

    url = KALSHI_BASE + quote(ticker, safe="")

    try:
        response = requests.get(
            url,
            timeout=10,
            headers={"User-Agent": "Monitor-NFL"}
        )
    except Exception as e:
        return None, [], f"REQUEST ERROR: {e}"

    if response.status_code != 200:
        return None, [], f"HTTP {response.status_code}"

    try:
        data = response.json()
    except Exception as e:
        return None, [], f"JSON ERROR: {e}"

    event = data.get("event")
    markets = data.get("markets") or []

    if event and not markets:
        markets = event.get("markets") or []

    return event, markets, None


def market_team(market, team):
    if not market:
        return False
    ticker = str(market.get("ticker", "")).upper()
    return ticker.endswith("-" + norm_team(team))


def get_price(market, fields):
    if not market:
        return None

    for field in fields:
        value = fnum(market.get(field))
        if value is not None:
            if value > 1:
                value /= 100
            return value
    return None


def get_ask(market):
    return get_price(
        market,
        ["yes_ask_dollars", "yes_ask", "ask"]
    )


# ============================================================
# NEWS
# ============================================================

def news_check(away, home, date_str):
    query = quote(
        f"NFL {away} {home} quarterback injury starter {date_str}"
    )

    url = (
        "https://news.google.com/rss/search?"
        f"q={query}&hl=en-US&gl=US&ceid=US:en"
    )

    try:
        response = requests.get(
            url,
            timeout=8,
            headers={"User-Agent": "Mozilla/5.0"}
        )

        if response.status_code != 200:
            return "UNAVAILABLE", 0.0, "RSS unavailable"

        root = ET.fromstring(response.text)
        titles = []

        for item in root.findall(".//item")[:12]:
            title = item.findtext("title")
            if title:
                titles.append(title)

        text = " ".join(titles).lower()

        high_terms = [
            "starting quarterback", "starting qb",
            "backup quarterback", "backup qb",
            "quarterback competition", "qb competition",
            "won't play", "will not play",
            "not expected to play",
        ]

        medium_terms = [
            "resting", "rest", "sitting", "inactive",
            "limited", "snap count", "snaps", "injury",
            "injured", "questionable", "out",
        ]

        high = [x for x in high_terms if x in text]
        medium = [x for x in medium_terms if x in text]

        if high:
            return "HIGH_RISK", 0.35, ", ".join(high[:4])

        if medium:
            return "MEDIUM_RISK", 0.15, ", ".join(medium[:5])

        return "NO_MAJOR_RISK", 0.0, "No major risk"

    except Exception as e:
        return "UNAVAILABLE", 0.0, str(e)[:100]


# ============================================================
# PARTIDOS ACTUALES
# ============================================================

@st.cache_data(ttl=300)
def load_schedule():
    try:
        df = pd.read_csv(NFLVERSE_SCHEDULE_URL)
        return df, None
    except Exception as e:
        return None, str(e)


@st.cache_data(ttl=3600)
def load_calibration_reference():
    """Carga el histórico V6 disponible para calibrar las predicciones actuales."""
    try:
        historical, error = build_real_v6_backtest()
        if historical is None or len(historical) < 50:
            return None, error or "Histórico V6 insuficiente para calibración."
        calibrator = fit_probability_calibrator(historical)
        return calibrator, None
    except Exception as e:
        return None, str(e)


def analyze_current_games():
    v6, v6_error = load_v6()
    team_probs = build_team_probs(v6)

    today = date.today()
    end_date = today + timedelta(days=WINDOW_DAYS)
    games = []

    for game in get_preseason_games():
        try:
            game_date = datetime.strptime(
                game["date"], "%Y-%m-%d"
            ).date()
        except Exception:
            continue

        if today <= game_date <= end_date:
            games.append(game)

    schedule, schedule_error = load_schedule()

    if schedule is not None:
        if "gameday" in schedule.columns and "season" in schedule.columns:
            schedule = schedule.copy()
            schedule = schedule[
                pd.to_numeric(schedule["season"], errors="coerce") == 2026
            ]

            for _, row in schedule.iterrows():
                gd = row.get("gameday")
                if pd.isna(gd):
                    continue

                try:
                    game_date = pd.to_datetime(gd).date()
                except Exception:
                    continue

                if not (today <= game_date <= end_date):
                    continue

                game_type = str(row.get("game_type", "")).upper()
                if game_type != "REG":
                    continue

                away = norm_team(row.get("away_team"))
                home = norm_team(row.get("home_team"))

                if not away or not home:
                    continue

                games.append({
                    "game_id": str(
                        row.get("game_id", f"{gd}_{away}_{home}")
                    ),
                    "date": str(gd)[:10],
                    "away": away,
                    "home": home,
                    "type": "REG",
                    "week": str(row.get("week", "")),
                })

    unique = {}
    for game in games:
        unique[(game["date"], game["away"], game["home"])] = game

    games = sorted(
        unique.values(),
        key=lambda x: (x["date"], x["away"], x["home"])
    )

    results = []

    for game in games:
        away = game["away"]
        home = game["home"]

        if game["type"] == "PRE":
            home_prob, confidence, quality = preseason_probability(
                away, home, team_probs
            )

            if home_prob >= 0.50:
                model_team = home
                model_prob = home_prob
            else:
                model_team = away
                model_prob = 1 - home_prob

            model_source = "V6 PRESEASON"

        else:
            model_team = None
            model_prob = None
            confidence = "LOW"
            quality = "NO V6 MATCH"

            if v6 is not None:
                candidates = v6.copy()

                if "team" in candidates.columns and "opponent_team" in candidates.columns:
                    candidates["_team"] = candidates["team"].map(norm_team)
                    candidates["_opp"] = candidates["opponent_team"].map(norm_team)

                    found = candidates[
                        (candidates["_team"] == home)
                        & (candidates["_opp"] == away)
                    ]

                    if len(found) == 0:
                        found = candidates[
                            (candidates["_team"] == away)
                            & (candidates["_opp"] == home)
                        ]

                    if len(found):
                        row = found.iloc[0]
                        team = norm_team(row.get("team"))
                        p = fnum(row.get("model_prob"))

                        if p is not None:
                            if p > 1:
                                p /= 100

                            model_team = team
                            model_prob = p if team == home else 1 - p

            if model_prob is None:
                model_team = home
                model_prob = 0.50
            else:
                confidence = "HIGH"
                quality = "V6"

            model_source = "V6"

        # ----------------------------------------------------
        # CALIBRACIÓN V8
        # ----------------------------------------------------
        calibrated_favorite_prob = None
        calibration_source = "NO CALIBRATION"

        if model_prob is not None and game["type"] == "REG":
            calibrator, calibration_error = load_calibration_reference()
            raw_favorite_prob = (
                model_prob if model_team == home else 1.0 - model_prob
            )
            calibrated_favorite_prob = apply_probability_calibrator(
                raw_favorite_prob, calibrator
            )

            if calibrator is not None:
                calibration_source = "V8 CALIBRATED"
                if model_team == home:
                    model_prob = calibrated_favorite_prob
                else:
                    model_prob = 1.0 - calibrated_favorite_prob
                quality = "V6 + CALIBRATED"
            else:
                calibrated_favorite_prob = raw_favorite_prob

        ticker = make_ticker(game["date"], away, home)
        event, markets, api_error = get_kalshi_event(ticker)

        away_ask = None
        home_ask = None

        if event is not None:
            for market in markets:
                if market_team(market, away):
                    away_ask = get_ask(market)
                if market_team(market, home):
                    home_ask = get_ask(market)

        selected_ask = home_ask if model_team == home else away_ask

        raw_edge = None
        if model_prob is not None and selected_ask is not None:
            raw_edge = model_prob - selected_ask

        news_status, news_risk, news_reason = news_check(
            away, home, game["date"]
        )

        news_factor = (
            0.65 if news_risk >= 0.35
            else 0.85 if news_risk >= 0.15
            else 1.0
        )

        adjusted_edge = raw_edge * news_factor if raw_edge is not None else None

        final_confidence = confidence
        if news_risk >= 0.35 and confidence == "HIGH":
            final_confidence = "MEDIUM"
        elif news_risk >= 0.35 and confidence == "MEDIUM":
            final_confidence = "LOW"

        confidence_factor = {
            "HIGH": 1.00,
            "MEDIUM": 0.70,
            "LOW": 0.40
        }.get(final_confidence, 0.40)

        if adjusted_edge is not None:
            adjusted_edge *= confidence_factor

        if adjusted_edge is None:
            status = "SIN PRECIO"
        elif adjusted_edge >= 0.15:
            status = "STRONG SIGNAL"
        elif adjusted_edge >= 0.08:
            status = "OPPORTUNITY"
        elif adjusted_edge >= 0.04:
            status = "WATCH"
        elif adjusted_edge > 0:
            status = "SMALL EDGE"
        else:
            status = "NO EDGE"

        results.append({
            "game_id": game["game_id"],
            "date": game["date"],
            "type": game["type"],
            "week": game["week"],
            "away": away,
            "home": home,
            "model_team": model_team,
            "model_prob": model_prob,
            "confidence": final_confidence,
            "quality": quality,
            "model_source": model_source,
            "calibrated_favorite_prob": calibrated_favorite_prob,
            "calibration_source": calibration_source,
            "away_ask": away_ask,
            "home_ask": home_ask,
            "selected_ask": selected_ask,
            "raw_edge": raw_edge,
            "adjusted_edge": adjusted_edge,
            "news_status": news_status,
            "news_reason": news_reason,
            "status": status,
            "ticker": ticker,
            "event_found": event is not None,
            "api_error": api_error,
        })

    return pd.DataFrame(results), v6, v6_error, schedule_error


# ============================================================
# HISTÓRICO NFLVERSE
# ============================================================

@st.cache_data(ttl=86400)
def load_historical_schedule():
    try:
        df = pd.read_csv(NFLVERSE_SCHEDULE_URL)
        return df, None
    except Exception as e:
        return None, str(e)


def prepare_historical_schedule():
    schedule, error = load_historical_schedule()

    if schedule is None:
        return None, error

    df = schedule.copy()

    required = [
        "season", "game_type", "gameday",
        "away_team", "home_team",
        "away_score", "home_score"
    ]

    missing = [c for c in required if c not in df.columns]

    if missing:
        return None, "Faltan columnas: " + ", ".join(missing)

    df = df[
        df["game_type"].astype(str).str.upper().eq("REG")
    ].copy()

    df["season"] = pd.to_numeric(df["season"], errors="coerce")
    df["gameday"] = pd.to_datetime(df["gameday"], errors="coerce")
    df["away_score"] = pd.to_numeric(df["away_score"], errors="coerce")
    df["home_score"] = pd.to_numeric(df["home_score"], errors="coerce")

    df["away"] = df["away_team"].map(norm_team)
    df["home"] = df["home_team"].map(norm_team)

    df = df.dropna(
        subset=[
            "season", "gameday",
            "away_score", "home_score"
        ]
    ).copy()

    df["date"] = df["gameday"].dt.strftime("%Y-%m-%d")

    # Identificador estable para cruzar predicciones.
    df["match_key"] = (
        df["date"] + "|" +
        df["away"] + "|" +
        df["home"]
    )

    return df, None


# ============================================================
# DESCUBRIR ARCHIVOS V6 HISTÓRICOS
# ============================================================

def discover_v6_files():
    found = set()

    for pattern in HISTORICAL_PATTERNS:
        for path in glob.glob(pattern):
            if os.path.isfile(path):
                found.add(os.path.abspath(path))

    # Excluir el archivo actual 2026 del backtest histórico.
    current_abs = os.path.abspath(V6_FILE)

    files = sorted(
        p for p in found
        if p != current_abs
    )

    return files


def infer_season_from_filename(path):
    base = os.path.basename(path)
    digits = []

    for token in base.replace(".", "_").replace("-", "_").split("_"):
        if token.isdigit():
            value = int(token)
            if 1999 <= value <= 2100:
                digits.append(value)

    return digits[-1] if digits else None


# ============================================================
# NORMALIZAR PREDICCIONES V6 HISTÓRICAS
# ============================================================

def normalize_v6_history_file(path):
    try:
        raw = pd.read_csv(path)
    except Exception as e:
        return None, f"{os.path.basename(path)}: {e}"

    team_col = find_column(
        raw,
        ["team", "prediction_team", "pick", "favorite", "model_team"]
    )

    opp_col = find_column(
        raw,
        ["opponent_team", "opponent", "opp", "opponent_team_abbr"]
    )

    prob_col = find_column(
        raw,
        ["model_prob", "probability", "win_prob", "pred_prob", "p_win"]
    )

    date_col = find_column(
        raw,
        ["date", "game_date", "gameday", "game_day", "datetime"]
    )

    season_col = find_column(
        raw,
        ["season", "year"]
    )

    home_col = find_column(
        raw,
        ["home_team", "home", "home_abbr"]
    )

    away_col = find_column(
        raw,
        ["away_team", "away", "away_abbr"]
    )

    if team_col is None or prob_col is None or date_col is None:
        return None, (
            f"{os.path.basename(path)} no tiene las columnas mínimas. "
            f"Se necesitan team + model_prob + date."
        )

    work = pd.DataFrame()

    work["team"] = raw[team_col].map(norm_team)
    work["model_prob"] = normalize_probability_series(raw[prob_col])

    dates = pd.to_datetime(
        raw[date_col],
        errors="coerce"
    )
    work["date"] = dates.dt.strftime("%Y-%m-%d")

    if opp_col is not None:
        work["opponent_team"] = raw[opp_col].map(norm_team)
    else:
        work["opponent_team"] = ""

    if season_col is not None:
        work["season"] = pd.to_numeric(
            raw[season_col],
            errors="coerce"
        )
    else:
        inferred = infer_season_from_filename(path)
        work["season"] = inferred

    if home_col is not None:
        work["home"] = raw[home_col].map(norm_team)
    else:
        work["home"] = ""

    if away_col is not None:
        work["away"] = raw[away_col].map(norm_team)
    else:
        work["away"] = ""

    work["source_file"] = os.path.basename(path)

    work = work[
        work["team"].ne("")
        & work["model_prob"].notna()
        & work["date"].notna()
    ].copy()

    # Si home/away existen en el propio archivo, construir match_key.
    work["match_key"] = ""

    mask_full_game = (
        work["away"].ne("")
        & work["home"].ne("")
    )

    work.loc[mask_full_game, "match_key"] = (
        work.loc[mask_full_game, "date"] + "|" +
        work.loc[mask_full_game, "away"] + "|" +
        work.loc[mask_full_game, "home"]
    )

    # Si sólo tenemos team/opponent, todavía no sabemos quién es local.
    # El cruce se resolverá contra nflverse.
    return work, None


# ============================================================
# CRUCE V6 REAL VS RESULTADOS
# ============================================================

@st.cache_data(ttl=86400)
def build_real_v6_backtest():
    files = discover_v6_files()

    if not files:
        return None, (
            "No se encontraron archivos históricos V6. "
            "Sube al proyecto archivos como "
            "nfl_v6_predictions_2019.csv ... nfl_v6_predictions_2025.csv."
        )

    schedule, error = prepare_historical_schedule()

    if schedule is None:
        return None, error

    all_predictions = []

    for path in files:
        work, file_error = normalize_v6_history_file(path)

        if work is None:
            continue

        all_predictions.append(work)

    if not all_predictions:
        return None, (
            "Se encontraron archivos V6, pero ninguno tiene "
            "las columnas necesarias."
        )

    preds = pd.concat(
        all_predictions,
        ignore_index=True
    )

    # --------------------------------------------------------
    # Cruzar cada predicción con el partido real.
    # Caso A: archivo trae home/away.
    # Caso B: sólo trae team/opponent.
    # --------------------------------------------------------

    rows = []

    for _, pred in preds.iterrows():
        p_team = norm_team(pred["team"])
        p_opp = norm_team(pred["opponent_team"])
        p_date = str(pred["date"])[:10]

        candidates = schedule[
            schedule["date"].eq(p_date)
        ]

        match = None

        # Si conocemos home/away, cruce exacto.
        if pred.get("match_key", ""):
            candidates2 = candidates[
                candidates["match_key"].eq(pred["match_key"])
            ]
            if len(candidates2):
                match = candidates2.iloc[0]

        # Si no, buscar por team + opponent.
        if match is None and p_opp:
            candidates2 = candidates[
                (
                    (
                        candidates["away"].eq(p_team)
                        & candidates["home"].eq(p_opp)
                    )
                    |
                    (
                        candidates["home"].eq(p_team)
                        & candidates["away"].eq(p_opp)
                    )
                )
            ]

            if len(candidates2):
                match = candidates2.iloc[0]

        if match is None:
            continue

        away = match["away"]
        home = match["home"]

        model_p = float(pred["model_prob"])

        # La predicción es para "team".
        # Convertimos a probabilidad del favorito.
        if p_team == away:
            team_won = float(match["away_score"] > match["home_score"])
        elif p_team == home:
            team_won = float(match["home_score"] > match["away_score"])
        else:
            continue

        opponent = home if p_team == away else away

        # Sólo contamos como favorito el lado con >= 50%.
        # Si V6 da 0.42 a team, el favorito es el rival con 0.58.
        if model_p >= 0.50:
            favorite = p_team
            favorite_prob = model_p
            favorite_won = team_won
        else:
            favorite = opponent
            favorite_prob = 1.0 - model_p
            favorite_won = 1.0 - team_won

        rows.append({
            "date": p_date,
            "season": int(match["season"]),
            "away": away,
            "home": home,
            "model_team": p_team,
            "opponent": opponent,
            "model_prob_team": model_p,
            "favorite": favorite,
            "favorite_prob": favorite_prob,
            "favorite_won": favorite_won,
            "away_score": float(match["away_score"]),
            "home_score": float(match["home_score"]),
            "source_file": pred["source_file"],
        })

    if not rows:
        return None, (
            "No se pudieron cruzar las predicciones V6 históricas "
            "con los resultados de nflverse. Revisa fecha, team, "
            "opponent_team y model_prob."
        )

    result = pd.DataFrame(rows)

    # Eliminar duplicados exactos.
    result = result.drop_duplicates(
        subset=[
            "date", "away", "home",
            "model_team", "model_prob_team"
        ]
    )

    return result.reset_index(drop=True), None


# ============================================================
# MÉTRICAS V6 REAL
# ============================================================

def calculate_v6_metrics(df):
    if df is None or len(df) == 0:
        return {}

    p = np.clip(
        df["favorite_prob"].astype(float).values,
        0.001,
        0.999
    )

    y = df["favorite_won"].astype(float).values

    accuracy = float(np.mean(y == 1))

    log_loss = float(
        -np.mean(
            y * np.log(p)
            + (1 - y) * np.log(1 - p)
        )
    )

    brier = float(np.mean((p - y) ** 2))

    return {
        "games": len(df),
        "accuracy": accuracy,
        "log_loss": log_loss,
        "brier": brier,
    }


# ============================================================
# CALIBRACIÓN DEL FAVORITO
# ============================================================

def favorite_log_loss(df, prob_col="favorite_prob"):
    if df is None or len(df) == 0:
        return None

    p = np.clip(df[prob_col].astype(float).values, 0.001, 0.999)
    y = df["favorite_won"].astype(float).values

    return float(-np.mean(
        y * np.log(p) + (1 - y) * np.log(1 - p)
    ))


def favorite_calibration_table(df):
    if df is None or len(df) == 0:
        return pd.DataFrame()

    work = df.copy()

    bins = [
        0.50, 0.55, 0.60, 0.65, 0.70,
        0.75, 0.80, 0.85, 0.90, 1.01
    ]

    labels = [
        "50-54%", "55-59%", "60-64%",
        "65-69%", "70-74%", "75-79%",
        "80-84%", "85-89%", "90%+"
    ]

    work["bucket"] = pd.cut(
        work["favorite_prob"],
        bins=bins,
        labels=labels,
        right=False
    )

    result = (
        work.groupby("bucket", observed=False)
        .agg(
            partidos=("favorite_won", "count"),
            prob_media=("favorite_prob", "mean"),
            victorias=("favorite_won", "sum")
        )
        .reset_index()
    )

    result["victoria_real"] = (
        result["victorias"]
        / result["partidos"].replace(0, np.nan)
    )

    result["error_calibracion"] = (
        result["victoria_real"] - result["prob_media"]
    )

    return result


CALIBRATION_BINS = np.array([
    0.50, 0.55, 0.60, 0.65, 0.70,
    0.75, 0.80, 0.85, 0.90, 0.95, 1.00
])


def _bin_center(p):
    idx = int(np.clip(np.searchsorted(CALIBRATION_BINS, p, side="right") - 1, 0, len(CALIBRATION_BINS)-2))
    return (CALIBRATION_BINS[idx] + CALIBRATION_BINS[idx+1]) / 2


def fit_probability_calibrator(df, prior_weight=30.0):
    """
    Calibrador empírico conservador.
    Cada rango se suaviza hacia su probabilidad central para evitar
    que buckets pequeños produzcan correcciones extremas.
    Después se fuerza monotonía para que una probabilidad mayor no
    termine mapeando a una probabilidad menor.
    """
    if df is None or len(df) == 0:
        return None

    work = df.copy()
    p = pd.to_numeric(work["favorite_prob"], errors="coerce")
    y = pd.to_numeric(work["favorite_won"], errors="coerce")
    work = work.assign(_p=p, _y=y).dropna(subset=["_p", "_y"])
    work = work[(work["_p"] >= 0.50) & (work["_p"] <= 1.0)]

    if len(work) < 50:
        return None

    centers=[]
    rates=[]
    counts=[]

    for lo, hi in zip(CALIBRATION_BINS[:-1], CALIBRATION_BINS[1:]):
        bucket = work[(work["_p"] >= lo) & (work["_p"] < hi if hi < 1.0 else work["_p"] <= hi)]
        n=len(bucket)
        if n == 0:
            continue
        wins=float(bucket["_y"].sum())
        center=(lo+hi)/2
        rate=(wins + prior_weight*center)/(n+prior_weight)
        centers.append(center)
        rates.append(rate)
        counts.append(n)

    if not centers:
        return None

    # Isotonic regression manual: pool adjacent violators.
    vals=list(rates)
    weights=[float(n) for n in counts]
    changed=True
    while changed:
        changed=False
        i=0
        while i < len(vals)-1:
            if vals[i] > vals[i+1]:
                total_w=weights[i]+weights[i+1]
                pooled=(vals[i]*weights[i]+vals[i+1]*weights[i+1])/total_w
                vals[i]=pooled
                weights[i]=total_w
                del vals[i+1]
                del weights[i+1]
                del centers[i+1]
                changed=True
                if i>0: i-=1
            else:
                i+=1

    return {
        "centers": np.array(centers, dtype=float),
        "rates": np.array(vals, dtype=float),
        "n": int(len(work)),
    }


def apply_probability_calibrator(prob, calibrator):
    if calibrator is None or prob is None:
        return prob

    p=float(np.clip(prob, 0.50, 0.999))
    centers=calibrator["centers"]
    rates=calibrator["rates"]

    if len(centers)==1:
        out=float(rates[0])
    else:
        out=float(np.interp(p, centers, rates, left=rates[0], right=rates[-1]))

    return float(np.clip(out, 0.50, 0.99))


def add_oos_calibration(df):
    """
    Aplica calibración leave-one-season-out. Cada temporada se calibra
    usando las otras temporadas, evitando entrenar y evaluar en los mismos juegos.
    """
    if df is None or len(df)==0:
        return df

    out=df.copy()
    out["favorite_prob_calibrated"]=np.nan

    seasons=sorted(out["season"].dropna().unique())

    for season in seasons:
        train=out[out["season"] != season]
        test_idx=out["season"] == season
        cal=fit_probability_calibrator(train)

        if cal is None:
            out.loc[test_idx,"favorite_prob_calibrated"] = out.loc[test_idx,"favorite_prob"]
        else:
            out.loc[test_idx,"favorite_prob_calibrated"] = out.loc[test_idx,"favorite_prob"].apply(
                lambda x: apply_probability_calibrator(x, cal)
            )

    return out


def calibrated_metrics(df):
    if df is None or len(df)==0 or "favorite_prob_calibrated" not in df.columns:
        return {}

    work=df.dropna(subset=["favorite_prob_calibrated"]).copy()
    if len(work)==0:
        return {}

    p=np.clip(work["favorite_prob_calibrated"].astype(float).values,0.001,0.999)
    y=work["favorite_won"].astype(float).values

    return {
        "games":len(work),
        "accuracy":float(np.mean(y==1)),
        "log_loss":float(-np.mean(y*np.log(p)+(1-y)*np.log(1-p))),
        "brier":float(np.mean((p-y)**2)),
    }


def calibrated_calibration_table(df):
    if df is None or len(df)==0 or "favorite_prob_calibrated" not in df.columns:
        return pd.DataFrame()

    work=df.dropna(subset=["favorite_prob_calibrated"]).copy()
    bins=[0.50,0.55,0.60,0.65,0.70,0.75,0.80,0.85,0.90,1.01]
    labels=["50-54%","55-59%","60-64%","65-69%","70-74%","75-79%","80-84%","85-89%","90%+"]
    work["bucket"]=pd.cut(work["favorite_prob_calibrated"],bins=bins,labels=labels,right=False)
    result=(work.groupby("bucket",observed=False).agg(
        partidos=("favorite_won","count"),
        prob_media=("favorite_prob_calibrated","mean"),
        victorias=("favorite_won","sum")
    ).reset_index())
    result["victoria_real"]=result["victorias"]/result["partidos"].replace(0,np.nan)
    result["error_calibracion"]=result["victoria_real"]-result["prob_media"]
    return result


# ============================================================
# RESULTADOS POR TEMPORADA
# ============================================================

def season_metrics(df):
    if df is None or len(df) == 0:
        return pd.DataFrame()

    rows = []
    for season, group in df.groupby("season"):
        metrics = calculate_v6_metrics(group)
        rows.append({
            "Temporada": int(season),
            "Partidos": metrics["games"],
            "Accuracy": metrics["accuracy"],
            "Log Loss": metrics["log_loss"],
            "Brier": metrics["brier"],
        })

    return pd.DataFrame(rows).sort_values("Temporada")


# ============================================================
# SELECCIÓN POR UMBRAL
# ============================================================

def calculate_selection(df, threshold):
    if df is None or len(df) == 0:
        return None

    bets = df[
        df["favorite_prob"] >= threshold
    ].copy()

    if len(bets) == 0:
        return None

    wins = bets["favorite_won"].astype(float)

    # Unidades a cuota justa NO son ROI real.
    # Se reporta primero hit rate.
    hit_rate = float(wins.mean())

    # Edge teórico contra una cuota justa:
    # sirve sólo como diagnóstico matemático.
    theoretical_profit = (
        wins / bets["favorite_prob"]
        - 1
    )

    return {
        "bets": len(bets),
        "wins": int(wins.sum()),
        "losses": int(len(bets) - wins.sum()),
        "hit_rate": hit_rate,
        "theoretical_profit": float(theoretical_profit.sum()),
        "theoretical_roi": float(theoretical_profit.mean()),
    }


# ============================================================
# BACKTEST DE PRECISIÓN SIN CUOTAS
# ============================================================

def build_threshold_table(df):
    if df is None or len(df) == 0:
        return pd.DataFrame()

    thresholds = [
        0.50, 0.55, 0.60, 0.63,
        0.65, 0.70, 0.75, 0.80
    ]

    rows = []

    for threshold in thresholds:
        selection = calculate_selection(df, threshold)

        if selection is None:
            rows.append({
                "Umbral": f"{threshold*100:.0f}%",
                "Señales": 0,
                "Victorias": 0,
                "Hit rate": np.nan,
            })
        else:
            rows.append({
                "Umbral": f"{threshold*100:.0f}%",
                "Señales": selection["bets"],
                "Victorias": selection["wins"],
                "Hit rate": selection["hit_rate"],
            })

    return pd.DataFrame(rows)


# ============================================================
# CSS
# ============================================================

st.markdown(
    """
    <style>
    .main { background-color: #0e0f14; }
    .block-container {
        max-width: 1100px;
        padding-top: 2rem;
    }
    h1, h2, h3 { color: #f5f5f5; }
    .big-number {
        font-size: 56px;
        font-weight: 800;
        line-height: 1.0;
    }
    .game-card {
        padding: 28px;
        border-radius: 24px;
        border: 1px solid #3a3c45;
        background: #15161d;
        margin-bottom: 20px;
    }
    .projection {
        padding: 30px;
        border-radius: 24px;
        border: 2px solid #438c60;
        background: #173a28;
        margin-top: 20px;
        margin-bottom: 25px;
    }
    .projection h3 { color: #a9e4bd; }
    .projection p {
        color: #b3e7c3;
        font-size: 20px;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# ============================================================
# HEADER
# ============================================================

st.title("🏈 Monitor NFL")
st.subheader("Modelo propio — análisis NFL automático")

tab1, tab2, tab3 = st.tabs([
    "🏈 NFL DE HOY",
    "🧪 VALIDACIÓN DEL MODELO",
    "📊 INFORMACIÓN"
])

# ============================================================
# TAB 1
# ============================================================

with tab1:

    st.header("🏈 NFL DE HOY")

    if st.button(
        "🔄 ACTUALIZAR PARTIDOS",
        use_container_width=True
    ):
        st.cache_data.clear()
        st.rerun()

    with st.spinner("Consultando partidos y modelo..."):
        games_df, v6, v6_error, schedule_error = analyze_current_games()

    if games_df is None or len(games_df) == 0:
        st.warning(
            "⚠️ No se encontraron partidos NFL "
            "en los próximos 7 días."
        )
    else:

        st.success(
            f"Se encontraron {len(games_df)} partidos."
        )

        for _, game in games_df.iterrows():

            away = game["away"]
            home = game["home"]

            away_name = TEAM_NAMES.get(away, away)
            home_name = TEAM_NAMES.get(home, home)

            model_team = game["model_team"]
            model_prob = float(game["model_prob"])

            st.markdown(
                '<div class="game-card">',
                unsafe_allow_html=True
            )

            st.subheader(f"🏈 {away_name}")
            st.subheader(f"@ {home_name}")
            st.write(f"📅 {game['date']}")
            st.write(f"🕒 Partido NFL")

            st.markdown("</div>", unsafe_allow_html=True)

            away_prob = 1 - model_prob
            home_prob = model_prob

            st.markdown(
                f"""
                ### ✈️ {away_name}

                Probabilidad modelo

                <div class="big-number">
                {away_prob * 100:.1f}%
                </div>
                """,
                unsafe_allow_html=True
            )

            st.write(
                f"🎯 Cuota justa: "
                f"{probability_to_american(away_prob):+d}"
            )

            st.markdown(
                f"""
                ### 🏠 {home_name}

                Probabilidad modelo

                <div class="big-number">
                {home_prob * 100:.1f}%
                </div>
                """,
                unsafe_allow_html=True
            )

            st.write(
                f"🎯 Cuota justa: "
                f"{probability_to_american(home_prob):+d}"
            )

            favorite_prob = (
                model_prob
                if model_team == home
                else 1 - model_prob
            )

            fair_odds = probability_to_american(favorite_prob)

            st.markdown(
                f"""
                <div class="projection">
                <h3>🧠 PROYECCIÓN DEL MODELO</h3>
                <p>Favorito:
                <strong>{TEAM_NAMES.get(model_team, model_team)}</strong></p>
                <p>Probabilidad estimada:
                <strong>{favorite_prob * 100:.1f}%</strong></p>
                <p>Cuota justa:
                <strong>{fair_odds:+d}</strong></p>
                <p>Confianza:
                <strong>{game['confidence']}</strong></p>
                <p>Calibración:
                <strong>{game.get('calibration_source', 'N/A')}</strong></p>
                </div>
                """,
                unsafe_allow_html=True
            )

            st.subheader("🏦 COMPARACIÓN CON LA CASA")

            selected_ask = game["selected_ask"]

            if selected_ask is not None:

                st.write(
                    f"Mercado: {selected_ask * 100:.1f}%"
                )

                edge = game["adjusted_edge"]

                if edge is not None:

                    st.write(
                        f"Edge ajustado: {edge * 100:+.2f}%"
                    )

                    if edge >= 0.15:
                        st.success("🚨 STRONG SIGNAL")
                    elif edge >= 0.08:
                        st.success("🟢 OPPORTUNITY")
                    elif edge >= 0.04:
                        st.warning("🟡 WATCH")
                    else:
                        st.info("Sin edge suficiente.")
            else:
                st.info("No hay precio de mercado disponible.")

            st.write(f"📡 Fuente: {game['quality']}")
            st.write(f"📰 News risk: {game['news_status']}")
            st.write(f"📌 Estado: {game['status']}")

            st.markdown("---")


# ============================================================
# TAB 2 — VALIDACIÓN REAL V6
# ============================================================

with tab2:

    st.header("🧪 VALIDACIÓN REAL V6 + CALIBRACIÓN V8")

    st.write(
        """
        Esta prueba ya no sustituye V6 por Elo.

        El sistema toma las predicciones históricas V6 guardadas
        en CSV, cruza cada predicción con el partido real de
        nflverse y mide al FAVORITO que V6 seleccionó.

        Por eso, esta es la prueba que necesitamos para saber
        si V6 realmente está funcionando.
        """
    )

    st.info(
        """
        ⚠️ Para que sea un backtest real, el proyecto necesita
        archivos históricos de predicciones V6. El archivo
        de 2026 solamente NO permite reconstruir lo que V6
        habría predicho en 2019–2025.
        """
    )

    st.markdown("---")

    files_now = discover_v6_files()

    if files_now:
        st.success(
            f"Archivos históricos V6 encontrados: {len(files_now)}"
        )

        st.code(
            "\n".join(
                os.path.basename(x)
                for x in files_now
            )
        )
    else:
        st.warning(
            "No hay archivos históricos V6 todavía."
        )

    col1, col2 = st.columns(2)

    current_year = datetime.now().year

    with col1:
        start_season = st.number_input(
            "Temporada inicial",
            min_value=1999,
            max_value=current_year - 1,
            value=max(2019, current_year - 7),
            step=1
        )

    with col2:
        end_season = st.number_input(
            "Temporada final",
            min_value=1999,
            max_value=current_year - 1,
            value=current_year - 1,
            step=1
        )

    if st.button(
        "🧪 EJECUTAR BACKTEST V6 REAL",
        use_container_width=True
    ):

        if start_season > end_season:
            st.error(
                "La temporada inicial no puede ser mayor que la final."
            )
        else:

            st.cache_data.clear()

            with st.spinner(
                "Cruzando predicciones V6 con resultados históricos..."
            ):
                backtest, error = build_real_v6_backtest()

            if backtest is None:
                st.error(f"No se pudo ejecutar: {error}")
            else:

                selected = backtest[
                    backtest["season"].between(
                        int(start_season),
                        int(end_season)
                    )
                ].copy()

                if len(selected) == 0:
                    st.error(
                        "Hay predicciones V6 históricas, pero no hay "
                        "datos dentro del rango seleccionado."
                    )
                else:
                    st.session_state["v6_backtest"] = selected
                    st.success(
                        f"Backtest V6 terminado: "
                        f"{len(selected):,} predicciones cruzadas."
                    )

    if "v6_backtest" in st.session_state:

        backtest = st.session_state["v6_backtest"]

        metrics = calculate_v6_metrics(backtest)

        st.markdown("---")
        st.subheader("📊 RESULTADOS GENERALES V6")

        c1, c2, c3, c4 = st.columns(4)

        c1.metric(
            "Predicciones",
            f"{metrics['games']:,}"
        )

        c2.metric(
            "Accuracy favorito",
            f"{metrics['accuracy'] * 100:.2f}%"
        )

        c3.metric(
            "Log Loss",
            f"{metrics['log_loss']:.4f}"
        )

        c4.metric(
            "Brier",
            f"{metrics['brier']:.4f}"
        )

        # ----------------------------------------------------
        # V8: CALIBRACIÓN OOS
        # ----------------------------------------------------

        oos = add_oos_calibration(backtest)
        oos_metrics = calibrated_metrics(oos)

        st.markdown("---")
        st.subheader("🧠 V8 — PROBABILIDAD CALIBRADA")
        st.caption(
            "La calibración OOS usa cada temporada como prueba y entrena "
            "el calibrador con las demás temporadas. Así evitamos leakage."
        )

        if oos_metrics:
            k1, k2, k3, k4 = st.columns(4)
            k1.metric("Predicciones", f"{oos_metrics['games']:,}")
            k2.metric("Accuracy", f"{oos_metrics['accuracy']*100:.2f}%")
            k3.metric("Log Loss", f"{oos_metrics['log_loss']:.4f}")
            k4.metric("Brier", f"{oos_metrics['brier']:.4f}")

            delta_ll = oos_metrics['log_loss'] - metrics['log_loss']
            delta_br = oos_metrics['brier'] - metrics['brier']
            if delta_ll < 0 and delta_br < 0:
                st.success("✅ La calibración mejora Log Loss y Brier en la prueba OOS.")
            elif delta_ll > 0 or delta_br > 0:
                st.warning("⚠️ La calibración no mejora todas las métricas OOS. No se debe asumir que V8 es mejor todavía.")
            else:
                st.info("La calibración no cambia las métricas de forma material.")

            oos_show=oos.copy()
            oos_show["Prob. V6"]= (oos_show["favorite_prob"]*100).round(1).astype(str)+"%"
            oos_show["Prob. V8"]= (oos_show["favorite_prob_calibrated"]*100).round(1).astype(str)+"%"
            oos_show["Resultado"]=np.where(oos_show["favorite_won"]==1,"GANÓ","PERDIÓ")
            st.dataframe(
                oos_show[["season","away","home","Prob. V6","Prob. V8","Resultado"]].tail(30),
                use_container_width=True, hide_index=True
            )

        # ----------------------------------------------------
        # CALIBRACIÓN
        # ----------------------------------------------------

        st.markdown("---")
        st.subheader("🎯 CALIBRACIÓN DEL FAVORITO V6")

        calibration = favorite_calibration_table(backtest)

        if len(calibration):

            display = calibration.copy()

            display["Prob. modelo"] = (
                display["prob_media"] * 100
            ).round(1).astype(str) + "%"

            display["Victoria real"] = (
                display["victoria_real"] * 100
            ).round(1).astype(str) + "%"

            display["Error"] = (
                display["error_calibracion"] * 100
            ).round(1).astype(str) + "%"

            display = display[
                [
                    "bucket",
                    "partidos",
                    "Prob. modelo",
                    "victorias",
                    "Victoria real",
                    "Error",
                ]
            ]

            display.columns = [
                "Rango",
                "Partidos",
                "Prob. modelo",
                "Victorias",
                "Victoria real",
                "Error",
            ]

            st.dataframe(
                display,
                use_container_width=True,
                hide_index=True
            )

        # ----------------------------------------------------
        # TABLA DESPUÉS DE CALIBRACIÓN OOS
        # ----------------------------------------------------

        if "oos" in locals() and len(oos):
            st.markdown("### 🎯 CALIBRACIÓN V8 — RESULTADO OOS")
            cal8 = calibrated_calibration_table(oos)
            if len(cal8):
                show8=cal8.copy()
                show8["Prob. V8"]=(show8["prob_media"]*100).round(1).astype(str)+"%"
                show8["Victoria real"]=(show8["victoria_real"]*100).round(1).astype(str)+"%"
                show8["Error"]=(show8["error_calibracion"]*100).round(1).astype(str)+"%"
                show8=show8[["bucket","partidos","Prob. V8","victorias","Victoria real","Error"]]
                show8.columns=["Rango","Partidos","Prob. V8","Victorias","Victoria real","Error"]
                st.dataframe(show8,use_container_width=True,hide_index=True)

        # ----------------------------------------------------
        # POR TEMPORADA
        # ----------------------------------------------------

        st.markdown("---")
        st.subheader("📅 RESULTADOS POR TEMPORADA")

        season_table = season_metrics(backtest)

        if len(season_table):

            show = season_table.copy()

            show["Accuracy"] = (
                show["Accuracy"] * 100
            ).round(2).astype(str) + "%"

            show["Log Loss"] = show["Log Loss"].round(4)
            show["Brier"] = show["Brier"].round(4)

            st.dataframe(
                show,
                use_container_width=True,
                hide_index=True
            )

        # ----------------------------------------------------
        # UMBRALES
        # ----------------------------------------------------

        st.markdown("---")
        st.subheader("🎯 RENDIMIENTO POR UMBRAL")

        threshold_table = build_threshold_table(backtest)

        if len(threshold_table):

            threshold_display = threshold_table.copy()

            threshold_display["Hit rate"] = (
                threshold_display["Hit rate"] * 100
            ).round(2).astype(str) + "%"

            threshold_display.loc[
                threshold_display["Señales"] == 0,
                "Hit rate"
            ] = "N/A"

            st.dataframe(
                threshold_display,
                use_container_width=True,
                hide_index=True
            )

        # ----------------------------------------------------
        # SLIDER
        # ----------------------------------------------------

        st.markdown("---")
        st.subheader("💰 PRUEBA DE SELECCIÓN")

        threshold = st.slider(
            "Probabilidad mínima del favorito",
            min_value=0.50,
            max_value=0.90,
            value=0.63,
            step=0.01
        )

        selection = calculate_selection(
            backtest,
            threshold
        )

        if selection:

            c1, c2, c3, c4 = st.columns(4)

            c1.metric(
                "Señales",
                selection["bets"]
            )

            c2.metric(
                "Victorias",
                selection["wins"]
            )

            c3.metric(
                "Hit rate",
                f"{selection['hit_rate'] * 100:.2f}%"
            )

            c4.metric(
                "Pérdidas",
                selection["losses"]
            )

            st.caption(
                """
                El hit rate es una métrica histórica real de las
                predicciones V6. Esto todavía NO es ROI real,
                porque no estamos usando cuotas históricas de
                sportsbook.
                """
            )

        else:
            st.info(
                "No hay señales con ese umbral."
            )

        # ----------------------------------------------------
        # SELECCIÓN V8 CALIBRADA
        # ----------------------------------------------------

        if "oos" in locals() and len(oos):
            st.markdown("---")
            st.subheader("🚀 SELECCIÓN V8 CALIBRADA")
            v8_threshold = st.slider(
                "Probabilidad mínima calibrada",
                min_value=0.50,
                max_value=0.90,
                value=0.65,
                step=0.01,
                key="v8_threshold"
            )

            v8_selection_df=oos.copy()
            v8_selection_df["favorite_prob"]=v8_selection_df["favorite_prob_calibrated"]
            v8_sel=calculate_selection(v8_selection_df,v8_threshold)

            if v8_sel:
                a,b,c,d=st.columns(4)
                a.metric("Señales",v8_sel["bets"])
                b.metric("Victorias",v8_sel["wins"])
                c.metric("Hit rate",f"{v8_sel['hit_rate']*100:.2f}%")
                d.metric("Pérdidas",v8_sel["losses"])
                st.caption("Hit rate histórico OOS de la probabilidad calibrada. No es ROI real porque no usa cuotas históricas.")
            else:
                st.info("No hay señales V8 con ese umbral.")

        # ----------------------------------------------------
        # ÚLTIMAS PREDICCIONES
        # ----------------------------------------------------

        st.markdown("---")
        st.subheader("📋 ÚLTIMAS PREDICCIONES V6")

        recent = backtest.tail(50).copy()

        recent["Partido"] = (
            recent["away"]
            + " @ "
            + recent["home"]
        )

        recent["Prob. favorito V6"] = (
            recent["favorite_prob"] * 100
        ).round(1).astype(str) + "%"

        if "favorite_prob_calibrated" in recent.columns:
            recent["Prob. V8 OOS"] = (
                recent["favorite_prob_calibrated"] * 100
            ).round(1).astype(str) + "%"

        recent["Resultado"] = np.where(
            recent["favorite_won"] == 1,
            "✅ FAVORITO GANÓ",
            "❌ FAVORITO PERDIÓ"
        )

        recent["Marcador"] = (
            recent["away_score"].astype(int).astype(str)
            + "-"
            + recent["home_score"].astype(int).astype(str)
        )

        st.dataframe(
            recent[
                [
                    "date",
                    "season",
                    "Partido",
                    "favorite",
                    "Prob. favorito V6",
                    "Prob. V8 OOS",
                    "Marcador",
                    "Resultado",
                    "source_file",
                ]
            ].rename(
                columns={
                    "date": "Fecha",
                    "season": "Temporada",
                    "favorite": "Favorito",
                    "source_file": "Archivo V6",
                }
            ),
            use_container_width=True,
            hide_index=True
        )


# ============================================================
# TAB 3
# ============================================================

with tab3:

    st.header("📊 INFORMACIÓN DEL MODELO")

    st.markdown(
        """
        ### 🧠 ¿Qué queremos comprobar?

        **1. Precisión**

        ¿El favorito seleccionado por V6 gana con una frecuencia
        claramente superior al 50%?

        **2. Calibración**

        Si V6 dice 65%, ¿gana aproximadamente 65%?

        **3. Estabilidad**

        ¿El resultado se mantiene entre temporadas?

        **4. Selección**

        ¿Qué ocurre cuando exigimos 60%, 63%, 65%, 70%, etc.?

        **5. Valor**

        Sólo después de comprobar lo anterior tiene sentido
        incorporar cuotas históricas reales para calcular ROI.

        ---

        ### 🎯 Umbrales

        Diagnóstico: **60%**

        Señal oficial: **63%**

        V8 usa además una **calibración histórica** de V6.

        Edge mínimo actual: **8%**

        Edge máximo actual: **20%**

        ---

        ### ⚠️ MUY IMPORTANTE

        El backtest V6 NO puede fabricar predicciones históricas.

        Si solamente existe:

        `nfl_v6_predictions_2026.csv`

        no podemos decir qué habría predicho V6 en 2019,
        2020, 2021, etc.

        Por eso este V7 busca archivos históricos reales.

        ---

        ### 📁 Archivos esperados

        Puedes tener:

        `nfl_v6_predictions_2019.csv`

        `nfl_v6_predictions_2020.csv`

        `...`

        `nfl_v6_predictions_2025.csv`

        El sistema los detectará automáticamente.

        ---

        ### 📡 Fuentes

        Resultados/calendario histórico: nflverse.

        Predicciones actuales: `nfl_v6_predictions_2026.csv`.

        Predicciones históricas: archivos V6 guardados por el proyecto.

        Mercados actuales: Kalshi cuando están disponibles.

        ---

        ### 🚫 No realiza apuestas

        Este sistema únicamente analiza información estadística.
        No ejecuta apuestas automáticamente.
        """
    )

    st.markdown("---")

    st.subheader("🔎 Estado V6 actual")

    v6_current, current_error = load_v6()

    if v6_current is not None:
        st.success(
            f"V6 actual cargado correctamente: "
            f"{len(v6_current):,} filas."
        )
    else:
        st.warning(
            f"No se encontró {V6_FILE}."
        )
        if current_error:
            st.caption(current_error)

    st.markdown("---")

    st.subheader("📁 Estado del histórico V6")

    historical_files = discover_v6_files()

    if historical_files:
        st.success(
            f"{len(historical_files)} archivos históricos encontrados."
        )

        for path in historical_files:
            st.write(
                f"• {os.path.basename(path)}"
            )
    else:
        st.warning(
            "Todavía no hay archivos históricos V6."
        )


# ============================================================
# FOOTER
# ============================================================

st.markdown("---")

st.caption(
    "Monitor NFL V7 — análisis estadístico experimental. "
    "Las probabilidades son estimaciones y no garantizan "
    "resultados futuros."
)
