import streamlit as st
import pandas as pd
import numpy as np
import requests
import math
from datetime import datetime
from zoneinfo import ZoneInfo


# ============================================================
# CONFIGURACIÓN
# ============================================================

st.set_page_config(
    page_title="Monitor NFL - Modelo Propio",
    page_icon="🏈",
    layout="centered"
)

st.markdown("""
<style>

.block-container {
    max-width: 950px;
    padding-top: 2rem;
}

.title {
    font-size: 42px;
    font-weight: 800;
}

.subtitle {
    font-size: 20px;
    color: #9ca3af;
    margin-bottom: 25px;
}

.game-card {
    background: #17191f;
    border: 1px solid #30343d;
    border-radius: 18px;
    padding: 22px;
    margin-bottom: 22px;
}

.prob {
    font-size: 35px;
    font-weight: 800;
}

.high {
    background: #163c29;
    border-radius: 14px;
    padding: 15px;
    color: #69e69a;
    font-size: 21px;
    font-weight: 800;
    margin: 15px 0;
}

.medium {
    background: #40351b;
    border-radius: 14px;
    padding: 15px;
    color: #ffd45c;
    font-size: 21px;
    font-weight: 800;
    margin: 15px 0;
}

.low {
    background: #3c2b19;
    border-radius: 14px;
    padding: 15px;
    color: #ffb45c;
    font-size: 21px;
    font-weight: 800;
    margin: 15px 0;
}

.metric {
    background: #20242c;
    border-radius: 12px;
    padding: 12px;
    margin: 5px 0;
}

.small {
    color: #9ca3af;
    font-size: 14px;
}

</style>
""", unsafe_allow_html=True)


# ============================================================
# CONSTANTES
# ============================================================

NFLVERSE_GAMES = (
    "https://raw.githubusercontent.com/leesharpe/nfldata/"
    "master/data/games.csv"
)

ESPN_SCOREBOARD = (
    "https://site.api.espn.com/apis/site/v2/sports/"
    "football/nfl/scoreboard"
)


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
    "LV": "Las Vegas Raiders",
    "LAC": "Los Angeles Chargers",
    "LAR": "Los Angeles Rams",
    "MIA": "Miami Dolphins",
    "MIN": "Minnesota Vikings",
    "NE": "New England Patriots",
    "NO": "New Orleans Saints",
    "NYG": "New York Giants",
    "NYJ": "New York Jets",
    "PHI": "Philadelphia Eagles",
    "PIT": "Pittsburgh Steelers",
    "SF": "San Francisco 49ers",
    "SEA": "Seattle Seahawks",
    "TB": "Tampa Bay Buccaneers",
    "TEN": "Tennessee Titans",
    "WAS": "Washington Commanders",
}


# ============================================================
# NORMALIZACIÓN
# ============================================================

def normalize_team(team):

    if pd.isna(team):
        return None

    team = str(team).strip()

    replacements = {
        "JAC": "JAX",
        "LA": "LAR",
        "Los Angeles Rams": "LAR",
        "Los Angeles Chargers": "LAC",
        "San Francisco 49ers": "SF",
        "Tennessee Titans": "TEN",
        "Detroit Lions": "DET",
        "Cincinnati Bengals": "CIN",
        "New England Patriots": "NE",
        "Indianapolis Colts": "IND",
        "Houston Texans": "HOU",
        "Kansas City Chiefs": "KC",
        "Dallas Cowboys": "DAL",
        "Philadelphia Eagles": "PHI",
        "Buffalo Bills": "BUF",
        "Baltimore Ravens": "BAL",
        "Green Bay Packers": "GB",
        "Pittsburgh Steelers": "PIT",
        "Miami Dolphins": "MIA",
        "New York Giants": "NYG",
        "New York Jets": "NYJ",
        "Seattle Seahawks": "SEA",
        "Tampa Bay Buccaneers": "TB",
        "Minnesota Vikings": "MIN",
        "Chicago Bears": "CHI",
        "Cleveland Browns": "CLE",
        "Denver Broncos": "DEN",
        "Las Vegas Raiders": "LV",
        "Arizona Cardinals": "ARI",
        "Atlanta Falcons": "ATL",
        "Carolina Panthers": "CAR",
        "Jacksonville Jaguars": "JAX",
        "New Orleans Saints": "NO",
        "Washington Commanders": "WAS",
    }

    return replacements.get(team, team)


def team_display(team):

    return TEAM_NAMES.get(
        normalize_team(team),
        team
    )


# ============================================================
# CARGAR PARTIDOS NFL
# ============================================================

@st.cache_data(ttl=3600)
def load_nfl_games():

    df = pd.read_csv(NFLVERSE_GAMES)

    df.columns = [
        str(c).lower().strip()
        for c in df.columns
    ]

    # --------------------------------------------------------
    # Detectar columnas
    # --------------------------------------------------------

    home_col = None
    away_col = None
    score_home_col = None
    score_away_col = None

    possible_home = [
        "team_home",
        "home_team",
        "home"
    ]

    possible_away = [
        "team_away",
        "away_team",
        "away"
    ]

    possible_score_home = [
        "score_home",
        "home_score",
        "points_home"
    ]

    possible_score_away = [
        "score_away",
        "away_score",
        "points_away"
    ]

    for c in possible_home:

        if c in df.columns:
            home_col = c
            break

    for c in possible_away:

        if c in df.columns:
            away_col = c
            break

    for c in possible_score_home:

        if c in df.columns:
            score_home_col = c
            break

    for c in possible_score_away:

        if c in df.columns:
            score_away_col = c
            break

    if not all([
        home_col,
        away_col,
        score_home_col,
        score_away_col
    ]):

        raise ValueError(
            "No se encontraron las columnas necesarias."
        )

    # --------------------------------------------------------
    # Fecha
    # --------------------------------------------------------

    date_col = None

    for c in [
        "gameday",
        "game_date",
        "date",
        "schedule_date"
    ]:

        if c in df.columns:
            date_col = c
            break

    if date_col is None:

        raise ValueError(
            "No se encontró columna de fecha."
        )

    df["game_date"] = pd.to_datetime(
        df[date_col],
        errors="coerce"
    )

    # --------------------------------------------------------
    # Temporada 2025
    # --------------------------------------------------------

    if "season" in df.columns:

        df = df[
            df["season"] == 2025
        ].copy()

    # --------------------------------------------------------
    # Solo regular season
    # --------------------------------------------------------

    if "game_type" in df.columns:

        df = df[
            df["game_type"]
            .astype(str)
            .str.lower()
            .isin(["reg", "regular"])
        ].copy()

    # --------------------------------------------------------
    # Construcción
    # --------------------------------------------------------

    df["home"] = df[home_col].apply(
        normalize_team
    )

    df["away"] = df[away_col].apply(
        normalize_team
    )

    df["home_score"] = pd.to_numeric(
        df[score_home_col],
        errors="coerce"
    )

    df["away_score"] = pd.to_numeric(
        df[score_away_col],
        errors="coerce"
    )

    df = df.dropna(
        subset=[
            "game_date",
            "home",
            "away",
            "home_score",
            "away_score"
        ]
    ).copy()

    df = df.sort_values(
        "game_date"
    ).reset_index(drop=True)

    return df


# ============================================================
# ESTADÍSTICAS PREVIAS
# ============================================================

def build_team_stats(games):

    teams = {}

    for _, row in games.iterrows():

        home = row["home"]
        away = row["away"]

        hs = float(row["home_score"])
        aws = float(row["away_score"])

        if home not in teams:

            teams[home] = {
                "games": 0,
                "wins": 0,
                "losses": 0,
                "points_for": 0,
                "points_against": 0,
                "home_games": 0,
                "home_wins": 0,
                "away_games": 0,
                "away_wins": 0,
            }

        if away not in teams:

            teams[away] = {
                "games": 0,
                "wins": 0,
                "losses": 0,
                "points_for": 0,
                "points_against": 0,
                "home_games": 0,
                "home_wins": 0,
                "away_games": 0,
                "away_wins": 0,
            }

        # HOME

        teams[home]["games"] += 1
        teams[home]["home_games"] += 1
        teams[home]["points_for"] += hs
        teams[home]["points_against"] += aws

        if hs > aws:

            teams[home]["wins"] += 1
            teams[home]["home_wins"] += 1

        else:

            teams[home]["losses"] += 1

        # AWAY

        teams[away]["games"] += 1
        teams[away]["away_games"] += 1
        teams[away]["points_for"] += aws
        teams[away]["points_against"] += hs

        if aws > hs:

            teams[away]["wins"] += 1
            teams[away]["away_wins"] += 1

        else:

            teams[away]["losses"] += 1

    stats = {}

    for team, x in teams.items():

        n = max(
            x["games"],
            1
        )

        stats[team] = {

            **x,

            "win_pct":
                x["wins"] / n,

            "ppg":
                x["points_for"] / n,

            "papg":
                x["points_against"] / n,

            "point_diff":
                (
                    x["points_for"]
                    - x["points_against"]
                ) / n,

            "home_win_pct":
                (
                    x["home_wins"]
                    / x["home_games"]
                    if x["home_games"] > 0
                    else 0.5
                ),

            "away_win_pct":
                (
                    x["away_wins"]
                    / x["away_games"]
                    if x["away_games"] > 0
                    else 0.5
                ),
        }

    return stats


# ============================================================
# Z-SCORE
# ============================================================

def zscore(value, mean, std):

    if std == 0 or pd.isna(std):

        return 0

    return (
        value - mean
    ) / std


# ============================================================
# FUERZA
# ============================================================

def calculate_team_strength(
    team,
    stats
):

    if team not in stats:

        return None

    s = stats[team]

    all_stats = list(
        stats.values()
    )

    win_values = [
        x["win_pct"]
        for x in all_stats
    ]

    diff_values = [
        x["point_diff"]
        for x in all_stats
    ]

    ppg_values = [
        x["ppg"]
        for x in all_stats
    ]

    papg_values = [
        x["papg"]
        for x in all_stats
    ]

    strength = (

        0.35 *
        zscore(
            s["win_pct"],
            np.mean(win_values),
            np.std(win_values)
        )

        +

        0.35 *
        zscore(
            s["point_diff"],
            np.mean(diff_values),
            np.std(diff_values)
        )

        +

        0.15 *
        zscore(
            s["ppg"],
            np.mean(ppg_values),
            np.std(ppg_values)
        )

        -

        0.15 *
        zscore(
            s["papg"],
            np.mean(papg_values),
            np.std(papg_values)
        )
    )

    return strength


# ============================================================
# PROBABILIDAD
# ============================================================

def calculate_probability(
    home,
    away,
    stats
):

    home = normalize_team(home)
    away = normalize_team(away)

    home_strength = (
        calculate_team_strength(
            home,
            stats
        )
    )

    away_strength = (
        calculate_team_strength(
            away,
            stats
        )
    )

    if (
        home_strength is None
        or
        away_strength is None
    ):

        return None

    home_advantage = 0.18

    difference = (
        home_strength
        - away_strength
        + home_advantage
    )

    probability_home = (

        1 /

        (
            1 +
            math.exp(
                -1.35 *
                difference
            )
        )
    )

    probability_home = max(
        0.05,
        min(
            0.95,
            probability_home
        )
    )

    probability_away = (
        1 - probability_home
    )

    return {

        "home_probability":
            probability_home,

        "away_probability":
            probability_away,

        "home_strength":
            home_strength,

        "away_strength":
            away_strength
    }


# ============================================================
# WALK-FORWARD BACKTEST
# ============================================================

def run_walk_forward_backtest(
    games,
    minimum_probability=0.70
):

    results = []

    # Necesitamos suficientes partidos
    # antes de comenzar a confiar en las estadísticas.

    for i in range(
        1,
        len(games)
    ):

        current_game = games.iloc[i]

        previous_games = games.iloc[:i]

        # -----------------------------------------------
        # Solo datos anteriores al partido
        # -----------------------------------------------

        stats = build_team_stats(
            previous_games
        )

        home = current_game["home"]
        away = current_game["away"]

        prediction = calculate_probability(
            home,
            away,
            stats
        )

        if prediction is None:
            continue

        hp = prediction[
            "home_probability"
        ]

        ap = prediction[
            "away_probability"
        ]

        if hp >= ap:

            pick = home
            probability = hp

        else:

            pick = away
            probability = ap

        # Resultado real

        if (
            current_game["home_score"]
            >
            current_game["away_score"]
        ):

            winner = home

        elif (
            current_game["away_score"]
            >
            current_game["home_score"]
        ):

            winner = away

        else:

            winner = "TIE"

        correct = (
            pick == winner
        )

        results.append({

            "date":
                current_game[
                    "game_date"
                ],

            "home":
                home,

            "away":
                away,

            "home_score":
                current_game[
                    "home_score"
                ],

            "away_score":
                current_game[
                    "away_score"
                ],

            "pick":
                pick,

            "probability":
                probability,

            "correct":
                correct,

            "winner":
                winner
        })

    results = pd.DataFrame(
        results
    )

    return results


# ============================================================
# AMERICAN ODDS
# ============================================================

def american_to_decimal(odds):

    odds = float(odds)

    if odds > 0:

        return (
            1 +
            odds / 100
        )

    else:

        return (
            1 +
            100 / abs(odds)
        )


def profit_from_odds(
    stake,
    american_odds
):

    decimal_odds = (
        american_to_decimal(
            american_odds
        )
    )

    return (
        stake *
        (
            decimal_odds - 1
        )
    )


# ============================================================
# DETECTAR COLUMNAS DE ODDS
# ============================================================

def find_column(
    df,
    possibilities
):

    lower_map = {
        str(c).lower().strip(): c
        for c in df.columns
    }

    for p in possibilities:

        if p.lower() in lower_map:

            return lower_map[
                p.lower()
            ]

    return None


# ============================================================
# PREPARAR ODDS
# ============================================================

def prepare_odds(
    odds_df
):

    df = odds_df.copy()

    df.columns = [
        str(c).lower().strip()
        for c in df.columns
    ]

    # -----------------------------------------------
    # Buscar equipos
    # -----------------------------------------------

    home_col = find_column(
        df,
        [
            "home",
            "home_team",
            "team_home",
            "home_name"
        ]
    )

    away_col = find_column(
        df,
        [
            "away",
            "away_team",
            "team_away",
            "away_name"
        ]
    )

    # -----------------------------------------------
    # Fecha
    # -----------------------------------------------

    date_col = find_column(
        df,
        [
            "date",
            "game_date",
            "gameday",
            "schedule_date"
        ]
    )

    # -----------------------------------------------
    # Moneyline
    # -----------------------------------------------

    home_ml_col = find_column(
        df,
        [
            "home_moneyline",
            "home_ml",
            "moneyline_home",
            "home_odds",
            "ml_home"
        ]
    )

    away_ml_col = find_column(
        df,
        [
            "away_moneyline",
            "away_ml",
            "moneyline_away",
            "away_odds",
            "ml_away"
        ]
    )

    if not home_col or not away_col:

        raise ValueError(
            "No pude encontrar las columnas "
            "home y away en el archivo de cuotas."
        )

    if not home_ml_col or not away_ml_col:

        raise ValueError(
            "No pude encontrar las columnas "
            "de moneyline."
        )

    if not date_col:

        raise ValueError(
            "No pude encontrar la columna de fecha."
        )

    df["home"] = df[
        home_col
    ].apply(
        normalize_team
    )

    df["away"] = df[
        away_col
    ].apply(
        normalize_team
    )

    df["date"] = pd.to_datetime(
        df[date_col],
        errors="coerce"
    )

    df["home_ml"] = pd.to_numeric(
        df[home_ml_col],
        errors="coerce"
    )

    df["away_ml"] = pd.to_numeric(
        df[away_ml_col],
        errors="coerce"
    )

    df = df.dropna(
        subset=[
            "date",
            "home",
            "away",
            "home_ml",
            "away_ml"
        ]
    )

    return df


# ============================================================
# CRUZAR MODELO + ODDS
# ============================================================

def merge_model_odds(
    model_results,
    odds
):

    model = model_results.copy()

    odds = odds.copy()

    model["date_key"] = (
        pd.to_datetime(
            model["date"]
        ).dt.date
    )

    odds["date_key"] = (
        pd.to_datetime(
            odds["date"]
        ).dt.date
    )

    merged = model.merge(
        odds[
            [
                "date_key",
                "home",
                "away",
                "home_ml",
                "away_ml"
            ]
        ],
        on=[
            "date_key",
            "home",
            "away"
        ],
        how="left"
    )

    return merged


# ============================================================
# CALCULAR ROI
# ============================================================

def calculate_betting_results(
    df,
    minimum_probability=0.70,
    stake=10
):

    bets = df[
        df["probability"]
        >= minimum_probability
    ].copy()

    if bets.empty:

        return bets

    bets["american_odds"] = np.where(

        bets["pick"] == bets["home"],

        bets["home_ml"],

        bets["away_ml"]
    )

    bets["has_odds"] = (
        bets["american_odds"]
        .notna()
    )

    bets = bets[
        bets["has_odds"]
    ].copy()

    if bets.empty:

        return bets

    bets["stake"] = stake

    bets["profit"] = np.where(

        bets["correct"],

        bets["american_odds"].apply(
            lambda x:
            profit_from_odds(
                stake,
                x
            )
        ),

        -stake
    )

    bets["return"] = (
        bets["stake"]
        +
        bets["profit"]
    )

    return bets


# ============================================================
# ACTUAL NFL DE HOY
# ============================================================

@st.cache_data(ttl=300)
def get_today_games():

    dallas = ZoneInfo(
        "America/Chicago"
    )

    today = datetime.now(
        dallas
    ).strftime(
        "%Y%m%d"
    )

    response = requests.get(
        ESPN_SCOREBOARD,
        params={
            "dates": today,
            "limit": 100
        },
        timeout=15
    )

    response.raise_for_status()

    data = response.json()

    games = []

    for event in data.get(
        "events",
        []
    ):

        competitions = event.get(
            "competitions",
            []
        )

        if not competitions:
            continue

        competition = (
            competitions[0]
        )

        competitors = (
            competition.get(
                "competitors",
                []
            )
        )

        home = None
        away = None

        for c in competitors:

            abbr = (
                c.get(
                    "team",
                    {}
                )
                .get(
                    "abbreviation"
                )
            )

            if c.get(
                "homeAway"
            ) == "home":

                home = abbr

            elif c.get(
                "homeAway"
            ) == "away":

                away = abbr

        if not home or not away:
            continue

        games.append({

            "id":
                event.get("id"),

            "home":
                normalize_team(home),

            "away":
                normalize_team(away),

            "date":
                event.get("date", ""),

            "name":
                event.get("name", "")
        })

    return games


# ============================================================
# ENCABEZADO
# ============================================================

st.markdown(
    '<div class="title">'
    '🏈 Monitor NFL'
    '</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtitle">'
    'Modelo propio — Backtest + ROI'
    '</div>',
    unsafe_allow_html=True
)

st.info(
    "El backtest utiliza únicamente información "
    "disponible ANTES de cada partido."
)


# ============================================================
# CARGAR NFL
# ============================================================

try:

    nfl_games = load_nfl_games()

except Exception as e:

    st.error(
        "No se pudieron cargar los partidos NFL."
    )

    st.code(str(e))

    st.stop()


# ============================================================
# TABS
# ============================================================

tab1, tab2, tab3 = st.tabs(
    [
        "🏈 NFL DE HOY",
        "📈 BACKTEST ROI",
        "📊 DATOS"
    ]
)


# ============================================================
# TAB 1 — HOY
# ============================================================

with tab1:

    st.subheader(
        "🔎 NFL DE HOY"
    )

    if st.button(
        "🔄 ACTUALIZAR",
        use_container_width=True
    ):

        st.cache_data.clear()

        st.rerun()

    try:

        today_games = (
            get_today_games()
        )

    except Exception as e:

        st.error(
            "No se pudo obtener "
            "el calendario."
        )

        today_games = []

    if not today_games:

        st.warning(
            "No se encontraron "
            "partidos NFL hoy."
        )

    else:

        st.success(
            f"{len(today_games)} "
            "partido(s) encontrados."
        )

        # Usamos todos los datos 2025
        # únicamente para mostrar el modelo actual.
        stats = build_team_stats(
            nfl_games
        )

        predictions = []

        for game in today_games:

            prediction = (
                calculate_probability(
                    game["home"],
                    game["away"],
                    stats
                )
            )

            if prediction is None:
                continue

            hp = prediction[
                "home_probability"
            ]

            ap = prediction[
                "away_probability"
            ]

            if hp >= ap:

                favorite = game["home"]
                probability = hp

            else:

                favorite = game["away"]
                probability = ap

            predictions.append({

                "game": game,

                "prediction":
                    prediction,

                "favorite":
                    favorite,

                "probability":
                    probability
            })

        predictions.sort(
            key=lambda x:
            x["probability"],
            reverse=True
        )

        for i, item in enumerate(
            predictions,
            start=1
        ):

            game = item["game"]

            prediction = (
                item["prediction"]
            )

            hp = prediction[
                "home_probability"
            ]

            ap = prediction[
                "away_probability"
            ]

            st.markdown(
                '<div class="game-card">',
                unsafe_allow_html=True
            )

            st.markdown(
                f"### #{i} 🏈 "
                f"{team_display(item['favorite'])}"
            )

            st.write(
                f"**{team_display(game['away'])}** "
                f"vs "
                f"**{team_display(game['home'])}**"
            )

            label = (
                "🟢 PROBABILIDAD ALTA"
                if item["probability"] >= 0.65
                else
                "🟡 PROBABILIDAD MEDIA"
                if item["probability"] >= 0.55
                else
                "⚪ PROBABILIDAD BAJA"
            )

            st.success(
                label
            )

            c1, c2 = st.columns(2)

            with c1:

                st.markdown(
                    f"### "
                    f"{team_display(game['home'])}"
                )

                st.markdown(
                    f'<div class="prob">'
                    f'{hp*100:.1f}%'
                    f'</div>',
                    unsafe_allow_html=True
                )

            with c2:

                st.markdown(
                    f"### "
                    f"{team_display(game['away'])}"
                )

                st.markdown(
                    f'<div class="prob">'
                    f'{ap*100:.1f}%'
                    f'</div>',
                    unsafe_allow_html=True
                )

            st.markdown(
                "</div>",
                unsafe_allow_html=True
            )


# ============================================================
# TAB 2 — BACKTEST
# ============================================================

with tab2:

    st.header(
        "📈 Backtest realista"
    )

    st.write(
        "Aquí probamos el modelo partido por partido "
        "sin utilizar información futura."
    )

    st.warning(
        "Necesitamos las cuotas históricas para calcular "
        "el dinero ganado o perdido."
    )

    # --------------------------------------------------------
    # Parámetros
    # --------------------------------------------------------

    col1, col2 = st.columns(2)

    with col1:

        threshold = st.number_input(
            "Probabilidad mínima",
            min_value=0.50,
            max_value=0.95,
            value=0.70,
            step=0.01
        )

    with col2:

        stake = st.number_input(
            "Apuesta por partido ($)",
            min_value=1.0,
            max_value=10000.0,
            value=10.0,
            step=1.0
        )

    st.divider()

    if st.button(
        "🚀 EJECUTAR BACKTEST",
        use_container_width=True
    ):

        with st.spinner(
            "Calculando partido por partido..."
        ):

            model_results = (
                run_walk_forward_backtest(
                    nfl_games,
                    threshold
                )
            )

        st.session_state[
            "model_results"
        ] = model_results

    # --------------------------------------------------------
    # Resultados del modelo
    # --------------------------------------------------------

    if (
        "model_results"
        in st.session_state
    ):

        model_results = (
            st.session_state[
                "model_results"
            ]
        )

        if model_results.empty:

            st.error(
                "No se generaron predicciones."
            )

        else:

            total = len(
                model_results
            )

            correct = int(
                model_results[
                    "correct"
                ].sum()
            )

            accuracy = (
                correct / total
                if total > 0
                else 0
            )

            c1, c2, c3 = st.columns(3)

            with c1:

                st.metric(
                    "Partidos",
                    total
                )

            with c2:

                st.metric(
                    "Aciertos",
                    correct
                )

            with c3:

                st.metric(
                    "Acierto",
                    f"{accuracy*100:.1f}%"
                )

            st.subheader(
                "💰 Cargar cuotas históricas"
            )

            odds_file = st.file_uploader(
                "Sube el CSV de moneyline 2025",
                type=[
                    "csv"
                ]
            )

            st.caption(
                "El archivo debe contener fecha, "
                "equipo local, equipo visitante, "
                "moneyline local y moneyline visitante."
            )

            if odds_file is not None:

                try:

                    raw_odds = pd.read_csv(
                        odds_file
                    )

                    odds = prepare_odds(
                        raw_odds
                    )

                    st.success(
                        f"{len(odds)} "
                        "registros de cuotas cargados."
                    )

                    merged = (
                        merge_model_odds(
                            model_results,
                            odds
                        )
                    )

                    betting_results = (
                        calculate_betting_results(
                            merged,
                            threshold,
                            stake
                        )
                    )

                    if betting_results.empty:

                        st.warning(
                            "No encontramos cuotas "
                            "que coincidan con los partidos "
                            "del modelo."
                        )

                    else:

                        total_bets = len(
                            betting_results
                        )

                        wins = int(
                            betting_results[
                                "correct"
                            ].sum()
                        )

                        losses = (
                            total_bets
                            - wins
                        )

                        total_staked = (
                            betting_results[
                                "stake"
                            ].sum()
                        )

                        net_profit = (
                            betting_results[
                                "profit"
                            ].sum()
                        )

                        total_return = (
                            betting_results[
                                "return"
                            ].sum()
                        )

                        roi = (
                            net_profit
                            / total_staked
                            if total_staked > 0
                            else 0
                        )

                        st.divider()

                        st.subheader(
                            "🔥 RESULTADO REAL"
                        )

                        c1, c2 = st.columns(2)

                        with c1:

                            st.metric(
                                "Apuestas",
                                total_bets
                            )

                            st.metric(
                                "Ganadas",
                                wins
                            )

                            st.metric(
                                "Perdidas",
                                losses
                            )

                        with c2:

                            st.metric(
                                "Total apostado",
                                f"${total_staked:,.2f}"
                            )

                            st.metric(
                                "Ganancia / pérdida",
                                f"${net_profit:,.2f}"
                            )

                            st.metric(
                                "ROI",
                                f"{roi*100:.2f}%"
                            )

                        st.success(
                            f"Bankroll final: "
                            f"${total_return:,.2f}"
                        )

                        # --------------------------------
                        # Tabla
                        # --------------------------------

                        st.subheader(
                            "📋 Apuestas"
                        )

                        display = (
                            betting_results[
                                [
                                    "date",
                                    "away",
                                    "home",
                                    "pick",
                                    "probability",
                                    "american_odds",
                                    "correct",
                                    "profit"
                                ]
                            ].copy()
                        )

                        display["probability"] = (
                            display[
                                "probability"
                            ] * 100
                        ).round(1)

                        display["profit"] = (
                            display[
                                "profit"
                            ].round(2)
                        )

                        display["result"] = np.where(
                            display[
                                "correct"
                            ],
                            "✅ WIN",
                            "❌ LOSS"
                        )

                        display = display[
                            [
                                "date",
                                "away",
                                "home",
                                "pick",
                                "probability",
                                "american_odds",
                                "result",
                                "profit"
                            ]
                        ]

                        st.dataframe(
                            display,
                            use_container_width=True
                        )

                        # --------------------------------
                        # Descargar
                        # --------------------------------

                        csv = (
                            betting_results
                            .to_csv(
                                index=False
                            )
                        )

                        st.download_button(
                            "⬇️ DESCARGAR RESULTADOS CSV",
                            csv,
                            "backtest_nfl_2025.csv",
                            "text/csv",
                            use_container_width=True
                        )

                except Exception as e:

                    st.error(
                        "No pude procesar el "
                        "archivo de cuotas."
                    )

                    st.code(
                        str(e)
                    )


# ============================================================
# TAB 3 — DATOS
# ============================================================

with tab3:

    st.header(
        "📊 Datos del modelo"
    )

    st.write(
        f"Partidos NFL 2025: "
        f"{len(nfl_games)}"
    )

    st.write(
        f"Fecha inicial: "
        f"{nfl_games['game_date'].min().date()}"
    )

    st.write(
        f"Fecha final: "
        f"{nfl_games['game_date'].max().date()}"
    )

    st.info(
        "El modelo histórico utiliza estadísticas "
        "acumuladas únicamente hasta antes de cada "
        "partido durante el backtest."
    )

    st.dataframe(
        nfl_games[
            [
                "game_date",
                "away",
                "home",
                "away_score",
                "home_score"
            ]
        ],
        use_container_width=True
    )
