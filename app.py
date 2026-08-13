import streamlit as st
import requests
import math
from datetime import datetime
from zoneinfo import ZoneInfo


# ============================================================
# CONFIGURACIÓN
# ============================================================

st.set_page_config(
    page_title="Monitor 60% NFL",
    page_icon="🏈",
    layout="centered"
)

DALLAS_TZ = ZoneInfo("America/Chicago")

# Temporada histórica que utilizaremos como base.
BASE_SEASON = 2025

ESPN_BASE = (
    "https://site.api.espn.com/apis/site/v2/"
    "sports/football/nfl"
)


# ============================================================
# ESTILO
# ============================================================

st.markdown(
    """
    <style>

    .stApp {
        background-color: #0d0f14;
    }

    .title {
        font-size: 42px;
        font-weight: 800;
        margin-bottom: 5px;
    }

    .subtitle {
        color: #9ca3af;
        font-size: 19px;
        margin-bottom: 25px;
    }

    .pick-card {
        background: #15181d;
        border: 1px solid #292d35;
        border-radius: 18px;
        padding: 22px;
        margin-bottom: 22px;
    }

    .probability {
        font-size: 48px;
        font-weight: 800;
        margin: 8px 0;
    }

    .strong {
        background: #163a29;
        color: #72e39b;
        padding: 15px;
        border-radius: 12px;
        font-size: 19px;
        font-weight: 700;
    }

    .good {
        background: #3a3216;
        color: #f4d35e;
        padding: 15px;
        border-radius: 12px;
        font-size: 19px;
        font-weight: 700;
    }

    .moderate {
        background: #3a2916;
        color: #ffb45c;
        padding: 15px;
        border-radius: 12px;
        font-size: 19px;
        font-weight: 700;
    }

    .stat-box {
        background: #15181d;
        border-radius: 12px;
        padding: 12px;
        margin-top: 8px;
    }

    </style>
    """,
    unsafe_allow_html=True
)


# ============================================================
# FUNCIONES GENERALES
# ============================================================

def safe_float(value, default=0.0):

    try:
        return float(value)
    except Exception:
        return default


def logistic(x):

    try:
        return 1 / (1 + math.exp(-x))

    except OverflowError:

        if x > 0:
            return 1.0

        return 0.0


# ============================================================
# OBTENER PARTIDOS DE HOY
# ============================================================

@st.cache_data(ttl=60)
def get_today_games():

    url = (
        f"{ESPN_BASE}/scoreboard"
    )

    try:

        response = requests.get(
            url,
            params={
                "limit": 1000
            },
            timeout=30
        )

        if response.status_code != 200:

            return None, (
                f"ESPN respondió "
                f"{response.status_code}"
            )

        data = response.json()

        today = datetime.now(
            DALLAS_TZ
        ).date()

        games = []

        for event in data.get(
            "events",
            []
        ):

            date_string = event.get(
                "date"
            )

            if not date_string:
                continue

            try:

                dt = datetime.fromisoformat(
                    date_string.replace(
                        "Z",
                        "+00:00"
                    )
                )

                local_dt = dt.astimezone(
                    DALLAS_TZ
                )

            except Exception:

                continue

            # SOLO HOY
            if local_dt.date() != today:
                continue

            competitions = event.get(
                "competitions",
                []
            )

            if not competitions:
                continue

            competition = competitions[0]

            competitors = (
                competition.get(
                    "competitors",
                    []
                )
            )

            if len(competitors) < 2:
                continue

            home = None
            away = None

            for competitor in competitors:

                if competitor.get(
                    "homeAway"
                ) == "home":

                    home = competitor

                elif competitor.get(
                    "homeAway"
                ) == "away":

                    away = competitor

            if not home or not away:
                continue

            games.append({

                "id":
                    event.get("id"),

                "name":
                    event.get(
                        "name",
                        "NFL Game"
                    ),

                "date":
                    local_dt,

                "home":
                    home,

                "away":
                    away

            })

        games.sort(
            key=lambda x: x["date"]
        )

        return games, None

    except Exception as e:

        return None, (
            f"Error obteniendo "
            f"partidos: {e}"
        )


# ============================================================
# OBTENER EQUIPOS NFL
# ============================================================

@st.cache_data(ttl=86400)
def get_teams():

    url = (
        f"{ESPN_BASE}/teams"
    )

    try:

        response = requests.get(
            url,
            params={
                "limit": 100
            },
            timeout=30
        )

        if response.status_code != 200:

            return {}, (
                f"ESPN teams error "
                f"{response.status_code}"
            )

        data = response.json()

        teams = {}

        sports = data.get(
            "sports",
            []
        )

        for sport in sports:

            leagues = sport.get(
                "leagues",
                []
            )

            for league in leagues:

                for item in league.get(
                    "teams",
                    []
                ):

                    team = item.get(
                        "team",
                        {}
                    )

                    team_id = team.get(
                        "id"
                    )

                    name = team.get(
                        "displayName"
                    )

                    abbreviation = team.get(
                        "abbreviation"
                    )

                    if team_id and name:

                        teams[str(team_id)] = {
                            "id": str(team_id),
                            "name": name,
                            "abbreviation":
                                abbreviation
                        }

        return teams, None

    except Exception as e:

        return {}, str(e)


# ============================================================
# OBTENER TEMPORADA DE UN EQUIPO
# ============================================================

@st.cache_data(ttl=86400)
def get_team_schedule(
    team_id,
    season=BASE_SEASON
):

    url = (
        f"{ESPN_BASE}/teams/"
        f"{team_id}/schedule"
    )

    params = {
        "season": season,
        "seasontype": 2
    }

    try:

        response = requests.get(
            url,
            params=params,
            timeout=30
        )

        if response.status_code != 200:

            return []

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

            competitors = (
                competition.get(
                    "competitors",
                    []
                )
            )

            if len(competitors) != 2:
                continue

            team_competitor = None
            opponent_competitor = None

            for competitor in competitors:

                competitor_team = (
                    competitor.get(
                        "team",
                        {}
                    )
                )

                competitor_id = str(
                    competitor_team.get(
                        "id",
                        ""
                    )
                )

                if competitor_id == str(
                    team_id
                ):

                    team_competitor = (
                        competitor
                    )

                else:

                    opponent_competitor = (
                        competitor
                    )

            if (
                not team_competitor
                or not opponent_competitor
            ):
                continue

            # ------------------------------------------------
            # SCORES
            # ------------------------------------------------

            team_score = safe_float(
                team_competitor.get(
                    "score",
                    0
                )
            )

            opponent_score = safe_float(
                opponent_competitor.get(
                    "score",
                    0
                )
            )

            # ------------------------------------------------
            # FECHA
            # ------------------------------------------------

            date_string = event.get(
                "date"
            )

            game_date = None

            if date_string:

                try:

                    game_date = datetime.fromisoformat(
                        date_string.replace(
                            "Z",
                            "+00:00"
                        )
                    )

                except Exception:

                    pass

            # ------------------------------------------------
            # LOCAL / VISITANTE
            # ------------------------------------------------

            home_away = team_competitor.get(
                "homeAway"
            )

            completed = competition.get(
                "status",
                {}
            ).get(
                "type",
                {}
            ).get(
                "completed",
                False
            )

            if not completed:
                continue

            games.append({

                "date":
                    game_date,

                "team_score":
                    team_score,

                "opponent_score":
                    opponent_score,

                "point_diff":
                    team_score
                    - opponent_score,

                "home":
                    home_away == "home",

                "win":
                    team_score
                    > opponent_score

            })

        games.sort(
            key=lambda x:
                x["date"]
                if x["date"]
                else datetime.min.replace(
                    tzinfo=ZoneInfo("UTC")
                )
        )

        return games

    except Exception:

        return []


# ============================================================
# CALCULAR ESTADÍSTICAS
# ============================================================

def calculate_stats(
    games,
    current_date=None
):

    if not games:

        return {

            "games": 0,

            "wins": 0,

            "losses": 0,

            "win_rate": 0.50,

            "points_for": 0,

            "points_against": 0,

            "point_diff": 0,

            "recent_win_rate": 0.50,

            "recent_point_diff": 0,

            "home_win_rate": 0.50,

            "away_win_rate": 0.50

        }

    # ========================================================
    # FILTRAR SOLO PARTIDOS ANTERIORES
    # ========================================================

    if current_date:

        usable = []

        for game in games:

            if (
                game["date"]
                and game["date"] < current_date
            ):

                usable.append(game)

        games = usable

    if not games:

        return {

            "games": 0,

            "wins": 0,

            "losses": 0,

            "win_rate": 0.50,

            "points_for": 0,

            "points_against": 0,

            "point_diff": 0,

            "recent_win_rate": 0.50,

            "recent_point_diff": 0,

            "home_win_rate": 0.50,

            "away_win_rate": 0.50

        }

    # ========================================================
    # ÚLTIMOS 10
    # ========================================================

    games = games[-10:]

    total = len(games)

    wins = sum(
        1
        for g in games
        if g["win"]
    )

    losses = total - wins

    points_for = sum(
        g["team_score"]
        for g in games
    ) / total

    points_against = sum(
        g["opponent_score"]
        for g in games
    ) / total

    point_diff = (
        points_for
        - points_against
    )

    # ========================================================
    # ÚLTIMOS 5
    # ========================================================

    recent = games[-5:]

    recent_total = len(
        recent
    )

    recent_wins = sum(
        1
        for g in recent
        if g["win"]
    )

    recent_win_rate = (
        recent_wins
        / recent_total
    )

    recent_point_diff = sum(
        g["point_diff"]
        for g in recent
    ) / recent_total

    # ========================================================
    # LOCAL
    # ========================================================

    home_games = [
        g
        for g in games
        if g["home"]
    ]

    if home_games:

        home_win_rate = (
            sum(
                1
                for g in home_games
                if g["win"]
            )
            / len(home_games)
        )

    else:

        home_win_rate = 0.50

    # ========================================================
    # VISITANTE
    # ========================================================

    away_games = [
        g
        for g in games
        if not g["home"]
    ]

    if away_games:

        away_win_rate = (
            sum(
                1
                for g in away_games
                if g["win"]
            )
            / len(away_games)
        )

    else:

        away_win_rate = 0.50

    return {

        "games": total,

        "wins": wins,

        "losses": losses,

        "win_rate":
            wins / total,

        "points_for":
            points_for,

        "points_against":
            points_against,

        "point_diff":
            point_diff,

        "recent_win_rate":
            recent_win_rate,

        "recent_point_diff":
            recent_point_diff,

        "home_win_rate":
            home_win_rate,

        "away_win_rate":
            away_win_rate

    }


# ============================================================
# MODELO PROPIO
# ============================================================

def calculate_probability(
    home_stats,
    away_stats
):

    # ========================================================
    # FACTOR 1
    # DIFERENCIAL DE PUNTOS
    # PESO: 25%
    # ========================================================

    point_diff_difference = (
        home_stats["point_diff"]
        - away_stats["point_diff"]
    )

    point_component = (
        point_diff_difference
        / 20
    )

    # ========================================================
    # FACTOR 2
    # FORMA ÚLTIMOS 5
    # PESO: 20%
    # ========================================================

    form_difference = (
        home_stats["recent_win_rate"]
        - away_stats["recent_win_rate"]
    )

    form_component = (
        form_difference
    )

    # ========================================================
    # FACTOR 3
    # RÉCORD
    # PESO: 15%
    # ========================================================

    record_difference = (
        home_stats["win_rate"]
        - away_stats["win_rate"]
    )

    record_component = (
        record_difference
    )

    # ========================================================
    # FACTOR 4
    # OFENSIVA
    # PESO: 15%
    # ========================================================

    offense_difference = (
        home_stats["points_for"]
        - away_stats["points_for"]
    )

    offense_component = (
        offense_difference
        / 20
    )

    # ========================================================
    # FACTOR 5
    # DEFENSA
    # PESO: 15%
    # ========================================================

    defense_difference = (
        away_stats["points_against"]
        - home_stats["points_against"]
    )

    defense_component = (
        defense_difference
        / 20
    )

    # ========================================================
    # FACTOR 6
    # LOCAL / VISITANTE
    # PESO: 5%
    # ========================================================

    location_difference = (
        home_stats["home_win_rate"]
        - away_stats["away_win_rate"]
    )

    location_component = (
        location_difference
    )

    # ========================================================
    # FACTOR 7
    # DIFERENCIAL RECIENTE
    # PESO: 5%
    # ========================================================

    recent_difference = (
        home_stats["recent_point_diff"]
        - away_stats["recent_point_diff"]
    )

    recent_component = (
        recent_difference
        / 20
    )

    # ========================================================
    # SCORE DEL MODELO
    # ========================================================

    score = (

        point_component * 2.5

        + form_component * 2.0

        + record_component * 1.5

        + offense_component * 1.5

        + defense_component * 1.5

        + location_component * 0.5

        + recent_component * 0.5

    )

    # ========================================================
    # VENTAJA DE LOCAL
    #
    # Pequeña ventaja fija.
    # NO viene de cuotas.
    # ========================================================

    score += 0.12

    home_probability = logistic(
        score
    )

    # ========================================================
    # LIMITES RAZONABLES
    # ========================================================

    home_probability = max(
        0.50,
        min(
            0.90,
            home_probability
        )
    )

    away_probability = (
        1
        - home_probability
    )

    return (
        home_probability,
        away_probability
    )


# ============================================================
# ANALIZAR PARTIDO
# ============================================================

def analyze_game(
    game,
    teams
):

    home_team = game["home"]
    away_team = game["away"]

    home_team_info = (
        home_team.get(
            "team",
            {}
        )
    )

    away_team_info = (
        away_team.get(
            "team",
            {}
        )
    )

    home_id = str(
        home_team_info.get(
            "id",
            ""
        )
    )

    away_id = str(
        away_team_info.get(
            "id",
            ""
        )
    )

    home_name = (
        home_team_info.get(
            "displayName",
            "Home"
        )
    )

    away_name = (
        away_team_info.get(
            "displayName",
            "Away"
        )
    )

    if not home_id or not away_id:

        return None

    # ========================================================
    # FECHA DEL PARTIDO
    # ========================================================

    game_date = game["date"]

    # ========================================================
    # HISTORIAL 2025
    # ========================================================

    home_history = get_team_schedule(
        home_id,
        BASE_SEASON
    )

    away_history = get_team_schedule(
        away_id,
        BASE_SEASON
    )

    # ========================================================
    # ESTADÍSTICAS
    # ========================================================

    home_stats = calculate_stats(
        home_history
    )

    away_stats = calculate_stats(
        away_history
    )

    # ========================================================
    # SI NO HAY DATOS
    # ========================================================

    if (
        home_stats["games"] < 5
        or away_stats["games"] < 5
    ):

        return None

    # ========================================================
    # PROBABILIDAD PROPIA
    # ========================================================

    home_probability, away_probability = (
        calculate_probability(
            home_stats,
            away_stats
        )
    )

    # ========================================================
    # ELEGIR MEJOR LADO
    # ========================================================

    if home_probability >= away_probability:

        pick = home_name
        probability = home_probability

    else:

        pick = away_name
        probability = away_probability

    return {

        "home":
            home_name,

        "away":
            away_name,

        "pick":
            pick,

        "probability":
            probability,

        "home_probability":
            home_probability,

        "away_probability":
            away_probability,

        "home_stats":
            home_stats,

        "away_stats":
            away_stats,

        "date":
            game_date

    }


# ============================================================
# CLASIFICACIÓN
# ============================================================

def probability_label(probability):

    percentage = (
        probability * 100
    )

    if percentage >= 70:

        return (
            "🟢 PROBABILIDAD ALTA",
            "strong"
        )

    elif percentage >= 65:

        return (
            "🟡 PROBABILIDAD INTERESANTE",
            "good"
        )

    elif percentage >= 60:

        return (
            "🟠 PROBABILIDAD MODERADA",
            "moderate"
        )

    else:

        return (
            "⚪ PROBABILIDAD BAJA",
            "moderate"
        )


# ============================================================
# MOSTRAR PICK
# ============================================================

def display_pick(
    result,
    ranking
):

    probability = (
        result["probability"]
        * 100
    )

    label, css_class = (
        probability_label(
            result["probability"]
        )
    )

    home_stats = result[
        "home_stats"
    ]

    away_stats = result[
        "away_stats"
    ]

    st.markdown(
        f"""
        <div class="pick-card">

        <h2>
        #{ranking} 🏈 {result["pick"]}
        </h2>

        <p>
        {result["away"]}
        vs
        {result["home"]}
        </p>

        <div class="{css_class}">
        {label}
        </div>

        <div class="probability">
        {probability:.1f}%
        </div>

        <p>
        <b>Probabilidad Monitor 60%</b>
        </p>

        <p>
        🏈 {result["away"]}:
        {result["away_probability"] * 100:.1f}%
        </p>

        <p>
        🏈 {result["home"]}:
        {result["home_probability"] * 100:.1f}%
        </p>

        </div>
        """,
        unsafe_allow_html=True
    )

    # ========================================================
    # DATOS QUE UTILIZÓ EL MODELO
    # ========================================================

    with st.expander(
        "📊 Ver datos utilizados"
    ):

        col1, col2 = st.columns(2)

        with col1:

            st.markdown(
                f"### {result['away']}"
            )

            st.write(
                f"Récord 2025: "
                f"{away_stats['wins']}-"
                f"{away_stats['losses']}"
            )

            st.write(
                f"Puntos por partido: "
                f"{away_stats['points_for']:.1f}"
            )

            st.write(
                f"Puntos permitidos: "
                f"{away_stats['points_against']:.1f}"
            )

            st.write(
                f"Diferencial: "
                f"{away_stats['point_diff']:+.1f}"
            )

            st.write(
                f"Últimos 5: "
                f"{away_stats['recent_win_rate'] * 100:.1f}%"
            )

        with col2:

            st.markdown(
                f"### {result['home']}"
            )

            st.write(
                f"Récord 2025: "
                f"{home_stats['wins']}-"
                f"{home_stats['losses']}"
            )

            st.write(
                f"Puntos por partido: "
                f"{home_stats['points_for']:.1f}"
            )

            st.write(
                f"Puntos permitidos: "
                f"{home_stats['points_against']:.1f}"
            )

            st.write(
                f"Diferencial: "
                f"{home_stats['point_diff']:+.1f}"
            )

            st.write(
                f"Últimos 5: "
                f"{home_stats['recent_win_rate'] * 100:.1f}%"
            )


# ============================================================
# ENCABEZADO
# ============================================================

st.markdown(
    """
    <div class="title">
    🏈 Monitor 60%
    </div>

    <div class="subtitle">
    Probabilidad propia NFL — sin cuotas
    </div>
    """,
    unsafe_allow_html=True
)

st.caption(
    "Las cuotas de las casas NO participan "
    "en el cálculo de esta probabilidad."
)


# ============================================================
# BOTÓN
# ============================================================

scan = st.button(
    "🔎 ESCANEAR NFL DE HOY",
    use_container_width=True
)


# ============================================================
# ESCANEO
# ============================================================

if scan:

    # --------------------------------------------------------
    # PARTIDOS
    # --------------------------------------------------------

    with st.spinner(
        "Buscando partidos NFL de hoy..."
    ):

        games, games_error = (
            get_today_games()
        )

    if games_error:

        st.error(
            games_error
        )

        st.stop()

    if not games:

        st.warning(
            "No encontramos partidos NFL "
            "para HOY."
        )

        st.write(
            "Fecha en Dallas: "
            f"**{datetime.now(DALLAS_TZ).strftime('%m/%d/%Y')}**"
        )

        st.stop()

    # --------------------------------------------------------
    # EQUIPOS
    # --------------------------------------------------------

    with st.spinner(
        "Cargando equipos y estadísticas..."
    ):

        teams, teams_error = (
            get_teams()
        )

    if teams_error:

        st.error(
            teams_error
        )

        st.stop()

    # ========================================================
    # PARTIDOS DE HOY
    # ========================================================

    st.header(
        f"📅 PARTIDOS DE HOY — NFL"
    )

    st.success(
        f"{len(games)} partido(s) encontrados."
    )

    for index, game in enumerate(
        games,
        start=1
    ):

        dt = game["date"]

        time_string = (
            dt.strftime(
                "%I:%M %p"
            ).lstrip("0")
        )

        away_name = (
            game["away"]
            .get("team", {})
            .get(
                "displayName",
                "Away"
            )
        )

        home_name = (
            game["home"]
            .get("team", {})
            .get(
                "displayName",
                "Home"
            )
        )

        st.write(
            f"**{index}. "
            f"{away_name} vs "
            f"{home_name}**"
        )

        st.caption(
            f"🕐 HOY — {time_string}"
        )

    st.divider()

    # ========================================================
    # MODELO
    # ========================================================

    st.header(
        "🧠 PROBABILIDAD PROPIA"
    )

    st.caption(
        "Esta sección NO utiliza cuotas "
        "de ninguna casa de apuestas."
    )

    analyzed = []

    with st.spinner(
        "Calculando probabilidades..."
    ):

        for game in games:

            result = analyze_game(
                game,
                teams
            )

            if result:

                analyzed.append(
                    result
                )

    # ========================================================
    # ORDENAR
    # ========================================================

    analyzed.sort(
        key=lambda x:
            x["probability"],
        reverse=True
    )

    # ========================================================
    # TOP 3
    # ========================================================

    if not analyzed:

        st.error(
            "No pudimos calcular probabilidades "
            "con los datos históricos disponibles."
        )

        st.stop()

    top3 = analyzed[:3]

    for ranking, result in enumerate(
        top3,
        start=1
    ):

        display_pick(
            result,
            ranking
        )

    # ========================================================
    # TABLA GENERAL
    # ========================================================

    st.divider()

    st.header(
        "📊 Todos los partidos analizados"
    )

    for ranking, result in enumerate(
        analyzed,
        start=1
    ):

        st.write(
            f"**#{ranking} "
            f"{result['pick']} — "
            f"{result['probability'] * 100:.1f}%**"
        )

        st.caption(
            f"{result['away']} vs "
            f"{result['home']}"
        )


# ============================================================
# PANTALLA INICIAL
# ============================================================

else:

    st.info(
        "Presiona **🔎 ESCANEAR NFL DE HOY** "
        "para calcular nuestras propias "
        "probabilidades."
    )

    st.write(
        "### 🧠 El modelo utiliza:"
    )

    st.write(
        "• Diferencial de puntos"
    )

    st.write(
        "• Forma de los últimos 5 partidos"
    )

    st.write(
        "• Récord"
    )

    st.write(
        "• Producción ofensiva"
    )

    st.write(
        "• Defensa"
    )

    st.write(
        "• Rendimiento local/visitante"
    )

    st.write(
        "• Diferencial reciente"
    )

    st.caption(
        "Las cuotas de apuestas no se utilizan "
        "para calcular la probabilidad."
    )
