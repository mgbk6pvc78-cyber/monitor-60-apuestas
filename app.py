import streamlit as st
import requests
import numpy as np
from datetime import datetime
from zoneinfo import ZoneInfo

st.set_page_config(
    page_title="NFL EDGE",
    page_icon="🏈",
    layout="wide"
)

API = "https://site.api.espn.com/apis/site/v2/sports/football/nfl"
TZ = ZoneInfo("America/Chicago")


# ============================================================
# API
# ============================================================

def get_json(url, params=None):

    try:
        r = requests.get(
            url,
            params=params,
            timeout=20,
            headers={
                "User-Agent": "Mozilla/5.0"
            }
        )

        if r.status_code == 200:
            return r.json()

    except Exception:
        pass

    return None


# ============================================================
# PARTIDOS DE HOY
# ============================================================

@st.cache_data(ttl=300)
def get_today_games():

    today = datetime.now(TZ).strftime("%Y%m%d")

    data = get_json(
        f"{API}/scoreboard",
        {
            "dates": today,
            "limit": 100
        }
    )

    if not data:
        return []

    games = []

    for event in data.get("events", []):

        try:

            competition = event["competitions"][0]

            teams = competition["competitors"]

            home = next(
                x for x in teams
                if x["homeAway"] == "home"
            )

            away = next(
                x for x in teams
                if x["homeAway"] == "away"
            )

            games.append({
                "id": event["id"],

                "date": event.get(
                    "date",
                    ""
                ),

                "home": home["team"].get(
                    "abbreviation",
                    ""
                ),

                "home_name": home["team"].get(
                    "displayName",
                    ""
                ),

                "home_id": home["team"].get(
                    "id"
                ),

                "away": away["team"].get(
                    "abbreviation",
                    ""
                ),

                "away_name": away["team"].get(
                    "displayName",
                    ""
                ),

                "away_id": away["team"].get(
                    "id"
                ),

                "status": event.get(
                    "status",
                    {}
                )
            })

        except Exception:
            continue

    return games


# ============================================================
# HISTÓRICO
#
# SOLO 2025 + 2026
# ============================================================

@st.cache_data(ttl=3600)
def get_history():

    games = []

    # Solo fechas de temporada NFL.
    # No necesitamos 2019, 2020, 2021, etc.

    for year in [2025, 2026]:

        data = get_json(
            f"{API}/scoreboard",
            {
                "dates": str(year),
                "limit": 1000
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
                    event["competitions"][0]
                )

                teams = (
                    competition["competitors"]
                )

                home = next(
                    x for x in teams
                    if x["homeAway"] == "home"
                )

                away = next(
                    x for x in teams
                    if x["homeAway"] == "away"
                )

                status = (
                    event
                    .get("status", {})
                    .get("type", {})
                    .get("completed", False)
                )

                if not status:
                    continue

                games.append({

                    "home":
                        home["team"].get(
                            "abbreviation"
                        ),

                    "away":
                        away["team"].get(
                            "abbreviation"
                        ),

                    "home_score":
                        float(
                            home.get(
                                "score",
                                0
                            )
                        ),

                    "away_score":
                        float(
                            away.get(
                                "score",
                                0
                            )
                        )
                })

            except Exception:
                continue

    return games


# ============================================================
# ESTADÍSTICAS
# ============================================================

def build_stats(history):

    teams = {}

    for game in history:

        home = game["home"]
        away = game["away"]

        hs = game["home_score"]
        aws = game["away_score"]

        for team in [home, away]:

            if team not in teams:

                teams[team] = {
                    "games": 0,
                    "wins": 0,
                    "pf": 0,
                    "pa": 0,
                    "margins": []
                }

        teams[home]["games"] += 1
        teams[away]["games"] += 1

        teams[home]["pf"] += hs
        teams[home]["pa"] += aws

        teams[away]["pf"] += aws
        teams[away]["pa"] += hs

        if hs > aws:

            teams[home]["wins"] += 1

        elif aws > hs:

            teams[away]["wins"] += 1

        teams[home]["margins"].append(
            hs - aws
        )

        teams[away]["margins"].append(
            aws - hs
        )

    return teams


# ============================================================
# PERFIL
# ============================================================

def profile(team, stats):

    if team not in stats:

        return {
            "win": 0.50,
            "pf": 21.5,
            "pa": 21.5,
            "margin": 0
        }

    x = stats[team]

    games = max(
        1,
        x["games"]
    )

    return {

        "win":
            x["wins"] / games,

        "pf":
            x["pf"] / games,

        "pa":
            x["pa"] / games,

        "margin":
            np.mean(
                x["margins"]
            )
            if x["margins"]
            else 0
    }


# ============================================================
# LESIONES
# ============================================================

@st.cache_data(ttl=600)
def get_injuries(team_id):

    if not team_id:
        return []

    data = get_json(
        f"{API}/teams/{team_id}/injuries"
    )

    if not data:
        return []

    injuries = []

    def scan(obj):

        if isinstance(obj, dict):

            athlete = obj.get(
                "athlete",
                {}
            )

            if isinstance(
                athlete,
                dict
            ):

                name = athlete.get(
                    "displayName",
                    ""
                )

                position = (
                    athlete
                    .get(
                        "position",
                        {}
                    )
                )

                if isinstance(
                    position,
                    dict
                ):

                    position = position.get(
                        "abbreviation",
                        ""
                    )

                status = (
                    obj.get(
                        "status"
                    )
                    or obj.get(
                        "injuryStatus"
                    )
                    or ""
                )

                if name:

                    injuries.append({
                        "name": name,
                        "position":
                            position,
                        "status":
                            str(status)
                    })

            for value in obj.values():
                scan(value)

        elif isinstance(
            obj,
            list
        ):

            for item in obj:
                scan(item)

    scan(data)

    return injuries


# ============================================================
# MODELO
# ============================================================

def model_probability(
    game,
    stats,
    home_injuries,
    away_injuries
):

    home = profile(
        game["home"],
        stats
    )

    away = profile(
        game["away"],
        stats
    )

    # --------------------------------------------
    # RENDIMIENTO
    # --------------------------------------------

    win_diff = (
        home["win"]
        - away["win"]
    )

    offense_diff = (
        home["pf"]
        - away["pf"]
    )

    defense_diff = (
        away["pa"]
        - home["pa"]
    )

    margin_diff = (
        home["margin"]
        - away["margin"]
    )

    # --------------------------------------------
    # LESIONES
    #
    # No inventamos impacto.
    # Solo contamos jugadores reportados
    # como OUT / IR / QUESTIONABLE.
    # --------------------------------------------

    home_out = sum(
        1
        for x in home_injuries
        if any(
            word in x["status"].lower()
            for word in [
                "out",
                "ir",
                "reserve"
            ]
        )
    )

    away_out = sum(
        1
        for x in away_injuries
        if any(
            word in x["status"].lower()
            for word in [
                "out",
                "ir",
                "reserve"
            ]
        )
    )

    injury_diff = (
        away_out
        - home_out
    )

    # --------------------------------------------
    # SCORE
    # --------------------------------------------

    score = (

        win_diff * 1.20

        + offense_diff * 0.025

        + defense_diff * 0.025

        + margin_diff * 0.025

        + injury_diff * 0.025

        + 0.12
    )

    probability = (
        1 /
        (
            1
            + np.exp(
                -score * 2
            )
        )
    )

    # --------------------------------------------
    # EVITAR FALSOS 90-100%
    # --------------------------------------------

    probability = np.clip(
        probability,
        0.20,
        0.80
    )

    return probability


# ============================================================
# CARGAR DATOS
# ============================================================

with st.spinner(
    "🧠 Analizando datos NFL..."
):

    today_games = (
        get_today_games()
    )

    history = (
        get_history()
    )

    stats = build_stats(
        history
    )


# ============================================================
# INTERFAZ
# ============================================================

st.title(
    "🏈 NFL EDGE"
)

st.caption(
    "Modelo independiente del mercado"
)

st.write(
    "🚫 Las cuotas de sportsbooks NO se utilizan "
    "para generar las probabilidades."
)

st.divider()

st.header(
    "🏈 PARTIDOS DE HOY"
)


# ============================================================
# PARTIDOS
# ============================================================

if not today_games:

    st.error(
        "⚠️ La aplicación no pudo obtener "
        "los partidos de hoy desde ESPN."
    )

    st.info(
        "Si esto aparece, el problema es la "
        "fuente de datos y NO el modelo."
    )

else:

    for game in today_games:

        home_injuries = get_injuries(
            game["home_id"]
        )

        away_injuries = get_injuries(
            game["away_id"]
        )

        home_prob = model_probability(
            game,
            stats,
            home_injuries,
            away_injuries
        )

        away_prob = (
            1 - home_prob
        )

        if home_prob >= away_prob:

            pick = game["home"]
            pick_probability = home_prob

        else:

            pick = game["away"]
            pick_probability = away_prob

        st.markdown(
            f"""
            <div style="
                border:1px solid #363944;
                border-radius:16px;
                padding:22px;
                margin-bottom:20px;
                background:#151922;
            ">

            <h2>
            🏈 {game["away"]} @ {game["home"]}
            </h2>

            <hr>

            <h3>
            🎯 PICK DEL MODELO:
            {pick}
            </h3>

            <div style="
                font-size:46px;
                font-weight:800;
            ">
            {pick_probability * 100:.1f}%
            </div>

            <p>
            {game["away"]}:
            <b>{away_prob * 100:.1f}%</b>
            &nbsp;&nbsp;&nbsp;
            {game["home"]}:
            <b>{home_prob * 100:.1f}%</b>
            </p>

            </div>
            """,
            unsafe_allow_html=True
        )

        with st.expander(
            "🧠 Factores considerados"
        ):

            st.write(
                "📊 Histórico: 2025 + 2026 disponible"
            )

            st.write(
                "📈 Rendimiento de los equipos"
            )

            st.write(
                "⚔️ Ataque y defensa"
            )

            st.write(
                "📉 Diferencial de puntos"
            )

            st.write(
                "🏠 Ventaja de localía"
            )

            st.write(
                "🏥 Información de lesiones disponible"
            )


# ============================================================
# EXPLICACIÓN
# ============================================================

st.divider()

with st.expander(
    "ℹ️ ¿Cómo utilizar el porcentaje?"
):

    st.write(
        """
        El modelo NO intenta decir que una apuesta
        sea segura.

        Ejemplo:

        Si aparece:

        🎯 TEAM A — 70%

        significa que el modelo estima
        aproximadamente 70% de probabilidad
        de que TEAM A gane.

        Tú después comparas ese porcentaje
        con la cuota que ofrece la casa.

        La cuota NO entra en el cálculo
        de esta probabilidad.
        """
    )


st.caption(
    "NFL EDGE — Modelo experimental independiente. "
    "No garantiza resultados."
)
