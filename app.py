import streamlit as st
import requests
import math
from datetime import datetime
from zoneinfo import ZoneInfo

# ============================================================
# NFL EDGE
# Modelo independiente del mercado
#
# HISTÓRICO:
#   2025 + 2026 disponible
#
# IMPORTANTE:
#   Las cuotas NO se utilizan para calcular probabilidades.
#
# DATOS UTILIZADOS:
#   - resultados
#   - rendimiento
#   - puntos anotados
#   - puntos permitidos
#   - diferencial
#   - forma reciente
#   - local/visitante
#   - lesiones disponibles en ESPN
#
# ============================================================

st.set_page_config(
    page_title="NFL EDGE",
    page_icon="🏈",
    layout="centered"
)

BASE_URL = (
    "https://site.api.espn.com/"
    "apis/site/v2/sports/football/nfl"
)

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

TIMEOUT = 15


# ============================================================
# FUNCIONES BÁSICAS
# ============================================================

@st.cache_data(ttl=900)
def get_json(url, params=None):

    try:
        response = requests.get(
            url,
            params=params,
            headers=HEADERS,
            timeout=TIMEOUT
        )

        if response.status_code != 200:
            return None

        return response.json()

    except Exception:
        return None


def safe_float(value, default=0.0):

    try:
        return float(value)
    except Exception:
        return default


def clamp(value, minimum, maximum):

    return max(
        minimum,
        min(maximum, value)
    )


# ============================================================
# FECHA LOCAL
# Dallas / Central Time
# ============================================================

local_now = datetime.now(
    ZoneInfo("America/Chicago")
)

today = local_now.date()

today_string = today.strftime("%Y%m%d")


# ============================================================
# NOMBRE DEL TIPO DE TEMPORADA
# ESPN:
#
# 1 = PRESEASON
# 2 = REGULAR
# 3 = POSTSEASON
# ============================================================

def season_type_name(season_type):

    if season_type == 1:
        return "Pretemporada"

    if season_type == 2:
        return "Temporada regular"

    if season_type == 3:
        return "Playoffs"

    return "NFL"


# ============================================================
# PARTIDOS DE UNA FECHA
# ============================================================

@st.cache_data(ttl=300)
def get_games_for_date(date_string):

    url = f"{BASE_URL}/scoreboard"

    all_games = []

    # Probamos los 3 tipos de competición.
    for season_type in [1, 2, 3]:

        data = get_json(
            url,
            params={
                "dates": date_string,
                "seasontype": season_type,
                "limit": 100
            }
        )

        if not data:
            continue

        for event in data.get("events", []):

            try:

                competition = (
                    event
                    .get("competitions", [])[0]
                )

                competitors = (
                    competition
                    .get("competitors", [])
                )

                home = None
                away = None

                for competitor in competitors:

                    team_data = competitor.get(
                        "team",
                        {}
                    )

                    team = {
                        "id": team_data.get("id"),
                        "name": team_data.get(
                            "displayName",
                            "Unknown"
                        ),
                        "abbr": team_data.get(
                            "abbreviation",
                            "UNK"
                        ),
                        "home": (
                            competitor.get(
                                "homeAway"
                            ) == "home"
                        ),
                        "score": safe_float(
                            competitor.get(
                                "score",
                                0
                            )
                        ),
                        "winner": competitor.get(
                            "winner",
                            False
                        )
                    }

                    if team["home"]:
                        home = team
                    else:
                        away = team

                if not home or not away:
                    continue

                status = (
                    event
                    .get("status", {})
                    .get("type", {})
                    .get("name", "")
                )

                # Evitar duplicados
                event_id = event.get("id")

                already_exists = any(
                    g["id"] == event_id
                    for g in all_games
                )

                if already_exists:
                    continue

                all_games.append(
                    {
                        "id": event_id,
                        "date": event.get(
                            "date",
                            ""
                        ),
                        "name": event.get(
                            "name",
                            ""
                        ),
                        "season_type": season_type,
                        "season_name":
                            season_type_name(
                                season_type
                            ),
                        "status": status,
                        "home": home,
                        "away": away
                    }
                )

            except Exception:
                continue

    # Ordenar por hora
    all_games.sort(
        key=lambda x: x.get(
            "date",
            ""
        )
    )

    return all_games


# ============================================================
# HISTÓRICO DE UNA TEMPORADA
#
# Usamos semanas, no cientos de fechas.
# Esto hace la aplicación mucho más rápida.
# ============================================================

@st.cache_data(ttl=3600)
def get_season_games(
    year,
    season_type,
    max_weeks
):

    games = []

    for week in range(
        1,
        max_weeks + 1
    ):

        url = f"{BASE_URL}/scoreboard"

        data = get_json(
            url,
            params={
                "year": year,
                "seasontype": season_type,
                "week": week,
                "limit": 100
            }
        )

        if not data:
            continue

        for event in data.get(
            "events",
            []
        ):

            try:

                competition = (
                    event
                    .get(
                        "competitions",
                        []
                    )[0]
                )

                competitors = (
                    competition
                    .get(
                        "competitors",
                        []
                    )
                )

                home = None
                away = None

                for competitor in competitors:

                    team = competitor.get(
                        "team",
                        {}
                    )

                    item = {
                        "id": team.get(
                            "id"
                        ),
                        "name": team.get(
                            "displayName",
                            ""
                        ),
                        "abbr": team.get(
                            "abbreviation",
                            ""
                        ),
                        "home":
                            competitor.get(
                                "homeAway"
                            ) == "home",
                        "score":
                            safe_float(
                                competitor.get(
                                    "score",
                                    0
                                )
                            )
                    }

                    if item["home"]:
                        home = item
                    else:
                        away = item

                if not home or not away:
                    continue

                status = (
                    event
                    .get("status", {})
                    .get("type", {})
                    .get("name", "")
                )

                # Solamente partidos terminados
                if status not in [
                    "STATUS_FINAL",
                    "STATUS_FINAL_OT"
                ]:
                    continue

                games.append(
                    {
                        "id":
                            event.get(
                                "id"
                            ),
                        "date":
                            event.get(
                                "date",
                                ""
                            ),
                        "home": home,
                        "away": away
                    }
                )

            except Exception:
                continue

    # Quitar duplicados
    unique = {}

    for game in games:

        unique[
            game["id"]
        ] = game

    return list(
        unique.values()
    )


# ============================================================
# CARGAR HISTÓRICO
#
# 2025:
#   temporada regular
#
# 2026:
#   todo lo disponible hasta ahora:
#   pretemporada + regular + playoffs
# ============================================================

@st.cache_data(ttl=3600)
def load_history():

    history = []

    # --------------------------------------------------------
    # 2025 REGULAR
    # --------------------------------------------------------

    history.extend(
        get_season_games(
            2025,
            2,
            18
        )
    )

    # --------------------------------------------------------
    # 2025 PLAYOFFS
    # --------------------------------------------------------

    history.extend(
        get_season_games(
            2025,
            3,
            5
        )
    )

    # --------------------------------------------------------
    # 2026 PRESEASON
    # --------------------------------------------------------

    history.extend(
        get_season_games(
            2026,
            1,
            3
        )
    )

    # --------------------------------------------------------
    # 2026 REGULAR
    #
    # Todavía no hay partidos en agosto,
    # pero dejamos la estructura preparada.
    # --------------------------------------------------------

    history.extend(
        get_season_games(
            2026,
            2,
            18
        )
    )

    # --------------------------------------------------------
    # 2026 PLAYOFFS
    # --------------------------------------------------------

    history.extend(
        get_season_games(
            2026,
            3,
            5
        )
    )

    # Eliminar duplicados
    unique = {}

    for game in history:

        unique[
            game["id"]
        ] = game

    return list(
        unique.values()
    )


# ============================================================
# ESTADÍSTICAS DE EQUIPOS
# ============================================================

def create_team():

    return {
        "games": 0,
        "wins": 0,
        "losses": 0,

        "points_for": 0.0,
        "points_against": 0.0,

        "home_games": 0,
        "home_wins": 0,

        "results": [],
        "points_for_recent": [],
        "points_against_recent": []
    }


def build_team_stats(
    games
):

    teams = {}

    for game in games:

        home = game["home"]
        away = game["away"]

        home_id = home["id"]
        away_id = away["id"]

        if home_id not in teams:

            teams[home_id] = {
                "id": home_id,
                "name": home["name"],
                "abbr": home["abbr"],
                **create_team()
            }

        if away_id not in teams:

            teams[away_id] = {
                "id": away_id,
                "name": away["name"],
                "abbr": away["abbr"],
                **create_team()
            }

        home_stats = teams[home_id]
        away_stats = teams[away_id]

        home_score = home["score"]
        away_score = away["score"]

        # HOME
        home_stats["games"] += 1

        home_stats["points_for"] += (
            home_score
        )

        home_stats["points_against"] += (
            away_score
        )

        home_stats["home_games"] += 1

        if home_score > away_score:

            home_stats["wins"] += 1
            home_stats["home_wins"] += 1
            home_stats["results"].append(1)

        else:

            home_stats["losses"] += 1
            home_stats["results"].append(0)

        home_stats[
            "points_for_recent"
        ].append(home_score)

        home_stats[
            "points_against_recent"
        ].append(away_score)

        # AWAY
        away_stats["games"] += 1

        away_stats["points_for"] += (
            away_score
        )

        away_stats["points_against"] += (
            home_score
        )

        if away_score > home_score:

            away_stats["wins"] += 1
            away_stats["results"].append(1)

        else:

            away_stats["losses"] += 1
            away_stats["results"].append(0)

        away_stats[
            "points_for_recent"
        ].append(away_score)

        away_stats[
            "points_against_recent"
        ].append(home_score)

    # Métricas
    for team in teams.values():

        games_count = max(
            team["games"],
            1
        )

        team["win_rate"] = (
            team["wins"] /
            games_count
        )

        team["ppg"] = (
            team["points_for"] /
            games_count
        )

        team["papg"] = (
            team["points_against"] /
            games_count
        )

        team["point_diff"] = (
            team["ppg"] -
            team["papg"]
        )

        recent_results = (
            team["results"][-5:]
        )

        if recent_results:

            team["recent_win_rate"] = (
                sum(recent_results) /
                len(recent_results)
            )

        else:

            team["recent_win_rate"] = (
                team["win_rate"]
            )

        recent_pf = (
            team[
                "points_for_recent"
            ][-5:]
        )

        recent_pa = (
            team[
                "points_against_recent"
            ][-5:]
        )

        if recent_pf:

            team["recent_ppg"] = (
                sum(recent_pf) /
                len(recent_pf)
            )

        else:

            team["recent_ppg"] = (
                team["ppg"]
            )

        if recent_pa:

            team["recent_papg"] = (
                sum(recent_pa) /
                len(recent_pa)
            )

        else:

            team["recent_papg"] = (
                team["papg"]
            )

        team["recent_diff"] = (
            team["recent_ppg"] -
            team["recent_papg"]
        )

    return teams


# ============================================================
# LESIONES ESPN
# ============================================================

@st.cache_data(ttl=1800)
def get_injuries(
    team_id
):

    url = (
        f"{BASE_URL}/teams/"
        f"{team_id}/injuries"
    )

    data = get_json(url)

    if not data:
        return []

    injuries = []

    for item in data.get(
        "items",
        []
    ):

        athlete = item.get(
            "athlete",
            {}
        )

        name = athlete.get(
            "displayName",
            ""
        )

        status = str(
            item.get(
                "status",
                ""
            )
        )

        injuries.append(
            {
                "name": name,
                "status": status
            }
        )

    return injuries


def injury_impact(
    team_id
):

    injuries = get_injuries(
        team_id
    )

    impact = 0.0

    for injury in injuries:

        status = (
            injury["status"]
            .lower()
        )

        if (
            "out" in status
            or "ir" in status
            or "injured reserve"
            in status
        ):

            impact += 1.0

        elif (
            "doubtful" in status
        ):

            impact += 0.60

        elif (
            "questionable"
            in status
        ):

            impact += 0.25

    return min(
        impact,
        5.0
    )


# ============================================================
# FUERZA DEL EQUIPO
# ============================================================

def calculate_strength(
    team
):

    # Si hay pocos partidos históricos,
    # reducimos la confianza.

    games = team["games"]

    sample_factor = clamp(
        games / 17.0,
        0.25,
        1.0
    )

    win_component = (
        team["win_rate"]
    )

    recent_component = (
        team["recent_win_rate"]
    )

    offense_component = clamp(
        team["ppg"] / 30.0,
        0.0,
        1.0
    )

    defense_component = (
        1.0 -
        clamp(
            team["papg"] / 30.0,
            0.0,
            1.0
        )
    )

    differential_component = (
        0.5 +
        clamp(
            team["point_diff"] / 30.0,
            -0.5,
            0.5
        )
    )

    recent_diff_component = (
        0.5 +
        clamp(
            team["recent_diff"] / 30.0,
            -0.5,
            0.5
        )
    )

    strength = (

        0.25 *
        win_component

        +

        0.20 *
        recent_component

        +

        0.15 *
        offense_component

        +

        0.15 *
        defense_component

        +

        0.15 *
        differential_component

        +

        0.10 *
        recent_diff_component
    )

    # Acercar equipos con poca información
    # hacia el promedio de la liga.

    league_average = 0.50

    strength = (
        league_average
        +
        (
            strength -
            league_average
        )
        * sample_factor
    )

    return strength


# ============================================================
# PROBABILIDAD
# ============================================================

def calculate_probability(
    home_team,
    away_team,
    season_type
):

    home_strength = (
        calculate_strength(
            home_team
        )
    )

    away_strength = (
        calculate_strength(
            away_team
        )
    )

    difference = (
        home_strength -
        away_strength
    )

    # Ventaja de local
    home_advantage = 0.035

    # Lesiones
    home_injuries = (
        injury_impact(
            home_team["id"]
        )
    )

    away_injuries = (
        injury_impact(
            away_team["id"]
        )
    )

    injury_difference = (
        away_injuries -
        home_injuries
    )

    # En pretemporada reducimos la influencia
    # de las estadísticas normales porque
    # los titulares pueden jugar menos.

    if season_type == 1:

        home_advantage *= 0.50

        injury_weight = 0.008

    else:

        injury_weight = 0.018

    raw_score = (

        difference

        +

        home_advantage

        +

        (
            injury_difference *
            injury_weight
        )
    )

    probability_home = (
        1.0 /
        (
            1.0 +
            math.exp(
                -7.0 *
                raw_score
            )
        )
    )

    # No permitimos 99% o 1%.
    probability_home = clamp(
        probability_home,
        0.10,
        0.90
    )

    probability_away = (
        1.0 -
        probability_home
    )

    return (
        probability_home,
        probability_away,
        home_injuries,
        away_injuries
    )


# ============================================================
# CONFIANZA
# ============================================================

def confidence_level(
    probability,
    home_team,
    away_team,
    season_type
):

    difference = abs(
        probability - 0.50
    )

    sample = min(
        (
            home_team["games"] +
            away_team["games"]
        ) / 34.0,
        1.0
    )

    confidence_score = (
        difference * 2.0
        + sample * 0.5
    )

    if season_type == 1:

        confidence_score *= 0.55

    if confidence_score >= 0.70:

        return "ALTA"

    if confidence_score >= 0.45:

        return "MEDIA"

    return "BAJA"


# ============================================================
# INTERFAZ
# ============================================================

st.title("🏈 NFL EDGE")

st.subheader(
    "Modelo independiente del mercado"
)

st.write(
    "Probabilidad estimada utilizando "
    "información deportiva, sin utilizar "
    "las cuotas de las sportsbooks."
)

st.warning(
    "🚫 Las cuotas NO se utilizan para "
    "generar las probabilidades."
)

st.caption(
    "Histórico máximo utilizado: "
    "2025 + 2026 disponible."
)

st.divider()


# ============================================================
# PARTIDOS DE HOY
# ============================================================

st.header(
    "🏈 PARTIDOS DE HOY"
)

games_today = get_games_for_date(
    today_string
)

if not games_today:

    st.info(
        "No se encontraron partidos NFL "
        "para hoy."
    )

    st.caption(
        "La aplicación consulta "
        "pretemporada, temporada regular "
        "y playoffs."
    )

else:

    # --------------------------------------------------------
    # HISTÓRICO
    # --------------------------------------------------------

    with st.spinner(
        "Analizando NFL..."
    ):

        historical_games = (
            load_history()
        )

        teams = build_team_stats(
            historical_games
        )

    # --------------------------------------------------------
    # PARTIDOS
    # --------------------------------------------------------

    for game in games_today:

        home_id = (
            game["home"]["id"]
        )

        away_id = (
            game["away"]["id"]
        )

        # Si un equipo no tiene suficiente
        # información, igual mostramos el partido.

        if home_id not in teams:

            teams[home_id] = {
                "id": home_id,
                "name":
                    game["home"]["name"],
                "abbr":
                    game["home"]["abbr"],
                **create_team()
            }

        if away_id not in teams:

            teams[away_id] = {
                "id": away_id,
                "name":
                    game["away"]["name"],
                "abbr":
                    game["away"]["abbr"],
                **create_team()
            }

        home_team = teams[
            home_id
        ]

        away_team = teams[
            away_id
        ]

        (
            home_probability,
            away_probability,
            home_injuries,
            away_injuries
        ) = calculate_probability(
            home_team,
            away_team,
            game["season_type"]
        )

        home_pct = round(
            home_probability * 100,
            1
        )

        away_pct = round(
            away_probability * 100,
            1
        )

        # Pick
        if home_pct >= away_pct:

            pick = home_team["abbr"]

            pick_probability = (
                home_pct
            )

            pick_team = home_team

        else:

            pick = away_team["abbr"]

            pick_probability = (
                away_pct
            )

            pick_team = away_team

        confidence = (
            confidence_level(
                (
                    max(
                        home_probability,
                        away_probability
                    )
                ),
                home_team,
                away_team,
                game["season_type"]
            )
        )

        # ----------------------------------------------------
        # PARTIDO
        # ----------------------------------------------------

        st.divider()

        st.subheader(
            f"🏈 "
            f"{away_team['abbr']} "
            f"@ "
            f"{home_team['abbr']}"
        )

        st.caption(
            game["season_name"]
        )

        col1, col2 = st.columns(
            2
        )

        with col1:

            st.metric(
                away_team["abbr"],
                f"{away_pct}%"
            )

        with col2:

            st.metric(
                home_team["abbr"],
                f"{home_pct}%"
            )

        st.success(
            f"🎯 PICK DEL MODELO: "
            f"{pick} — "
            f"{pick_probability}%"
        )

        st.write(
            f"Nivel de confianza: "
            f"**{confidence}**"
        )

        # ----------------------------------------------------
        # DATOS UTILIZADOS
        # ----------------------------------------------------

        with st.expander(
            "🧠 Ver qué tomó en cuenta"
        ):

            st.write(
                "• Rendimiento histórico"
            )

            st.write(
                "• Forma reciente"
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
                "• Ventaja de local"
            )

            st.write(
                "• Lesiones disponibles"
            )

            st.write(
                f"🏥 Impacto lesiones "
                f"{away_team['abbr']}: "
                f"{away_injuries:.2f}"
            )

            st.write(
                f"🏥 Impacto lesiones "
                f"{home_team['abbr']}: "
                f"{home_injuries:.2f}"
            )

            st.write(
                f"📊 Partidos utilizados "
                f"{away_team['abbr']}: "
                f"{away_team['games']}"
            )

            st.write(
                f"📊 Partidos utilizados "
                f"{home_team['abbr']}: "
                f"{home_team['games']}"
            )

        # ----------------------------------------------------
        # AVISO PRETEMPORADA
        # ----------------------------------------------------

        if game["season_type"] == 1:

            st.warning(
                "⚠️ PRETEMPORADA: la confianza "
                "se reduce porque la cantidad "
                "de minutos de los titulares "
                "y las alineaciones pueden variar."
            )

        st.caption(
            "La probabilidad es una estimación "
            "del modelo y NO una garantía."
        )


# ============================================================
# EXPLICACIÓN
# ============================================================

st.divider()

with st.expander(
    "🧠 ¿Cómo usar el porcentaje?"
):

    st.write(
        "El modelo primero genera su propia "
        "probabilidad utilizando datos deportivos."
    )

    st.write(
        "Después tú puedes comparar ese "
        "porcentaje con la cuota que te "
        "ofrezca tu sportsbook."
    )

    st.write(
        "Ejemplo: si el modelo dice 68%, "
        "eso NO significa que sea una apuesta "
        "segura. Significa que esa es la "
        "estimación independiente del modelo."
    )

    st.write(
        "La decisión de apostar o no queda "
        "separada del modelo."
    )


st.caption(
    "NFL EDGE — Modelo experimental "
    "independiente del mercado."
)
