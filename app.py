import streamlit as st
import pandas as pd
import numpy as np
import requests
import math
from datetime import datetime, timedelta, date
from urllib.parse import quote
import xml.etree.ElementTree as ET

# ============================================================
# MONITOR NFL
# VERSIÓN CON VALIDACIÓN HISTÓRICA
#
# - Monitor NFL 2026
# - V6 predictions si existen
# - Pretemporada 2026
# - Próximos 7 días
# - Comparación con mercado cuando existe
# - Validación / backtest histórico
# - Calibración por rangos de probabilidad
# - ROI teórico
# - NO REALIZA APUESTAS
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

# ============================================================
# PRETEMPORADA 2026
# ============================================================

PRESEASON = [

    # WEEK 1
    ("2026-08-13", "DET", "CIN", "PRE1"),
    ("2026-08-13", "GB",  "PIT", "PRE1"),
    ("2026-08-13", "IND", "NE",  "PRE1"),
    ("2026-08-13", "LAC", "HOU", "PRE1"),
    ("2026-08-13", "TEN", "SF",  "PRE1"),

    ("2026-08-14", "ARI", "LV",  "PRE1"),
    ("2026-08-14", "DEN", "ATL", "PRE1"),
    ("2026-08-14", "TB",  "NYJ", "PRE1"),
    ("2026-08-14", "MIA", "WAS", "PRE1"),

    ("2026-08-15", "CAR", "BUF", "PRE1"),
    ("2026-08-15", "CLE", "CHI", "PRE1"),
    ("2026-08-15", "MIN", "NYG", "PRE1"),
    ("2026-08-15", "LAR", "KC",  "PRE1"),
    ("2026-08-15", "JAX", "NO",  "PRE1"),
    ("2026-08-15", "PHI", "BAL", "PRE1"),

    ("2026-08-16", "DAL", "SEA", "PRE1"),

    # WEEK 2
    ("2026-08-20", "LV",  "HOU", "PRE2"),
    ("2026-08-20", "SF",  "LAC", "PRE2"),

    ("2026-08-21", "NYJ", "PIT", "PRE2"),
    ("2026-08-21", "CAR", "JAX", "PRE2"),
    ("2026-08-21", "GB",  "DEN", "PRE2"),

    ("2026-08-22", "WAS", "DET", "PRE2"),
    ("2026-08-22", "BUF", "CLE", "PRE2"),
    ("2026-08-22", "ATL", "IND", "PRE2"),
    ("2026-08-22", "BAL", "MIN", "PRE2"),
    ("2026-08-22", "NO",  "LAR", "PRE2"),
    ("2026-08-22", "NYG", "MIA", "PRE2"),
    ("2026-08-22", "CHI", "CIN", "PRE2"),
    ("2026-08-22", "PHI", "NE",  "PRE2"),
    ("2026-08-22", "KC",  "TB",  "PRE2"),
    ("2026-08-22", "DAL", "ARI", "PRE2"),

    ("2026-08-23", "SEA", "TEN", "PRE2"),

    # WEEK 3
    ("2026-08-27", "PIT", "BUF", "PRE3"),
    ("2026-08-27", "NE",  "CLE", "PRE3"),
    ("2026-08-27", "SF",  "LV",  "PRE3"),
    ("2026-08-27", "LAR", "LAC", "PRE3"),

    ("2026-08-28", "ATL", "MIA", "PRE3"),
    ("2026-08-28", "HOU", "CAR", "PRE3"),
    ("2026-08-28", "WAS", "BAL", "PRE3"),
    ("2026-08-28", "NYG", "NYJ", "PRE3"),
    ("2026-08-28", "TB",  "JAX", "PRE3"),
    ("2026-08-28", "NO",  "DAL", "PRE3"),
    ("2026-08-28", "ARI", "GB",  "PRE3"),
    ("2026-08-28", "SEA", "KC",  "PRE3"),
    ("2026-08-28", "CIN", "PHI", "PRE3"),
    ("2026-08-28", "MIN", "DEN", "PRE3"),

    ("2026-08-29", "DET", "IND", "PRE3"),
    ("2026-08-29", "CHI", "TEN", "PRE3"),
]

# ============================================================
# NOMBRES
# ============================================================

TEAM_NAMES = {
    "ARI": "Arizona Cardinals",
    "ATL": "Atlanta Falcons",
    "BAL": "Baltimore Ravens",
    "BUF": "Buffalo Bills",
    "CAR": "Carolina Panthers",
    "CHI": "Chicago Bears",
    "CIN": "Cincinnati Bengals",
    "CLE": "Cleveland Browns",
    "DAL": "Dallas Cowboys",
    "DEN": "Denver Broncos",
    "DET": "Detroit Lions",
    "GB": "Green Bay Packers",
    "HOU": "Houston Texans",
    "IND": "Indianapolis Colts",
    "JAX": "Jacksonville Jaguars",
    "KC": "Kansas City Chiefs",
    "LAC": "Los Angeles Chargers",
    "LAR": "Los Angeles Rams",
    "LV": "Las Vegas Raiders",
    "MIA": "Miami Dolphins",
    "MIN": "Minnesota Vikings",
    "NE": "New England Patriots",
    "NO": "New Orleans Saints",
    "NYG": "New York Giants",
    "NYJ": "New York Jets",
    "PHI": "Philadelphia Eagles",
    "PIT": "Pittsburgh Steelers",
    "SEA": "Seattle Seahawks",
    "SF": "San Francisco 49ers",
    "TB": "Tampa Bay Buccaneers",
    "TEN": "Tennessee Titans",
    "WAS": "Washington Commanders",
}

ALIASES = {
    "AZ": "ARI",
    "JAC": "JAX",
    "JACKSONVILLE": "JAX",
    "LAS VEGAS": "LV",
    "OAK": "LV",
    "LA": "LAR",
    "LOS ANGELES RAMS": "LAR",
    "LOS ANGELES CHARGERS": "LAC",
    "WASHINGTON": "WAS",
    "NEW ENGLAND": "NE",
    "NEW ORLEANS": "NO",
    "NEW YORK GIANTS": "NYG",
    "NEW YORK JETS": "NYJ",
    "TAMPA BAY": "TB",
    "GREEN BAY": "GB",
    "KANSAS CITY": "KC",
    "SAN FRANCISCO": "SF",
    "SEATTLE": "SEA",
    "TENNESSEE": "TEN",
}

# ============================================================
# UTILIDADES
# ============================================================

def norm_team(x):

    if x is None:
        return ""

    x = str(x).strip().upper()

    return ALIASES.get(x, x)


def fnum(x):

    try:

        if x is None:
            return None

        if pd.isna(x):
            return None

        return float(x)

    except Exception:

        return None


def pct(x):

    if x is None:
        return "N/A"

    return f"{x * 100:.1f}%"


def american_to_probability(odds):

    odds = fnum(odds)

    if odds is None:
        return None

    if odds < 0:

        return (-odds) / ((-odds) + 100)

    return 100 / (odds + 100)


def probability_to_american(p):

    if p is None:
        return None

    p = float(p)

    p = max(0.001, min(0.999, p))

    if p >= 0.5:

        return int(round(-100 * p / (1 - p)))

    return int(round(100 * (1 - p) / p))


def make_ticker(date_str, away, home):

    try:

        d = datetime.strptime(
            date_str,
            "%Y-%m-%d"
        )

        code = d.strftime(
            "%y%b%d"
        ).upper()

        return (
            f"KXNFLGAME-{code}"
            f"{away}{home}"
        )

    except Exception:

        return ""


# ============================================================
# CARGAR V6
# ============================================================

@st.cache_data(ttl=300)
def load_v6():

    try:

        df = pd.read_csv(
            V6_FILE
        )

        return df, None

    except Exception as e:

        return None, str(e)


# ============================================================
# FUERZA BASE V6
# ============================================================

def build_team_probs(v6):

    if v6 is None:
        return {}

    if "team" not in v6.columns:
        return {}

    if "model_prob" not in v6.columns:
        return {}

    data = {}

    for _, row in v6.iterrows():

        team = norm_team(
            row.get("team")
        )

        p = fnum(
            row.get("model_prob")
        )

        if not team or p is None:
            continue

        if 0.01 <= p <= 0.99:

            data.setdefault(
                team,
                []
            ).append(p)

    result = {}

    for team, values in data.items():

        if values:

            result[team] = float(
                np.median(values)
            )

    return result


# ============================================================
# PRESEASON MODEL
# ============================================================

def preseason_probability(
    away,
    home,
    team_probs
):

    ap = team_probs.get(
        away
    )

    hp = team_probs.get(
        home
    )

    # Ningún dato
    if ap is None and hp is None:

        return (
            0.50,
            "LOW",
            "NO V6 DATA"
        )

    # Solo visitante
    if ap is not None and hp is None:

        p_home = (
            0.50
            + (0.50 - ap) * 0.20
        )

        return (
            max(0.25, min(0.75, p_home)),
            "LOW",
            "AWAY ONLY"
        )

    # Solo local
    if ap is None and hp is not None:

        p_home = (
            0.50
            + (0.50 - hp) * 0.20
        )

        return (
            max(0.25, min(0.75, p_home)),
            "LOW",
            "HOME ONLY"
        )

    # Ambos
    strength = hp - ap

    # Compresión preseason
    p_home = (
        0.50
        + strength * 0.55
    )

    # Ventaja local pequeña
    p_home += 0.015

    p_home = max(
        0.25,
        min(0.75, p_home)
    )

    return (
        p_home,
        "MEDIUM",
        "BOTH TEAMS"
    )


# ============================================================
# CALENDARIO PRESEASON
# ============================================================

def get_preseason_games():

    games = []

    for (
        date_str,
        away,
        home,
        week
    ) in PRESEASON:

        games.append({

            "game_id":
                f"{date_str}_{away}_{home}",

            "date":
                date_str,

            "away":
                away,

            "home":
                home,

            "type":
                "PRE",

            "week":
                week
        })

    return games


# ============================================================
# KALSHI
# ============================================================

def get_kalshi_event(ticker):

    if not ticker:
        return None, [], "NO TICKER"

    url = (
        KALSHI_BASE
        + quote(
            ticker,
            safe=""
        )
    )

    try:

        response = requests.get(
            url,
            timeout=10,
            headers={
                "User-Agent":
                    "Monitor-NFL"
            }
        )

    except Exception as e:

        return (
            None,
            [],
            f"REQUEST ERROR: {e}"
        )

    if response.status_code != 200:

        return (
            None,
            [],
            f"HTTP {response.status_code}"
        )

    try:

        data = response.json()

    except Exception as e:

        return (
            None,
            [],
            f"JSON ERROR: {e}"
        )

    event = data.get(
        "event"
    )

    markets = (
        data.get("markets")
        or []
    )

    if event and not markets:

        markets = (
            event.get("markets")
            or []
        )

    return (
        event,
        markets,
        None
    )


def market_team(
    market,
    team
):

    if not market:
        return False

    ticker = str(
        market.get(
            "ticker",
            ""
        )
    ).upper()

    team = norm_team(team)

    return ticker.endswith(
        "-" + team
    )


def get_price(
    market,
    fields
):

    if not market:
        return None

    for field in fields:

        value = fnum(
            market.get(field)
        )

        if value is not None:

            if value > 1:

                value /= 100

            return value

    return None


def get_ask(market):

    return get_price(
        market,
        [
            "yes_ask_dollars",
            "yes_ask",
            "ask"
        ]
    )


# ============================================================
# NEWS
# ============================================================

def news_check(
    away,
    home,
    date_str
):

    query = quote(
        f"NFL {away} {home} "
        f"quarterback injury "
        f"starter {date_str}"
    )

    url = (
        "https://news.google.com/rss/search?"
        f"q={query}"
        "&hl=en-US"
        "&gl=US"
        "&ceid=US:en"
    )

    try:

        response = requests.get(
            url,
            timeout=8,
            headers={
                "User-Agent":
                    "Mozilla/5.0"
            }
        )

        if response.status_code != 200:

            return (
                "UNAVAILABLE",
                0.0,
                "RSS unavailable"
            )

        root = ET.fromstring(
            response.text
        )

        titles = []

        for item in root.findall(
            ".//item"
        )[:12]:

            title = item.findtext(
                "title"
            )

            if title:

                titles.append(
                    title
                )

        text = " ".join(
            titles
        ).lower()

        high_terms = [

            "starting quarterback",
            "starting qb",
            "backup quarterback",
            "backup qb",
            "quarterback competition",
            "qb competition",
            "won't play",
            "will not play",
            "not expected to play",

        ]

        medium_terms = [

            "resting",
            "rest",
            "sitting",
            "inactive",
            "limited",
            "snap count",
            "snaps",
            "injury",
            "injured",
            "questionable",
            "out",

        ]

        high = [
            x
            for x in high_terms
            if x in text
        ]

        medium = [
            x
            for x in medium_terms
            if x in text
        ]

        if high:

            return (
                "HIGH_RISK",
                0.35,
                ", ".join(
                    high[:4]
                )
            )

        if medium:

            return (
                "MEDIUM_RISK",
                0.15,
                ", ".join(
                    medium[:5]
                )
            )

        return (
            "NO_MAJOR_RISK",
            0.0,
            "No major risk"
        )

    except Exception as e:

        return (
            "UNAVAILABLE",
            0.0,
            str(e)[:100]
        )


# ============================================================
# ANALIZAR PARTIDOS ACTUALES
# ============================================================

def analyze_current_games():

    v6, v6_error = load_v6()

    team_probs = build_team_probs(
        v6
    )

    today = date.today()

    end_date = (
        today
        + timedelta(
            days=WINDOW_DAYS
        )
    )

    games = []

    # --------------------------------------------------------
    # PRESEASON
    # --------------------------------------------------------

    for game in get_preseason_games():

        try:

            game_date = datetime.strptime(
                game["date"],
                "%Y-%m-%d"
            ).date()

        except Exception:

            continue

        if today <= game_date <= end_date:

            games.append(
                game
            )

    # --------------------------------------------------------
    # REGULAR SEASON DESDE NFLVERSE
    # --------------------------------------------------------

    try:

        schedule = pd.read_csv(
            NFLVERSE_SCHEDULE_URL
        )

        if (
            "gameday" in schedule.columns
            and "season" in schedule.columns
        ):

            schedule = schedule[
                schedule["season"] == 2026
            ].copy()

            for _, row in schedule.iterrows():

                gd = row.get(
                    "gameday"
                )

                if pd.isna(gd):
                    continue

                try:

                    game_date = (
                        pd.to_datetime(
                            gd
                        ).date()
                    )

                except Exception:

                    continue

                if not (
                    today
                    <= game_date
                    <= end_date
                ):
                    continue

                game_type = str(
                    row.get(
                        "game_type",
                        ""
                    )
                ).upper()

                if game_type != "REG":
                    continue

                away = norm_team(
                    row.get(
                        "away_team"
                    )
                )

                home = norm_team(
                    row.get(
                        "home_team"
                    )
                )

                if not away or not home:
                    continue

                games.append({

                    "game_id":
                        str(
                            row.get(
                                "game_id",
                                f"{gd}_{away}_{home}"
                            )
                        ),

                    "date":
                        str(gd),

                    "away":
                        away,

                    "home":
                        home,

                    "type":
                        "REG",

                    "week":
                        str(
                            row.get(
                                "week",
                                ""
                            )
                        )
                })

    except Exception:
        pass

    # --------------------------------------------------------
    # ELIMINAR DUPLICADOS
    # --------------------------------------------------------

    unique = {}

    for game in games:

        key = (
            game["date"],
            game["away"],
            game["home"]
        )

        unique[key] = game

    games = sorted(
        unique.values(),
        key=lambda x: (
            x["date"],
            x["away"],
            x["home"]
        )
    )

    results = []

    for game in games:

        away = game["away"]
        home = game["home"]

        # ----------------------------------------------------
        # MODELO
        # ----------------------------------------------------

        if game["type"] == "PRE":

            home_prob, confidence, quality = (
                preseason_probability(
                    away,
                    home,
                    team_probs
                )
            )

            if home_prob >= 0.50:

                model_team = home
                model_prob = home_prob

            else:

                model_team = away
                model_prob = 1 - home_prob

            model_source = (
                "V6 PRESEASON"
            )

        else:

            model_team = None
            model_prob = None

            if v6 is not None:

                candidates = v6.copy()

                if (
                    "team" in candidates.columns
                    and
                    "opponent_team"
                    in candidates.columns
                ):

                    candidates[
                        "_team"
                    ] = (
                        candidates[
                            "team"
                        ]
                        .astype(str)
                        .str.upper()
                        .map(norm_team)
                    )

                    candidates[
                        "_opp"
                    ] = (
                        candidates[
                            "opponent_team"
                        ]
                        .astype(str)
                        .str.upper()
                        .map(norm_team)
                    )

                    found = candidates[
                        (
                            candidates[
                                "_team"
                            ] == home
                        )
                        &
                        (
                            candidates[
                                "_opp"
                            ] == away
                        )
                    ]

                    if len(found) == 0:

                        found = candidates[
                            (
                                candidates[
                                    "_team"
                                ] == away
                            )
                            &
                            (
                                candidates[
                                    "_opp"
                                ] == home
                            )
                        ]

                    if len(found):

                        row = found.iloc[0]

                        team = norm_team(
                            row["team"]
                        )

                        p = fnum(
                            row.get(
                                "model_prob"
                            )
                        )

                        if p is not None:

                            model_team = team

                            if team == home:

                                model_prob = p

                            else:

                                model_prob = 1 - p

            if model_prob is None:

                model_team = home
                model_prob = 0.50

                confidence = "LOW"
                quality = "NO V6 MATCH"

            else:

                confidence = "HIGH"
                quality = "V6"

            model_source = "V6"

        # ----------------------------------------------------
        # KALSHI
        # ----------------------------------------------------

        ticker = make_ticker(
            game["date"],
            away,
            home
        )

        event, markets, api_error = (
            get_kalshi_event(
                ticker
            )
        )

        away_ask = None
        home_ask = None

        if event is not None:

            for market in markets:

                if market_team(
                    market,
                    away
                ):

                    away_ask = get_ask(
                        market
                    )

                if market_team(
                    market,
                    home
                ):

                    home_ask = get_ask(
                        market
                    )

        # ----------------------------------------------------
        # EDGE
        # ----------------------------------------------------

        if model_team == home:

            selected_ask = home_ask

        else:

            selected_ask = away_ask

        raw_edge = None

        if (
            model_prob is not None
            and selected_ask is not None
        ):

            raw_edge = (
                model_prob
                - selected_ask
            )

        # ----------------------------------------------------
        # NEWS
        # ----------------------------------------------------

        news_status, news_risk, news_reason = (
            news_check(
                away,
                home,
                game["date"]
            )
        )

        if news_risk >= 0.35:

            news_factor = 0.65

        elif news_risk >= 0.15:

            news_factor = 0.85

        else:

            news_factor = 1.0

        adjusted_edge = None

        if raw_edge is not None:

            adjusted_edge = (
                raw_edge
                * news_factor
            )

        # ----------------------------------------------------
        # CONFIDENCE
        # ----------------------------------------------------

        final_confidence = confidence

        if (
            news_risk >= 0.35
            and confidence == "HIGH"
        ):

            final_confidence = "MEDIUM"

        elif (
            news_risk >= 0.35
            and confidence == "MEDIUM"
        ):

            final_confidence = "LOW"

        confidence_factor = {

            "HIGH": 1.00,
            "MEDIUM": 0.70,
            "LOW": 0.40

        }.get(
            final_confidence,
            0.40
        )

        if adjusted_edge is not None:

            adjusted_edge *= (
                confidence_factor
            )

        # ----------------------------------------------------
        # STATUS
        # ----------------------------------------------------

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

            "game_id":
                game["game_id"],

            "date":
                game["date"],

            "type":
                game["type"],

            "week":
                game["week"],

            "away":
                away,

            "home":
                home,

            "model_team":
                model_team,

            "model_prob":
                model_prob,

            "confidence":
                final_confidence,

            "quality":
                quality,

            "away_ask":
                away_ask,

            "home_ask":
                home_ask,

            "selected_ask":
                selected_ask,

            "raw_edge":
                raw_edge,

            "adjusted_edge":
                adjusted_edge,

            "news_status":
                news_status,

            "news_reason":
                news_reason,

            "status":
                status,

            "ticker":
                ticker,

            "event_found":
                event is not None,

            "api_error":
                api_error,

        })

    return (
        pd.DataFrame(results),
        v6,
        v6_error
    )


# ============================================================
# HISTORICAL DATA
# ============================================================

@st.cache_data(ttl=86400)
def load_historical_schedule():

    try:

        df = pd.read_csv(
            NFLVERSE_SCHEDULE_URL
        )

        return df, None

    except Exception as e:

        return None, str(e)


# ============================================================
# ELO
# ============================================================

def expected_result(
    rating_a,
    rating_b
):

    return (
        1
        /
        (
            1
            +
            10 ** (
                (rating_b - rating_a)
                / 400
            )
        )
    )


def run_elo_backtest(
    seasons
):

    schedule, error = (
        load_historical_schedule()
    )

    if schedule is None:

        return None, error

    df = schedule.copy()

    required = [
        "season",
        "game_type",
        "gameday",
        "away_team",
        "home_team",
        "away_score",
        "home_score"
    ]

    missing = [
        c
        for c in required
        if c not in df.columns
    ]

    if missing:

        return (
            None,
            "Faltan columnas: "
            + ", ".join(missing)
        )

    # --------------------------------------------------------
    # SOLO REGULAR SEASON
    # --------------------------------------------------------

    df = df[
        df["game_type"]
        .astype(str)
        .str.upper()
        .eq("REG")
    ].copy()

    df = df[
        df["season"].isin(
            seasons
        )
    ].copy()

    df["gameday"] = pd.to_datetime(
        df["gameday"],
        errors="coerce"
    )

    df["away_score"] = pd.to_numeric(
        df["away_score"],
        errors="coerce"
    )

    df["home_score"] = pd.to_numeric(
        df["home_score"],
        errors="coerce"
    )

    df = df.dropna(
        subset=[
            "gameday",
            "away_score",
            "home_score"
        ]
    )

    df = df.sort_values(
        "gameday"
    ).reset_index(
        drop=True
    )

    # --------------------------------------------------------
    # ELO INICIAL
    # --------------------------------------------------------

    ratings = {}

    base_rating = 1500

    K = 20

    HOME_ADVANTAGE = 48

    records = []

    for _, row in df.iterrows():

        away = norm_team(
            row["away_team"]
        )

        home = norm_team(
            row["home_team"]
        )

        if away not in ratings:

            ratings[away] = (
                base_rating
            )

        if home not in ratings:

            ratings[home] = (
                base_rating
            )

        away_rating = ratings[
            away
        ]

        home_rating = ratings[
            home
        ]

        # ----------------------------------------------------
        # PREDICCIÓN ANTES DEL RESULTADO
        # ----------------------------------------------------

        home_expected = expected_result(
            home_rating + HOME_ADVANTAGE,
            away_rating
        )

        away_expected = (
            1 - home_expected
        )

        actual_home = float(
            row["home_score"]
        )

        actual_away = float(
            row["away_score"]
        )

        if actual_home > actual_away:

            home_result = 1.0
            away_result = 0.0

        elif actual_home < actual_away:

            home_result = 0.0
            away_result = 1.0

        else:

            home_result = 0.5
            away_result = 0.5

        # ----------------------------------------------------
        # GUARDAR PREDICCIÓN
        # ----------------------------------------------------

        records.append({

            "date":
                row["gameday"],

            "season":
                int(row["season"]),

            "away":
                away,

            "home":
                home,

            "away_prob":
                away_expected,

            "home_prob":
                home_expected,

            "away_score":
                actual_away,

            "home_score":
                actual_home,

            "home_win":
                1
                if home_result == 1
                else 0,

            "away_win":
                1
                if away_result == 1
                else 0,

        })

        # ----------------------------------------------------
        # ACTUALIZAR ELO DESPUÉS DEL RESULTADO
        # ----------------------------------------------------

        home_change = (
            K
            *
            (
                home_result
                - home_expected
            )
        )

        away_change = (
            K
            *
            (
                away_result
                - away_expected
            )
        )

        ratings[home] += (
            home_change
        )

        ratings[away] += (
            away_change
        )

    result = pd.DataFrame(
        records
    )

    return result, None


# ============================================================
# MÉTRICAS DE BACKTEST
# ============================================================

def calculate_backtest_metrics(
    df
):

    if df is None or len(df) == 0:

        return {}

    predictions = []

    actuals = []

    for _, row in df.iterrows():

        p = float(
            row["home_prob"]
        )

        y = int(
            row["home_win"]
        )

        predictions.append(p)
        actuals.append(y)

    p = np.array(
        predictions
    )

    y = np.array(
        actuals
    )

    # --------------------------------------------------------
    # LOG LOSS
    # --------------------------------------------------------

    p_clip = np.clip(
        p,
        0.001,
        0.999
    )

    log_loss = -np.mean(
        y * np.log(p_clip)
        +
        (1 - y)
        * np.log(1 - p_clip)
    )

    # --------------------------------------------------------
    # BRIER
    # --------------------------------------------------------

    brier = np.mean(
        (p - y) ** 2
    )

    # --------------------------------------------------------
    # ACCURACY
    # --------------------------------------------------------

    predicted_home = (
        p >= 0.50
    )

    accuracy = np.mean(
        predicted_home == (
            y == 1
        )
    )

    return {

        "games":
            len(df),

        "accuracy":
            accuracy,

        "log_loss":
            log_loss,

        "brier":
            brier
    }


# ============================================================
# CALIBRACIÓN
# ============================================================

def calibration_table(
    df
):

    if df is None or len(df) == 0:

        return pd.DataFrame()

    work = df.copy()

    work["predicted_prob"] = (
        work["home_prob"]
    )

    work["actual"] = (
        work["home_win"]
    )

    bins = [
        0.50,
        0.55,
        0.60,
        0.65,
        0.70,
        0.75,
        0.80,
        0.85,
        0.90,
        1.01
    ]

    labels = [
        "50-54%",
        "55-59%",
        "60-64%",
        "65-69%",
        "70-74%",
        "75-79%",
        "80-84%",
        "85-89%",
        "90%+"
    ]

    work["bucket"] = pd.cut(
        work["predicted_prob"],
        bins=bins,
        labels=labels,
        right=False
    )

    result = (
        work
        .groupby(
            "bucket",
            observed=False
        )
        .agg(
            partidos=(
                "actual",
                "count"
            ),
            prob_media=(
                "predicted_prob",
                "mean"
            ),
            victorias=(
                "actual",
                "sum"
            )
        )
        .reset_index()
    )

    result[
        "victoria_real"
    ] = (
        result["victorias"]
        /
        result["partidos"]
        .replace(0, np.nan)
    )

    result[
        "error_calibracion"
    ] = (
        result["victoria_real"]
        -
        result["prob_media"]
    )

    return result


# ============================================================
# ROI TEÓRICO
# ============================================================

def calculate_roi(
    df,
    threshold=0.60
):

    if df is None or len(df) == 0:

        return None

    # Apostamos al lado que el modelo
    # considera favorito.
    #
    # Para no introducir ventaja artificial,
    # usamos cuota justa aproximada
    # derivada de la probabilidad.
    #
    # Esto NO representa una cuota real
    # histórica de sportsbook.

    bets = []

    for _, row in df.iterrows():

        home_p = float(
            row["home_prob"]
        )

        if home_p >= threshold:

            predicted_win = (
                int(row["home_win"])
            )

            p = home_p

        else:

            away_p = (
                1 - home_p
            )

            if away_p < threshold:

                continue

            predicted_win = (
                int(row["away_win"])
            )

            p = away_p

        # Cuota teórica
        decimal_odds = (
            1 / p
        )

        if predicted_win == 1:

            profit = (
                decimal_odds - 1
            )

        else:

            profit = -1

        bets.append(
            profit
        )

    if not bets:

        return None

    total_profit = sum(
        bets
    )

    stake = len(bets)

    roi = (
        total_profit
        /
        stake
    )

    return {

        "bets":
            len(bets),

        "profit":
            total_profit,

        "roi":
            roi

    }


# ============================================================
# CSS
# ============================================================

st.markdown(
    """
    <style>

    .main {
        background-color: #0e0f14;
    }

    .block-container {
        max-width: 1100px;
        padding-top: 2rem;
    }

    h1, h2, h3 {
        color: #f5f5f5;
    }

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

    .projection h3 {
        color: #a9e4bd;
    }

    .projection p {
        color: #b3e7c3;
        font-size: 20px;
    }

    .positive {
        padding: 20px;
        border-radius: 18px;
        background: #173b29;
        color: #78df9b;
        font-size: 20px;
    }

    .warning {
        padding: 20px;
        border-radius: 18px;
        background: #3b3620;
        color: #f3e7a1;
        font-size: 20px;
    }

    .danger {
        padding: 20px;
        border-radius: 18px;
        background: #3d2025;
        color: #ff8f8f;
        font-size: 20px;
    }

    .muted {
        color: #a5a6ad;
    }

    </style>
    """,
    unsafe_allow_html=True
)


# ============================================================
# HEADER
# ============================================================

st.title(
    "🏈 Monitor NFL"
)

st.subheader(
    "Modelo propio — análisis NFL automático"
)

tab1, tab2, tab3 = st.tabs(
    [
        "🏈 NFL DE HOY",
        "🧪 VALIDACIÓN DEL MODELO",
        "📊 INFORMACIÓN"
    ]
)


# ============================================================
# TAB 1 — NFL DE HOY
# ============================================================

with tab1:

    st.header(
        "🏈 NFL DE HOY"
    )

    if st.button(
        "🔄 ACTUALIZAR PARTIDOS",
        use_container_width=True
    ):

        st.cache_data.clear()

        st.rerun()

    with st.spinner(
        "Consultando partidos y modelo..."
    ):

        games_df, v6, v6_error = (
            analyze_current_games()
        )

    if games_df is None:

        st.error(
            "No se pudo cargar el monitor."
        )

    elif len(games_df) == 0:

        st.warning(
            "⚠️ No se encontraron partidos "
            "NFL en los próximos 7 días."
        )

    else:

        st.success(
            f"Se encontraron "
            f"{len(games_df)} partidos."
        )

        st.markdown("---")

        # ====================================================
        # MOSTRAR PARTIDOS
        # ====================================================

        for _, game in games_df.iterrows():

            away = game["away"]
            home = game["home"]

            away_name = TEAM_NAMES.get(
                away,
                away
            )

            home_name = TEAM_NAMES.get(
                home,
                home
            )

            model_team = game[
                "model_team"
            ]

            model_prob = game[
                "model_prob"
            ]

            # ------------------------------------------------
            # TARJETA
            # ------------------------------------------------

            st.markdown(
                '<div class="game-card">',
                unsafe_allow_html=True
            )

            st.subheader(
                f"🏈 {away_name}"
            )

            st.subheader(
                f"@ {home_name}"
            )

            st.write(
                f"📅 {game['date']}"
            )

            st.write(
                f"🕒 Partido NFL"
            )

            st.markdown(
                "</div>",
                unsafe_allow_html=True
            )

            # ------------------------------------------------
            # PROBABILIDADES
            # ------------------------------------------------

            away_prob = (
                1 - model_prob
            )

            home_prob = (
                model_prob
            )

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

            away_fair = probability_to_american(
                away_prob
            )

            st.write(
                f"🎯 Cuota justa: "
                f"{away_fair:+d}"
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

            home_fair = probability_to_american(
                home_prob
            )

            st.write(
                f"🎯 Cuota justa: "
                f"{home_fair:+d}"
            )

            # ------------------------------------------------
            # PROYECCIÓN
            # ------------------------------------------------

            favorite = (
                model_team
            )

            favorite_prob = (
                model_prob
                if model_team == home
                else 1 - model_prob
            )

            fair_odds = (
                probability_to_american(
                    favorite_prob
                )
            )

            confidence = game[
                "confidence"
            ]

            st.markdown(
                f"""
                <div class="projection">

                <h3>
                🧠 PROYECCIÓN DEL MODELO
                </h3>

                <p>
                Favorito:
                <strong>
                {TEAM_NAMES.get(
                    favorite,
                    favorite
                )}
                </strong>
                </p>

                <p>
                Probabilidad estimada:
                <strong>
                {favorite_prob * 100:.1f}%
                </strong>
                </p>

                <p>
                Cuota justa:
                <strong>
                {fair_odds:+d}
                </strong>
                </p>

                <p>
                Confianza:
                <strong>
                {confidence}
                </strong>
                </p>

                </div>
                """,
                unsafe_allow_html=True
            )

            # ------------------------------------------------
            # COMPARACIÓN
            # ------------------------------------------------

            st.subheader(
                "🏦 COMPARACIÓN CON LA CASA"
            )

            selected_ask = game[
                "selected_ask"
            ]

            if selected_ask is not None:

                market_prob = (
                    selected_ask
                )

                edge = game[
                    "adjusted_edge"
                ]

                st.write(
                    f"Mercado: "
                    f"{market_prob * 100:.1f}%"
                )

                if edge is not None:

                    st.write(
                        f"Edge ajustado: "
                        f"{edge * 100:+.2f}%"
                    )

                    if edge >= 0.15:

                        st.success(
                            "🚨 STRONG SIGNAL"
                        )

                    elif edge >= 0.08:

                        st.success(
                            "🟢 OPPORTUNITY"
                        )

                    elif edge >= 0.04:

                        st.warning(
                            "🟡 WATCH"
                        )

                    else:

                        st.info(
                            "Sin edge suficiente."
                        )

            else:

                st.info(
                    "No hay precio de mercado "
                    "disponible."
                )

            st.write(
                f"📡 Fuente: "
                f"{game['quality']}"
            )

            st.write(
                f"📰 News risk: "
                f"{game['news_status']}"
            )

            st.write(
                f"📌 Estado: "
                f"{game['status']}"
            )

            st.markdown("---")


# ============================================================
# TAB 2 — VALIDACIÓN
# ============================================================

with tab2:

    st.header(
        "🧪 VALIDACIÓN DEL MODELO"
    )

    st.write(
        """
        Esta sección sirve para responder la pregunta
        más importante:

        **Cuando el modelo dice 60%, 65%, 70%, etc.,
        realmente gana aproximadamente ese porcentaje?**

        El backtest utiliza únicamente información disponible
        antes de cada partido para calcular la predicción.
        El resultado del partido se incorpora después.
        """
    )

    st.info(
        """
        ⚠️ IMPORTANTE:
        Este backtest histórico utiliza un modelo Elo
        independiente como prueba de calibración
        sin leakage. No se debe interpretar como que
        reproduce exactamente cada peso interno de V6.
        """
    )

    st.markdown("---")

    current_year = datetime.now().year

    default_start = max(
        2018,
        current_year - 7
    )

    col1, col2 = st.columns(2)

    with col1:

        start_season = st.number_input(
            "Temporada inicial",
            min_value=2000,
            max_value=current_year - 1,
            value=default_start,
            step=1
        )

    with col2:

        end_season = st.number_input(
            "Temporada final",
            min_value=2000,
            max_value=current_year - 1,
            value=current_year - 1,
            step=1
        )

    if start_season > end_season:

        st.error(
            "La temporada inicial no puede "
            "ser mayor que la final."
        )

    else:

        if st.button(
            "🧪 EJECUTAR BACKTEST",
            use_container_width=True
        ):

            seasons = list(
                range(
                    int(start_season),
                    int(end_season) + 1
                )
            )

            with st.spinner(
                "Ejecutando backtest histórico..."
            ):

                backtest, error = (
                    run_elo_backtest(
                        seasons
                    )
                )

            if backtest is None:

                st.error(
                    f"No se pudo ejecutar: {error}"
                )

            else:

                st.session_state[
                    "backtest"
                ] = backtest

    # ========================================================
    # MOSTRAR RESULTADOS
    # ========================================================

    if "backtest" in st.session_state:

        backtest = st.session_state[
            "backtest"
        ]

        metrics = (
            calculate_backtest_metrics(
                backtest
            )
        )

        st.markdown("---")

        st.subheader(
            "📊 RESULTADOS GENERALES"
        )

        c1, c2, c3, c4 = st.columns(4)

        c1.metric(
            "Partidos",
            f"{metrics['games']:,}"
        )

        c2.metric(
            "Accuracy",
            f"{metrics['accuracy'] * 100:.2f}%"
        )

        c3.metric(
            "Log Loss",
            f"{metrics['log_loss']:.4f}"
        )

        c4.metric(
            "Brier Score",
            f"{metrics['brier']:.4f}"
        )

        st.markdown("---")

        # ====================================================
        # CALIBRACIÓN
        # ====================================================

        st.subheader(
            "🎯 CALIBRACIÓN POR PROBABILIDAD"
        )

        calibration = (
            calibration_table(
                backtest
            )
        )

        if len(calibration):

            display = calibration.copy()

            display[
                "Prob. modelo"
            ] = (
                display[
                    "prob_media"
                ] * 100
            ).round(1).astype(str) + "%"

            display[
                "Victoria real"
            ] = (
                display[
                    "victoria_real"
                ] * 100
            ).round(1).astype(str) + "%"

            display[
                "Error"
            ] = (
                display[
                    "error_calibracion"
                ] * 100
            ).round(1).astype(str) + "%"

            display = display[
                [
                    "bucket",
                    "partidos",
                    "Prob. modelo",
                    "victorias",
                    "Victoria real",
                    "Error"
                ]
            ]

            st.dataframe(
                display,
                use_container_width=True,
                hide_index=True
            )

        # ====================================================
        # INTERPRETACIÓN
        # ====================================================

        st.markdown("---")

        st.subheader(
            "🧠 ¿CÓMO LEER ESTO?"
        )

        st.write(
            """
            Lo que queremos ver es algo parecido a:

            • 60–64% → alrededor de 60–64% de victorias

            • 65–69% → alrededor de 65–69%

            • 70–74% → alrededor de 70–74%

            • 75–79% → alrededor de 75–79%

            Si las probabilidades están muy por encima o
            por debajo de los resultados reales, el modelo
            necesita calibración.
            """
        )

        # ====================================================
        # ROI TEÓRICO
        # ====================================================

        st.markdown("---")

        st.subheader(
            "💰 PRUEBA DE SELECCIÓN"
        )

        threshold = st.slider(
            "Probabilidad mínima",
            min_value=0.50,
            max_value=0.80,
            value=0.60,
            step=0.01
        )

        roi = calculate_roi(
            backtest,
            threshold
        )

        if roi is not None:

            c1, c2, c3 = st.columns(3)

            c1.metric(
                "Señales",
                roi["bets"]
            )

            c2.metric(
                "Resultado teórico",
                f"{roi['profit']:+.2f} unidades"
            )

            c3.metric(
                "ROI teórico",
                f"{roi['roi'] * 100:+.2f}%"
            )

            st.caption(
                """
                Este ROI es únicamente una prueba matemática
                usando cuotas derivadas de la propia probabilidad.
                NO representa rendimiento real de sportsbook.
                """
            )

        # ====================================================
        # ÚLTIMOS PARTIDOS
        # ====================================================

        st.markdown("---")

        st.subheader(
            "📋 ÚLTIMOS PARTIDOS DEL BACKTEST"
        )

        recent = backtest.tail(
            30
        ).copy()

        recent[
            "Modelo"
        ] = (
            recent[
                "home_prob"
            ] * 100
        ).round(1).astype(str) + "%"

        recent[
            "Resultado"
        ] = np.where(
            recent[
                "home_win"
            ] == 1,
            "HOME WIN",
            "AWAY WIN"
        )

        recent[
            "Partido"
        ] = (
            recent["away"]
            + " @ "
            + recent["home"]
        )

        recent[
            "Marcador"
        ] = (
            recent[
                "away_score"
            ].astype(int).astype(str)
            + "-"
            + recent[
                "home_score"
            ].astype(int).astype(str)
        )

        st.dataframe(
            recent[
                [
                    "date",
                    "season",
                    "Partido",
                    "Modelo",
                    "Marcador",
                    "Resultado"
                ]
            ],
            use_container_width=True,
            hide_index=True
        )


# ============================================================
# TAB 3 — INFORMACIÓN
# ============================================================

with tab3:

    st.header(
        "📊 INFORMACIÓN DEL MODELO"
    )

    st.markdown(
        """
        ### 🧠 ¿Qué estamos intentando comprobar?

        El objetivo no es simplemente que el modelo diga
        quién es favorito.

        Queremos comprobar tres cosas:

        **1. Precisión**

        ¿El favorito del modelo gana más veces que el 50%?

        **2. Calibración**

        Si dice 65%, ¿realmente gana cerca del 65%?

        **3. Valor**

        Cuando existe diferencia entre la probabilidad
        del modelo y la probabilidad implícita del mercado,
        ¿esa diferencia tiene valor histórico?

        ---

        ### 🎯 Umbrales actuales

        **Diagnóstico:** 60%

        **Señal oficial:** 63%

        **Edge mínimo:** 8%

        **Edge máximo:** 20%

        ---

        ### ⚠️ IMPORTANTE

        El sistema es experimental.

        Las probabilidades son estimaciones estadísticas.

        No garantizan resultados futuros.

        El monitor no realiza apuestas automáticamente.
        """
    )

    st.markdown("---")

    st.subheader(
        "📡 Fuentes"
    )

    st.write(
        "NFL Schedule / resultados históricos: NFL / nflverse"
    )

    st.write(
        "Modelo actual 2026: nfl_v6_predictions_2026.csv"
    )

    st.write(
        "Mercados: Kalshi cuando están disponibles"
    )

    st.markdown("---")

    st.subheader(
        "🔎 Estado V6"
    )

    if v6 is not None:

        st.success(
            f"V6 cargado correctamente: "
            f"{len(v6)} filas."
        )

    else:

        st.warning(
            "No se encontró "
            f"{V6_FILE}."
        )

        if v6_error:

            st.caption(
                v6_error
            )


# ============================================================
# FOOTER
# ============================================================

st.markdown(
    "---"
)

st.caption(
    "Monitor NFL — herramienta experimental de análisis estadístico. "
    "Las probabilidades son estimaciones y no garantizan resultados futuros."
)
