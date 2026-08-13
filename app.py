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
        padding-top: 1.5rem;
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
        font-size: 36px;
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

    .model-box {
        background: #182536;
        border: 1px solid #29476b;
        border-radius: 14px;
        padding: 16px;
        margin: 15px 0;
    }

    .backtest-box {
        background: #17191f;
        border: 1px solid #30343d;
        border-radius: 18px;
        padding: 20px;
        margin-bottom: 20px;
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

    replacements = {
        "JAC": "JAX",
        "LA": "LAR",
    }

    return replacements.get(str(team), str(team))


def team_display(team):

    team = normalize_team(team)

    return TEAM_NAMES.get(team, team)


# ============================================================
# CARGAR DATOS NFL
# ============================================================

@st.cache_data(ttl=3600)
def load_games():

    df = pd.read_csv(NFLVERSE_GAMES)

    df.columns = [
        str(c).lower().strip()
        for c in df.columns
    ]

    required = [
        "season",
        "game_type",
        "week",
        "away_team",
        "home_team",
        "away_score",
        "home_score"
    ]

    missing = [
        c for c in required
        if c not in df.columns
    ]

    if missing:

        raise ValueError(
            "Faltan columnas en games.csv: "
            + ", ".join(missing)
        )

    df = df.copy()

    df["season"] = pd.to_numeric(
        df["season"],
        errors="coerce"
    )

    df["week"] = pd.to_numeric(
        df["week"],
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
            "season",
            "week",
            "away_score",
            "home_score"
        ]
    )

    df["away_team"] = df["away_team"].apply(
        normalize_team
    )

    df["home_team"] = df["home_team"].apply(
        normalize_team
    )

    # Solo temporada regular
    df = df[
        df["game_type"].astype(str).str.lower() == "reg"
    ].copy()

    # Solo 2025
    df = df[
        df["season"] == 2025
    ].copy()

    # Orden cronológico
    if "gameday" in df.columns:

        df["gameday"] = pd.to_datetime(
            df["gameday"],
            errors="coerce"
        )

        df = df.sort_values(
            ["gameday", "week"]
        )

    else:

        df = df.sort_values(
            ["week"]
        )

    return df.reset_index(drop=True)


# ============================================================
# ESTADÍSTICAS
# ============================================================

def empty_team():

    return {
        "games": 0,
        "wins": 0,
        "losses": 0,
        "points_for": 0.0,
        "points_against": 0.0,
        "recent_results": [],
    }


def update_team(
    stats,
    team,
    points_for,
    points_against
):

    if team not in stats:
        stats[team] = empty_team()

    s = stats[team]

    s["games"] += 1
    s["points_for"] += points_for
    s["points_against"] += points_against

    if points_for > points_against:

        s["wins"] += 1
        result = 1

    else:

        s["losses"] += 1
        result = 0

    s["recent_results"].append(result)

    # Solo mantenemos los últimos 5
    s["recent_results"] = (
        s["recent_results"][-5:]
    )


def build_stats_from_games(games):

    stats = {}

    for _, row in games.iterrows():

        away = normalize_team(
            row["away_team"]
        )

        home = normalize_team(
            row["home_team"]
        )

        away_score = float(
            row["away_score"]
        )

        home_score = float(
            row["home_score"]
        )

        update_team(
            stats,
            away,
            away_score,
            home_score
        )

        update_team(
            stats,
            home,
            home_score,
            away_score
        )

    return stats


# ============================================================
# ELO
# ============================================================

def initial_elo():

    return 1500.0


def expected_elo(
    rating_a,
    rating_b
):

    return (
        1 /
        (
            1 +
            10 ** (
                (rating_b - rating_a) / 400
            )
        )
    )


def update_elo(
    rating_winner,
    rating_loser,
    margin
):

    # K moderado para NFL
    k = 24

    # Ajuste por margen
    margin_multiplier = (
        math.log(
            max(abs(margin), 1) + 1
        )
        * 2.0
    )

    expected = expected_elo(
        rating_winner,
        rating_loser
    )

    change = (
        k
        * margin_multiplier
        * (1 - expected)
    )

    return (
        rating_winner + change,
        rating_loser - change
    )


def build_elo_from_games(games):

    elo = {}

    for team in TEAM_NAMES.keys():

        elo[team] = initial_elo()

    for _, row in games.iterrows():

        away = normalize_team(
            row["away_team"]
        )

        home = normalize_team(
            row["home_team"]
        )

        away_score = float(
            row["away_score"]
        )

        home_score = float(
            row["home_score"]
        )

        if away not in elo:
            elo[away] = initial_elo()

        if home not in elo:
            elo[home] = initial_elo()

        away_rating = elo[away]
        home_rating = elo[home]

        if home_score > away_score:

            new_home, new_away = update_elo(
                home_rating,
                away_rating,
                home_score - away_score
            )

            elo[home] = new_home
            elo[away] = new_away

        else:

            new_away, new_home = update_elo(
                away_rating,
                home_rating,
                away_score - home_score
            )

            elo[away] = new_away
            elo[home] = new_home

    return elo


# ============================================================
# FUERZA ESTADÍSTICA
# ============================================================

def safe_average(
    values,
    default=0.0
):

    values = [
        x for x in values
        if x is not None
        and not pd.isna(x)
    ]

    if not values:
        return default

    return float(
        np.mean(values)
    )


def safe_std(
    values
):

    values = [
        x for x in values
        if x is not None
        and not pd.isna(x)
    ]

    if len(values) < 2:
        return 1.0

    std = float(
        np.std(values)
    )

    return max(std, 0.0001)


def team_metrics(
    team,
    stats,
    elo
):

    if team not in stats:

        return {
            "win_pct": 0.5,
            "ppg": 22.0,
            "papg": 22.0,
            "point_diff": 0.0,
            "recent_win_pct": 0.5,
            "elo": elo.get(
                team,
                1500.0
            )
        }

    s = stats[team]

    games = max(
        s["games"],
        1
    )

    win_pct = (
        s["wins"] / games
    )

    ppg = (
        s["points_for"] / games
    )

    papg = (
        s["points_against"] / games
    )

    point_diff = (
        ppg - papg
    )

    recent = s["recent_results"]

    if recent:

        recent_win_pct = (
            sum(recent)
            / len(recent)
        )

    else:

        recent_win_pct = 0.5

    return {
        "win_pct": win_pct,
        "ppg": ppg,
        "papg": papg,
        "point_diff": point_diff,
        "recent_win_pct":
            recent_win_pct,
        "elo": elo.get(
            team,
            1500.0
        )
    }


# ============================================================
# PROBABILIDAD DEL MODELO
# ============================================================

def calculate_probability(
    home,
    away,
    stats,
    elo
):

    home = normalize_team(home)
    away = normalize_team(away)

    h = team_metrics(
        home,
        stats,
        elo
    )

    a = team_metrics(
        away,
        stats,
        elo
    )

    # --------------------------------------------------------
    # DIFERENCIAS
    # --------------------------------------------------------

    elo_diff = (
        h["elo"] - a["elo"]
    )

    elo_component = (
        elo_diff / 400
    )

    win_component = (
        h["win_pct"]
        - a["win_pct"]
    )

    point_component = (
        h["point_diff"]
        - a["point_diff"]
    ) / 20

    recent_component = (
        h["recent_win_pct"]
        - a["recent_win_pct"]
    )

    offense_component = (
        h["ppg"] - a["ppg"]
    ) / 30

    defense_component = (
        a["papg"] - h["papg"]
    ) / 30

    # --------------------------------------------------------
    # MODELO
    # --------------------------------------------------------

    score = (

        0.45 * elo_component

        +

        0.20 * win_component

        +

        0.18 * point_component

        +

        0.07 * recent_component

        +

        0.05 * offense_component

        +

        0.05 * defense_component

    )

    # Ventaja de local
    score += 0.075

    # Transformación logística
    probability_home = (
        1 /
        (
            1 +
            math.exp(
                -4.0 * score
            )
        )
    )

    # Limitar extremos
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

        "home_elo":
            h["elo"],

        "away_elo":
            a["elo"],

        "elo_difference":
            elo_diff,

        "home_win_pct":
            h["win_pct"],

        "away_win_pct":
            a["win_pct"],

        "home_point_diff":
            h["point_diff"],

        "away_point_diff":
            a["point_diff"],

        "home_recent":
            h["recent_win_pct"],

        "away_recent":
            a["recent_win_pct"],
    }


# ============================================================
# CLASIFICACIÓN
# ============================================================

def classification(probability):

    if probability >= 0.70:

        return (
            "🟢 PROBABILIDAD MUY ALTA",
            "high"
        )

    elif probability >= 0.60:

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
# BACKTEST 2025
# ============================================================

def run_backtest(games):

    stats = {}

    elo = {
        team: initial_elo()
        for team in TEAM_NAMES.keys()
    }

    results = []

    for _, row in games.iterrows():

        home = normalize_team(
            row["home_team"]
        )

        away = normalize_team(
            row["away_team"]
        )

        home_score = float(
            row["home_score"]
        )

        away_score = float(
            row["away_score"]
        )

        # ----------------------------------------------------
        # PREDICCIÓN ANTES DEL PARTIDO
        # ----------------------------------------------------

        prediction = calculate_probability(
            home,
            away,
            stats,
            elo
        )

        hp = prediction[
            "home_probability"
        ]

        ap = prediction[
            "away_probability"
        ]

        actual_home_win = (
            1
            if home_score > away_score
            else 0
        )

        predicted_home_win = (
            1
            if hp >= 0.5
            else 0
        )

        correct = (
            predicted_home_win
            == actual_home_win
        )

        confidence = max(
            hp,
            ap
        )

        if confidence >= 0.70:

            bucket = "70%+"

        elif confidence >= 0.60:

            bucket = "60-69%"

        elif confidence >= 0.55:

            bucket = "55-59%"

        else:

            bucket = "<55%"

        results.append({

            "home":
                home,

            "away":
                away,

            "home_probability":
                hp,

            "away_probability":
                ap,

            "confidence":
                confidence,

            "correct":
                correct,

            "bucket":
                bucket,

            "actual_home_win":
                actual_home_win
        })

        # ----------------------------------------------------
        # ACTUALIZAMOS EL MODELO DESPUÉS DEL PARTIDO
        # ----------------------------------------------------

        update_team(
            stats,
            home,
            home_score,
            away_score
        )

        update_team(
            stats,
            away,
            away_score,
            home_score
        )

        # Elo
        home_rating = elo.get(
            home,
            initial_elo()
        )

        away_rating = elo.get(
            away,
            initial_elo()
        )

        if home_score > away_score:

            new_home, new_away = update_elo(
                home_rating,
                away_rating,
                home_score - away_score
            )

            elo[home] = new_home
            elo[away] = new_away

        else:

            new_away, new_home = update_elo(
                away_rating,
                home_rating,
                away_score - home_score
            )

            elo[away] = new_away
            elo[home] = new_home

    return pd.DataFrame(results)


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
    ).strftime("%Y%m%d")

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

        competition = competitions[0]

        competitors = competition.get(
            "competitors",
            []
        )

        if len(competitors) < 2:
            continue

        home = None
        away = None

        for competitor in competitors:

            team = competitor.get(
                "team",
                {}
            )

            abbr = team.get(
                "abbreviation"
            )

            if competitor.get(
                "homeAway"
            ) == "home":

                home = normalize_team(
                    abbr
                )

            elif competitor.get(
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

            "status":
                event.get(
                    "status",
                    {}
                ).get(
                    "type",
                    {}
                ).get(
                    "description",
                    ""
                )
        })

    return games


# ============================================================
# ENCABEZADO
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
    "🧠 Esta probabilidad es generada exclusivamente "
    "por nuestro modelo. NO utiliza cuotas de apuestas."
)


# ============================================================
# CARGAR HISTÓRICO
# ============================================================

try:

    historical_games = load_games()

except Exception as e:

    st.error(
        "No se pudieron cargar los datos NFL."
    )

    st.code(str(e))

    st.stop()


# ============================================================
# BACKTEST
# ============================================================

st.divider()

st.subheader(
    "🧪 VALIDACIÓN DEL MODELO — TEMPORADA 2025"
)

st.write(
    "Esta prueba simula lo que habría ocurrido si "
    "nuestro modelo hubiera analizado cada partido "
    "antes de que comenzara."
)

if st.button(
    "🧪 EJECUTAR BACKTEST 2025",
    use_container_width=True
):

    with st.spinner(
        "Analizando todos los partidos de 2025..."
    ):

        backtest = run_backtest(
            historical_games
        )

        st.session_state[
            "backtest"
        ] = backtest


if "backtest" in st.session_state:

    backtest = st.session_state[
        "backtest"
    ]

    total = len(
        backtest
    )

    accuracy = (
        backtest["correct"].mean()
        if total
        else 0
    )

    brier = np.mean(
        (
            backtest["home_probability"]
            -
            backtest["actual_home_win"]
        ) ** 2
    )

    st.markdown(
        '<div class="backtest-box">',
        unsafe_allow_html=True
    )

    c1, c2 = st.columns(2)

    with c1:

        st.metric(
            "🎯 Acierto",
            fmt_pct(accuracy)
        )

    with c2:

        st.metric(
            "📉 Brier Score",
            f"{brier:.3f}"
        )

    st.write(
        f"Partidos evaluados: **{total}**"
    )

    st.markdown(
        "</div>",
        unsafe_allow_html=True
    )

    # --------------------------------------------------------
    # RESULTADOS POR CONFIANZA
    # --------------------------------------------------------

    st.subheader(
        "📊 Rendimiento por nivel de confianza"
    )

    buckets = []

    for bucket_name in [
        "70%+",
        "60-69%",
        "55-59%",
        "<55%"
    ]:

        subset = backtest[
            backtest["bucket"]
            == bucket_name
        ]

        if len(subset) == 0:

            continue

        buckets.append({

            "Nivel":
                bucket_name,

            "Partidos":
                len(subset),

            "Aciertos":
                int(
                    subset["correct"].sum()
                ),

            "Acierto %":
                f"{subset['correct'].mean()*100:.1f}%"
        })

    if buckets:

        st.dataframe(
            pd.DataFrame(buckets),
            use_container_width=True,
            hide_index=True
        )

    st.caption(
        "Importante: una probabilidad del 70% no "
        "significa que el modelo deba acertar 7 de "
        "cada 10 partidos exactamente en una muestra "
        "pequeña. La validación debe hacerse con una "
        "cantidad suficiente de partidos."
    )


# ============================================================
# MODELO ACTUAL PARA HOY
# ============================================================

st.divider()

st.subheader(
    "🔎 NFL DE HOY"
)

if st.button(
    "🔄 ACTUALIZAR PARTIDOS DE HOY",
    use_container_width=True
):

    st.cache_data.clear()

    st.rerun()


# Para las predicciones actuales usamos
# TODA la temporada 2025 como información histórica.

current_stats = build_stats_from_games(
    historical_games
)

current_elo = build_elo_from_games(
    historical_games
)


try:

    today_games = get_today_games()

except Exception as e:

    st.error(
        "No se pudo obtener el calendario de hoy."
    )

    st.code(str(e))

    today_games = []


if not today_games:

    st.warning(
        "No se encontraron partidos NFL para hoy."
    )

else:

    st.success(
        f"{len(today_games)} partido(s) encontrados para hoy."
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
            current_stats,
            current_elo
        )

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
                css
        })

    predictions.sort(
        key=lambda x:
        x["favorite_probability"],
        reverse=True
    )

    # --------------------------------------------------------
    # MOSTRAR PARTIDOS
    # --------------------------------------------------------

    for index, item in enumerate(
        predictions,
        start=1
    ):

        game = item["game"]

        prediction = item[
            "prediction"
        ]

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

        # Hora
        try:

            dt = datetime.fromisoformat(
                game["date"].replace(
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
                dt_dallas.strftime(
                    "%I:%M %p"
                ).lstrip("0")
            )

        except Exception:

            game_time = (
                "Hora no disponible"
            )

        st.markdown(
            '<div class="game-card">',
            unsafe_allow_html=True
        )

        st.markdown(
            f"## #{index} 🏈 "
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

        # Información del modelo
        st.markdown(
            '<div class="model-box">'
            '<b>🏈 PARTIDO NFL</b><br>'
            'Modelo basado en temporada regular 2025.'
            '</div>',
            unsafe_allow_html=True
        )

        label = item["label"]
        css = item["css"]

        st.markdown(
            f'<div class="{css}">'
            f'{label}'
            f'</div>',
            unsafe_allow_html=True
        )

        # ----------------------------------------------------
        # PROBABILIDADES
        # ----------------------------------------------------

        c1, c2 = st.columns(2)

        with c1:

            st.markdown(
                f"### {team_display(home)}"
            )

            st.markdown(
                f'<div class="prob">'
                f'{fmt_pct(hp)}'
                f'</div>',
                unsafe_allow_html=True
            )

        with c2:

            st.markdown(
                f"### {team_display(away)}"
            )

            st.markdown(
                f'<div class="prob">'
                f'{fmt_pct(ap)}'
                f'</div>',
                unsafe_allow_html=True
            )

        # ----------------------------------------------------
        # DATOS
        # ----------------------------------------------------

        with st.expander(
            "📊 Datos utilizados por nuestro modelo"
        ):

            home_metrics = team_metrics(
                home,
                current_stats,
                current_elo
            )

            away_metrics = team_metrics(
                away,
                current_stats,
                current_elo
            )

            c1, c2 = st.columns(2)

            with c1:

                st.markdown(
                    f"**{team_display(home)}**"
                )

                st.write(
                    f"🏆 Récord: "
                    f"{current_stats.get(home, {}).get('wins', 0)}-"
                    f"{current_stats.get(home, {}).get('losses', 0)}"
                )

                st.write(
                    f"📈 Win %: "
                    f"{home_metrics['win_pct']*100:.1f}%"
                )

                st.write(
                    f"🔥 Puntos/partido: "
                    f"{home_metrics['ppg']:.1f}"
                )

                st.write(
                    f"🛡️ Permitidos/partido: "
                    f"{home_metrics['papg']:.1f}"
                )

                st.write(
                    f"📊 Diferencial: "
                    f"{home_metrics['point_diff']:+.1f}"
                )

                st.write(
                    f"🏅 Elo: "
                    f"{home_metrics['elo']:.0f}"
                )

                st.write(
                    f"🔥 Forma últimos 5: "
                    f"{home_metrics['recent_win_pct']*100:.1f}%"
                )

            with c2:

                st.markdown(
                    f"**{team_display(away)}**"
                )

                st.write(
                    f"🏆 Récord: "
                    f"{current_stats.get(away, {}).get('wins', 0)}-"
                    f"{current_stats.get(away, {}).get('losses', 0)}"
                )

                st.write(
                    f"📈 Win %: "
                    f"{away_metrics['win_pct']*100:.1f}%"
                )

                st.write(
                    f"🔥 Puntos/partido: "
                    f"{away_metrics['ppg']:.1f}"
                )

                st.write(
                    f"🛡️ Permitidos/partido: "
                    f"{away_metrics['papg']:.1f}"
                )

                st.write(
                    f"📊 Diferencial: "
                    f"{away_metrics['point_diff']:+.1f}"
                )

                st.write(
                    f"🏅 Elo: "
                    f"{away_metrics['elo']:.0f}"
                )

                st.write(
                    f"🔥 Forma últimos 5: "
                    f"{away_metrics['recent_win_pct']*100:.1f}%"
                )

            st.write(
                f"📈 Diferencia Elo: "
                f"{prediction['elo_difference']:+.0f}"
            )

        # ----------------------------------------------------
        # EXPLICACIÓN
        # ----------------------------------------------------

        with st.expander(
            "🧠 ¿Cómo calcula la probabilidad?"
        ):

            st.write(
                "Nuestro modelo combina diferentes "
                "señales estadísticas independientes:"
            )

            st.write(
                "• 🏅 Elo: 45%\n"
                "• 📈 Récord / Win %: 20%\n"
                "• 📊 Diferencial de puntos: 18%\n"
                "• 🔥 Forma reciente: 7%\n"
                "• 🔥 Ataque: 5%\n"
                "• 🛡️ Defensa: 5%\n"
                "• 🏠 Ventaja de localía"
            )

            st.write(
                "❌ No utiliza cuotas."
            )

            st.write(
                "❌ No utiliza probabilidades de sportsbooks."
            )

            st.write(
                "❌ No utiliza DraftKings."
            )

            st.write(
                "❌ No utiliza BetMGM."
            )

            st.write(
                "❌ No copia probabilidades externas."
            )

        st.markdown(
            "</div>",
            unsafe_allow_html=True
        )


# ============================================================
# INFORMACIÓN FINAL
# ============================================================

st.divider()

st.subheader(
    "🧠 Información del modelo"
)

st.write(
    "📅 Base histórica: temporada regular NFL 2025."
)

st.write(
    f"🏈 Equipos analizados: "
    f"{len(current_stats)}"
)

st.write(
    f"📊 Partidos históricos: "
    f"{len(historical_games)}"
)

st.write(
    "🧪 El backtest utiliza únicamente la "
    "información disponible antes de cada partido."
)

st.write(
    "🚫 El modelo no utiliza cuotas de sportsbooks."
)

st.caption(
    "La probabilidad es una estimación estadística "
    "y no garantiza el resultado de un partido."
)

st.caption(
    "IMPORTANTE: primero debemos validar el modelo "
    "con el backtest antes de utilizar porcentajes "
    "altos como criterio de apuesta."
)
