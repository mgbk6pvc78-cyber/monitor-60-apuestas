import streamlit as st
import pandas as pd
import numpy as np
import requests
from datetime import datetime, timedelta, timezone

# ============================================================
# NFL EDGE
# Modelo independiente del mercado
#
# HISTORICO:
#   2025 + 2026 disponible
#
# NO utiliza cuotas de sportsbooks para calcular probabilidades.
# ============================================================

st.set_page_config(
    page_title="NFL EDGE",
    page_icon="🏈",
    layout="wide"
)

# ------------------------------------------------------------
# CONFIGURACION
# ------------------------------------------------------------

ESPN_SCOREBOARD = (
    "https://site.api.espn.com/apis/site/v2/sports/"
    "football/nfl/scoreboard"
)

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

CURRENT_YEAR = 2026
HISTORICAL_YEAR = 2025

# ------------------------------------------------------------
# ESTILO
# ------------------------------------------------------------

st.markdown("""
<style>

.main {
    background-color: #0e1117;
}

.block-container {
    padding-top: 2rem;
    padding-bottom: 3rem;
}

h1 {
    font-size: 3rem !important;
}

h2 {
    font-size: 2rem !important;
}

.game-card {
    border: 1px solid #343944;
    border-radius: 15px;
    padding: 22px;
    margin-bottom: 18px;
    background: #151922;
}

.pick {
    font-size: 28px;
    font-weight: bold;
}

.prob {
    font-size: 40px;
    font-weight: bold;
}

.small {
    color: #9da3ae;
    font-size: 14px;
}

.edge-good {
    color: #55d98b;
    font-weight: bold;
}

.edge-neutral {
    color: #f2c94c;
    font-weight: bold;
}

</style>
""", unsafe_allow_html=True)


# ------------------------------------------------------------
# UTILIDADES
# ------------------------------------------------------------

@st.cache_data(ttl=900)
def get_json(url, params=None):

    try:

        r = requests.get(
            url,
            params=params,
            headers=HEADERS,
            timeout=20
        )

        if r.status_code != 200:
            return None

        return r.json()

    except Exception:
        return None


def normalize_team(name):

    if not name:
        return ""

    return name.upper().strip()


# ------------------------------------------------------------
# OBTENER PARTIDOS DE UNA FECHA
# ------------------------------------------------------------

@st.cache_data(ttl=900)
def get_games_for_date(date_string):

    data = get_json(
        ESPN_SCOREBOARD,
        {
            "dates": date_string,
            "limit": 100
        }
    )

    if not data:
        return []

    games = []

    for event in data.get("events", []):

        try:

            competition = event["competitions"][0]

            competitors = competition["competitors"]

            home = None
            away = None

            for team in competitors:

                if team.get("homeAway") == "home":
                    home = team

                elif team.get("homeAway") == "away":
                    away = team

            if not home or not away:
                continue

            home_team = normalize_team(
                home["team"].get("abbreviation")
                or home["team"].get("shortDisplayName")
            )

            away_team = normalize_team(
                away["team"].get("abbreviation")
                or away["team"].get("shortDisplayName")
            )

            home_name = home["team"].get(
                "displayName",
                home_team
            )

            away_name = away["team"].get(
                "displayName",
                away_team
            )

            games.append({

                "id": event.get("id"),

                "date": event.get("date"),

                "home": home_team,

                "away": away_team,

                "home_name": home_name,

                "away_name": away_name,

                "status": event.get(
                    "status",
                    {}
                ).get(
                    "type",
                    {}
                ).get(
                    "description",
                    ""
                ),

                "home_score": float(
                    home.get("score", 0)
                    or 0
                ),

                "away_score": float(
                    away.get("score", 0)
                    or 0
                )

            })

        except Exception:
            continue

    return games


# ------------------------------------------------------------
# OBTENER PARTIDOS DE TODA UNA TEMPORADA
# ------------------------------------------------------------

@st.cache_data(ttl=3600)
def get_season_games(year):

    all_games = []

    # NFL regular season + preseason.
    # Revisamos desde agosto hasta enero.
    start = datetime(year, 8, 1)
    end = datetime(year + 1, 1, 20)

    current = start

    while current <= end:

        date_string = current.strftime("%Y%m%d")

        games = get_games_for_date(date_string)

        for game in games:

            # Solo partidos terminados.
            status = game["status"].lower()

            if (
                "final" in status
                or status == "final"
            ):
                all_games.append(game)

        current += timedelta(days=1)

    if not all_games:
        return pd.DataFrame()

    df = pd.DataFrame(all_games)

    df = df.drop_duplicates(
        subset=["id"]
    )

    return df


# ------------------------------------------------------------
# CONSTRUIR ESTADISTICAS DE EQUIPOS
# ------------------------------------------------------------

def build_team_stats(df):

    teams = {}

    if df.empty:
        return teams

    for _, game in df.iterrows():

        home = game["home"]
        away = game["away"]

        hs = float(game["home_score"])
        aws = float(game["away_score"])

        if home not in teams:

            teams[home] = {
                "games": 0,
                "wins": 0,
                "losses": 0,
                "points_for": 0,
                "points_against": 0,
                "recent": []
            }

        if away not in teams:

            teams[away] = {
                "games": 0,
                "wins": 0,
                "losses": 0,
                "points_for": 0,
                "points_against": 0,
                "recent": []
            }

        # HOME
        teams[home]["games"] += 1
        teams[home]["points_for"] += hs
        teams[home]["points_against"] += aws

        if hs > aws:
            teams[home]["wins"] += 1
            result_home = 1
        else:
            teams[home]["losses"] += 1
            result_home = 0

        teams[home]["recent"].append({
            "date": game["date"],
            "result": result_home,
            "margin": hs - aws
        })

        # AWAY
        teams[away]["games"] += 1
        teams[away]["points_for"] += aws
        teams[away]["points_against"] += hs

        if aws > hs:
            teams[away]["wins"] += 1
            result_away = 1
        else:
            teams[away]["losses"] += 1
            result_away = 0

        teams[away]["recent"].append({
            "date": game["date"],
            "result": result_away,
            "margin": aws - hs
        })

    return teams


# ------------------------------------------------------------
# DATOS DE EQUIPO
# ------------------------------------------------------------

def team_profile(team, stats):

    if team not in stats:

        return {
            "win_pct": 0.50,
            "ppg": 21.5,
            "papg": 21.5,
            "recent_win_pct": 0.50,
            "recent_margin": 0
        }

    t = stats[team]

    games = max(
        1,
        t["games"]
    )

    recent = t["recent"][-8:]

    if recent:

        recent_win_pct = np.mean([
            x["result"]
            for x in recent
        ])

        recent_margin = np.mean([
            x["margin"]
            for x in recent
        ])

    else:

        recent_win_pct = 0.50
        recent_margin = 0

    return {

        "win_pct":
            t["wins"] / games,

        "ppg":
            t["points_for"] / games,

        "papg":
            t["points_against"] / games,

        "recent_win_pct":
            recent_win_pct,

        "recent_margin":
            recent_margin
    }


# ------------------------------------------------------------
# MODELO
# ------------------------------------------------------------

def sigmoid(x):

    x = np.clip(
        x,
        -10,
        10
    )

    return 1 / (
        1 + np.exp(-x)
    )


def calculate_probability(
    home_team,
    away_team,
    stats
):

    home = team_profile(
        home_team,
        stats
    )

    away = team_profile(
        away_team,
        stats
    )

    # --------------------------------------------------------
    # DIFERENCIAS
    # --------------------------------------------------------

    win_diff = (
        home["win_pct"]
        - away["win_pct"]
    )

    recent_diff = (
        home["recent_win_pct"]
        - away["recent_win_pct"]
    )

    offense_diff = (
        home["ppg"]
        - away["ppg"]
    )

    defense_diff = (
        away["papg"]
        - home["papg"]
    )

    margin_diff = (
        home["recent_margin"]
        - away["recent_margin"]
    )

    # --------------------------------------------------------
    # SCORE DEL MODELO
    #
    # La localia agrega una pequeña ventaja.
    # NO se utilizan cuotas.
    # --------------------------------------------------------

    score = (

        win_diff * 1.20

        + recent_diff * 1.35

        + offense_diff * 0.035

        + defense_diff * 0.035

        + margin_diff * 0.025

        + 0.12

    )

    home_probability = sigmoid(
        score * 2.0
    )

    away_probability = (
        1 - home_probability
    )

    # Limitar probabilidades extremas.
    # No queremos vender una falsa certeza.

    home_probability = np.clip(
        home_probability,
        0.15,
        0.85
    )

    away_probability = (
        1 - home_probability
    )

    return (
        home_probability,
        away_probability
    )


# ------------------------------------------------------------
# PROBABILIDAD AJUSTADA PARA PRETEMPORADA
# ------------------------------------------------------------

def preseason_adjustment(
    probability,
    game
):

    # En pretemporada existe mucha incertidumbre
    # por rotaciones y jugadores que no juegan.
    #
    # Por eso acercamos la probabilidad al 50%.

    status = str(
        game.get("status", "")
    ).lower()

    # Los partidos actuales de agosto
    # normalmente serán preseason.

    if "preseason" in status:
        probability = (
            probability * 0.65
            + 0.50 * 0.35
        )

    return probability


# ------------------------------------------------------------
# GENERAR ANALISIS
# ------------------------------------------------------------

def analyze_game(
    game,
    stats
):

    home = game["home"]
    away = game["away"]

    home_prob, away_prob = calculate_probability(
        home,
        away,
        stats
    )

    home_prob = preseason_adjustment(
        home_prob,
        game
    )

    away_prob = 1 - home_prob

    if home_prob >= away_prob:

        pick = home
        probability = home_prob

    else:

        pick = away
        probability = away_prob

    return {

        "pick": pick,

        "probability": probability,

        "home_probability": home_prob,

        "away_probability": away_prob

    }


# ------------------------------------------------------------
# CARGAR HISTORICO
# ------------------------------------------------------------

with st.spinner(
    "🧠 Cargando histórico 2025..."
):

    historical_2025 = get_season_games(
        HISTORICAL_YEAR
    )


# ------------------------------------------------------------
# CARGAR RESULTADOS 2026
# ------------------------------------------------------------

with st.spinner(
    "📊 Cargando resultados 2026..."
):

    historical_2026 = get_season_games(
        CURRENT_YEAR
    )


# ------------------------------------------------------------
# COMBINAR DATOS
# ------------------------------------------------------------

frames = []

if not historical_2025.empty:
    frames.append(
        historical_2025
    )

if not historical_2026.empty:
    frames.append(
        historical_2026
    )

if frames:

    historical = pd.concat(
        frames,
        ignore_index=True
    )

else:

    historical = pd.DataFrame()


stats = build_team_stats(
    historical
)


# ------------------------------------------------------------
# PARTIDOS DE HOY
# ------------------------------------------------------------

today = datetime.now(
    timezone.utc
).astimezone().strftime(
    "%Y%m%d"
)

today_games = get_games_for_date(
    today
)


# ------------------------------------------------------------
# TITULO
# ------------------------------------------------------------

st.title(
    "🏈 NFL EDGE"
)

st.caption(
    "Probabilidad independiente del modelo"
)

st.caption(
    "🚫 Las cuotas de sportsbooks NO se utilizan para generar la probabilidad."
)

st.divider()


# ------------------------------------------------------------
# PARTIDOS
# ------------------------------------------------------------

st.header(
    "🏈 PARTIDOS DE HOY"
)

if not today_games:

    st.info(
        "No se encontraron partidos NFL para hoy."
    )

else:

    for game in today_games:

        analysis = analyze_game(
            game,
            stats
        )

        home = game["home"]
        away = game["away"]

        home_prob = (
            analysis["home_probability"]
            * 100
        )

        away_prob = (
            analysis["away_probability"]
            * 100
        )

        pick = analysis["pick"]

        probability = (
            analysis["probability"]
            * 100
        )

        # ----------------------------------------------------
        # TARJETA
        # ----------------------------------------------------

        st.markdown(
            '<div class="game-card">',
            unsafe_allow_html=True
        )

        col1, col2, col3 = st.columns(
            [2, 1, 2]
        )

        with col1:

            st.subheader(
                f"{away}"
            )

            st.write(
                f"Probabilidad: **{away_prob:.1f}%**"
            )

        with col2:

            st.markdown(
                "<h3 style='text-align:center'>@</h3>",
                unsafe_allow_html=True
            )

        with col3:

            st.subheader(
                f"{home}"
            )

            st.write(
                f"Probabilidad: **{home_prob:.1f}%**"
            )

        st.divider()

        st.markdown(
            f"""
            <div class="pick">
            🎯 PICK DEL MODELO: {pick}
            </div>

            <div class="prob">
            {probability:.1f}%
            </div>

            <div class="small">
            Probabilidad estimada por nuestro modelo,
            sin utilizar cuotas de sportsbooks.
            </div>
            """,
            unsafe_allow_html=True
        )

        # ----------------------------------------------------
        # INFORMACION DEL MODELO
        # ----------------------------------------------------

        if probability >= 65:

            st.success(
                f"🟢 Señal fuerte del modelo: {pick} "
                f"{probability:.1f}%"
            )

        elif probability >= 58:

            st.warning(
                f"🟡 Ventaja moderada: {pick} "
                f"{probability:.1f}%"
            )

        else:

            st.info(
                f"⚪ Partido cerrado: {pick} "
                f"{probability:.1f}%"
            )

        st.markdown(
            "</div>",
            unsafe_allow_html=True
        )


# ------------------------------------------------------------
# METODOLOGIA MINIMA
# ------------------------------------------------------------

st.divider()

with st.expander(
    "🧠 ¿Cómo calcula la probabilidad?"
):

    st.write(
        """
        El modelo utiliza únicamente información deportiva.

        Histórico utilizado:
        • Temporada 2025
        • Resultados disponibles de 2026

        Factores principales:
        • Rendimiento general
        • Rendimiento reciente
        • Puntos anotados
        • Puntos permitidos
        • Diferencial reciente
        • Porcentaje de victorias
        • Localía

        Las cuotas de las casas NO forman parte del cálculo.

        La probabilidad no significa certeza.
        Es una estimación matemática del modelo.
        """
    )


# ------------------------------------------------------------
# NOTA
# ------------------------------------------------------------

st.caption(
    "NFL EDGE — Modelo experimental independiente. "
    "No garantiza resultados ni constituye asesoramiento financiero."
)
