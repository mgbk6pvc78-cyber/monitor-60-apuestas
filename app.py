import streamlit as st
import pandas as pd
import numpy as np
import requests
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# ============================================================
# 🏈 NFL EDGE V2
#
# OBJETIVO:
# Mostrar solamente los partidos del día y la probabilidad
# independiente del modelo.
#
# HISTÓRICO:
# 2025 + 2026 disponible
#
# NO UTILIZA CUOTAS DE SPORTSBOOK PARA GENERAR LA PROBABILIDAD.
#
# FACTORES:
# - rendimiento histórico
# - forma reciente
# - ataque
# - defensa
# - diferencial de puntos
# - localía
# - lesiones disponibles
# - incertidumbre de pretemporada
# ============================================================


# ============================================================
# CONFIGURACIÓN
# ============================================================

st.set_page_config(
    page_title="NFL EDGE",
    page_icon="🏈",
    layout="wide"
)

API = (
    "https://site.api.espn.com/apis/site/v2/"
    "sports/football/nfl"
)

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

TIMEZONE = ZoneInfo("America/Chicago")

HISTORICAL_YEAR = 2025
CURRENT_YEAR = 2026


# ============================================================
# ESTILO
# ============================================================

st.markdown(
    """
    <style>

    .block-container {
        padding-top: 2rem;
        padding-bottom: 3rem;
        max-width: 1100px;
    }

    .game-card {
        border: 1px solid #353944;
        border-radius: 16px;
        padding: 22px;
        margin-bottom: 20px;
        background: #151922;
    }

    .pick-title {
        font-size: 28px;
        font-weight: 700;
    }

    .probability {
        font-size: 44px;
        font-weight: 800;
        margin-top: 4px;
    }

    .muted {
        color: #9da3ae;
        font-size: 14px;
    }

    .factor {
        padding: 8px 0;
    }

    </style>
    """,
    unsafe_allow_html=True
)


# ============================================================
# REQUEST
# ============================================================

@st.cache_data(ttl=900)
def api_get(url, params=None):

    try:

        response = requests.get(
            url,
            params=params,
            headers=HEADERS,
            timeout=20
        )

        if response.status_code != 200:
            return None

        return response.json()

    except Exception:
        return None


# ============================================================
# FECHA LOCAL
# ============================================================

def local_today():

    return datetime.now(
        TIMEZONE
    ).date()


# ============================================================
# EXTRAER PARTIDOS
# ============================================================

def parse_games(data):

    if not data:
        return []

    games = []

    for event in data.get(
        "events",
        []
    ):

        try:

            competition = (
                event
                .get("competitions", [{}])[0]
            )

            competitors = (
                competition
                .get("competitors", [])
            )

            home = None
            away = None

            for team in competitors:

                if team.get("homeAway") == "home":
                    home = team

                elif team.get("homeAway") == "away":
                    away = team

            if not home or not away:
                continue

            home_team = home.get(
                "team",
                {}
            )

            away_team = away.get(
                "team",
                {}
            )

            event_date = event.get(
                "date"
            )

            local_date = None

            if event_date:

                try:

                    dt = datetime.fromisoformat(
                        event_date.replace(
                            "Z",
                            "+00:00"
                        )
                    )

                    local_date = (
                        dt.astimezone(
                            TIMEZONE
                        ).date()
                    )

                except Exception:
                    pass

            # Tipo de partido
            season_type = (
                event
                .get("season", {})
                .get("slug", "")
            )

            competitions_type = (
                competition
                .get("type", {})
                .get("abbreviation", "")
            )

            notes = (
                competition
                .get("notes", [])
            )

            note_text = ""

            if notes:

                note_text = " ".join(
                    str(x.get("headline", ""))
                    for x in notes
                    if isinstance(x, dict)
                )

            status = (
                event
                .get("status", {})
                .get("type", {})
                .get("description", "")
            )

            # Clima si ESPN lo proporciona
            weather = competition.get(
                "weather",
                {}
            )

            games.append(
                {
                    "id": event.get("id"),

                    "date": event_date,

                    "local_date": local_date,

                    "home": home_team.get(
                        "abbreviation",
                        ""
                    ),

                    "away": away_team.get(
                        "abbreviation",
                        ""
                    ),

                    "home_name": home_team.get(
                        "displayName",
                        ""
                    ),

                    "away_name": away_team.get(
                        "displayName",
                        ""
                    ),

                    "home_id": home_team.get(
                        "id"
                    ),

                    "away_id": away_team.get(
                        "id"
                    ),

                    "status": status,

                    "home_score": safe_float(
                        home.get("score")
                    ),

                    "away_score": safe_float(
                        away.get("score")
                    ),

                    "season_type": season_type,

                    "competition_type":
                        competitions_type,

                    "notes":
                        note_text,

                    "weather":
                        weather
                }
            )

        except Exception:

            continue

    return games


def safe_float(value):

    try:

        if value is None:
            return 0.0

        return float(value)

    except Exception:

        return 0.0


# ============================================================
# PARTIDOS POR FECHA
# ============================================================

@st.cache_data(ttl=300)
def games_by_date(date_string):

    data = api_get(
        f"{API}/scoreboard",
        {
            "dates": date_string,
            "limit": 1000
        }
    )

    return parse_games(data)


# ============================================================
# PARTIDOS ACTUALES
#
# Hacemos varias consultas:
# 1. fecha local
# 2. día anterior
# 3. día siguiente
#
# Esto evita problemas de zona horaria.
# ============================================================

def get_today_games():

    today = local_today()

    dates = [
        today - timedelta(days=1),
        today,
        today + timedelta(days=1)
    ]

    all_games = []

    for d in dates:

        games = games_by_date(
            d.strftime("%Y%m%d")
        )

        all_games.extend(
            games
        )

    unique = {}

    for game in all_games:

        if game["local_date"] == today:

            unique[
                game["id"]
            ] = game

    return list(
        unique.values()
    )


# ============================================================
# PARTIDOS HISTÓRICOS POR RANGO
#
# ESPN permite consultar rangos de fechas.
# Usamos bloques para no hacer cientos de requests.
# ============================================================

@st.cache_data(ttl=3600)
def get_historical_games(
    year
):

    start = datetime(
        year,
        8,
        1
    ).date()

    end = datetime(
        year + 1,
        2,
        15
    ).date()

    # Para 2026 solamente utilizamos
    # hasta hoy.
    if year == CURRENT_YEAR:

        end = local_today()

    all_games = []

    current = start

    while current <= end:

        block_end = min(
            current + timedelta(days=12),
            end
        )

        date_range = (
            current.strftime("%Y%m%d")
            + "-"
            + block_end.strftime("%Y%m%d")
        )

        data = api_get(
            f"{API}/scoreboard",
            {
                "dates": date_range,
                "limit": 1000
            }
        )

        games = parse_games(
            data
        )

        all_games.extend(
            games
        )

        current = (
            block_end
            + timedelta(days=1)
        )

    # Solo juegos terminados
    finished = []

    for game in all_games:

        status = str(
            game.get(
                "status",
                ""
            )
        ).lower()

        if (
            "final" in status
            or status == "final"
        ):

            finished.append(
                game
            )

    # Eliminar duplicados
    unique = {}

    for game in finished:

        unique[
            game["id"]
        ] = game

    return list(
        unique.values()
    )


# ============================================================
# CONVERTIR JUEGOS A ESTADÍSTICAS
# ============================================================

def build_stats(
    games
):

    teams = {}

    for game in games:

        home = game["home"]
        away = game["away"]

        hs = game["home_score"]
        aws = game["away_score"]

        if not home or not away:
            continue

        if home not in teams:

            teams[home] = {
                "games": 0,
                "wins": 0,
                "points_for": 0,
                "points_against": 0,
                "margins": [],
                "recent": [],
                "home_games": 0,
                "home_wins": 0
            }

        if away not in teams:

            teams[away] = {
                "games": 0,
                "wins": 0,
                "points_for": 0,
                "points_against": 0,
                "margins": [],
                "recent": [],
                "home_games": 0,
                "home_wins": 0
            }

        # HOME
        teams[home]["games"] += 1
        teams[home]["points_for"] += hs
        teams[home]["points_against"] += aws

        home_win = 1 if hs > aws else 0

        teams[home]["wins"] += home_win

        teams[home]["margins"].append(
            hs - aws
        )

        teams[home]["recent"].append(
            {
                "date": game["date"],
                "win": home_win,
                "margin": hs - aws
            }
        )

        teams[home]["home_games"] += 1

        teams[home]["home_wins"] += home_win

        # AWAY
        teams[away]["games"] += 1
        teams[away]["points_for"] += aws
        teams[away]["points_against"] += hs

        away_win = 1 if aws > hs else 0

        teams[away]["wins"] += away_win

        teams[away]["margins"].append(
            aws - hs
        )

        teams[away]["recent"].append(
            {
                "date": game["date"],
                "win": away_win,
                "margin": aws - hs
            }
        )

    return teams


# ============================================================
# PERFIL DEL EQUIPO
# ============================================================

def team_profile(
    team,
    stats
):

    if team not in stats:

        return {
            "games": 0,
            "win_pct": 0.50,
            "ppg": 21.5,
            "papg": 21.5,
            "margin": 0,
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

        recent_win_pct = np.mean(
            [
                x["win"]
                for x in recent
            ]
        )

        recent_margin = np.mean(
            [
                x["margin"]
                for x in recent
            ]
        )

    else:

        recent_win_pct = 0.50
        recent_margin = 0

    margin = np.mean(
        t["margins"]
    ) if t["margins"] else 0

    return {

        "games":
            t["games"],

        "win_pct":
            t["wins"] / games,

        "ppg":
            t["points_for"] / games,

        "papg":
            t["points_against"] / games,

        "margin":
            margin,

        "recent_win_pct":
            recent_win_pct,

        "recent_margin":
            recent_margin
    }


# ============================================================
# LESIONES
# ============================================================

@st.cache_data(ttl=600)
def get_team_injuries(
    team_id
):

    if not team_id:
        return []

    data = api_get(
        f"{API}/teams/{team_id}/injuries"
    )

    if not data:
        return []

    injuries = []

    # La estructura puede variar.
    # Buscamos recursivamente registros
    # de lesiones.

    def walk(obj):

        if isinstance(obj, dict):

            # Posibles nombres
            # utilizados por ESPN.
            status = (
                obj.get("status")
                or obj.get("injuryStatus")
                or obj.get("state")
                or ""
            )

            athlete = obj.get(
                "athlete",
                {}
            )

            if isinstance(
                athlete,
                dict
            ):

                name = (
                    athlete.get(
                        "displayName"
                    )
                    or athlete.get(
                        "shortName"
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

                    position = (
                        position.get(
                            "abbreviation",
                            ""
                        )
                    )

                if name and (
                    status
                    or position
                ):

                    injuries.append(
                        {
                            "name": name,
                            "status": str(
                                status
                            ),
                            "position": str(
                                position
                            )
                        }
                    )

            for value in obj.values():

                walk(value)

        elif isinstance(
            obj,
            list
        ):

            for item in obj:

                walk(item)

    walk(data)

    # Eliminar duplicados
    unique = {}

    for item in injuries:

        key = (
            item["name"],
            item["status"],
            item["position"]
        )

        unique[key] = item

    return list(
        unique.values()
    )


# ============================================================
# IMPACTO DE LESIONES
# ============================================================

POSITION_WEIGHT = {

    "QB": 1.00,

    "OT": 0.55,
    "OL": 0.55,
    "OG": 0.55,
    "C": 0.55,

    "WR": 0.45,
    "TE": 0.40,

    "RB": 0.35,

    "DE": 0.45,
    "DT": 0.45,
    "DL": 0.45,

    "LB": 0.40,

    "CB": 0.40,
    "S": 0.40,
    "DB": 0.40
}


def injury_impact(
    injuries
):

    score = 0

    important = 0

    for injury in injuries:

        status = (
            injury["status"]
            .lower()
        )

        position = (
            injury["position"]
            .upper()
        )

        # Solo lesiones que realmente
        # pueden afectar disponibilidad.

        if (
            "out" in status
            or "ir" in status
            or "reserve" in status
            or "pup" in status
        ):

            severity = 1.0

        elif "doubtful" in status:

            severity = 0.75

        elif "questionable" in status:

            severity = 0.35

        else:

            continue

        weight = POSITION_WEIGHT.get(
            position,
            0.15
        )

        score += (
            weight
            * severity
        )

        if weight >= 0.40:
            important += 1

    return score, important


# ============================================================
# LOGIT
# ============================================================

def sigmoid(
    value
):

    value = np.clip(
        value,
        -8,
        8
    )

    return (
        1
        /
        (
            1
            + np.exp(-value)
        )
    )


# ============================================================
# MODELO PRINCIPAL
# ============================================================

def calculate_model(
    game,
    stats,
    home_injuries,
    away_injuries
):

    home = team_profile(
        game["home"],
        stats
    )

    away = team_profile(
        game["away"],
        stats
    )

    # --------------------------------------------
    # FACTORES ESTADÍSTICOS
    # --------------------------------------------

    overall = (
        home["win_pct"]
        - away["win_pct"]
    )

    recent = (
        home["recent_win_pct"]
        - away["recent_win_pct"]
    )

    offense = (
        home["ppg"]
        - away["ppg"]
    )

    defense = (
        away["papg"]
        - home["papg"]
    )

    margin = (
        home["recent_margin"]
        - away["recent_margin"]
    )

    # --------------------------------------------
    # LESIONES
    # --------------------------------------------

    home_injury_score, home_important = (
        injury_impact(
            home_injuries
        )
    )

    away_injury_score, away_important = (
        injury_impact(
            away_injuries
        )
    )

    # Positivo favorece HOME.
    injury_difference = (
        away_injury_score
        - home_injury_score
    )

    # --------------------------------------------
    # LOCALÍA
    # --------------------------------------------

    home_advantage = 0.12

    # --------------------------------------------
    # SCORE
    #
    # IMPORTANTE:
    # NO entra ninguna cuota.
    # --------------------------------------------

    score = (

        overall * 1.00

        + recent * 1.25

        + offense * 0.025

        + defense * 0.025

        + margin * 0.025

        + injury_difference * 0.10

        + home_advantage
    )

    probability = sigmoid(
        score * 2.15
    )

    # --------------------------------------------
    # PRETEMPORADA
    #
    # Reducimos confianza porque las rotaciones
    # hacen que el resultado sea mucho menos
    # predecible.
    # --------------------------------------------

    is_preseason = (
        "preseason"
        in str(
            game.get(
                "season_type",
                ""
            )
        ).lower()
        or "preseason"
        in str(
            game.get(
                "notes",
                ""
            )
        ).lower()
    )

    if is_preseason:

        probability = (
            probability * 0.72
            + 0.50 * 0.28
        )

    # --------------------------------------------
    # LIMITAR EXTREMOS
    # --------------------------------------------

    probability = np.clip(
        probability,
        0.20,
        0.80
    )

    away_probability = (
        1
        - probability
    )

    if probability >= away_probability:

        pick = game["home"]

        pick_probability = probability

    else:

        pick = game["away"]

        pick_probability = (
            away_probability
        )

    # --------------------------------------------
    # CONFIANZA
    # --------------------------------------------

    difference = abs(
        probability
        - 0.50
    )

    if difference >= 0.15:

        signal = "FUERTE"

    elif difference >= 0.08:

        signal = "MODERADA"

    else:

        signal = "CERRADA"

    return {

        "pick":
            pick,

        "probability":
            pick_probability,

        "home_probability":
            probability,

        "away_probability":
            away_probability,

        "signal":
            signal,

        "home_injuries":
            home_important,

        "away_injuries":
            away_important,

        "is_preseason":
            is_preseason
    }


# ============================================================
# CARGAR HISTÓRICO
# ============================================================

with st.spinner(
    "🧠 Preparando modelo..."
):

    games_2025 = (
        get_historical_games(
            HISTORICAL_YEAR
        )
    )

    games_2026 = (
        get_historical_games(
            CURRENT_YEAR
        )
    )


historical_games = (
    games_2025
    + games_2026
)


stats = build_stats(
    historical_games
)


# ============================================================
# PARTIDOS DE HOY
# ============================================================

today_games = (
    get_today_games()
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

st.caption(
    "🚫 Las cuotas de sportsbooks NO se utilizan para generar las probabilidades."
)

st.divider()


st.header(
    "🏈 PARTIDOS DE HOY"
)


# ============================================================
# SI NO HAY PARTIDOS
# ============================================================

if not today_games:

    st.info(
        "No se encontraron partidos NFL para hoy."
    )

    st.caption(
        "La aplicación consulta automáticamente "
        "el calendario NFL y también contempla "
        "partidos de pretemporada."
    )


# ============================================================
# MOSTRAR PARTIDOS
# ============================================================

for game in today_games:

    home_injuries = (
        get_team_injuries(
            game["home_id"]
        )
    )

    away_injuries = (
        get_team_injuries(
            game["away_id"]
        )
    )

    result = calculate_model(
        game,
        stats,
        home_injuries,
        away_injuries
    )

    home_pct = (
        result["home_probability"]
        * 100
    )

    away_pct = (
        result["away_probability"]
        * 100
    )

    pick_pct = (
        result["probability"]
        * 100
    )

    st.markdown(
        '<div class="game-card">',
        unsafe_allow_html=True
    )

    # --------------------------------------------------------
    # PARTIDO
    # --------------------------------------------------------

    c1, c2, c3 = st.columns(
        [2, 1, 2]
    )

    with c1:

        st.subheader(
            game["away"]
        )

        st.write(
            f"Probabilidad: **{away_pct:.1f}%**"
        )

    with c2:

        st.markdown(
            "<h2 style='text-align:center'>@</h2>",
            unsafe_allow_html=True
        )

    with c3:

        st.subheader(
            game["home"]
        )

        st.write(
            f"Probabilidad: **{home_pct:.1f}%**"
        )

    st.divider()

    # --------------------------------------------------------
    # PICK
    # --------------------------------------------------------

    st.markdown(
        f"""
        <div class="pick-title">
        🎯 PICK DEL MODELO: {result["pick"]}
        </div>

        <div class="probability">
        {pick_pct:.1f}%
        </div>
        """,
        unsafe_allow_html=True
    )

    # --------------------------------------------------------
    # SEÑAL
    # --------------------------------------------------------

    if result["signal"] == "FUERTE":

        st.success(
            f"🟢 SEÑAL FUERTE — "
            f"{result['pick']} "
            f"{pick_pct:.1f}%"
        )

    elif result["signal"] == "MODERADA":

        st.warning(
            f"🟡 SEÑAL MODERADA — "
            f"{result['pick']} "
            f"{pick_pct:.1f}%"
        )

    else:

        st.info(
            f"⚪ PARTIDO CERRADO — "
            f"{result['pick']} "
            f"{pick_pct:.1f}%"
        )

    # --------------------------------------------------------
    # INFORMACIÓN MÍNIMA
    # --------------------------------------------------------

    factors = []

    factors.append(
        "📊 Histórico 2025 + 2026 disponible"
    )

    factors.append(
        "🏠 Localía"
    )

    factors.append(
        "📈 Rendimiento reciente"
    )

    factors.append(
        "⚔️ Ataque y defensa"
    )

    factors.append(
        "📉 Diferencial de puntos"
    )

    if (
        result["home_injuries"] > 0
        or result["away_injuries"] > 0
    ):

        factors.append(
            "🏥 Lesiones disponibles"
        )

    if result["is_preseason"]:

        factors.append(
            "⚠️ Ajuste por incertidumbre de pretemporada"
        )

    with st.expander(
        "🧠 Factores utilizados"
    ):

        for factor in factors:

            st.write(
                f"• {factor}"
            )

    st.markdown(
        "</div>",
        unsafe_allow_html=True
    )


# ============================================================
# EXPLICACIÓN MUY CORTA
# ============================================================

st.divider()

with st.expander(
    "ℹ️ ¿Qué significa el porcentaje?"
):

    st.write(
        """
        Ejemplo:

        Si el modelo muestra:

        SEA — 68%

        significa que, según los datos utilizados
        por nuestro modelo, Seattle tiene una
        probabilidad estimada de aproximadamente
        68% de ganar.

        NO significa que sea una apuesta segura.

        La idea es que tú compares ese porcentaje
        con la cuota que ofrece la casa.

        El modelo calcula primero su probabilidad.
        La cuota de la casa se analiza después,
        fuera del modelo.
        """
    )


st.caption(
    "NFL EDGE — Modelo experimental independiente. "
    "No garantiza resultados."
)
