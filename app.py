import streamlit as st
import requests
import pandas as pd
import math
from datetime import datetime, timedelta, timezone

# ============================================================
# NFL EDGE
# Modelo independiente del mercado
# Histórico máximo: 2025 + 2026 disponible
# ============================================================

st.set_page_config(
    page_title="NFL EDGE",
    page_icon="🏈",
    layout="wide"
)

# ------------------------------------------------------------
# CONFIGURACIÓN
# ------------------------------------------------------------

BASE_URL = "https://site.api.espn.com/apis/site/v2/sports/football/nfl"

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

TIMEOUT = 15


# ------------------------------------------------------------
# FUNCIONES GENERALES
# ------------------------------------------------------------

@st.cache_data(ttl=900)
def get_json(url, params=None):
    try:
        r = requests.get(
            url,
            params=params,
            headers=HEADERS,
            timeout=TIMEOUT
        )

        if r.status_code != 200:
            return None

        return r.json()

    except Exception:
        return None


def safe_float(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return default


def clamp(value, low, high):
    return max(low, min(high, value))


# ------------------------------------------------------------
# FECHA ACTUAL
# ------------------------------------------------------------

today = datetime.now().date()

today_str = today.strftime("%Y%m%d")


# ------------------------------------------------------------
# OBTENER PARTIDOS DEL DÍA
# ------------------------------------------------------------

@st.cache_data(ttl=300)
def get_games_for_date(date_string):

    url = f"{BASE_URL}/scoreboard"

    data = get_json(
        url,
        params={
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

                info = {
                    "id": team.get("team", {}).get("id"),
                    "name": team.get("team", {}).get("displayName"),
                    "abbreviation": team.get("team", {}).get("abbreviation"),
                    "score": safe_float(team.get("score", 0)),
                    "home": team.get("homeAway") == "home",
                    "winner": team.get("winner", False)
                }

                if info["home"]:
                    home = info
                else:
                    away = info

            if not home or not away:
                continue

            status = (
                event.get("status", {})
                .get("type", {})
                .get("name", "")
            )

            games.append({
                "id": event.get("id"),
                "name": event.get("name", ""),
                "date": event.get("date"),
                "status": status,
                "home": home,
                "away": away
            })

        except Exception:
            continue

    return games


# ------------------------------------------------------------
# OBTENER RESULTADOS HISTÓRICOS
# ------------------------------------------------------------

@st.cache_data(ttl=3600)
def get_season_games(year):

    games = []

    start = datetime(year, 9, 1).date()
    end = datetime(year + 1, 2, 20).date()

    current = start

    while current <= end:

        date_string = current.strftime("%Y%m%d")

        daily = get_games_for_date(date_string)

        for game in daily:

            # Solo partidos terminados
            if game["status"] in [
                "STATUS_FINAL",
                "STATUS_FINAL_OT"
            ]:

                games.append({
                    "date": current.isoformat(),
                    "home_id": game["home"]["id"],
                    "home_name": game["home"]["name"],
                    "home_abbr": game["home"]["abbreviation"],
                    "home_score": game["home"]["score"],
                    "away_id": game["away"]["id"],
                    "away_name": game["away"]["name"],
                    "away_abbr": game["away"]["abbreviation"],
                    "away_score": game["away"]["score"]
                })

        current += timedelta(days=1)

    return games


# ------------------------------------------------------------
# CONSTRUIR ESTADÍSTICAS DE EQUIPOS
# ------------------------------------------------------------

def build_team_stats(games):

    teams = {}

    def create_team(team_id, name, abbr):

        if team_id not in teams:

            teams[team_id] = {
                "id": team_id,
                "name": name,
                "abbr": abbr,

                "games": 0,
                "wins": 0,
                "losses": 0,

                "points_for": 0.0,
                "points_against": 0.0,

                "home_games": 0,
                "home_wins": 0,

                "recent_results": [],

                "recent_points_for": [],
                "recent_points_against": []
            }

    for game in games:

        home_id = game["home_id"]
        away_id = game["away_id"]

        create_team(
            home_id,
            game["home_name"],
            game["home_abbr"]
        )

        create_team(
            away_id,
            game["away_name"],
            game["away_abbr"]
        )

        hs = game["home_score"]
        aas = game["away_score"]

        # HOME
        home = teams[home_id]

        home["games"] += 1
        home["points_for"] += hs
        home["points_against"] += aas

        home["home_games"] += 1

        if hs > aas:
            home["wins"] += 1
            home["home_wins"] += 1
            home["recent_results"].append(1)
        else:
            home["losses"] += 1
            home["recent_results"].append(0)

        home["recent_points_for"].append(hs)
        home["recent_points_against"].append(aas)

        # AWAY
        away = teams[away_id]

        away["games"] += 1
        away["points_for"] += aas
        away["points_against"] += hs

        if aas > hs:
            away["wins"] += 1
            away["recent_results"].append(1)
        else:
            away["losses"] += 1
            away["recent_results"].append(0)

        away["recent_points_for"].append(aas)
        away["recent_points_against"].append(hs)

    # Calcular métricas finales
    for team in teams.values():

        games_count = max(team["games"], 1)

        team["win_rate"] = team["wins"] / games_count

        team["ppg"] = team["points_for"] / games_count

        team["papg"] = team["points_against"] / games_count

        team["point_diff"] = (
            team["points_for"] -
            team["points_against"]
        ) / games_count

        recent = team["recent_results"][-5:]

        if recent:
            team["recent_win_rate"] = sum(recent) / len(recent)
        else:
            team["recent_win_rate"] = team["win_rate"]

        recent_pf = team["recent_points_for"][-5:]
        recent_pa = team["recent_points_against"][-5:]

        if recent_pf:
            team["recent_ppg"] = sum(recent_pf) / len(recent_pf)
        else:
            team["recent_ppg"] = team["ppg"]

        if recent_pa:
            team["recent_papg"] = sum(recent_pa) / len(recent_pa)
        else:
            team["recent_papg"] = team["papg"]

        team["recent_diff"] = (
            team["recent_ppg"] -
            team["recent_papg"]
        )

    return teams


# ------------------------------------------------------------
# LESIONES
# ------------------------------------------------------------

@st.cache_data(ttl=1800)
def get_team_injuries(team_id):

    url = f"{BASE_URL}/teams/{team_id}/injuries"

    data = get_json(url)

    if not data:
        return []

    injuries = []

    try:
        items = data.get("items", [])

        for item in items:

            athlete = item.get("athlete", {})

            status = (
                item.get("status")
                or item.get("type")
                or ""
            )

            name = athlete.get("displayName", "")

            injuries.append({
                "name": name,
                "status": str(status)
            })

    except Exception:
        return []

    return injuries


def injury_score(team_id):

    injuries = get_team_injuries(team_id)

    if not injuries:
        return 0.0

    score = 0.0

    for injury in injuries:

        status = injury["status"].lower()

        if (
            "out" in status
            or "ir" in status
            or "injured reserve" in status
        ):
            score += 1.0

        elif (
            "doubtful" in status
            or "questionable" in status
        ):
            score += 0.35

    return min(score, 4.0)


# ------------------------------------------------------------
# FUERZA DEL EQUIPO
# ------------------------------------------------------------

def team_strength(team):

    # Componentes independientes del mercado
    win_component = team["win_rate"]

    recent_component = team["recent_win_rate"]

    offense_component = (
        clamp(team["ppg"] / 30.0, 0.0, 1.0)
    )

    defense_component = (
        1.0 -
        clamp(team["papg"] / 30.0, 0.0, 1.0)
    )

    differential_component = (
        0.5 +
        clamp(team["point_diff"] / 30.0, -0.5, 0.5)
    )

    recent_diff_component = (
        0.5 +
        clamp(team["recent_diff"] / 30.0, -0.5, 0.5)
    )

    strength = (
        0.25 * win_component
        + 0.20 * recent_component
        + 0.15 * offense_component
        + 0.15 * defense_component
        + 0.15 * differential_component
        + 0.10 * recent_diff_component
    )

    return strength


# ------------------------------------------------------------
# PROBABILIDAD
# ------------------------------------------------------------

def calculate_probability(
    home_team,
    away_team
):

    home_strength = team_strength(home_team)
    away_strength = team_strength(away_team)

    # Diferencia de fuerza
    difference = home_strength - away_strength

    # Ventaja de local
    home_advantage = 0.035

    # Lesiones
    home_injuries = injury_score(home_team["id"])
    away_injuries = injury_score(away_team["id"])

    injury_difference = (
        away_injuries -
        home_injuries
    )

    # Convertimos la diferencia a una escala razonable
    raw_score = (
        difference
        + home_advantage
        + injury_difference * 0.018
    )

    # Función logística
    probability_home = (
        1.0 /
        (
            1.0 +
            math.exp(-7.0 * raw_score)
        )
    )

    # Evitar números absurdamente extremos
    probability_home = clamp(
        probability_home,
        0.05,
        0.95
    )

    probability_away = 1.0 - probability_home

    return (
        probability_home,
        probability_away,
        home_injuries,
        away_injuries
    )


# ------------------------------------------------------------
# CARGAR HISTÓRICO
# ------------------------------------------------------------

@st.cache_data(ttl=3600)
def load_historical_data():

    all_games = []

    # 2025
    games_2025 = get_season_games(2025)

    all_games.extend(games_2025)

    # Resultados disponibles de 2026
    games_2026 = get_season_games(2026)

    all_games.extend(games_2026)

    return all_games


# ------------------------------------------------------------
# INTERFAZ
# ------------------------------------------------------------

st.title("🏈 NFL EDGE")

st.subheader("Modelo independiente del mercado")

st.write(
    "Probabilidad estimada utilizando únicamente información deportiva."
)

st.warning(
    "🚫 Las cuotas de sportsbooks NO se utilizan para generar las probabilidades."
)

st.caption(
    "Histórico utilizado: 2025 + resultados disponibles de 2026."
)

st.divider()


# ------------------------------------------------------------
# PARTIDOS DE HOY
# ------------------------------------------------------------

st.header("🏈 PARTIDOS DE HOY")

games_today = get_games_for_date(today_str)


# Si no hay partidos
if not games_today:

    st.info(
        "No se encontraron partidos NFL para hoy."
    )

    st.caption(
        "La aplicación consulta automáticamente el calendario NFL."
    )

else:

    # --------------------------------------------------------
    # HISTÓRICO
    # --------------------------------------------------------

    with st.spinner("Analizando datos NFL..."):

        historical_games = load_historical_data()

        teams = build_team_stats(
            historical_games
        )

    # --------------------------------------------------------
    # MOSTRAR PARTIDOS
    # --------------------------------------------------------

    for game in games_today:

        home_id = game["home"]["id"]
        away_id = game["away"]["id"]

        if (
            home_id not in teams
            or away_id not in teams
        ):
            continue

        home_team = teams[home_id]
        away_team = teams[away_id]

        (
            home_prob,
            away_prob,
            home_injuries,
            away_injuries
        ) = calculate_probability(
            home_team,
            away_team
        )

        home_pct = round(
            home_prob * 100,
            1
        )

        away_pct = round(
            away_prob * 100,
            1
        )

        # Elegir pick
        if home_pct >= away_pct:

            pick = home_team["abbr"]
            pick_probability = home_pct

        else:

            pick = away_team["abbr"]
            pick_probability = away_pct

        # ----------------------------------------------------
        # TARJETA DEL PARTIDO
        # ----------------------------------------------------

        st.markdown("---")

        st.subheader(
            f"🏈 {away_team['abbr']} @ {home_team['abbr']}"
        )

        col1, col2 = st.columns(2)

        with col1:

            st.metric(
                f"{away_team['abbr']} — Probabilidad",
                f"{away_pct}%"
            )

            st.caption(
                f"Récord histórico utilizado: "
                f"{away_team['wins']}-{away_team['losses']}"
            )

        with col2:

            st.metric(
                f"{home_team['abbr']} — Probabilidad",
                f"{home_pct}%"
            )

            st.caption(
                f"Récord histórico utilizado: "
                f"{home_team['wins']}-{home_team['losses']}"
            )

        st.success(
            f"🎯 PICK DEL MODELO: {pick} — "
            f"{pick_probability}%"
        )

        # ----------------------------------------------------
        # INFORMACIÓN ADICIONAL
        # ----------------------------------------------------

        with st.expander("📊 ¿Qué tomó en cuenta el modelo?"):

            st.write(
                "• Rendimiento histórico"
            )

            st.write(
                "• Rendimiento reciente"
            )

            st.write(
                "• Puntos anotados"
            )

            st.write(
                "• Puntos permitidos"
            )

            st.write(
                "• Diferencial de puntos"
            )

            st.write(
                "• Ventaja de jugar como local"
            )

            st.write(
                "• Información de lesiones disponible"
            )

            st.write(
                f"🏥 Lesiones detectadas "
                f"{away_team['abbr']}: "
                f"{home_injuries if False else away_injuries}"
            )

            st.write(
                f"🏥 Lesiones detectadas "
                f"{home_team['abbr']}: "
                f"{home_injuries}"
            )

        st.caption(
            "La probabilidad es una estimación estadística, "
            "no una garantía del resultado."
        )


# ------------------------------------------------------------
# EXPLICACIÓN SIMPLE
# ------------------------------------------------------------

st.divider()

with st.expander("🧠 ¿Cómo interpretar el porcentaje?"):

    st.write(
        "Si el modelo muestra 70%, significa que según "
        "la información utilizada por el modelo, ese resultado "
        "tiene una probabilidad estimada cercana al 70%."
    )

    st.write(
        "NO significa que el equipo vaya a ganar con certeza."
    )

    st.write(
        "La idea es que tú compares este porcentaje "
        "con la cuota que ofrece la sportsbook y decidas "
        "si existe una diferencia suficientemente interesante."
    )


st.caption(
    "NFL EDGE — Modelo experimental independiente del mercado. "
    "No garantiza resultados."
)
