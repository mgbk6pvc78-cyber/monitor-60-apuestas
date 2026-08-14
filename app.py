import streamlit as st
import requests
import math
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


# ============================================================
# CONFIGURACIÓN
# ============================================================

st.set_page_config(
    page_title="NFL EDGE",
    page_icon="🏈",
    layout="wide"
)

API = "https://site.api.espn.com/apis/site/v2/sports/football/nfl"

TZ = ZoneInfo("America/Chicago")


# ============================================================
# FUNCIONES GENERALES
# ============================================================

def get_json(url, params=None):

    try:

        response = requests.get(
            url,
            params=params,
            timeout=20,
            headers={
                "User-Agent": "Mozilla/5.0"
            }
        )

        if response.status_code == 200:

            return response.json()

    except Exception:

        return None

    return None


# ============================================================
# SCOREBOARD DE UNA FECHA
# ============================================================

def get_scoreboard(
    date_string,
    season_type
):

    return get_json(
        f"{API}/scoreboard",
        {
            "dates": date_string,
            "seasontype": season_type,
            "limit": 100
        }
    )


# ============================================================
# EXTRAER PARTIDOS
# ============================================================

def parse_games(data):

    games = []

    if not data:
        return games

    for event in data.get(
        "events",
        []
    ):

        try:

            competition = (
                event["competitions"][0]
            )

            competitors = (
                competition["competitors"]
            )

            home = next(
                x for x in competitors
                if x["homeAway"] == "home"
            )

            away = next(
                x for x in competitors
                if x["homeAway"] == "away"
            )

            home_team = home["team"]

            away_team = away["team"]

            status = (
                event
                .get("status", {})
                .get("type", {})
            )

            completed = status.get(
                "completed",
                False
            )

            home_score = None
            away_score = None

            try:

                home_score = float(
                    home.get(
                        "score",
                        0
                    )
                )

                away_score = float(
                    away.get(
                        "score",
                        0
                    )
                )

            except Exception:

                pass

            games.append({

                "id":
                    event.get("id"),

                "date":
                    event.get(
                        "date",
                        ""
                    ),

                "home":
                    home_team.get(
                        "abbreviation",
                        ""
                    ),

                "home_name":
                    home_team.get(
                        "displayName",
                        ""
                    ),

                "home_id":
                    home_team.get(
                        "id"
                    ),

                "away":
                    away_team.get(
                        "abbreviation",
                        ""
                    ),

                "away_name":
                    away_team.get(
                        "displayName",
                        ""
                    ),

                "away_id":
                    away_team.get(
                        "id"
                    ),

                "home_score":
                    home_score,

                "away_score":
                    away_score,

                "completed":
                    completed

            })

        except Exception:

            continue

    return games


# ============================================================
# PARTIDOS DE HOY
# ============================================================

@st.cache_data(ttl=300)
def get_today_games():

    today = datetime.now(
        TZ
    ).strftime("%Y%m%d")

    games = []

    # --------------------------------------------------------
    # PRESEASON
    # --------------------------------------------------------

    preseason = get_scoreboard(
        today,
        1
    )

    games.extend(
        parse_games(
            preseason
        )
    )

    # --------------------------------------------------------
    # REGULAR SEASON
    # --------------------------------------------------------

    regular = get_scoreboard(
        today,
        2
    )

    games.extend(
        parse_games(
            regular
        )
    )

    # --------------------------------------------------------
    # PLAYOFFS
    # --------------------------------------------------------

    playoffs = get_scoreboard(
        today,
        3
    )

    games.extend(
        parse_games(
            playoffs
        )
    )

    # --------------------------------------------------------
    # ELIMINAR DUPLICADOS
    # --------------------------------------------------------

    unique = {}

    for game in games:

        unique[
            game["id"]
        ] = game

    return list(
        unique.values()
    )


# ============================================================
# HISTÓRICO
#
# SOLO:
# 2025
# 2026 HASTA HOY
#
# NO 2019
# NO 2020
# NO 2021
# NO 2022
# NO 2023
# NO 2024
# ============================================================

@st.cache_data(ttl=3600)
def get_historical_games():

    all_games = []

    # ========================================================
    # 2025 REGULAR SEASON
    # ========================================================

    start_2025 = datetime(
        2025,
        9,
        1
    )

    end_2025 = datetime(
        2026,
        1,
        15
    )

    current = start_2025

    while current <= end_2025:

        week_end = min(
            current + timedelta(
                days=6
            ),
            end_2025
        )

        date_range = (
            current.strftime("%Y%m%d")
            + "-"
            + week_end.strftime("%Y%m%d")
        )

        data = get_scoreboard(
            date_range,
            2
        )

        all_games.extend(
            parse_games(
                data
            )
        )

        current = (
            week_end
            + timedelta(days=1)
        )

    # ========================================================
    # 2025 PLAYOFFS
    # ========================================================

    playoff_start = datetime(
        2026,
        1,
        10
    )

    playoff_end = datetime(
        2026,
        2,
        20
    )

    current = playoff_start

    while current <= playoff_end:

        week_end = min(
            current + timedelta(
                days=6
            ),
            playoff_end
        )

        date_range = (
            current.strftime("%Y%m%d")
            + "-"
            + week_end.strftime("%Y%m%d")
        )

        data = get_scoreboard(
            date_range,
            3
        )

        all_games.extend(
            parse_games(
                data
            )
        )

        current = (
            week_end
            + timedelta(days=1)
        )

    # ========================================================
    # 2026 HASTA HOY
    # ========================================================

    today = datetime.now(
        TZ
    ).replace(
        tzinfo=None
    )

    start_2026 = datetime(
        2026,
        1,
        1
    )

    current = start_2026

    while current <= today:

        week_end = min(
            current + timedelta(
                days=6
            ),
            today
        )

        date_range = (
            current.strftime("%Y%m%d")
            + "-"
            + week_end.strftime("%Y%m%d")
        )

        # ----------------------------------------------------
        # PRESEASON
        # ----------------------------------------------------

        data = get_scoreboard(
            date_range,
            1
        )

        all_games.extend(
            parse_games(
                data
            )
        )

        # ----------------------------------------------------
        # REGULAR
        # ----------------------------------------------------

        data = get_scoreboard(
            date_range,
            2
        )

        all_games.extend(
            parse_games(
                data
            )
        )

        # ----------------------------------------------------
        # PLAYOFFS
        # ----------------------------------------------------

        data = get_scoreboard(
            date_range,
            3
        )

        all_games.extend(
            parse_games(
                data
            )
        )

        current = (
            week_end
            + timedelta(days=1)
        )

    # ========================================================
    # SOLO PARTIDOS TERMINADOS
    # ========================================================

    completed = []

    seen = set()

    for game in all_games:

        if not game["completed"]:
            continue

        if (
            game["home_score"]
            is None
        ):
            continue

        if (
            game["away_score"]
            is None
        ):
            continue

        game_id = game["id"]

        if game_id in seen:
            continue

        seen.add(
            game_id
        )

        completed.append(
            game
        )

    return completed


# ============================================================
# ESTADÍSTICAS DE EQUIPOS
# ============================================================

def build_team_stats(
    games
):

    stats = {}

    for game in games:

        home = game["home"]
        away = game["away"]

        hs = game["home_score"]
        aws = game["away_score"]

        if home not in stats:

            stats[home] = {
                "games": 0,
                "wins": 0,
                "losses": 0,
                "points_for": 0,
                "points_against": 0,
                "margins": [],
                "home_games": 0,
                "home_wins": 0
            }

        if away not in stats:

            stats[away] = {
                "games": 0,
                "wins": 0,
                "losses": 0,
                "points_for": 0,
                "points_against": 0,
                "margins": [],
                "home_games": 0,
                "home_wins": 0
            }

        # ----------------------------------------------------
        # HOME
        # ----------------------------------------------------

        stats[home]["games"] += 1

        stats[home]["points_for"] += hs

        stats[home]["points_against"] += aws

        stats[home]["margins"].append(
            hs - aws
        )

        stats[home]["home_games"] += 1

        if hs > aws:

            stats[home]["wins"] += 1

            stats[home]["home_wins"] += 1

        else:

            stats[home]["losses"] += 1

        # ----------------------------------------------------
        # AWAY
        # ----------------------------------------------------

        stats[away]["games"] += 1

        stats[away]["points_for"] += aws

        stats[away]["points_against"] += hs

        stats[away]["margins"].append(
            aws - hs
        )

        if aws > hs:

            stats[away]["wins"] += 1

        else:

            stats[away]["losses"] += 1

    return stats


# ============================================================
# PERFIL DE EQUIPO
# ============================================================

def get_team_profile(
    team,
    stats
):

    if team not in stats:

        return {

            "win_pct": 0.50,

            "points_for": 21.5,

            "points_against": 21.5,

            "margin": 0,

            "home_win_pct": 0.50,

            "games": 0
        }

    x = stats[team]

    games = max(
        1,
        x["games"]
    )

    home_games = max(
        1,
        x["home_games"]
    )

    return {

        "win_pct":
            x["wins"] / games,

        "points_for":
            x["points_for"] / games,

        "points_against":
            x["points_against"] / games,

        "margin":
            sum(
                x["margins"]
            ) / len(
                x["margins"]
            )
            if x["margins"]
            else 0,

        "home_win_pct":
            x["home_wins"]
            / home_games,

        "games":
            x["games"]
    }


# ============================================================
# LESIONES
#
# Intentamos obtener lesiones de ESPN.
# Si no están disponibles, NO inventamos datos.
# ============================================================

@st.cache_data(ttl=600)
def get_team_injuries(
    team_id
):

    if not team_id:

        return []

    urls = [

        f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/teams/{team_id}/injuries",

        f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/teams/{team_id}?enable=injuries"

    ]

    for url in urls:

        data = get_json(
            url
        )

        if not data:
            continue

        injuries = []

        def search(
            obj
        ):

            if isinstance(
                obj,
                dict
            ):

                athlete = obj.get(
                    "athlete"
                )

                if isinstance(
                    athlete,
                    dict
                ):

                    name = athlete.get(
                        "displayName",
                        ""
                    )

                    status = (
                        obj.get(
                            "status"
                        )
                        or obj.get(
                            "injuryStatus"
                        )
                        or obj.get(
                            "type"
                        )
                        or ""
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

                    if name:

                        injuries.append({

                            "name":
                                name,

                            "status":
                                str(
                                    status
                                ),

                            "position":
                                position
                        })

                for value in obj.values():

                    search(
                        value
                    )

            elif isinstance(
                obj,
                list
            ):

                for item in obj:

                    search(
                        item
                    )

        search(
            data
        )

        if injuries:

            # eliminar duplicados

            unique = {}

            for injury in injuries:

                key = (
                    injury["name"],
                    injury["status"]
                )

                unique[key] = injury

            return list(
                unique.values()
            )

    return []


# ============================================================
# IMPACTO SIMPLE DE LESIONES
#
# No pretendemos decir que un QB OUT equivale
# exactamente a X puntos.
#
# Solo utilizamos una pequeña corrección.
# ============================================================

def injury_adjustment(
    injuries
):

    adjustment = 0

    important_positions = [
        "QB",
        "RB",
        "WR",
        "TE",
        "OT",
        "T",
        "G",
        "C",
        "DE",
        "DT",
        "DL",
        "LB",
        "CB",
        "S"
    ]

    for injury in injuries:

        status = injury[
            "status"
        ].lower()

        position = injury[
            "position"
        ]

        if not any(
            word in status
            for word in [
                "out",
                "ir",
                "reserve"
            ]
        ):

            continue

        # QB tiene mayor impacto

        if position == "QB":

            adjustment -= 0.055

        elif position in [
            "WR",
            "RB",
            "TE"
        ]:

            adjustment -= 0.018

        elif position in [
            "CB",
            "S",
            "LB",
            "DE",
            "DT",
            "DL"
        ]:

            adjustment -= 0.014

        elif position in important_positions:

            adjustment -= 0.008

    return adjustment


# ============================================================
# MODELO
#
# IMPORTANTE:
# NO VE LAS CUOTAS.
# ============================================================

def calculate_probability(
    game,
    stats,
    home_injuries,
    away_injuries
):

    home = get_team_profile(
        game["home"],
        stats
    )

    away = get_team_profile(
        game["away"],
        stats
    )

    # --------------------------------------------------------
    # DIFERENCIAS
    # --------------------------------------------------------

    win_difference = (
        home["win_pct"]
        - away["win_pct"]
    )

    offense_difference = (
        home["points_for"]
        - away["points_for"]
    )

    defense_difference = (
        away["points_against"]
        - home["points_against"]
    )

    margin_difference = (
        home["margin"]
        - away["margin"]
    )

    # --------------------------------------------------------
    # LOCALÍA
    # --------------------------------------------------------

    home_advantage = 0.035

    # --------------------------------------------------------
    # LESIONES
    # --------------------------------------------------------

    home_injury = injury_adjustment(
        home_injuries
    )

    away_injury = injury_adjustment(
        away_injuries
    )

    injury_difference = (
        home_injury
        - away_injury
    )

    # --------------------------------------------------------
    # SCORE DEL MODELO
    # --------------------------------------------------------

    score = (

        win_difference * 1.35

        + offense_difference * 0.018

        + defense_difference * 0.018

        + margin_difference * 0.022

        + home_advantage

        + injury_difference

    )

    # --------------------------------------------------------
    # LOGÍSTICA
    # --------------------------------------------------------

    probability_home = (
        1 /
        (
            1
            + math.exp(
                -score * 2.0
            )
        )
    )

    # --------------------------------------------------------
    # EVITAR PORCENTAJES ABSURDOS
    #
    # Nunca mostramos 95%, 99%, etc.
    # El modelo debe ser conservador.
    # --------------------------------------------------------

    probability_home = max(
        0.20,
        min(
            0.80,
            probability_home
        )
    )

    probability_away = (
        1
        - probability_home
    )

    return (
        probability_home,
        probability_away
    )


# ============================================================
# CARGAR DATOS
# ============================================================

st.title(
    "🏈 NFL EDGE"
)

st.subheader(
    "Modelo independiente del mercado"
)

st.write(
    "🚫 Las cuotas de sportsbooks NO se utilizan "
    "para generar las probabilidades."
)

st.caption(
    "Histórico utilizado: 2025 + 2026 disponible."
)

st.divider()


# ============================================================
# OBTENER DATOS
# ============================================================

with st.spinner(
    "🧠 Analizando NFL..."
):

    today_games = (
        get_today_games()
    )

    historical_games = (
        get_historical_games()
    )

    team_stats = build_team_stats(
        historical_games
    )


# ============================================================
# PARTIDOS DE HOY
# ============================================================

st.header(
    "🏈 PARTIDOS DE HOY"
)


if not today_games:

    st.warning(
        "⚠️ No se encontraron partidos NFL para hoy."
    )

    st.info(
        "La aplicación consulta automáticamente "
        "pretemporada, temporada regular y playoffs."
    )

else:

    st.success(
        f"Se encontraron {len(today_games)} partido(s)."
    )

    for game in today_games:

        # ----------------------------------------------------
        # LESIONES
        # ----------------------------------------------------

        home_injuries = get_team_injuries(
            game["home_id"]
        )

        away_injuries = get_team_injuries(
            game["away_id"]
        )

        # ----------------------------------------------------
        # PROBABILIDADES
        # ----------------------------------------------------

        home_probability, away_probability = (
            calculate_probability(
                game,
                team_stats,
                home_injuries,
                away_injuries
            )
        )

        # ----------------------------------------------------
        # PICK
        # ----------------------------------------------------

        if (
            home_probability
            >=
            away_probability
        ):

            pick = game["home"]

            pick_name = game[
                "home_name"
            ]

            pick_probability = (
                home_probability
            )

        else:

            pick = game["away"]

            pick_name = game[
                "away_name"
            ]

            pick_probability = (
                away_probability
            )

        # ----------------------------------------------------
        # TARJETA
        # ----------------------------------------------------

        st.markdown(
            f"""
            <div style="
                background:#151922;
                border:1px solid #383c48;
                border-radius:18px;
                padding:25px;
                margin:20px 0;
            ">

            <h2>
            🏈 {game["away"]} @ {game["home"]}
            </h2>

            <hr>

            <p style="
                font-size:18px;
                color:#AAAAAA;
            ">
            Modelo independiente
            </p>

            <p style="
                font-size:24px;
                font-weight:700;
            ">
            🎯 PICK: {pick} — {pick_name}
            </p>

            <p style="
                font-size:48px;
                font-weight:800;
            ">
            {pick_probability * 100:.1f}%
            </p>

            <p style="
                font-size:17px;
            ">
            Probabilidad estimada de ganar
            </p>

            </div>
            """,
            unsafe_allow_html=True
        )

        # ----------------------------------------------------
        # DETALLES
        # ----------------------------------------------------

        with st.expander(
            "🧠 Ver análisis"
        ):

            st.write(
                f"**{game['away']}**: "
                f"{away_probability * 100:.1f}%"
            )

            st.write(
                f"**{game['home']}**: "
                f"{home_probability * 100:.1f}%"
            )

            st.write(
                "📊 Rendimiento histórico utilizado"
            )

            st.write(
                "⚔️ Ataque y puntos anotados"
            )

            st.write(
                "🛡️ Defensa y puntos permitidos"
            )

            st.write(
                "📈 Diferencial de puntos"
            )

            st.write(
                "🏠 Ventaja de localía"
            )

            if (
                home_injuries
                or away_injuries
            ):

                st.write(
                    "🏥 Información de lesiones disponible"
                )

            else:

                st.write(
                    "🏥 No se obtuvo información de lesiones "
                    "para este partido."
                )


# ============================================================
# EXPLICACIÓN SIMPLE
# ============================================================

st.divider()

with st.expander(
    "🧠 ¿Cómo interpretar el porcentaje?"
):

    st.write(
        """
        El porcentaje NO significa que una apuesta sea segura.

        Ejemplo:

        🎯 TEAM A — 70%

        El modelo estima aproximadamente
        70% de probabilidad de que TEAM A gane.

        Después tú comparas ese número
        con la cuota que ofrece la casa.

        La cuota de la casa NO se utiliza
        para generar el 70%.
        """
    )

st.caption(
    "NFL EDGE — Modelo experimental independiente. "
    "No garantiza resultados."
)
