import streamlit as st
import pandas as pd
import numpy as np
import requests
import math
from datetime import datetime, timedelta, date
from urllib.parse import quote

# ============================================================
# MONITOR NFL — MODELO INDEPENDIENTE
#
# OBJETIVO:
#   Modelo propio -> Probabilidad -> Mercado -> EDGE
#
# IMPORTANTE:
#   - NO usa las cuotas para crear la probabilidad
#   - Máximo 2 temporadas históricas: 2024 y 2025
#   - No necesita archivos V6 históricos
#   - No realiza apuestas
# ============================================================

st.set_page_config(
    page_title="NFL Edge Monitor",
    page_icon="🏈",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ============================================================
# CONFIGURACIÓN
# ============================================================

NFLVERSE_SCHEDULE_URL = (
    "https://github.com/nflverse/nflverse-data/"
    "releases/download/schedules/schedules.csv"
)

WINDOW_DAYS = 7

# ------------------------------------------------------------
# HISTÓRICO — MÁXIMO 2 AÑOS
# ------------------------------------------------------------

HISTORICAL_SEASONS = [2024, 2025]

# ------------------------------------------------------------
# FILTROS
# ------------------------------------------------------------

MIN_MODEL_PROB = 0.55
MIN_EDGE = 0.06
STRONG_EDGE = 0.10

# ------------------------------------------------------------
# MODELO
# ------------------------------------------------------------

BASE_ELO = 1500

ELO_K = 20

HOME_ADVANTAGE = 48

# Peso del ELO vs rendimiento reciente
ELO_WEIGHT = 0.70
FORM_WEIGHT = 0.30

# ============================================================
# PRETEMPORADA 2026
# ============================================================

PRESEASON = [

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
    "OAK": "LV",
    "LAS VEGAS": "LV",
    "LA": "LAR",
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


def american_to_probability(odds):

    try:

        odds = float(odds)

    except:

        return None

    if odds < 0:

        return (-odds) / ((-odds) + 100)

    return 100 / (odds + 100)


def probability_to_american(p):

    if p is None:
        return None

    p = max(
        0.001,
        min(0.999, float(p))
    )

    if p >= 0.5:

        return int(
            round(
                -100 * p / (1 - p)
            )
        )

    return int(
        round(
            100 * (1 - p) / p
        )
    )


def pct(x):

    if x is None:
        return "N/A"

    return f"{x * 100:.1f}%"

# ============================================================
# CARGAR NFLVERSE
# ============================================================

@st.cache_data(ttl=86400)
def load_schedule():

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


def build_ratings():

    schedule, error = load_schedule()

    if schedule is None:

        return {}, {}, error

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

    for col in required:

        if col not in df.columns:

            return {}, {}, (
                f"Falta columna {col}"
            )

    df = df[
        df["game_type"]
        .astype(str)
        .str.upper()
        .eq("REG")
    ].copy()

    df = df[
        df["season"].isin(
            HISTORICAL_SEASONS
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
    )

    ratings = {}

    # Rendimiento reciente
    recent = {}

    for _, row in df.iterrows():

        away = norm_team(
            row["away_team"]
        )

        home = norm_team(
            row["home_team"]
        )

        if not away or not home:
            continue

        ratings.setdefault(
            away,
            BASE_ELO
        )

        ratings.setdefault(
            home,
            BASE_ELO
        )

        recent.setdefault(
            away,
            []
        )

        recent.setdefault(
            home,
            []
        )

        away_rating = ratings[
            away
        ]

        home_rating = ratings[
            home
        ]

        home_expected = expected_result(
            home_rating + HOME_ADVANTAGE,
            away_rating
        )

        away_expected = (
            1 - home_expected
        )

        home_score = float(
            row["home_score"]
        )

        away_score = float(
            row["away_score"]
        )

        if home_score > away_score:

            home_result = 1.0
            away_result = 0.0

        elif home_score < away_score:

            home_result = 0.0
            away_result = 1.0

        else:

            home_result = 0.5
            away_result = 0.5

        # Actualizar ELO
        ratings[home] += (
            ELO_K
            *
            (
                home_result
                -
                home_expected
            )
        )

        ratings[away] += (
            ELO_K
            *
            (
                away_result
                -
                away_expected
            )
        )

        # Diferencial de puntos
        margin_home = (
            home_score
            - away_score
        )

        margin_away = -margin_home

        recent[home].append(
            margin_home
        )

        recent[away].append(
            margin_away
        )

        # Mantener últimos 8 partidos
        recent[home] = recent[
            home
        ][-8:]

        recent[away] = recent[
            away
        ][-8:]

    return (
        ratings,
        recent,
        None
    )

# ============================================================
# MODELO PROPIO
# ============================================================

def logistic_probability(
    rating_difference
):

    return (
        1
        /
        (
            1
            +
            math.exp(
                -rating_difference
                / 400
            )
        )
    )


def model_probability(
    away,
    home,
    ratings,
    recent
):

    away_rating = ratings.get(
        away,
        BASE_ELO
    )

    home_rating = ratings.get(
        home,
        BASE_ELO
    )

    # --------------------------------------------------------
    # COMPONENTE ELO
    # --------------------------------------------------------

    elo_difference = (
        home_rating
        +
        HOME_ADVANTAGE
        -
        away_rating
    )

    elo_prob = logistic_probability(
        elo_difference
    )

    # --------------------------------------------------------
    # COMPONENTE FORMA
    # --------------------------------------------------------

    away_form = np.mean(
        recent.get(
            away,
            [0]
        )
    )

    home_form = np.mean(
        recent.get(
            home,
            [0]
        )
    )

    form_difference = (
        home_form
        -
        away_form
    )

    # Convertir diferencial de puntos
    # a una probabilidad pequeña.
    form_prob = (
        0.50
        +
        np.tanh(
            form_difference
            / 35
        )
        * 0.20
    )

    # --------------------------------------------------------
    # COMBINACIÓN
    # --------------------------------------------------------

    final_prob = (
        elo_prob
        * ELO_WEIGHT
        +
        form_prob
        * FORM_WEIGHT
    )

    # Evitamos probabilidades absurdas
    final_prob = max(
        0.15,
        min(
            0.85,
            final_prob
        )
    )

    return final_prob

# ============================================================
# PRETEMPORADA
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

            "date": date_str,
            "away": away,
            "home": home,
            "type": "PRE",
            "week": week

        })

    return games

# ============================================================
# PARTIDOS ACTUALES
# ============================================================

def get_current_games():

    schedule, error = load_schedule()

    today = date.today()

    end_date = (
        today
        +
        timedelta(
            days=WINDOW_DAYS
        )
    )

    games = []

    # --------------------------------------------------------
    # PRETEMPORADA
    # --------------------------------------------------------

    for game in get_preseason_games():

        d = datetime.strptime(
            game["date"],
            "%Y-%m-%d"
        ).date()

        if today <= d <= end_date:

            games.append(
                game
            )

    # --------------------------------------------------------
    # REGULAR SEASON
    # --------------------------------------------------------

    if schedule is not None:

        df = schedule.copy()

        if (
            "season" in df.columns
            and
            "game_type" in df.columns
            and
            "gameday" in df.columns
        ):

            df = df[
                (
                    df["season"]
                    == 2026
                )
                &
                (
                    df["game_type"]
                    .astype(str)
                    .str.upper()
                    == "REG"
                )
            ].copy()

            for _, row in df.iterrows():

                try:

                    d = pd.to_datetime(
                        row["gameday"]
                    ).date()

                except:

                    continue

                if not (
                    today
                    <= d
                    <= end_date
                ):

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

                if away and home:

                    games.append({

                        "date":
                            str(
                                row[
                                    "gameday"
                                ]
                            ),

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

    # --------------------------------------------------------
    # DEDUPLICAR
    # --------------------------------------------------------

    unique = {}

    for game in games:

        key = (
            game["date"],
            game["away"],
            game["home"]
        )

        unique[key] = game

    return sorted(
        unique.values(),
        key=lambda x: (
            x["date"],
            x["away"],
            x["home"]
        )
    )

# ============================================================
# MERCADO KALSHI
# ============================================================

KALSHI_BASE = (
    "https://external-api.kalshi.com/"
    "trade-api/v2/events/"
)


def make_ticker(
    date_str,
    away,
    home
):

    try:

        d = datetime.strptime(
            date_str[:10],
            "%Y-%m-%d"
        )

        code = d.strftime(
            "%y%b%d"
        ).upper()

        return (
            f"KXNFLGAME-{code}"
            f"{away}{home}"
        )

    except:

        return ""


def get_market(
    ticker
):

    if not ticker:

        return None, []

    url = (
        KALSHI_BASE
        +
        quote(
            ticker,
            safe=""
        )
    )

    try:

        r = requests.get(
            url,
            timeout=8,
            headers={
                "User-Agent":
                    "NFL-Edge-Monitor"
            }
        )

        if r.status_code != 200:

            return None, []

        data = r.json()

        event = data.get(
            "event"
        )

        markets = (
            data.get(
                "markets"
            )
            or []
        )

        if event and not markets:

            markets = (
                event.get(
                    "markets"
                )
                or []
            )

        return (
            event,
            markets
        )

    except:

        return None, []

# ============================================================
# EXTRAER PRECIO
# ============================================================

def get_price(
    market
):

    if not market:

        return None

    fields = [

        "yes_ask_dollars",
        "yes_ask",
        "ask"

    ]

    for field in fields:

        value = market.get(
            field
        )

        try:

            value = float(
                value
            )

        except:

            continue

        if value > 1:

            value /= 100

        return value

    return None


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

    return ticker.endswith(
        "-" + norm_team(team)
    )

# ============================================================
# ANALIZAR PARTIDOS
# ============================================================

def analyze_games():

    ratings, recent, error = (
        build_ratings()
    )

    if error:

        return pd.DataFrame(), error

    games = get_current_games()

    results = []

    for game in games:

        away = game["away"]
        home = game["home"]

        # ----------------------------------------------------
        # MODELO PROPIO
        # ----------------------------------------------------

        home_prob = model_probability(
            away,
            home,
            ratings,
            recent
        )

        away_prob = (
            1
            -
            home_prob
        )

        if home_prob >= away_prob:

            favorite = home
            favorite_prob = home_prob

        else:

            favorite = away
            favorite_prob = away_prob

        fair_odds = (
            probability_to_american(
                favorite_prob
            )
        )

        # ----------------------------------------------------
        # MERCADO
        # ----------------------------------------------------

        ticker = make_ticker(
            game["date"],
            away,
            home
        )

        event, markets = get_market(
            ticker
        )

        away_market = None
        home_market = None

        for market in markets:

            if market_team(
                market,
                away
            ):

                away_market = get_price(
                    market
                )

            if market_team(
                market,
                home
            ):

                home_market = get_price(
                    market
                )

        if favorite == home:

            market_prob = home_market

        else:

            market_prob = away_market

        # ----------------------------------------------------
        # EDGE
        # ----------------------------------------------------

        edge = None

        if market_prob is not None:

            edge = (
                favorite_prob
                -
                market_prob
            )

        # ----------------------------------------------------
        # SEÑAL
        # ----------------------------------------------------

        if edge is None:

            status = (
                "SIN PRECIO"
            )

        elif (
            favorite_prob
            < MIN_MODEL_PROB
        ):

            status = (
                "MODELO DÉBIL"
            )

        elif edge >= STRONG_EDGE:

            status = (
                "🟢 STRONG EDGE"
            )

        elif edge >= MIN_EDGE:

            status = (
                "🟢 OPPORTUNITY"
            )

        elif edge > 0:

            status = (
                "🟡 WATCH"
            )

        else:

            status = (
                "🔴 NO EDGE"
            )

        results.append({

            "date":
                game["date"],

            "type":
                game["type"],

            "away":
                away,

            "home":
                home,

            "favorite":
                favorite,

            "model_prob":
                favorite_prob,

            "fair_odds":
                fair_odds,

            "market_prob":
                market_prob,

            "edge":
                edge,

            "status":
                status,

            "ticker":
                ticker,

            "market_found":
                event is not None

        })

    return (
        pd.DataFrame(results),
        None
    )

# ============================================================
# BACKTEST — SOLO 2024-2025
# ============================================================

def backtest_model():

    schedule, error = load_schedule()

    if schedule is None:

        return None, error

    df = schedule.copy()

    df = df[
        (
            df["season"]
            .isin(
                HISTORICAL_SEASONS
            )
        )
        &
        (
            df["game_type"]
            .astype(str)
            .str.upper()
            == "REG"
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
    )

    ratings = {}

    recent = {}

    records = []

    for _, row in df.iterrows():

        away = norm_team(
            row["away_team"]
        )

        home = norm_team(
            row["home_team"]
        )

        if not away or not home:

            continue

        ratings.setdefault(
            away,
            BASE_ELO
        )

        ratings.setdefault(
            home,
            BASE_ELO
        )

        recent.setdefault(
            away,
            []
        )

        recent.setdefault(
            home,
            []
        )

        # ----------------------------------------------------
        # PREDICCIÓN ANTES DEL PARTIDO
        # ----------------------------------------------------

        home_prob = model_probability(
            away,
            home,
            ratings,
            recent
        )

        away_prob = (
            1
            -
            home_prob
        )

        home_score = float(
            row["home_score"]
        )

        away_score = float(
            row["away_score"]
        )

        if home_score > away_score:

            actual_home = 1
            actual_away = 0

        else:

            actual_home = 0
            actual_away = 1

        predicted_home = (
            1
            if home_prob >= 0.50
            else 0
        )

        correct = int(
            predicted_home
            ==
            actual_home
        )

        records.append({

            "date":
                row["gameday"],

            "season":
                int(
                    row["season"]
                ),

            "away":
                away,

            "home":
                home,

            "home_prob":
                home_prob,

            "away_prob":
                away_prob,

            "actual_home":
                actual_home,

            "correct":
                correct,

            "home_score":
                home_score,

            "away_score":
                away_score

        })

        # ----------------------------------------------------
        # ACTUALIZAR ELO
        # ----------------------------------------------------

        home_expected = expected_result(
            ratings[home]
            +
            HOME_ADVANTAGE,
            ratings[away]
        )

        away_expected = (
            1
            -
            home_expected
        )

        home_result = (
            1.0
            if actual_home
            else 0.0
        )

        away_result = (
            1.0
            if actual_away
            else 0.0
        )

        ratings[home] += (
            ELO_K
            *
            (
                home_result
                -
                home_expected
            )
        )

        ratings[away] += (
            ELO_K
            *
            (
                away_result
                -
                away_expected
            )
        )

        # ----------------------------------------------------
        # ACTUALIZAR FORMA
        # ----------------------------------------------------

        margin_home = (
            home_score
            -
            away_score
        )

        margin_away = (
            -margin_home
        )

        recent[home].append(
            margin_home
        )

        recent[away].append(
            margin_away
        )

        recent[home] = recent[
            home
        ][-8:]

        recent[away] = recent[
            away
        ][-8:]

    result = pd.DataFrame(
        records
    )

    return result, None

# ============================================================
# MÉTRICAS
# ============================================================

def calculate_metrics(
    df
):

    if df is None or len(df) == 0:

        return {}

    p = df[
        "home_prob"
    ].astype(float).values

    y = df[
        "actual_home"
    ].astype(int).values

    p_clip = np.clip(
        p,
        0.001,
        0.999
    )

    log_loss = -np.mean(
        y * np.log(p_clip)
        +
        (1 - y)
        *
        np.log(
            1 - p_clip
        )
    )

    brier = np.mean(
        (
            p - y
        ) ** 2
    )

    accuracy = np.mean(
        df["correct"]
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

    .signal {
        padding: 25px;
        border-radius: 20px;
        border: 2px solid #438c60;
        background: #173a28;
        margin: 20px 0;
    }

    .signal h2 {
        color: #8fe0a8;
    }

    .no-edge {
        padding: 25px;
        border-radius: 20px;
        background: #24252d;
        margin: 20px 0;
    }

    .metric-big {
        font-size: 42px;
        font-weight: 800;
    }

    </style>
    """,
    unsafe_allow_html=True
)

# ============================================================
# HEADER
# ============================================================

st.title(
    "🏈 NFL EDGE MONITOR"
)

st.subheader(
    "Modelo propio independiente del mercado"
)

st.caption(
    "Máximo histórico utilizado: temporadas 2024 y 2025"
)

tab1, tab2, tab3 = st.tabs(
    [
        "🏈 PARTIDOS",
        "🧪 BACKTEST 2 AÑOS",
        "ℹ️ MODELO"
    ]
)

# ============================================================
# TAB 1
# ============================================================

with tab1:

    st.header(
        "🏈 PRÓXIMOS PARTIDOS"
    )

    if st.button(
        "🔄 ACTUALIZAR",
        use_container_width=True
    ):

        st.cache_data.clear()

        st.rerun()

    with st.spinner(
        "Calculando modelo independiente..."
    ):

        games_df, error = (
            analyze_games()
        )

    if error:

        st.error(
            error
        )

    elif len(games_df) == 0:

        st.warning(
            "No hay partidos en los próximos 7 días."
        )

    else:

        # ----------------------------------------------------
        # RESUMEN DE SEÑALES
        # ----------------------------------------------------

        signals = games_df[
            games_df["edge"].notna()
            &
            (
                games_df["edge"]
                >= MIN_EDGE
            )
        ]

        st.metric(
            "🟢 Oportunidades encontradas",
            len(signals)
        )

        st.markdown("---")

        # ----------------------------------------------------
        # ORDENAR MEJORES EDGES
        # ----------------------------------------------------

        display_df = games_df.copy()

        display_df[
            "_edge"
        ] = display_df[
            "edge"
        ].fillna(-999)

        display_df = display_df.sort_values(
            "_edge",
            ascending=False
        )

        # ----------------------------------------------------
        # PARTIDOS
        # ----------------------------------------------------

        for _, game in display_df.iterrows():

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

            favorite = game[
                "favorite"
            ]

            favorite_name = TEAM_NAMES.get(
                favorite,
                favorite
            )

            model_prob = game[
                "model_prob"
            ]

            market_prob = game[
                "market_prob"
            ]

            edge = game[
                "edge"
            ]

            st.markdown(
                "---"
            )

            st.subheader(
                f"🏈 {away_name} @ {home_name}"
            )

            c1, c2, c3 = st.columns(3)

            with c1:

                st.write(
                    "🧠 Modelo"
                )

                st.markdown(
                    f"""
                    <div class="metric-big">
                    {model_prob * 100:.1f}%
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                st.write(
                    f"Favorito: **{favorite_name}**"
                )

            with c2:

                st.write(
                    "🎯 Cuota justa"
                )

                st.markdown(
                    f"""
                    <div class="metric-big">
                    {game['fair_odds']:+d}
                    </div>
                    """,
                    unsafe_allow_html=True
                )

            with c3:

                st.write(
                    "🏦 Mercado"
                )

                if market_prob is not None:

                    st.markdown(
                        f"""
                        <div class="metric-big">
                        {market_prob * 100:.1f}%
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

                else:

                    st.write(
                        "Sin precio"
                    )

            # ------------------------------------------------
            # EDGE
            # ------------------------------------------------

            if edge is not None:

                st.write(
                    f"**EDGE:** "
                    f"{edge * 100:+.2f}%"
                )

                if edge >= STRONG_EDGE:

                    st.markdown(
                        f"""
                        <div class="signal">

                        <h2>
                        🟢 STRONG EDGE
                        </h2>

                        <p>
                        El modelo estima
                        <strong>
                        {model_prob * 100:.1f}%
                        </strong>
                        y el mercado
                        <strong>
                        {market_prob * 100:.1f}%
                        </strong>.
                        </p>

                        <p>
                        Diferencia:
                        <strong>
                        +{edge * 100:.2f}%
                        </strong>
                        </p>

                        </div>
                        """,
                        unsafe_allow_html=True
                    )

                elif edge >= MIN_EDGE:

                    st.success(
                        f"🟢 OPPORTUNITY — "
                        f"Edge +{edge * 100:.2f}%"
                    )

                elif edge > 0:

                    st.warning(
                        f"🟡 WATCH — "
                        f"Edge +{edge * 100:.2f}%"
                    )

                else:

                    st.info(
                        "🔴 NO EDGE"
                    )

            else:

                st.info(
                    "🏦 No hay precio de mercado disponible."
                )

            st.caption(
                f"Tipo: {game['type']} | "
                f"Fecha: {game['date']}"
            )

# ============================================================
# TAB 2 — BACKTEST
# ============================================================

with tab2:

    st.header(
        "🧪 BACKTEST — SOLO 2 AÑOS"
    )

    st.info(
        """
        Este backtest utiliza únicamente las temporadas
        2024 y 2025.

        No utiliza cuotas de casas para crear las predicciones.

        El objetivo es comprobar si el modelo independiente
        realmente identifica correctamente al ganador.
        """
    )

    if st.button(
        "🧪 EJECUTAR BACKTEST 2024-2025",
        use_container_width=True
    ):

        with st.spinner(
            "Ejecutando 2 temporadas..."
        ):

            backtest, error = (
                backtest_model()
            )

        if error:

            st.error(
                error
            )

        else:

            st.session_state[
                "backtest"
            ] = backtest

    if (
        "backtest"
        in st.session_state
    ):

        backtest = st.session_state[
            "backtest"
        ]

        metrics = calculate_metrics(
            backtest
        )

        st.markdown(
            "---"
        )

        st.subheader(
            "📊 RESULTADOS"
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
            "Brier",
            f"{metrics['brier']:.4f}"
        )

        st.markdown(
            "---"
        )

        st.subheader(
            "📅 RESULTADOS POR TEMPORADA"
        )

        season_results = []

        for season in HISTORICAL_SEASONS:

            temp = backtest[
                backtest["season"]
                == season
            ]

            if len(temp) == 0:

                continue

            season_results.append({

                "Temporada":
                    season,

                "Partidos":
                    len(temp),

                "Accuracy":
                    f"{temp['correct'].mean() * 100:.2f}%"

            })

        st.dataframe(
            pd.DataFrame(
                season_results
            ),
            use_container_width=True,
            hide_index=True
        )

        st.markdown(
            "---"
        )

        st.subheader(
            "🎯 ¿CUÁNDO ES MÁS FUERTE?"
        )

        buckets = [

            (0.50, 0.55, "50-54%"),

            (0.55, 0.60, "55-59%"),

            (0.60, 0.65, "60-64%"),

            (0.65, 0.70, "65-69%"),

            (0.70, 0.75, "70-74%"),

            (0.75, 0.80, "75-79%"),

            (0.80, 0.86, "80%+")

        ]

        rows = []

        for low, high, label in buckets:

            temp = backtest[
                (
                    backtest[
                        "home_prob"
                    ]
                    >= low
                )
                &
                (
                    backtest[
                        "home_prob"
                    ]
                    < high
                )
            ]

            if len(temp) == 0:

                continue

            rows.append({

                "Rango":
                    label,

                "Partidos":
                    len(temp),

                "Prob. promedio":
                    f"{temp['home_prob'].mean() * 100:.1f}%",

                "Victoria real":
                    f"{temp['actual_home'].mean() * 100:.1f}%",

                "Accuracy":
                    f"{temp['correct'].mean() * 100:.1f}%"

            })

        st.dataframe(
            pd.DataFrame(rows),
            use_container_width=True,
            hide_index=True
        )

        st.markdown(
            "---"
        )

        st.subheader(
            "📋 ÚLTIMOS 20 PARTIDOS"
        )

        recent = backtest.tail(
            20
        ).copy()

        recent[
            "Partido"
        ] = (
            recent["away"]
            +
            " @ "
            +
            recent["home"]
        )

        recent[
            "Modelo"
        ] = (
            recent["home_prob"]
            * 100
        ).round(1).astype(str) + "%"

        recent[
            "Marcador"
        ] = (
            recent[
                "away_score"
            ].astype(int).astype(str)
            +
            "-"
            +
            recent[
                "home_score"
            ].astype(int).astype(str)
        )

        recent[
            "Resultado"
        ] = np.where(
            recent[
                "correct"
            ] == 1,
            "✅ CORRECTO",
            "❌ ERROR"
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

        st.caption(
            """
            IMPORTANTE: este backtest mide la capacidad
            predictiva del modelo. No es un ROI real de
            apuestas porque no estamos utilizando cuotas
            históricas de sportsbook.
            """
        )

# ============================================================
# TAB 3
# ============================================================

with tab3:

    st.header(
        "ℹ️ ¿CÓMO FUNCIONA?"
    )

    st.markdown(
        """
        ## 🧠 1. MODELO PROPIO

        La probabilidad se calcula utilizando:

        • ELO histórico

        • Ventaja de local

        • Diferencial de puntos

        • Forma reciente

        • Últimos partidos de cada equipo

        **Las cuotas del mercado NO entran en este cálculo.**

        ---

        ## 🏦 2. DESPUÉS MIRAMOS EL MERCADO

        Una vez que nuestro modelo calcula la probabilidad,
        buscamos el precio disponible.

        Ejemplo:

        **Modelo:** 64%

        **Mercado:** 55%

        **EDGE:** +9%

        El sistema detecta que nuestra estimación es
        considerablemente superior a la del mercado.

        ---

        ## 🎯 3. NO BUSCAMOS 100%

        Una probabilidad de 64% NO significa que el equipo
        vaya a ganar.

        Significa que, según nuestro modelo, ese resultado
        debería ocurrir aproximadamente 64 de cada 100 veces
        en situaciones similares.

        ---

        ## 🟢 FILTROS

        **OPPORTUNITY**

        Edge ≥ 6%

        **STRONG EDGE**

        Edge ≥ 10%

        **WATCH**

        Edge positivo pero menor de 6%

        **NO EDGE**

        El mercado no está por debajo de nuestra estimación.

        ---

        ## 📚 HISTÓRICO

        El sistema utiliza únicamente:

        **2024 + 2025**

        No utilizamos 2019, 2020, 2021, 2022 ni 2023.

        Tampoco necesitamos archivos históricos V6.

        ---

        ## ⚠️ IMPORTANTE

        Esto no garantiza ganancias.

        La finalidad es encontrar situaciones donde exista
        una diferencia estadística entre nuestro modelo y el
        mercado.

        El sistema NO realiza apuestas automáticamente.
        """
    )

# ============================================================
# FOOTER
# ============================================================

st.markdown(
    "---"
)

st.caption(
    "NFL Edge Monitor — modelo estadístico independiente. "
    "Máximo histórico: 2024-2025. "
    "No realiza apuestas automáticamente."
)
