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

    .team {
        font-size: 23px;
        font-weight: 700;
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
# FUNCIONES
# ============================================================

@st.cache_data(ttl=3600)
def load_2025_games():
    """
    Carga los partidos históricos de NFL.
    Usamos únicamente 2025 para construir la fuerza de cada equipo.
    """

    df = pd.read_csv(NFLVERSE_GAMES)

    # Normalizamos nombres
    df.columns = [c.lower().strip() for c in df.columns]

    # Detectar columnas comunes
    home_col = None
    away_col = None
    score_home_col = None
    score_away_col = None

    possible_home = ["team_home", "home_team", "home"]
    possible_away = ["team_away", "away_team", "away"]
    possible_score_home = ["score_home", "home_score", "points_home"]
    possible_score_away = ["score_away", "away_score", "points_away"]

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
            "No se encontraron las columnas necesarias en games.csv"
        )

    # Temporada 2025
    if "season" in df.columns:
        df = df[df["season"] == 2025].copy()

    # Solo temporada regular
    if "game_type" in df.columns:
        df = df[
            df["game_type"].astype(str).str.lower().isin(
                ["reg", "regular"]
            )
        ].copy()

    df = df.dropna(
        subset=[
            home_col,
            away_col,
            score_home_col,
            score_away_col
        ]
    ).copy()

    df["home"] = df[home_col].astype(str)
    df["away"] = df[away_col].astype(str)
    df["home_score"] = pd.to_numeric(
        df[score_home_col],
        errors="coerce"
    )
    df["away_score"] = pd.to_numeric(
        df[score_away_col],
        errors="coerce"
    )

    df = df.dropna(
        subset=["home_score", "away_score"]
    )

    return df


def build_team_stats(games):
    """
    Construye estadísticas independientes de cada equipo.
    """

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

        games_n = max(x["games"], 1)

        win_pct = x["wins"] / games_n

        ppg = x["points_for"] / games_n

        papg = x["points_against"] / games_n

        point_diff = ppg - papg

        home_win_pct = (
            x["home_wins"] / x["home_games"]
            if x["home_games"] > 0
            else 0.5
        )

        away_win_pct = (
            x["away_wins"] / x["away_games"]
            if x["away_games"] > 0
            else 0.5
        )

        stats[team] = {
            **x,
            "win_pct": win_pct,
            "ppg": ppg,
            "papg": papg,
            "point_diff": point_diff,
            "home_win_pct": home_win_pct,
            "away_win_pct": away_win_pct,
        }

    return stats


@st.cache_data(ttl=300)
def get_today_games():
    """
    Obtiene exclusivamente los partidos de HOY
    usando la fecha local de Dallas.
    """

    dallas = ZoneInfo("America/Chicago")
    today = datetime.now(dallas).strftime("%Y%m%d")

    params = {
        "dates": today,
        "limit": 100
    }

    response = requests.get(
        ESPN_SCOREBOARD,
        params=params,
        timeout=15
    )

    response.raise_for_status()

    data = response.json()

    games = []

    for event in data.get("events", []):

        competitions = event.get("competitions", [])

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

        for c in competitors:

            team = c.get("team", {})
            abbr = team.get("abbreviation")

            if c.get("homeAway") == "home":
                home = abbr

            elif c.get("homeAway") == "away":
                away = abbr

        if not home or not away:
            continue

        status = event.get("status", {}).get(
            "type", {}
        ).get("description", "")

        games.append({
            "id": event.get("id"),
            "name": event.get("name", ""),
            "home": home,
            "away": away,
            "status": status,
            "date": event.get("date", "")
        })

    return games


def normalize_team(abbr):
    """
    Normaliza algunas abreviaciones.
    """

    replacements = {
        "JAC": "JAX",
        "LA": "LAR",
    }

    return replacements.get(abbr, abbr)


def zscore(value, mean, std):
    if std == 0 or pd.isna(std):
        return 0

    return (value - mean) / std


def calculate_team_strength(team, stats):
    """
    FUERZA PROPIA DEL MODELO.

    IMPORTANTE:
    NO utiliza cuotas.
    NO utiliza probabilidades de sportsbooks.
    """

    if team not in stats:
        return None

    s = stats[team]

    all_stats = list(stats.values())

    win_values = [x["win_pct"] for x in all_stats]
    diff_values = [x["point_diff"] for x in all_stats]
    ppg_values = [x["ppg"] for x in all_stats]
    papg_values = [x["papg"] for x in all_stats]

    strength = (
        0.35 * zscore(
            s["win_pct"],
            np.mean(win_values),
            np.std(win_values)
        )
        +
        0.35 * zscore(
            s["point_diff"],
            np.mean(diff_values),
            np.std(diff_values)
        )
        +
        0.15 * zscore(
            s["ppg"],
            np.mean(ppg_values),
            np.std(ppg_values)
        )
        -
        0.15 * zscore(
            s["papg"],
            np.mean(papg_values),
            np.std(papg_values)
        )
    )

    return strength


def calculate_probability(home, away, stats):
    """
    Calcula nuestra probabilidad.

    No mira ninguna casa de apuestas.
    """

    home = normalize_team(home)
    away = normalize_team(away)

    home_strength = calculate_team_strength(
        home,
        stats
    )

    away_strength = calculate_team_strength(
        away,
        stats
    )

    if home_strength is None or away_strength is None:
        return None

    # Ventaja de localía.
    home_advantage = 0.18

    difference = (
        home_strength
        - away_strength
        + home_advantage
    )

    # Transformación logística.
    probability_home = (
        1 /
        (
            1 +
            math.exp(
                -1.35 * difference
            )
        )
    )

    # Evitamos extremos irreales.
    probability_home = max(
        0.05,
        min(0.95, probability_home)
    )

    probability_away = 1 - probability_home

    return {
        "home_probability": probability_home,
        "away_probability": probability_away,
        "home_strength": home_strength,
        "away_strength": away_strength
    }


def classification(probability):
    """
    Clasificación de nuestra probabilidad.
    """

    if probability >= 0.65:
        return "🟢 PROBABILIDAD ALTA", "high"

    elif probability >= 0.55:
        return "🟡 PROBABILIDAD MEDIA", "medium"

    else:
        return "⚪ PROBABILIDAD BAJA", "low"


def fmt_pct(x):
    return f"{x * 100:.1f}%"


def team_display(team):
    return TEAM_NAMES.get(
        team,
        team
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
    'Modelo propio — partidos de HOY solamente'
    '</div>',
    unsafe_allow_html=True
)

st.info(
    "Este modelo NO utiliza cuotas ni probabilidades "
    "de ninguna casa de apuestas."
)

# ============================================================
# CARGA DE DATOS
# ============================================================

try:

    historical_games = load_2025_games()

    team_stats = build_team_stats(
        historical_games
    )

except Exception as e:

    st.error(
        "No se pudieron cargar los datos históricos de 2025."
    )

    st.code(str(e))

    st.stop()


# ============================================================
# PARTIDOS DE HOY
# ============================================================

st.subheader("🔎 NFL DE HOY")

if st.button(
    "🔄 ACTUALIZAR PARTIDOS DE HOY",
    use_container_width=True
):

    st.cache_data.clear()
    st.rerun()


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

    st.caption(
        "El modelo solo muestra partidos cuya fecha "
        "local corresponde exactamente a HOY en Dallas."
    )

else:

    st.success(
        f"{len(today_games)} partido(s) encontrados para hoy."
    )

    # ========================================================
    # CALCULAMOS TODOS LOS PARTIDOS
    # ========================================================

    predictions = []

    for game in today_games:

        home = normalize_team(game["home"])
        away = normalize_team(game["away"])

        prediction = calculate_probability(
            home,
            away,
            team_stats
        )

        if prediction is None:
            continue

        hp = prediction["home_probability"]
        ap = prediction["away_probability"]

        if hp >= ap:

            favorite = home
            favorite_probability = hp

        else:

            favorite = away
            favorite_probability = ap

        label, css_class = classification(
            favorite_probability
        )

        predictions.append({
            "game": game,
            "prediction": prediction,
            "favorite": favorite,
            "favorite_probability":
                favorite_probability,
            "label": label,
            "css": css_class
        })

    # Ordenar por nuestra propia probabilidad
    predictions.sort(
        key=lambda x: x["favorite_probability"],
        reverse=True
    )

    # ========================================================
    # MOSTRAR
    # ========================================================

    for index, item in enumerate(
        predictions,
        start=1
    ):

        game = item["game"]
        prediction = item["prediction"]

        home = normalize_team(game["home"])
        away = normalize_team(game["away"])

        hp = prediction["home_probability"]
        ap = prediction["away_probability"]

        label = item["label"]
        css_class = item["css"]

        # Hora
        game_time = ""

        try:

            dt = datetime.fromisoformat(
                game["date"].replace(
                    "Z",
                    "+00:00"
                )
            )

            dt_dallas = dt.astimezone(
                ZoneInfo("America/Chicago")
            )

            game_time = dt_dallas.strftime(
                "%I:%M %p"
            ).lstrip("0")

        except Exception:

            game_time = "Hora no disponible"

        # ====================================================
        # TARJETA
        # ====================================================

        st.markdown(
            '<div class="game-card">',
            unsafe_allow_html=True
        )

        st.markdown(
            f"### #{index} 🏈 "
            f"{team_display(item['favorite'])}"
        )

        st.write(
            f"**{team_display(away)}** vs "
            f"**{team_display(home)}**"
        )

        st.markdown(
            f"🕐 **HOY — {game_time}**"
        )

        st.markdown(
            f'<div class="{css_class}">'
            f'{label}'
            f'</div>',
            unsafe_allow_html=True
        )

        # ====================================================
        # PROBABILIDADES
        # ====================================================

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

        # ====================================================
        # DATOS DEL MODELO
        # ====================================================

        st.markdown(
            "#### 📊 Datos utilizados por nuestro modelo"
        )

        home_stats = team_stats.get(home)
        away_stats = team_stats.get(away)

        if home_stats and away_stats:

            c1, c2 = st.columns(2)

            with c1:

                st.markdown(
                    f"**{team_display(home)}**"
                )

                st.markdown(
                    f"🏆 Récord: "
                    f"{home_stats['wins']}-"
                    f"{home_stats['losses']}"
                )

                st.markdown(
                    f"📈 Win %: "
                    f"{home_stats['win_pct']*100:.1f}%"
                )

                st.markdown(
                    f"🔥 Puntos/partido: "
                    f"{home_stats['ppg']:.1f}"
                )

                st.markdown(
                    f"🛡️ Permitidos/partido: "
                    f"{home_stats['papg']:.1f}"
                )

                st.markdown(
                    f"📊 Diferencial: "
                    f"{home_stats['point_diff']:+.1f}"
                )

            with c2:

                st.markdown(
                    f"**{team_display(away)}**"
                )

                st.markdown(
                    f"🏆 Récord: "
                    f"{away_stats['wins']}-"
                    f"{away_stats['losses']}"
                )

                st.markdown(
                    f"📈 Win %: "
                    f"{away_stats['win_pct']*100:.1f}%"
                )

                st.markdown(
                    f"🔥 Puntos/partido: "
                    f"{away_stats['ppg']:.1f}"
                )

                st.markdown(
                    f"🛡️ Permitidos/partido: "
                    f"{away_stats['papg']:.1f}"
                )

                st.markdown(
                    f"📊 Diferencial: "
                    f"{away_stats['point_diff']:+.1f}"
                )

        # ====================================================
        # EXPLICACIÓN
        # ====================================================

        with st.expander(
            "📚 ¿Cómo calculamos esta probabilidad?"
        ):

            st.write(
                "La probabilidad es generada por nuestro "
                "modelo independiente."
            )

            st.write(
                "La versión actual utiliza:"
            )

            st.write(
                "• Récord 2025\n"
                "• Porcentaje de victorias\n"
                "• Puntos anotados por partido\n"
                "• Puntos permitidos por partido\n"
                "• Diferencial de puntos\n"
                "• Ventaja de jugar como local"
            )

            st.write(
                "❌ NO utiliza cuotas."
            )

            st.write(
                "❌ NO utiliza probabilidades de sportsbooks."
            )

            st.write(
                "❌ NO utiliza DraftKings."
            )

            st.write(
                "❌ NO utiliza BetMGM."
            )

            st.write(
                "❌ NO copia la probabilidad que aparece "
                "en otra página."
            )

        st.markdown(
            "</div>",
            unsafe_allow_html=True
        )


# ============================================================
# INFORMACIÓN DEL MODELO
# ============================================================

st.divider()

st.subheader("🧠 Modelo")

st.write(
    "Base histórica: temporada regular NFL 2025."
)

st.write(
    f"Equipos analizados: {len(team_stats)}"
)

st.write(
    f"Partidos históricos utilizados: "
    f"{len(historical_games)}"
)

st.caption(
    "La probabilidad es una estimación estadística, "
    "no una garantía del resultado."
)

st.caption(
    "El modelo actual está diseñado como una primera "
    "versión independiente. El siguiente paso será "
    "validarlo con un backtest de 2025 antes de "
    "utilizarlo como criterio de apuesta."
)
