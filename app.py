import streamlit as st
import requests
import math
from datetime import datetime, timezone, timedelta

# ============================================================
# NFL EDGE
# Modelo independiente del mercado
#
# HISTORICO:
#   2025 + 2026 disponible
#
# IMPORTANTE:
#   Las cuotas de sportsbooks NO se utilizan para generar
#   la probabilidad del modelo.
# ============================================================

st.set_page_config(
    page_title="NFL EDGE",
    page_icon="🏈",
    layout="wide"
)

# ============================================================
# CONFIGURACION
# ============================================================

ESPN_SCOREBOARD = (
    "https://site.api.espn.com/apis/site/v2/sports/"
    "football/nfl/scoreboard"
)

ESPN_TEAM_SCHEDULE = (
    "https://site.api.espn.com/apis/site/v2/sports/"
    "football/nfl/teams/{team}/schedule"
)

ESPN_INJURIES = (
    "https://site.api.espn.com/apis/site/v2/sports/"
    "football/nfl/injuries"
)

HEADERS = {
    "User-Agent": "Mozilla/5.0 NFL-EDGE"
}

CURRENT_SEASON = 2026
HISTORICAL_SEASON = 2025

# Dallas / Texas
DALLAS_TZ = timezone(timedelta(hours=-5))

# ============================================================
# EQUIPOS
# ============================================================

TEAMS = {
    "ARI": "arizona",
    "ATL": "atlanta",
    "BAL": "baltimore",
    "BUF": "buffalo",
    "CAR": "carolina",
    "CHI": "chicago",
    "CIN": "cincinnati",
    "CLE": "cleveland",
    "DAL": "dallas",
    "DEN": "denver",
    "DET": "detroit",
    "GB": "green-bay",
    "HOU": "houston",
    "IND": "indianapolis",
    "JAX": "jacksonville",
    "KC": "kansas-city",
    "LAC": "los-angeles-chargers",
    "LAR": "los-angeles-rams",
    "LV": "las-vegas",
    "MIA": "miami",
    "MIN": "minnesota",
    "NE": "new-england",
    "NO": "new-orleans",
    "NYG": "new-york-giants",
    "NYJ": "new-york-jets",
    "PHI": "philadelphia",
    "PIT": "pittsburgh",
    "SEA": "seattle",
    "SF": "san-francisco",
    "TB": "tampa-bay",
    "TEN": "tennessee",
    "WAS": "washington",
}

# ============================================================
# FUNCIONES GENERALES
# ============================================================

def get_json(url, params=None, timeout=15):
    try:
        r = requests.get(
            url,
            params=params,
            headers=HEADERS,
            timeout=timeout
        )

        if r.status_code != 200:
            return None

        return r.json()

    except Exception:
        return None


def sigmoid(x):
    return 1 / (1 + math.exp(-x))


# ============================================================
# FECHA ACTUAL
# ============================================================

def today_dallas():
    return datetime.now(DALLAS_TZ).strftime("%Y%m%d")


# ============================================================
# PARTIDOS DEL DIA
# ============================================================

@st.cache_data(ttl=300)
def get_today_games():
    """
    Obtiene los partidos directamente de ESPN.

    Incluye:
    - preseason
    - regular season
    - playoffs
    """

    date_string = today_dallas()

    data = get_json(
        ESPN_SCOREBOARD,
        params={
            "dates": date_string,
            "limit": 100,
            "region": "us",
            "lang": "en"
        }
    )

    if not data:
        return []

    games = []

    for event in data.get("events", []):

        try:
            competition = event["competitions"][0]
            competitors = competition["competitors"]

            if len(competitors) != 2:
                continue

            home = None
            away = None

            for team in competitors:

                team_data = team.get("team", {})

                abbreviation = team_data.get("abbreviation")

                if team.get("homeAway") == "home":
                    home = {
                        "abbr": abbreviation,
                        "name": team_data.get("displayName", abbreviation)
                    }

                elif team.get("homeAway") == "away":
                    away = {
                        "abbr": abbreviation,
                        "name": team_data.get("displayName", abbreviation)
                    }

            if not home or not away:
                continue

            season_type = (
                event
                .get("season", {})
                .get("slug", "")
                .lower()
            )

            # ESPN puede usar diferentes nombres.
            # No filtramos preseason: queremos verla.
            if "pre" in season_type:
                phase = "PRETEMPORADA"
            elif "post" in season_type:
                phase = "PLAYOFFS"
            else:
                phase = "TEMPORADA REGULAR"

            games.append({
                "id": event.get("id"),
                "name": event.get("name"),
                "date": event.get("date"),
                "away": away["abbr"],
                "away_name": away["name"],
                "home": home["abbr"],
                "home_name": home["name"],
                "phase": phase,
                "status": event.get("status", {})
            })

        except Exception:
            continue

    return games


# ============================================================
# HISTORICO DE UN EQUIPO
# ============================================================

@st.cache_data(ttl=3600)
def get_team_schedule(team_abbr, season):

    if team_abbr not in TEAMS:
        return []

    url = ESPN_TEAM_SCHEDULE.format(
        team=TEAMS[team_abbr]
    )

    data = get_json(
        url,
        params={
            "season": season,
            "seasontype": 2
        }
    )

    if not data:
        return []

    games = []

    for event in data.get("events", []):

        try:

            competition = event["competitions"][0]

            if competition.get("status", {}).get(
                "type", {}
            ).get("completed") is not True:
                continue

            competitors = competition.get("competitors", [])

            our_team = None
            opponent = None

            for c in competitors:

                abbr = (
                    c.get("team", {})
                    .get("abbreviation")
                )

                if abbr == team_abbr:
                    our_team = c
                else:
                    opponent = c

            if not our_team or not opponent:
                continue

            our_score = float(
                our_team.get("score", 0)
            )

            opp_score = float(
                opponent.get("score", 0)
            )

            home_away = our_team.get("homeAway")

            if home_away == "home":
                home = True
            else:
                home = False

            result = "W" if our_score > opp_score else (
                "L" if our_score < opp_score else "T"
            )

            games.append({
                "date": event.get("date"),
                "team": team_abbr,
                "opponent": (
                    opponent
                    .get("team", {})
                    .get("abbreviation")
                ),
                "team_score": our_score,
                "opp_score": opp_score,
                "margin": our_score - opp_score,
                "home": home,
                "result": result
            })

        except Exception:
            continue

    return games


# ============================================================
# CONSTRUIR BASE HISTORICA
# ============================================================

@st.cache_data(ttl=3600)
def build_historical_data():

    all_games = []

    for season in [HISTORICAL_SEASON, CURRENT_SEASON]:

        for team in TEAMS.keys():

            games = get_team_schedule(
                team,
                season
            )

            all_games.extend(games)

    return all_games


# ============================================================
# ESTADISTICAS DEL EQUIPO
# ============================================================

def team_stats(team, historical):

    games = [
        g for g in historical
        if g["team"] == team
    ]

    if not games:

        return {
            "games": 0,
            "wins": 0,
            "losses": 0,
            "win_pct": 0.50,
            "margin": 0.0,
            "recent_margin": 0.0,
            "recent_win_pct": 0.50
        }

    wins = sum(
        1 for g in games
        if g["result"] == "W"
    )

    losses = sum(
        1 for g in games
        if g["result"] == "L"
    )

    win_pct = wins / len(games)

    avg_margin = sum(
        g["margin"] for g in games
    ) / len(games)

    # Ordenar cronologicamente
    games_sorted = sorted(
        games,
        key=lambda x: x.get("date", "")
    )

    recent = games_sorted[-8:]

    recent_margin = sum(
        g["margin"] for g in recent
    ) / len(recent)

    recent_wins = sum(
        1 for g in recent
        if g["result"] == "W"
    )

    recent_win_pct = (
        recent_wins / len(recent)
        if recent
        else 0.50
    )

    return {
        "games": len(games),
        "wins": wins,
        "losses": losses,
        "win_pct": win_pct,
        "margin": avg_margin,
        "recent_margin": recent_margin,
        "recent_win_pct": recent_win_pct
    }


# ============================================================
# ELO SIMPLE
# ============================================================

def build_elo(historical):

    elo = {
        team: 1500.0
        for team in TEAMS.keys()
    }

    # Ordenar por fecha para evitar mirar el futuro
    games = sorted(
        historical,
        key=lambda x: x.get("date", "")
    )

    for game in games:

        team = game["team"]
        opp = game["opponent"]

        if not opp or opp not in elo:
            continue

        team_elo = elo[team]
        opp_elo = elo[opp]

        expected = sigmoid(
            (team_elo + (55 if game["home"] else 0) - opp_elo)
            / 400
        )

        if game["result"] == "W":
            actual = 1
        elif game["result"] == "L":
            actual = 0
        else:
            actual = 0.5

        margin = abs(game["margin"])

        # K moderado
        multiplier = 20

        if margin >= 14:
            multiplier = 24
        elif margin >= 7:
            multiplier = 22

        change = multiplier * (
            actual - expected
        )

        elo[team] += change
        elo[opp] -= change

    return elo


# ============================================================
# LESIONES
# ============================================================

@st.cache_data(ttl=900)
def get_injury_data():

    data = get_json(
        ESPN_INJURIES,
        params={
            "limit": 500
        }
    )

    if not data:
        return {}

    injuries = {}

    # ESPN puede devolver diferentes estructuras.
    # Intentamos varias posibilidades sin romper la app.

    items = []

    if isinstance(data, dict):

        if isinstance(data.get("injuries"), list):
            items.extend(data["injuries"])

        if isinstance(data.get("teams"), list):
            for team in data["teams"]:

                team_abbr = (
                    team.get("team", {})
                    .get("abbreviation")
                )

                for injury in team.get(
                    "injuries",
                    []
                ):

                    injury["_team_abbr"] = team_abbr
                    items.append(injury)

    for item in items:

        try:

            team = item.get(
                "_team_abbr",
                item.get("team")
            )

            if isinstance(team, dict):
                team = team.get("abbreviation")

            if not team:
                continue

            status = str(
                item.get("status", "")
            ).lower()

            player = (
                item.get("athlete", {})
                .get("displayName", "Jugador")
            )

            text = (
                str(item.get("details", ""))
                + " "
                + str(item.get("description", ""))
            ).lower()

            severity = 0

            if "out" in status or "ir" in status:
                severity = 3
            elif "doubtful" in status:
                severity = 2
            elif "questionable" in status:
                severity = 1

            # QB tiene mayor peso
            position = (
                item.get("athlete", {})
                .get("position", {})
                .get("abbreviation", "")
            )

            if position == "QB":
                severity *= 2.0

            if severity > 0:

                injuries.setdefault(
                    team,
                    []
                ).append({
                    "player": player,
                    "status": status,
                    "severity": severity
                })

        except Exception:
            continue

    return injuries


def injury_penalty(team, injuries):

    data = injuries.get(team, [])

    if not data:
        return 0.0

    penalty = sum(
        float(x.get("severity", 0))
        for x in data
    )

    # Limitar para evitar que lesiones menores
    # destruyan completamente una prediccion.
    return min(penalty, 8.0)


# ============================================================
# MODELO
# ============================================================

def calculate_probability(
    away,
    home,
    historical,
    elo,
    injuries
):

    away_stats = team_stats(
        away,
        historical
    )

    home_stats = team_stats(
        home,
        historical
    )

    away_elo = elo.get(
        away,
        1500
    )

    home_elo = elo.get(
        home,
        1500
    )

    # --------------------------------------------------------
    # COMPONENTES
    # --------------------------------------------------------

    # ELO
    elo_component = (
        home_elo - away_elo
    )

    # Ventaja local
    home_advantage = 55

    # Diferencial de puntos
    margin_component = (
        home_stats["margin"]
        - away_stats["margin"]
    )

    # Forma reciente
    recent_component = (
        home_stats["recent_margin"]
        - away_stats["recent_margin"]
    )

    # Win %
    win_component = (
        home_stats["win_pct"]
        - away_stats["win_pct"]
    ) * 100

    # Lesiones
    home_injury = injury_penalty(
        home,
        injuries
    )

    away_injury = injury_penalty(
        away,
        injuries
    )

    injury_component = (
        away_injury - home_injury
    )

    # --------------------------------------------------------
    # SCORE
    # --------------------------------------------------------

    score = (
        elo_component * 0.55
        + margin_component * 8.0
        + recent_component * 5.0
        + win_component * 0.8
        + home_advantage
        + injury_component * 8.0
    )

    # Convertir score a probabilidad
    p_home = sigmoid(
        score / 400
    )

    # --------------------------------------------------------
    # LIMITES RAZONABLES
    # --------------------------------------------------------

    p_home = max(
        0.05,
        min(0.95, p_home)
    )

    # Pick
    if p_home >= 0.50:

        pick = home
        probability = p_home

    else:

        pick = away
        probability = 1 - p_home

    return {
        "pick": pick,
        "probability": probability,
        "home_probability": p_home,
        "away_probability": 1 - p_home,
        "home_stats": home_stats,
        "away_stats": away_stats,
        "home_elo": home_elo,
        "away_elo": away_elo,
        "home_injury": home_injury,
        "away_injury": away_injury
    }


# ============================================================
# INTERFAZ
# ============================================================

st.title("🏈 NFL EDGE")

st.subheader(
    "Modelo independiente del mercado"
)

st.write(
    "Probabilidad estimada únicamente con datos deportivos."
)

st.warning(
    "🚫 Las cuotas de sportsbooks NO se utilizan "
    "para generar las probabilidades."
)

st.caption(
    "Histórico utilizado: 2025 + 2026 disponible."
)

st.divider()

# ============================================================
# CARGAR DATOS
# ============================================================

with st.spinner(
    "Cargando partidos y datos NFL..."
):

    games = get_today_games()

    historical = build_historical_data()

    elo = build_elo(
        historical
    )

    injuries = get_injury_data()


# ============================================================
# PARTIDOS
# ============================================================

st.header("🏈 PARTIDOS DE HOY")

if not games:

    st.info(
        "No se encontraron partidos NFL para hoy."
    )

    st.caption(
        "La aplicación incluye pretemporada, "
        "temporada regular y playoffs."
    )

else:

    st.success(
        f"Se encontraron {len(games)} partido(s)."
    )

    for game in games:

        away = game["away"]
        home = game["home"]

        result = calculate_probability(
            away,
            home,
            historical,
            elo,
            injuries
        )

        pick = result["pick"]

        probability = (
            result["probability"] * 100
        )

        st.divider()

        st.subheader(
            f"🏈 {away} @ {home}"
        )

        st.caption(
            f"{game['away_name']} @ "
            f"{game['home_name']} · "
            f"{game['phase']}"
        )

        # ----------------------------------------------------
        # RESULTADO PRINCIPAL
        # ----------------------------------------------------

        col1, col2, col3 = st.columns(3)

        with col1:

            st.metric(
                "PICK DEL MODELO",
                pick
            )

        with col2:

            st.metric(
                "PROBABILIDAD",
                f"{probability:.1f}%"
            )

        with col3:

            if probability >= 65:
                label = "🔥 FUERTE"
            elif probability >= 58:
                label = "🟢 INTERESANTE"
            elif probability >= 53:
                label = "🟡 CERCANO"
            else:
                label = "⚪ SIN VENTAJA CLARA"

            st.metric(
                "SEÑAL",
                label
            )

        # ----------------------------------------------------
        # EXPLICACION CORTA
        # ----------------------------------------------------

        if pick == home:

            opponent = away

        else:

            opponent = home

        st.write(
            f"**El modelo estima que {pick} tiene "
            f"{probability:.1f}% de probabilidad "
            f"de ganar.**"
        )

        st.caption(
            "Esta probabilidad es independiente de "
            "las cuotas de la casa."
        )

        # ----------------------------------------------------
        # DATOS QUE UTILIZO
        # ----------------------------------------------------

        with st.expander(
            "📊 Ver factores utilizados"
        ):

            c1, c2 = st.columns(2)

            with c1:

                st.write(
                    f"**{away}**"
                )

                st.write(
                    f"Histórico: "
                    f"{result['away_stats']['wins']}-"
                    f"{result['away_stats']['losses']}"
                )

                st.write(
                    f"Win %: "
                    f"{result['away_stats']['win_pct']*100:.1f}%"
                )

                st.write(
                    f"Diferencial: "
                    f"{result['away_stats']['margin']:+.1f}"
                )

                st.write(
                    f"ELO: "
                    f"{result['away_elo']:.0f}"
                )

                st.write(
                    f"Impacto lesiones: "
                    f"{result['away_injury']:.1f}"
                )

            with c2:

                st.write(
                    f"**{home}**"
                )

                st.write(
                    f"Histórico: "
                    f"{result['home_stats']['wins']}-"
                    f"{result['home_stats']['losses']}"
                )

                st.write(
                    f"Win %: "
                    f"{result['home_stats']['win_pct']*100:.1f}%"
                )

                st.write(
                    f"Diferencial: "
                    f"{result['home_stats']['margin']:+.1f}"
                )

                st.write(
                    f"ELO: "
                    f"{result['home_elo']:.0f}"
                )

                st.write(
                    f"Impacto lesiones: "
                    f"{result['home_injury']:.1f}"
                )

        # ----------------------------------------------------
        # LESIONES DISPONIBLES
        # ----------------------------------------------------

        relevant_injuries = []

        for team in [away, home]:

            for injury in injuries.get(
                team,
                []
            ):

                relevant_injuries.append(
                    (
                        team,
                        injury
                    )
                )

        if relevant_injuries:

            with st.expander(
                "🏥 Lesiones relevantes encontradas"
            ):

                for team, injury in relevant_injuries:

                    st.write(
                        f"**{team}** — "
                        f"{injury['player']} — "
                        f"{injury['status']}"
                    )

        else:

            st.caption(
                "🏥 No se encontraron datos estructurados "
                "de lesiones disponibles en ESPN."
            )


# ============================================================
# COMO UTILIZARLO
# ============================================================

st.divider()

st.header(
    "🧠 ¿Cómo utilizar el porcentaje?"
)

st.write(
    """
El porcentaje NO significa que el resultado sea seguro.

Ejemplo:

**Modelo: 70%**

Eso significa que el modelo considera que, bajo sus
datos y supuestos actuales, ese equipo tiene aproximadamente
70% de probabilidad de ganar.

Después tú comparas ese porcentaje con la cuota que
te ofrece tu sportsbook.

La aplicación NO utiliza esa cuota para fabricar el 70%.
"""
)

st.info(
    "🎯 El objetivo es darte una segunda opinión "
    "independiente de la casa de apuestas."
)

st.caption(
    "NFL EDGE — Modelo experimental independiente. "
    "No garantiza resultados."
)
