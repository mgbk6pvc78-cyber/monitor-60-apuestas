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
    page_title="Monitor NFL",
    page_icon="🏈",
    layout="wide"
)


# ============================================================
# ESTILO
# ============================================================

st.markdown("""
<style>

.block-container {
    max-width: 1150px;
    padding-top: 2rem;
    padding-bottom: 4rem;
}

.title {
    font-size: 44px;
    font-weight: 800;
}

.subtitle {
    font-size: 20px;
    color: #9ca3af;
    margin-bottom: 25px;
}

.card {
    background: #171922;
    border: 1px solid #30333d;
    border-radius: 18px;
    padding: 24px;
    margin-bottom: 20px;
}

.blue-card {
    background: #192c43;
    border: 1px solid #294b70;
    border-radius: 18px;
    padding: 22px;
    margin-bottom: 20px;
}

.green-card {
    background: #193426;
    border: 1px solid #356b4c;
    border-radius: 18px;
    padding: 22px;
    margin-bottom: 20px;
}

.yellow-card {
    background: #40371d;
    border: 1px solid #6c5c2a;
    border-radius: 18px;
    padding: 22px;
    margin-bottom: 20px;
}

.high {
    background: #163c29;
    border-radius: 14px;
    padding: 14px;
    color: #69e69a;
    font-size: 20px;
    font-weight: 800;
    margin: 12px 0;
}

.medium {
    background: #40351b;
    border-radius: 14px;
    padding: 14px;
    color: #ffd45c;
    font-size: 20px;
    font-weight: 800;
    margin: 12px 0;
}

.low {
    background: #302f2f;
    border-radius: 14px;
    padding: 14px;
    color: #c9c9c9;
    font-size: 20px;
    font-weight: 800;
    margin: 12px 0;
}

.prob {
    font-size: 38px;
    font-weight: 800;
}

</style>
""", unsafe_allow_html=True)


# ============================================================
# FUENTES
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
# EQUIPOS
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
    "WAS": "Washington Commanders"
}


# ============================================================
# NORMALIZAR EQUIPO
# ============================================================

def normalize_team(team):

    if team is None:
        return None

    team = str(team).upper().strip()

    replacements = {
        "JAC": "JAX",
        "WSH": "WAS",
        "LA": "LAR"
    }

    return replacements.get(
        team,
        team
    )


def team_name(team):

    team = normalize_team(team)

    return TEAM_NAMES.get(
        team,
        team
    )


# ============================================================
# CARGAR DATOS NFL
# ============================================================

@st.cache_data(ttl=3600)
def load_all_games():

    df = pd.read_csv(
        NFLVERSE_GAMES
    )

    df.columns = [
        str(c).lower().strip()
        for c in df.columns
    ]

    rename = {}

    if "gameday" in df.columns:
        rename["gameday"] = "date"

    if "away_team" in df.columns:
        rename["away_team"] = "away"

    if "home_team" in df.columns:
        rename["home_team"] = "home"

    df = df.rename(
        columns=rename
    )

    required = [
        "season",
        "game_type",
        "date",
        "away",
        "home",
        "away_score",
        "home_score"
    ]

    missing = [
        x for x in required
        if x not in df.columns
    ]

    if missing:

        raise ValueError(
            "Faltan columnas: "
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

    df = df.dropna(
        subset=[
            "date",
            "away",
            "home",
            "away_score",
            "home_score"
        ]
    )

    return (
        df
        .sort_values("date")
        .reset_index(drop=True)
    )


# ============================================================
# CREAR ESTADÍSTICAS
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

        home_score = float(
            row["home_score"]
        )

        away_score = float(
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
                "away_wins": 0
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
                "away_wins": 0
            }

        # -------------------------
        # LOCAL
        # -------------------------

        teams[home]["games"] += 1
        teams[home]["home_games"] += 1

        teams[home]["points_for"] += home_score
        teams[home]["points_against"] += away_score

        if home_score > away_score:

            teams[home]["wins"] += 1
            teams[home]["home_wins"] += 1

        elif home_score < away_score:

            teams[home]["losses"] += 1

        else:

            teams[home]["ties"] += 1

        # -------------------------
        # VISITANTE
        # -------------------------

        teams[away]["games"] += 1
        teams[away]["away_games"] += 1

        teams[away]["points_for"] += away_score
        teams[away]["points_against"] += home_score

        if away_score > home_score:

            teams[away]["wins"] += 1
            teams[away]["away_wins"] += 1

        elif away_score < home_score:

            teams[away]["losses"] += 1

        else:

            teams[away]["ties"] += 1

    # -------------------------
    # MÉTRICAS
    # -------------------------

    stats = {}

    for team, x in teams.items():

        games_n = max(
            x["games"],
            1
        )

        win_pct = (
            x["wins"] / games_n
        )

        ppg = (
            x["points_for"] / games_n
        )

        papg = (
            x["points_against"] / games_n
        )

        point_diff = (
            ppg - papg
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
                away_win_pct
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
# PROBABILIDAD DEL MODELO
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

    # Ventaja de localía
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
            probability_away
    }


# ============================================================
# VALIDACIÓN MULTI-TEMPORADA
# ============================================================

@st.cache_data(ttl=3600)
def run_multiseason_validation():

    games = load_all_games()

    # Solo temporadas 2023-2025
    games = games[
        games["season"].isin(
            [2023, 2024, 2025]
        )
    ].copy()

    games = games[
        games["game_type"]
        .astype(str)
        .str.upper()
        == "REG"
    ].copy()

    games = (
        games
        .sort_values("date")
        .reset_index(drop=True)
    )

    past_games = []

    predictions = []

    for _, game in games.iterrows():

        home = normalize_team(
            game["home"]
        )

        away = normalize_team(
            game["away"]
        )

        # Necesitamos historial suficiente
        if len(past_games) >= 10:

            past_df = pd.DataFrame(
                past_games
            )

            stats = build_team_stats(
                past_df
            )

            prediction = calculate_probability(
                home,
                away,
                stats
            )

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

                else:

                    pick = away
                    probability = ap

                home_score = float(
                    game["home_score"]
                )

                away_score = float(
                    game["away_score"]
                )

                if home_score > away_score:

                    winner = home

                elif away_score > home_score:

                    winner = away

                else:

                    winner = "TIE"

                if winner == "TIE":

                    correct = None

                else:

                    correct = (
                        pick == winner
                    )

                predictions.append({

                    "season":
                        int(game["season"]),

                    "date":
                        game["date"],

                    "home":
                        home,

                    "away":
                        away,

                    "pick":
                        pick,

                    "probability":
                        probability,

                    "winner":
                        winner,

                    "correct":
                        correct
                })

        # IMPORTANTE:
        # Agregamos el partido DESPUÉS
        # de hacer la predicción.
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
                game["away_score"]
        })

    return pd.DataFrame(
        predictions
    )


# ============================================================
# TABLA POR NIVEL
# ============================================================

def analyze_levels(
    predictions
):

    levels = [
        0.55,
        0.60,
        0.65,
        0.70,
        0.75,
        0.80,
        0.85,
        0.90
    ]

    rows = []

    clean = predictions[
        predictions["correct"].notna()
    ].copy()

    for level in levels:

        group = clean[
            clean["probability"] >= level
        ]

        total = len(
            group
        )

        wins = int(
            group["correct"].sum()
        )

        rate = (

            wins / total

            if total > 0

            else 0
        )

        # Diferencia entre la probabilidad
        # media que decía el modelo y el
        # resultado real.
        avg_model = (

            group["probability"].mean()

            if total > 0

            else 0
        )

        calibration_error = (
            rate - avg_model
            if total > 0
            else 0
        )

        rows.append({

            "Probabilidad mínima":
                f"{level * 100:.0f}%",

            "Partidos":
                total,

            "Aciertos":
                wins,

            "Acierto real":
                f"{rate * 100:.1f}%",

            "Prob. promedio modelo":
                f"{avg_model * 100:.1f}%",

            "Diferencia":
                f"{calibration_error * 100:+.1f}%"
        })

    return pd.DataFrame(
        rows
    )


# ============================================================
# CALIBRACIÓN POR RANGOS
# ============================================================

def calibration_table(
    predictions
):

    clean = predictions[
        predictions["correct"].notna()
    ].copy()

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
        0.951
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

    clean["rango"] = pd.cut(
        clean["probability"],
        bins=bins,
        labels=labels,
        right=False
    )

    rows = []

    for label in labels:

        group = clean[
            clean["rango"] == label
        ]

        total = len(
            group
        )

        if total == 0:

            continue

        wins = int(
            group["correct"].sum()
        )

        real = (
            wins / total
        )

        model_average = (
            group["probability"].mean()
        )

        difference = (
            real - model_average
        )

        rows.append({

            "Rango del modelo":
                label,

            "Partidos":
                total,

            "Aciertos":
                wins,

            "Probabilidad modelo":
                f"{model_average * 100:.1f}%",

            "Resultado real":
                f"{real * 100:.1f}%",

            "Corrección":
                f"{difference * 100:+.1f}%"
        })

    return pd.DataFrame(
        rows
    )


# ============================================================
# CALIBRACIÓN POR TEMPORADA
# ============================================================

def season_table(
    predictions
):

    clean = predictions[
        predictions["correct"].notna()
    ].copy()

    rows = []

    for season in sorted(
        clean["season"].unique()
    ):

        group = clean[
            clean["season"] == season
        ]

        total = len(
            group
        )

        wins = int(
            group["correct"].sum()
        )

        rate = (
            wins / total
            if total > 0
            else 0
        )

        avg_probability = (
            group["probability"].mean()
            if total > 0
            else 0
        )

        rows.append({

            "Temporada":
                int(season),

            "Partidos":
                total,

            "Aciertos":
                wins,

            "Acierto real":
                f"{rate * 100:.1f}%",

            "Prob. promedio modelo":
                f"{avg_probability * 100:.1f}%",

            "Diferencia":
                f"{(rate - avg_probability) * 100:+.1f}%"
        })

    return pd.DataFrame(
        rows
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

        competitors = (
            competitions[0]
            .get(
                "competitors",
                []
            )
        )

        home = None
        away = None

        for competitor in competitors:

            abbreviation = (
                competitor
                .get("team", {})
                .get("abbreviation")
            )

            if competitor.get(
                "homeAway"
            ) == "home":

                home = normalize_team(
                    abbreviation
                )

            elif competitor.get(
                "homeAway"
            ) == "away":

                away = normalize_team(
                    abbreviation
                )

        if not home or not away:
            continue

        games.append({

            "id":
                event.get("id"),

            "date":
                event.get("date"),

            "home":
                home,

            "away":
                away
        })

    return games


# ============================================================
# CLASIFICACIÓN
# ============================================================

def classification(
    probability
):

    if probability >= 0.75:

        return (
            "🟢 CONFIANZA ALTA",
            "high"
        )

    if probability >= 0.60:

        return (
            "🟡 CONFIANZA MEDIA",
            "medium"
        )

    return (
        "⚪ CONFIANZA BAJA",
        "low"
    )


# ============================================================
# ENCABEZADO
# ============================================================

st.markdown(
    '<div class="title">🏈 Monitor NFL</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtitle">'
    'Modelo propio — probabilidad independiente'
    '</div>',
    unsafe_allow_html=True
)

st.markdown("""
<div class="blue-card">
🧠 El modelo NO utiliza cuotas ni probabilidades de
sportsbooks para generar sus probabilidades.
</div>
""", unsafe_allow_html=True)


# ============================================================
# TABS
# ============================================================

tab1, tab2, tab3 = st.tabs([
    "🏈 NFL DE HOY",
    "🧪 VALIDACIÓN Y CALIBRACIÓN",
    "📊 INFORMACIÓN"
])


# ============================================================
# TAB 1
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

    try:

        all_games = load_all_games()

        # Para las predicciones actuales
        # usamos hasta el final de 2025.
        historical = all_games[
            (
                all_games["season"] <= 2025
            )
            &
            (
                all_games["game_type"]
                .astype(str)
                .str.upper()
                == "REG"
            )
        ].copy()

        historical = (
            historical
            .sort_values("date")
            .reset_index(drop=True)
        )

        stats = build_team_stats(
            historical
        )

    except Exception as e:

        st.error(
            "No se pudieron cargar los datos históricos."
        )

        st.exception(e)

        st.stop()

    try:

        today_games = get_today_games()

    except Exception as e:

        st.error(
            "No se pudo obtener el calendario de hoy."
        )

        st.exception(e)

        today_games = []

    if not today_games:

        st.warning(
            "No hay partidos NFL detectados para hoy."
        )

    else:

        st.success(
            f"{len(today_games)} partido(s) encontrados."
        )

        predictions = []

        for game in today_games:

            prediction = calculate_probability(
                game["home"],
                game["away"],
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

                pick = game["home"]
                probability = hp

            else:

                pick = game["away"]
                probability = ap

            label, css = classification(
                probability
            )

            predictions.append({

                "game":
                    game,

                "prediction":
                    prediction,

                "pick":
                    pick,

                "probability":
                    probability,

                "label":
                    label,

                "css":
                    css
            })

        predictions.sort(
            key=lambda x:
            x["probability"],
            reverse=True
        )

        for number, item in enumerate(
            predictions,
            start=1
        ):

            game = item["game"]
            prediction = item["prediction"]

            hp = prediction[
                "home_probability"
            ]

            ap = prediction[
                "away_probability"
            ]

            game_time = "Hora no disponible"

            try:

                dt = datetime.fromisoformat(
                    game["date"]
                    .replace(
                        "Z",
                        "+00:00"
                    )
                )

                dt = dt.astimezone(
                    ZoneInfo(
                        "America/Chicago"
                    )
                )

                game_time = (
                    dt.strftime(
                        "%I:%M %p"
                    )
                    .lstrip("0")
                )

            except:
                pass

            st.markdown(
                '<div class="card">',
                unsafe_allow_html=True
            )

            st.markdown(
                f"## #{number} 🏈 "
                f"{team_name(item['pick'])}"
            )

            st.write(
                f"**{team_name(game['away'])}** "
                f"vs "
                f"**{team_name(game['home'])}**"
            )

            st.write(
                f"🕐 HOY — **{game_time}**"
            )

            st.markdown(
                f'<div class="{item["css"]}">'
                f'{item["label"]}'
                f'</div>',
                unsafe_allow_html=True
            )

            c1, c2 = st.columns(2)

            with c1:

                st.markdown(
                    f"### 🏠 {team_name(game['home'])}"
                )

                st.markdown(
                    f'<div class="prob">'
                    f'{hp * 100:.1f}%'
                    f'</div>',
                    unsafe_allow_html=True
                )

            with c2:

                st.markdown(
                    f"### ✈️ {team_name(game['away'])}"
                )

                st.markdown(
                    f'<div class="prob">'
                    f'{ap * 100:.1f}%'
                    f'</div>',
                    unsafe_allow_html=True
                )

            st.write(
                f"**Pick:** "
                f"{team_name(item['pick'])}"
            )

            st.write(
                f"**Probabilidad del modelo:** "
                f"{item['probability'] * 100:.1f}%"
            )

            st.caption(
                "Probabilidad calculada por nuestro "
                "modelo, sin utilizar cuotas."
            )

            st.markdown(
                "</div>",
                unsafe_allow_html=True
            )


# ============================================================
# TAB 2
# ============================================================

with tab2:

    st.header(
        "🧪 Validación y calibración"
    )

    st.write(
        "Vamos a comprobar si el modelo funciona "
        "de manera consistente en 2023, 2024 y 2025."
    )

    st.info(
        "Cada partido se predice usando únicamente "
        "información disponible ANTES de ese partido. "
        "Esto evita data leakage."
    )

    if st.button(
        "🚀 EJECUTAR VALIDACIÓN 2023–2025",
        use_container_width=True
    ):

        with st.spinner(
            "Analizando 3 temporadas partido por partido..."
        ):

            try:

                predictions = (
                    run_multiseason_validation()
                )

                clean = predictions[
                    predictions["correct"].notna()
                ].copy()

                if clean.empty:

                    st.warning(
                        "No se generaron resultados."
                    )

                    st.stop()

                # ==================================================
                # GENERAL
                # ==================================================

                total = len(
                    clean
                )

                wins = int(
                    clean["correct"].sum()
                )

                overall = (
                    wins / total
                )

                st.subheader(
                    "🏆 RESULTADO GENERAL"
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
                        wins
                    )

                with c3:

                    st.metric(
                        "Acierto",
                        f"{overall * 100:.1f}%"
                    )

                # ==================================================
                # POR TEMPORADA
                # ==================================================

                st.subheader(
                    "📅 Consistencia por temporada"
                )

                seasons = season_table(
                    predictions
                )

                st.dataframe(
                    seasons,
                    use_container_width=True,
                    hide_index=True
                )

                # ==================================================
                # NIVELES
                # ==================================================

                st.subheader(
                    "🎯 Probabilidad mínima vs realidad"
                )

                levels = analyze_levels(
                    predictions
                )

                st.dataframe(
                    levels,
                    use_container_width=True,
                    hide_index=True
                )

                st.markdown("""
                <div class="green-card">
                🧠 Lo importante aquí es comprobar si cuando
                nuestro modelo aumenta su confianza también
                aumenta el porcentaje real de aciertos.
                </div>
                """, unsafe_allow_html=True)

                # ==================================================
                # CALIBRACIÓN
                # ==================================================

                st.subheader(
                    "🎯 CALIBRACIÓN DEL MODELO"
                )

                st.write(
                    "Esta es la parte más importante. "
                    "Comparamos la probabilidad que decía "
                    "el modelo contra lo que realmente ocurrió."
                )

                calibration = calibration_table(
                    predictions
                )

                st.dataframe(
                    calibration,
                    use_container_width=True,
                    hide_index=True
                )

                st.markdown("""
                <div class="yellow-card">
                💡 Si el modelo dice 80%, pero históricamente
                esos partidos solo ganan 72%, el modelo está
                sobreestimando la probabilidad. La columna
                <b>Corrección</b> nos muestra cuánto.
                </div>
                """, unsafe_allow_html=True)

                # ==================================================
                # EJEMPLO DE INTERPRETACIÓN
                # ==================================================

                st.subheader(
                    "🧠 Cómo vamos a utilizar esto"
                )

                st.write(
                    "Ejemplo hipotético:"
                )

                st.write(
                    "Modelo: **88%**"
                )

                st.write(
                    "Históricamente esa zona: **78%**"
                )

                st.write(
                    "Entonces nuestra probabilidad corregida "
                    "sería aproximadamente **78%**, no 88%."
                )

                st.write(
                    "Esa probabilidad corregida es la que "
                    "posteriormente podremos comparar con "
                    "la probabilidad implícita de la casa."
                )

                # ==================================================
                # DATOS COMPLETOS
                # ==================================================

                with st.expander(
                    "📋 Ver todas las predicciones"
                ):

                    detail = predictions.copy()

                    detail["probability"] = (
                        detail["probability"]
                        * 100
                    ).round(1)

                    detail["home"] = (
                        detail["home"]
                        .map(team_name)
                    )

                    detail["away"] = (
                        detail["away"]
                        .map(team_name)
                    )

                    detail["pick"] = (
                        detail["pick"]
                        .map(team_name)
                    )

                    detail["correct"] = (
                        detail["correct"]
                        .map({
                            True: "✅",
                            False: "❌",
                            None: "➖"
                        })
                    )

                    detail = detail[
                        [
                            "season",
                            "date",
                            "away",
                            "home",
                            "pick",
                            "probability",
                            "winner",
                            "correct"
                        ]
                    ]

                    detail.columns = [
                        "Temporada",
                        "Fecha",
                        "Visitante",
                        "Local",
                        "Pick",
                        "Probabilidad %",
                        "Ganador",
                        "Resultado"
                    ]

                    st.dataframe(
                        detail,
                        use_container_width=True,
                        hide_index=True
                    )

                # ==================================================
                # DESCARGA
                # ==================================================

                csv = predictions.to_csv(
                    index=False
                )

                st.download_button(
                    "📥 DESCARGAR RESULTADOS",
                    data=csv,
                    file_name=(
                        "validacion_nfl_2023_2025.csv"
                    ),
                    mime="text/csv",
                    use_container_width=True
                )

            except Exception as e:

                st.error(
                    "❌ Ocurrió un error durante "
                    "la validación."
                )

                st.exception(e)


# ============================================================
# TAB 3
# ============================================================

with tab3:

    st.header(
        "📊 Información del modelo"
    )

    st.write(
        "El modelo utiliza estadísticas históricas "
        "de los equipos."
    )

    st.write(
        "Variables principales:"
    )

    st.write(
        "• Porcentaje de victorias\n"
        "• Puntos anotados\n"
        "• Puntos permitidos\n"
        "• Diferencial de puntos\n"
        "• Rendimiento como local\n"
        "• Rendimiento como visitante\n"
        "• Ventaja de localía"
    )

    st.divider()

    st.subheader(
        "🚫 No utilizamos"
    )

    st.write(
        "❌ DraftKings"
    )

    st.write(
        "❌ FanDuel"
    )

    st.write(
        "❌ BetMGM"
    )

    st.write(
        "❌ Caesars"
    )

    st.write(
        "❌ Moneylines"
    )

    st.write(
        "❌ Cuotas"
    )

    st.write(
        "❌ Probabilidades de sportsbooks"
    )

    st.divider()

    try:

        games = load_all_games()

        regular = games[
            games["game_type"]
            .astype(str)
            .str.upper()
            == "REG"
        ]

        st.write(
            f"Partidos disponibles: "
            f"**{len(regular)}**"
        )

        st.write(
            f"Temporadas disponibles: "
            f"**{int(regular['season'].min())} "
            f"– "
            f"{int(regular['season'].max())}**"
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
    "⚠️ Herramienta experimental de análisis estadístico. "
    "Las probabilidades históricas no garantizan resultados futuros."
)
