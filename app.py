import streamlit as st
import pandas as pd
import numpy as np
import requests
import math
from datetime import datetime
from zoneinfo import ZoneInfo


# ============================================================
# CONFIGURACION
# ============================================================

st.set_page_config(
    page_title="Monitor NFL - Modelo Propio",
    page_icon="🏈",
    layout="centered"
)


# ============================================================
# ESTILOS
# ============================================================

st.markdown(
    """
    <style>

    .block-container {
        max-width: 900px;
        padding-top: 2rem;
    }

    .title {
        font-size: 42px;
        font-weight: 800;
        margin-bottom: 0;
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

    </style>
    """,
    unsafe_allow_html=True
)


# ============================================================
# FUENTES DE DATOS
# ============================================================

NFLVERSE_GAMES = (
    "https://raw.githubusercontent.com/nflverse/nfldata/"
    "master/data/games.csv"
)

ESPN_SCOREBOARD = (
    "https://site.api.espn.com/apis/site/v2/sports/"
    "football/nfl/scoreboard"
)


# ============================================================
# NOMBRES DE EQUIPOS
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
# NORMALIZAR EQUIPOS
# ============================================================

def normalize_team(team):

    if team is None:
        return team

    team = str(team).upper().strip()

    replacements = {
        "JAC": "JAX",
        "LA": "LAR",
        "WSH": "WAS",
    }

    return replacements.get(
        team,
        team
    )


def team_display(team):

    team = normalize_team(team)

    return TEAM_NAMES.get(
        team,
        team
    )


# ============================================================
# CARGAR DATOS HISTORICOS
# ============================================================

@st.cache_data(ttl=3600)
def load_games():

    df = pd.read_csv(
        NFLVERSE_GAMES
    )

    df.columns = [
        str(c).lower().strip()
        for c in df.columns
    ]

    rename_map = {}

    if "gameday" in df.columns:
        rename_map["gameday"] = "date"

    if "away_team" in df.columns:
        rename_map["away_team"] = "away"

    if "home_team" in df.columns:
        rename_map["home_team"] = "home"

    df = df.rename(
        columns=rename_map
    )

    required = [
        "season",
        "game_type",
        "date",
        "away",
        "home",
        "away_score",
        "home_score",
    ]

    missing = [
        c for c in required
        if c not in df.columns
    ]

    if missing:

        raise ValueError(
            "Faltan columnas necesarias: "
            + ", ".join(missing)
        )

    df["date"] = pd.to_datetime(
        df["date"],
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

    df["away"] = (
        df["away"]
        .astype(str)
        .map(normalize_team)
    )

    df["home"] = (
        df["home"]
        .astype(str)
        .map(normalize_team)
    )

    return df


# ============================================================
# DATOS 2025
# ============================================================

@st.cache_data(ttl=3600)
def load_2025_games():

    df = load_games()

    df = df[
        df["season"] == 2025
    ].copy()

    df = df[
        df["game_type"]
        .astype(str)
        .str.upper()
        == "REG"
    ].copy()

    df = df.dropna(
        subset=[
            "date",
            "away",
            "home",
            "away_score",
            "home_score",
        ]
    )

    return df.sort_values(
        "date"
    ).reset_index(
        drop=True
    )


# ============================================================
# ESTADISTICAS DE EQUIPOS
# ============================================================

def build_team_stats(games):

    teams = {}

    for _, row in games.iterrows():

        home = normalize_team(
            row["home"]
        )

        away = normalize_team(
            row["away"]
        )

        hs = float(
            row["home_score"]
        )

        aws = float(
            row["away_score"]
        )

        if home not in teams:

            teams[home] = {
                "games": 0,
                "wins": 0,
                "losses": 0,
                "ties": 0,
                "points_for": 0.0,
                "points_against": 0.0,
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
                "ties": 0,
                "points_for": 0.0,
                "points_against": 0.0,
                "home_games": 0,
                "home_wins": 0,
                "away_games": 0,
                "away_wins": 0,
            }

        # ----------------------------
        # LOCAL
        # ----------------------------

        teams[home]["games"] += 1
        teams[home]["home_games"] += 1

        teams[home]["points_for"] += hs
        teams[home]["points_against"] += aws

        if hs > aws:

            teams[home]["wins"] += 1
            teams[home]["home_wins"] += 1

        elif hs < aws:

            teams[home]["losses"] += 1

        else:

            teams[home]["ties"] += 1

        # ----------------------------
        # VISITANTE
        # ----------------------------

        teams[away]["games"] += 1
        teams[away]["away_games"] += 1

        teams[away]["points_for"] += aws
        teams[away]["points_against"] += hs

        if aws > hs:

            teams[away]["wins"] += 1
            teams[away]["away_wins"] += 1

        elif aws < hs:

            teams[away]["losses"] += 1

        else:

            teams[away]["ties"] += 1

    stats = {}

    for team, x in teams.items():

        games_n = max(
            x["games"],
            1
        )

        win_pct = (
            x["wins"]
            /
            games_n
        )

        ppg = (
            x["points_for"]
            /
            games_n
        )

        papg = (
            x["points_against"]
            /
            games_n
        )

        point_diff = (
            ppg
            -
            papg
        )

        home_win_pct = (

            x["home_wins"]
            /
            x["home_games"]

            if x["home_games"] > 0

            else 0.5
        )

        away_win_pct = (

            x["away_wins"]
            /
            x["away_games"]

            if x["away_games"] > 0

            else 0.5
        )

        stats[team] = {

            **x,

            "win_pct":
                win_pct,

            "ppg":
                ppg,

            "papg":
                papg,

            "point_diff":
                point_diff,

            "home_win_pct":
                home_win_pct,

            "away_win_pct":
                away_win_pct,

        }

    return stats


# ============================================================
# Z SCORE
# ============================================================

def zscore(
    value,
    mean,
    std
):

    if std == 0 or pd.isna(std):

        return 0.0

    return (
        value - mean
    ) / std


# ============================================================
# FUERZA DEL EQUIPO
# ============================================================

def calculate_team_strength(
    team,
    stats
):

    team = normalize_team(
        team
    )

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

        0.35
        *
        zscore(
            s["win_pct"],
            np.mean(win_values),
            np.std(win_values)
        )

        +

        0.35
        *
        zscore(
            s["point_diff"],
            np.mean(diff_values),
            np.std(diff_values)
        )

        +

        0.15
        *
        zscore(
            s["ppg"],
            np.mean(ppg_values),
            np.std(ppg_values)
        )

        -

        0.15
        *
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

    home = normalize_team(
        home
    )

    away = normalize_team(
        away
    )

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
        -
        away_strength
        +
        home_advantage
    )

    probability_home = (

        1
        /
        (
            1
            +
            math.exp(
                -1.35 * difference
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
        1
        -
        probability_home
    )

    return {

        "home_probability":
            probability_home,

        "away_probability":
            probability_away,

        "home_strength":
            home_strength,

        "away_strength":
            away_strength,

    }


# ============================================================
# CLASIFICACION
# ============================================================

def classification(
    probability
):

    if probability >= 0.70:

        return (
            "🟢 PROBABILIDAD ALTA",
            "high"
        )

    elif probability >= 0.55:

        return (
            "🟡 PROBABILIDAD MEDIA",
            "medium"
        )

    else:

        return (
            "⚪ PROBABILIDAD BAJA",
            "low"
        )


def fmt_pct(x):

    return (
        f"{x * 100:.1f}%"
    )


# ============================================================
# PARTIDOS DE HOY
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

        competitions = (
            event.get(
                "competitions",
                []
            )
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

            team = c.get(
                "team",
                {}
            )

            abbr = team.get(
                "abbreviation"
            )

            if c.get(
                "homeAway"
            ) == "home":

                home = normalize_team(
                    abbr
                )

            elif c.get(
                "homeAway"
            ) == "away":

                away = normalize_team(
                    abbr
                )

        if not home or not away:
            continue

        games.append({

            "id":
                event.get("id"),

            "name":
                event.get("name", ""),

            "home":
                home,

            "away":
                away,

            "date":
                event.get("date", ""),

        })

    return games


# ============================================================
# MONEYLINE
# ============================================================

def american_profit(
    odds,
    stake
):

    if pd.isna(odds):

        return None

    odds = float(
        odds
    )

    if odds > 0:

        return (
            stake
            *
            odds
            /
            100
        )

    if odds < 0:

        return (
            stake
            *
            100
            /
            abs(odds)
        )

    return 0.0


# ============================================================
# PREPARAR CUOTAS HISTORICAS
# ============================================================

@st.cache_data(ttl=3600)
def load_2025_odds():

    df = load_games()

    required = [
        "season",
        "game_type",
        "date",
        "away",
        "home",
        "away_score",
        "home_score",
        "away_moneyline",
        "home_moneyline",
    ]

    missing = [
        c
        for c in required
        if c not in df.columns
    ]

    if missing:

        raise ValueError(
            "Los datos históricos no contienen "
            "las columnas de moneyline necesarias: "
            +
            ", ".join(missing)
        )

    df = df[
        df["season"] == 2025
    ].copy()

    df = df[
        df["game_type"]
        .astype(str)
        .str.upper()
        == "REG"
    ].copy()

    df["date"] = pd.to_datetime(
        df["date"],
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

    df["away_moneyline"] = pd.to_numeric(
        df["away_moneyline"],
        errors="coerce"
    )

    df["home_moneyline"] = pd.to_numeric(
        df["home_moneyline"],
        errors="coerce"
    )

    df["away"] = (
        df["away"]
        .astype(str)
        .map(normalize_team)
    )

    df["home"] = (
        df["home"]
        .astype(str)
        .map(normalize_team)
    )

    df = df.dropna(
        subset=[
            "date",
            "away",
            "home",
            "away_score",
            "home_score",
        ]
    )

    return df.sort_values(
        "date"
    ).reset_index(
        drop=True
    )


# ============================================================
# BACKTEST REALISTA
# ============================================================

def run_realistic_backtest(
    games,
    minimum_probability,
    stake
):

    games = (
        games
        .sort_values("date")
        .reset_index(drop=True)
    )

    past_games = []

    bets = []

    for _, game in games.iterrows():

        home = normalize_team(
            game["home"]
        )

        away = normalize_team(
            game["away"]
        )

        # --------------------------------------------
        # ESTADISTICAS DISPONIBLES ANTES DEL PARTIDO
        # --------------------------------------------

        if len(past_games) > 0:

            past_df = pd.DataFrame(
                past_games
            )

            stats = build_team_stats(
                past_df
            )

        else:

            stats = {}

        # --------------------------------------------
        # SOLO APOSTAMOS SI LOS DOS EQUIPOS
        # TIENEN HISTORIAL
        # --------------------------------------------

        can_predict = (

            home in stats
            and
            away in stats
            and
            stats[home]["games"] >= 3
            and
            stats[away]["games"] >= 3

        )

        prediction = None

        if can_predict:

            prediction = calculate_probability(
                home,
                away,
                stats
            )

        # --------------------------------------------
        # IMPORTANTE:
        # EL PARTIDO ACTUAL SE AGREGA DESPUES
        # DE CALCULAR LA PREDICCION.
        #
        # ASI NO HAY DATA LEAKAGE.
        # --------------------------------------------

        if prediction is not None:

            hp = prediction[
                "home_probability"
            ]

            ap = prediction[
                "away_probability"
            ]

            if hp >= ap:

                pick = home

                probability = hp

                odds = game[
                    "home_moneyline"
                ]

            else:

                pick = away

                probability = ap

                odds = game[
                    "away_moneyline"
                ]

            if (
                probability
                >=
                minimum_probability
                and
                not pd.isna(odds)
            ):

                home_score = float(
                    game["home_score"]
                )

                away_score = float(
                    game["away_score"]
                )

                # --------------------------------
                # RESULTADO REAL
                # --------------------------------

                if (
                    home_score
                    >
                    away_score
                ):

                    winner = home

                elif (
                    away_score
                    >
                    home_score
                ):

                    winner = away

                else:

                    winner = "TIE"

                # --------------------------------
                # GANANCIA
                # --------------------------------

                if winner == "TIE":

                    result = "PUSH"

                    profit = 0.0

                elif pick == winner:

                    result = "WIN"

                    profit = american_profit(
                        odds,
                        stake
                    )

                else:

                    result = "LOSS"

                    profit = -stake

                bets.append({

                    "date":
                        game["date"],

                    "away":
                        away,

                    "home":
                        home,

                    "pick":
                        pick,

                    "probability":
                        probability,

                    "moneyline":
                        odds,

                    "result":
                        result,

                    "stake":
                        stake,

                    "profit":
                        profit,

                })

        # --------------------------------------------
        # AHORA SI AGREGAMOS EL PARTIDO AL HISTORIAL
        # --------------------------------------------

        past_games.append({

            "date":
                game["date"],

            "home":
                home,

            "away":
                away,

            "home_score":
                game["home_score"],

            "away_score":
                game["away_score"],

        })

    return pd.DataFrame(
        bets
    )


# ============================================================
# INTERFAZ PRINCIPAL
# ============================================================

st.markdown(
    '<div class="title">🏈 Monitor NFL</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtitle">'
    'Modelo propio — sin cuotas de sportsbooks'
    '</div>',
    unsafe_allow_html=True
)

st.info(
    "🧠 Las probabilidades son generadas por "
    "nuestro modelo estadístico."
)


# ============================================================
# TABS
# ============================================================

tab_today, tab_backtest, tab_data = st.tabs(
    [
        "🏈 NFL DE HOY",
        "📈 BACKTEST ROI",
        "📊 DATOS",
    ]
)


# ============================================================
# TAB NFL DE HOY
# ============================================================

with tab_today:

    st.header(
        "🔎 NFL DE HOY"
    )

    if st.button(
        "🔄 ACTUALIZAR",
        use_container_width=True,
        key="refresh_today"
    ):

        st.cache_data.clear()

        st.rerun()

    try:

        historical = load_2025_games()

        team_stats = build_team_stats(
            historical
        )

    except Exception as e:

        st.error(
            "No se pudieron cargar los datos históricos."
        )

        st.code(
            str(e)
        )

        st.stop()

    try:

        today_games = get_today_games()

    except Exception as e:

        st.error(
            "No se pudo obtener el calendario de hoy."
        )

        st.code(
            str(e)
        )

        today_games = []

    if not today_games:

        st.warning(
            "No se encontraron partidos NFL para hoy."
        )

    else:

        st.success(
            f"{len(today_games)} partido(s) encontrados."
        )

        predictions = []

        for game in today_games:

            home = normalize_team(
                game["home"]
            )

            away = normalize_team(
                game["away"]
            )

            prediction = calculate_probability(
                home,
                away,
                team_stats
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

                favorite = home

                favorite_probability = hp

            else:

                favorite = away

                favorite_probability = ap

            label, css = classification(
                favorite_probability
            )

            predictions.append({

                "game":
                    game,

                "prediction":
                    prediction,

                "favorite":
                    favorite,

                "favorite_probability":
                    favorite_probability,

                "label":
                    label,

                "css":
                    css,

            })

        predictions.sort(
            key=lambda x:
            x["favorite_probability"],
            reverse=True
        )

        for index, item in enumerate(
            predictions,
            start=1
        ):

            game = item["game"]

            prediction = (
                item["prediction"]
            )

            home = normalize_team(
                game["home"]
            )

            away = normalize_team(
                game["away"]
            )

            hp = prediction[
                "home_probability"
            ]

            ap = prediction[
                "away_probability"
            ]

            game_time = (
                "Hora no disponible"
            )

            try:

                dt = datetime.fromisoformat(
                    game["date"]
                    .replace(
                        "Z",
                        "+00:00"
                    )
                )

                dt_dallas = dt.astimezone(
                    ZoneInfo(
                        "America/Chicago"
                    )
                )

                game_time = (
                    dt_dallas
                    .strftime(
                        "%I:%M %p"
                    )
                    .lstrip("0")
                )

            except Exception:

                pass

            st.markdown(
                '<div class="game-card">',
                unsafe_allow_html=True
            )

            st.markdown(
                f"### #{index} 🏈 "
                f"{team_display(item['favorite'])}"
            )

            st.write(
                f"**{team_display(away)}** "
                f"vs "
                f"**{team_display(home)}**"
            )

            st.markdown(
                f"🕐 **HOY — {game_time}**"
            )

            st.markdown(
                f'<div class="{item["css"]}">'
                f'{item["label"]}'
                f'</div>',
                unsafe_allow_html=True
            )

            col1, col2 = st.columns(2)

            with col1:

                st.markdown(
                    f"### {team_display(home)}"
                )

                st.markdown(
                    f'<div class="prob">'
                    f'{fmt_pct(hp)}'
                    f'</div>',
                    unsafe_allow_html=True
                )

            with col2:

                st.markdown(
                    f"### {team_display(away)}"
                )

                st.markdown(
                    f'<div class="prob">'
                    f'{fmt_pct(ap)}'
                    f'</div>',
                    unsafe_allow_html=True
                )

            home_stats = team_stats.get(
                home
            )

            away_stats = team_stats.get(
                away
            )

            st.markdown(
                "#### 📊 Datos utilizados por "
                "nuestro modelo"
            )

            if home_stats and away_stats:

                c1, c2 = st.columns(2)

                with c1:

                    st.markdown(
                        f"**{team_display(home)}**"
                    )

                    st.write(
                        f"🏆 Récord: "
                        f"{home_stats['wins']}-"
                        f"{home_stats['losses']}"
                    )

                    st.write(
                        f"📈 Win %: "
                        f"{home_stats['win_pct'] * 100:.1f}%"
                    )

                    st.write(
                        f"🔥 Puntos/partido: "
                        f"{home_stats['ppg']:.1f}"
                    )

                    st.write(
                        f"🛡️ Permitidos/partido: "
                        f"{home_stats['papg']:.1f}"
                    )

                    st.write(
                        f"📊 Diferencial: "
                        f"{home_stats['point_diff']:+.1f}"
                    )

                with c2:

                    st.markdown(
                        f"**{team_display(away)}**"
                    )

                    st.write(
                        f"🏆 Récord: "
                        f"{away_stats['wins']}-"
                        f"{away_stats['losses']}"
                    )

                    st.write(
                        f"📈 Win %: "
                        f"{away_stats['win_pct'] * 100:.1f}%"
                    )

                    st.write(
                        f"🔥 Puntos/partido: "
                        f"{away_stats['ppg']:.1f}"
                    )

                    st.write(
                        f"🛡️ Permitidos/partido: "
                        f"{away_stats['papg']:.1f}"
                    )

                    st.write(
                        f"📊 Diferencial: "
                        f"{away_stats['point_diff']:+.1f}"
                    )

            with st.expander(
                "📚 ¿Cómo funciona?"
            ):

                st.write(
                    "El modelo utiliza:"
                )

                st.write(
                    "• Porcentaje de victorias"
                )

                st.write(
                    "• Puntos anotados por partido"
                )

                st.write(
                    "• Puntos permitidos por partido"
                )

                st.write(
                    "• Diferencial de puntos"
                )

                st.write(
                    "• Ventaja de local"
                )

                st.write(
                    "Las cuotas NO se utilizan "
                    "para generar la probabilidad."
                )

            st.markdown(
                "</div>",
                unsafe_allow_html=True
            )


# ============================================================
# TAB BACKTEST
# ============================================================

with tab_backtest:

    st.header(
        "📈 Backtest realista"
    )

    st.write(
        "Probamos el modelo partido por partido "
        "sin utilizar información futura."
    )

    st.info(
        "Las cuotas históricas se utilizan "
        "ÚNICAMENTE para calcular cuánto "
        "habría ganado o perdido la apuesta."
    )

    minimum_probability = st.number_input(
        "Probabilidad mínima",
        min_value=0.50,
        max_value=0.95,
        value=0.70,
        step=0.01,
        format="%.2f",
        key="minimum_probability"
    )

    stake = st.number_input(
        "Apuesta por partido ($)",
        min_value=1.0,
        max_value=10000.0,
        value=10.0,
        step=1.0,
        key="stake"
    )

    st.divider()

    if st.button(
        "🚀 EJECUTAR BACKTEST",
        use_container_width=True,
        key="run_backtest"
    ):

        with st.spinner(
            "Calculando 2025 partido por partido..."
        ):

            try:

                historical_odds = (
                    load_2025_odds()
                )

                bets = run_realistic_backtest(
                    historical_odds,
                    minimum_probability,
                    stake
                )

                if bets.empty:

                    st.warning(
                        "No encontramos apuestas "
                        "con este criterio."
                    )

                else:

                    total_bets = len(
                        bets
                    )

                    wins = int(
                        (
                            bets["result"]
                            == "WIN"
                        ).sum()
                    )

                    losses = int(
                        (
                            bets["result"]
                            == "LOSS"
                        ).sum()
                    )

                    pushes = int(
                        (
                            bets["result"]
                            == "PUSH"
                        ).sum()
                    )

                    total_staked = (
                        bets["stake"]
                        .sum()
                    )

                    net_profit = (
                        bets["profit"]
                        .sum()
                    )

                    total_return = (
                        total_staked
                        +
                        net_profit
                    )

                    roi = (

                        net_profit
                        /
                        total_staked
                        *
                        100

                    )

                    win_rate = (

                        wins
                        /
                        total_bets
                        *
                        100

                    )

                    # ------------------------------------
                    # METRICAS
                    # ------------------------------------

                    st.subheader(
                        "🏆 RESULTADO"
                    )

                    c1, c2 = st.columns(2)

                    with c1:

                        st.metric(
                            "🎯 Apuestas",
                            total_bets
                        )

                    with c2:

                        st.metric(
                            "✅ Aciertos",
                            wins
                        )

                    c3, c4 = st.columns(2)

                    with c3:

                        st.metric(
                            "❌ Pérdidas",
                            losses
                        )

                    with c4:

                        st.metric(
                            "📈 Win Rate",
                            f"{win_rate:.1f}%"
                        )

                    c5, c6 = st.columns(2)

                    with c5:

                        st.metric(
                            "💵 Total apostado",
                            f"${total_staked:,.2f}"
                        )

                    with c6:

                        st.metric(
                            "💰 Ganancia/Pérdida",
                            f"${net_profit:+,.2f}"
                        )

                    c7, c8 = st.columns(2)

                    with c7:

                        st.metric(
                            "📊 ROI",
                            f"{roi:+.2f}%"
                        )

                    with c8:

                        st.metric(
                            "🏦 Retorno",
                            f"${total_return:,.2f}"
                        )

                    if pushes > 0:

                        st.caption(
                            f"Empates/PUSH: {pushes}"
                        )

                    # ------------------------------------
                    # MENSAJE
                    # ------------------------------------

                    if net_profit > 0:

                        st.success(
                            "🟢 EL MODELO TERMINÓ "
                            "CON GANANCIA"
                        )

                    elif net_profit < 0:

                        st.error(
                            "🔴 EL MODELO TERMINÓ "
                            "CON PÉRDIDA"
                        )

                    else:

                        st.info(
                            "⚪ EL MODELO TERMINÓ "
                            "EN BREAK-EVEN"
                        )

                    # ------------------------------------
                    # EVOLUCION DEL BANKROLL
                    # ------------------------------------

                    bets["bankroll"] = (
                        bets["profit"]
                        .cumsum()
                    )

                    st.subheader(
                        "📈 Evolución de $0"
                    )

                    chart_data = (
                        bets[
                            [
                                "bankroll"
                            ]
                        ]
                    )

                    st.line_chart(
                        chart_data
                    )

                    # ------------------------------------
                    # TABLA
                    # ------------------------------------

                    st.subheader(
                        "📋 Apuestas realizadas"
                    )

                    display = bets.copy()

                    display["probability"] = (
                        display["probability"]
                        *
                        100
                    ).round(1)

                    display["moneyline"] = (
                        display["moneyline"]
                        .round(0)
                    )

                    display["profit"] = (
                        display["profit"]
                        .round(2)
                    )

                    display["date"] = (
                        display["date"]
                        .dt.strftime(
                            "%Y-%m-%d"
                        )
                    )

                    display = display[
                        [
                            "date",
                            "away",
                            "home",
                            "pick",
                            "probability",
                            "moneyline",
                            "result",
                            "profit",
                        ]
                    ]

                    display.columns = [
                        "Fecha",
                        "Visitante",
                        "Local",
                        "Pick",
                        "Prob. %",
                        "Moneyline",
                        "Resultado",
                        "Ganancia",
                    ]

                    st.dataframe(
                        display,
                        use_container_width=True
                    )

                    # ------------------------------------
                    # DESCARGAR
                    # ------------------------------------

                    csv = bets.to_csv(
                        index=False
                    )

                    st.download_button(
                        "📥 DESCARGAR RESULTADOS",
                        data=csv,
                        file_name=(
                            "backtest_nfl_2025.csv"
                        ),
                        mime="text/csv",
                        use_container_width=True
                    )

            except Exception as e:

                st.error(
                    "❌ No se pudo ejecutar "
                    "el backtest."
                )

                st.code(
                    str(e)
                )

                st.info(
                    "Si el error indica que "
                    "no existe home_moneyline o "
                    "away_moneyline, mándame "
                    "la captura y adaptamos "
                    "la fuente de cuotas."
                )


# ============================================================
# TAB DATOS
# ============================================================

with tab_data:

    st.header(
        "📊 Datos del modelo"
    )

    try:

        historical = load_2025_games()

        stats = build_team_stats(
            historical
        )

        st.metric(
            "🏈 Partidos 2025",
            len(historical)
        )

        st.metric(
            "👥 Equipos",
            len(stats)
        )

        st.write(
            "Fuente histórica: nflverse."
        )

        st.write(
            "El modelo actual utiliza "
            "temporada regular 2025."
        )

        st.write(
            "El backtest calcula la fuerza "
            "de cada equipo utilizando "
            "únicamente partidos anteriores "
            "al partido evaluado."
        )

        st.write(
            "Las moneylines históricas "
            "se utilizan únicamente "
            "para calcular el resultado "
            "financiero."
        )

    except Exception as e:

        st.error(
            str(e)
        )


# ============================================================
# PIE
# ============================================================

st.divider()

st.caption(
    "⚠️ Este modelo es experimental. "
    "Un backtest positivo no garantiza "
    "ganancias futuras."
)

st.caption(
    "La validación debe continuar con "
    "muestras fuera de la muestra utilizada "
    "para desarrollar el modelo."
)
