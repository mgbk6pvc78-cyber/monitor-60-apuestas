import streamlit as st
import requests
import math
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


# ============================================================
# 🏈 MONITOR NFL
# ============================================================

st.set_page_config(
    page_title="Monitor NFL",
    page_icon="🏈",
    layout="wide"
)


# ============================================================
# CONFIGURACIÓN
# ============================================================

TIMEZONE = "America/Chicago"

HISTORICAL_SEASON = 2025

DAYS_AHEAD = 14

SCOREBOARD_URL = (
    "https://site.api.espn.com/apis/site/v2/"
    "sports/football/nfl/scoreboard"
)

TEAM_SCHEDULE_URL = (
    "https://site.api.espn.com/apis/site/v2/"
    "sports/football/nfl/teams/{team_id}/schedule"
)


# ============================================================
# ESTILO
# ============================================================

st.markdown(
    """
    <style>

    .main {
        background-color: #0e0f15;
    }

    .block-container {
        padding-top: 2rem;
        padding-bottom: 3rem;
        max-width: 1100px;
    }

    h1, h2, h3 {
        color: #f5f5f5;
    }

    .subtitle {
        color: #9da0aa;
        font-size: 1.2rem;
        margin-bottom: 25px;
    }

    .game-card {
        background: #171820;
        border: 1px solid #343641;
        border-radius: 22px;
        padding: 28px;
        margin-top: 25px;
        margin-bottom: 35px;
    }

    .prob {
        font-size: 3rem;
        font-weight: 700;
        color: white;
        margin-top: 5px;
    }

    .label {
        color: #9da0aa;
        font-size: 1rem;
    }

    .green-box {
        background: #183727;
        border: 1px solid #3d8258;
        border-radius: 18px;
        padding: 22px;
        color: #a9e8bd;
        margin-top: 22px;
    }

    .blue-box {
        background: #1c3049;
        border-radius: 18px;
        padding: 22px;
        color: #64aaff;
        margin-top: 22px;
    }

    .yellow-box {
        background: #3b351c;
        border: 1px solid #85752a;
        border-radius: 18px;
        padding: 22px;
        color: #fff0a0;
        margin-top: 22px;
    }

    .red-box {
        background: #422329;
        border: 1px solid #7b3e48;
        border-radius: 18px;
        padding: 22px;
        color: #ff9a9a;
        margin-top: 22px;
    }

    .small-text {
        color: #8f929c;
        font-size: 0.9rem;
    }

    </style>
    """,
    unsafe_allow_html=True
)


# ============================================================
# UTILIDADES
# ============================================================

def safe_float(value, default=0.0):

    try:

        if value is None:
            return default

        if isinstance(value, dict):

            for key in [
                "value",
                "displayValue",
                "score"
            ]:

                if key in value:

                    return safe_float(
                        value[key],
                        default
                    )

            return default

        if isinstance(value, str):

            value = value.replace(",", "").strip()

            if value == "":
                return default

        return float(value)

    except Exception:

        return default


def clamp(
    value,
    minimum,
    maximum
):

    return max(
        minimum,
        min(maximum, value)
    )


def american_odds(probability):

    probability = clamp(
        probability,
        0.01,
        0.99
    )

    if probability >= 0.5:

        odds = -(
            probability /
            (1 - probability)
        ) * 100

    else:

        odds = (
            (1 - probability) /
            probability
        ) * 100

    return int(
        round(odds)
    )


# ============================================================
# HTTP
# ============================================================

@st.cache_data(ttl=300)
def get_json(
    url,
    params=None
):

    headers = {

        "User-Agent":
            "Mozilla/5.0 "
            "(iPhone; CPU iPhone OS 18_0) "
            "AppleWebKit/605.1.15",

        "Accept":
            "application/json"
    }

    try:

        response = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=20
        )

        response.raise_for_status()

        return response.json()

    except Exception as e:

        return {
            "_error": str(e)
        }


# ============================================================
# CALENDARIO NFL
# ============================================================

@st.cache_data(ttl=300)
def get_nfl_schedule():

    now = datetime.now(
        ZoneInfo(TIMEZONE)
    )

    today = now.date()

    end_date = (
        today +
        timedelta(days=DAYS_AHEAD)
    )

    params = {

        "dates":
            f"{today.strftime('%Y%m%d')}-"
            f"{end_date.strftime('%Y%m%d')}"
    }

    data = get_json(
        SCOREBOARD_URL,
        params
    )

    if "_error" in data:

        return [], data["_error"]

    games = []

    for event in data.get(
        "events",
        []
    ):

        try:

            competitions = (
                event.get(
                    "competitions",
                    []
                )
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

            away = None
            home = None

            for competitor in competitors:

                location = competitor.get(
                    "homeAway"
                )

                if location == "away":

                    away = competitor

                elif location == "home":

                    home = competitor

            if not away or not home:
                continue

            games.append(
                {
                    "id":
                        event.get("id"),

                    "date":
                        event.get("date"),

                    "name":
                        event.get("name"),

                    "short_name":
                        event.get("shortName"),

                    "away":
                        away,

                    "home":
                        home,

                    "odds":
                        competition.get(
                            "odds",
                            []
                        ),

                    "status":
                        event.get(
                            "status",
                            {}
                        )
                }
            )

        except Exception:

            continue

    games.sort(
        key=lambda x:
            x.get("date", "")
    )

    return games, None


# ============================================================
# HISTORIAL
# ============================================================

@st.cache_data(ttl=3600)
def get_historical_schedule(
    team_id
):

    url = TEAM_SCHEDULE_URL.format(
        team_id=team_id
    )

    params = {

        "season":
            HISTORICAL_SEASON,

        "seasontype":
            2
    }

    data = get_json(
        url,
        params
    )

    if "_error" in data:

        return [], data["_error"]

    return (
        data.get(
            "events",
            []
        ),
        None
    )


# ============================================================
# ANALIZAR HISTORIAL
# ============================================================

@st.cache_data(ttl=3600)
def analyze_team_history(
    team_id
):

    events, error = (
        get_historical_schedule(
            team_id
        )
    )

    if error:

        return {

            "available":
                False,

            "wins":
                0,

            "losses":
                0,

            "games":
                0,

            "win_rate":
                0.5,

            "avg_margin":
                0.0,

            "recent_win_rate":
                0.5,

            "recent_margin":
                0.0,

            "rating":
                50.0,

            "error":
                error
        }

    completed = []

    for event in events:

        try:

            competitions = (
                event.get(
                    "competitions",
                    []
                )
            )

            if not competitions:
                continue

            competition = competitions[0]

            status = (
                competition
                .get(
                    "status",
                    {}
                )
                .get(
                    "type",
                    {}
                )
            )

            if not status.get(
                "completed",
                False
            ):

                continue

            competitors = (
                competition.get(
                    "competitors",
                    []
                )
            )

            if len(competitors) != 2:
                continue

            me = None
            opponent = None

            for competitor in competitors:

                team = competitor.get(
                    "team",
                    {}
                )

                current_id = str(
                    team.get("id")
                )

                if current_id == str(
                    team_id
                ):

                    me = competitor

                else:

                    opponent = competitor

            if not me or not opponent:
                continue

            my_score = safe_float(
                me.get("score")
            )

            opp_score = safe_float(
                opponent.get("score")
            )

            # ------------------------------------------------
            # IMPORTANTE:
            # No aceptamos un partido si ESPN devolvió
            # ambos marcadores como 0.
            # ------------------------------------------------

            if (
                my_score == 0
                and
                opp_score == 0
            ):

                continue

            margin = (
                my_score -
                opp_score
            )

            completed.append(
                {
                    "date":
                        event.get(
                            "date",
                            ""
                        ),

                    "win":
                        1 if margin > 0
                        else 0,

                    "margin":
                        margin,

                    "points_for":
                        my_score,

                    "points_against":
                        opp_score
                }
            )

        except Exception:

            continue

    # ========================================================
    # SIN DATOS
    # ========================================================

    if not completed:

        return {

            "available":
                False,

            "wins":
                0,

            "losses":
                0,

            "games":
                0,

            "win_rate":
                0.5,

            "avg_margin":
                0.0,

            "recent_win_rate":
                0.5,

            "recent_margin":
                0.0,

            "rating":
                50.0,

            "error":
                "No se encontraron partidos "
                "históricos completos."
        }

    # ========================================================
    # ORDENAR
    # ========================================================

    completed.sort(
        key=lambda x:
            x["date"]
    )

    games = len(
        completed
    )

    wins = sum(
        x["win"]
        for x in completed
    )

    losses = (
        games -
        wins
    )

    win_rate = (
        wins /
        games
    )

    avg_margin = (
        sum(
            x["margin"]
            for x in completed
        )
        /
        games
    )

    # ========================================================
    # ÚLTIMOS 8
    # ========================================================

    recent = completed[-8:]

    recent_games = len(
        recent
    )

    recent_wins = sum(
        x["win"]
        for x in recent
    )

    recent_win_rate = (
        recent_wins /
        recent_games
    )

    recent_margin = (
        sum(
            x["margin"]
            for x in recent
        )
        /
        recent_games
    )

    # ========================================================
    # RATING NUEVO
    # ========================================================
    #
    # ANTES:
    #
    # La diferencia de rating podía disparar
    # la probabilidad hasta 88%, 90%, etc.
    #
    # AHORA:
    #
    # 1. Récord
    # 2. Margen
    # 3. Forma reciente
    #
    # Se mantiene todo en una escala mucho más
    # controlada.
    # ========================================================

    record_component = (
        (win_rate - 0.50)
        * 60
    )

    margin_component = clamp(
        avg_margin * 2.0,
        -20,
        20
    )

    recent_record_component = (
        (recent_win_rate - 0.50)
        * 20
    )

    recent_margin_component = clamp(
        recent_margin * 0.75,
        -7.5,
        7.5
    )

    base_rating = (
        50
        +
        record_component
        +
        margin_component
    )

    recent_rating = (
        50
        +
        recent_record_component
        +
        recent_margin_component
    )

    # 80% historial completo
    # 20% forma reciente

    rating = (
        base_rating * 0.80
        +
        recent_rating * 0.20
    )

    rating = clamp(
        rating,
        20,
        80
    )

    return {

        "available":
            True,

        "wins":
            wins,

        "losses":
            losses,

        "games":
            games,

        "win_rate":
            win_rate,

        "avg_margin":
            avg_margin,

        "recent_win_rate":
            recent_win_rate,

        "recent_margin":
            recent_margin,

        "rating":
            rating,

        "error":
            None
    }


# ============================================================
# MODELO
# ============================================================

@st.cache_data(ttl=900)
def calculate_model(
    away_id,
    home_id
):

    away = analyze_team_history(
        away_id
    )

    home = analyze_team_history(
        home_id
    )

    away_rating = (
        away["rating"]
    )

    home_rating = (
        home["rating"]
    )

    # ========================================================
    # DIFERENCIA DE FUERZA
    # ========================================================

    strength_difference = (
        away_rating -
        home_rating
    )

    # ========================================================
    # LOCALÍA
    # ========================================================
    #
    # Como el HOME es Atlanta:
    #
    # se le da una pequeña ventaja.
    #
    # No estamos dando +10 ni +15.
    # Solamente +3 puntos de rating.
    # ========================================================

    HOME_ADVANTAGE = 3.0

    adjusted_difference = (
        strength_difference
        -
        HOME_ADVANTAGE
    )

    # ========================================================
    # PROBABILIDAD
    # ========================================================
    #
    # Escala 40:
    #
    # Evita que pequeñas diferencias históricas
    # se conviertan automáticamente en 90%.
    # ========================================================

    raw_probability = (
        1 /
        (
            1 +
            math.exp(
                -adjusted_difference
                /
                40
            )
        )
    )

    # ========================================================
    # REGRESIÓN HACIA 50%
    # ========================================================
    #
    # Esto es MUY importante.
    #
    # Tenemos solamente una temporada histórica.
    #
    # No queremos decir:
    #
    # "Denver tiene 89% de ganar"
    #
    # solamente porque tuvo un gran 2025.
    #
    # Movemos 15% de la estimación hacia 50%.
    # ========================================================

    probability_away = (
        raw_probability * 0.85
        +
        0.50 * 0.15
    )

    probability_home = (
        1 -
        probability_away
    )

    # ========================================================
    # LIMITES
    # ========================================================

    probability_away = clamp(
        probability_away,
        0.20,
        0.80
    )

    probability_home = (
        1 -
        probability_away
    )

    # ========================================================
    # CONFIANZA
    # ========================================================

    if (
        away["available"]
        and
        home["available"]
    ):

        if (
            away["games"] >= 17
            and
            home["games"] >= 17
        ):

            # Una sola temporada.
            confidence = "MEDIA"

        elif (
            away["games"] >= 10
            and
            home["games"] >= 10
        ):

            confidence = "MEDIA-BAJA"

        else:

            confidence = "BAJA"

    else:

        confidence = "BAJA"

    return {

        "away_probability":
            probability_away,

        "home_probability":
            probability_home,

        "away_rating":
            away_rating,

        "home_rating":
            home_rating,

        "strength_difference":
            strength_difference,

        "away_data":
            away,

        "home_data":
            home,

        "confidence":
            confidence
    }


# ============================================================
# MERCADO
# ============================================================

def extract_market(game):

    odds_list = game.get(
        "odds",
        []
    )

    if not odds_list:

        return None

    odds = odds_list[0]

    return {

        "details":
            odds.get(
                "details"
            ),

        "spread":
            odds.get(
                "spread"
            ),

        "over_under":
            odds.get(
                "overUnder"
            )
    }


# ============================================================
# FECHAS
# ============================================================

def format_date(
    date_string
):

    try:

        dt = datetime.fromisoformat(
            date_string.replace(
                "Z",
                "+00:00"
            )
        )

        dt = dt.astimezone(
            ZoneInfo(TIMEZONE)
        )

        return dt.strftime(
            "%m/%d/%Y"
        )

    except Exception:

        return "N/A"


def format_time(
    date_string
):

    try:

        dt = datetime.fromisoformat(
            date_string.replace(
                "Z",
                "+00:00"
            )
        )

        dt = dt.astimezone(
            ZoneInfo(TIMEZONE)
        )

        return dt.strftime(
            "%I:%M %p"
        ).lstrip("0")

    except Exception:

        return "N/A"


# ============================================================
# HEADER
# ============================================================

st.markdown(
    "# 🏈 Monitor NFL"
)

st.markdown(
    """
    <div class="subtitle">
    Modelo propio — análisis NFL automático
    </div>
    """,
    unsafe_allow_html=True
)


# ============================================================
# TABS
# ============================================================

tab_nfl, tab_validation, tab_info = st.tabs(
    [
        "🏈 NFL DE HOY",
        "🧪 VALIDACIÓN DEL MODELO",
        "📊 INFORMACIÓN"
    ]
)


# ============================================================
# NFL DE HOY
# ============================================================

with tab_nfl:

    st.markdown(
        "## 🏈 NFL DE HOY"
    )

    if st.button(
        "🔄 ACTUALIZAR PARTIDOS",
        use_container_width=True
    ):

        st.cache_data.clear()

        st.rerun()

    games, error = (
        get_nfl_schedule()
    )

    # ========================================================
    # ERROR
    # ========================================================

    if error:

        st.markdown(
            f"""
            <div class="red-box">

            ⚠️ La fuente automática presentó
            un problema al consultar el calendario.

            <br><br>

            {error}

            </div>
            """,
            unsafe_allow_html=True
        )

    # ========================================================
    # SIN PARTIDOS
    # ========================================================

    elif not games:

        st.markdown(
            """
            <div class="yellow-box">

            ⚠️ No se encontraron partidos NFL
            en los próximos días.

            </div>
            """,
            unsafe_allow_html=True
        )

    # ========================================================
    # PARTIDOS
    # ========================================================

    else:

        st.success(
            f"Se encontraron "
            f"{len(games)} partidos."
        )

        for game in games:

            away = game["away"]
            home = game["home"]

            away_team = (
                away["team"]
            )

            home_team = (
                home["team"]
            )

            away_id = (
                away_team["id"]
            )

            home_id = (
                home_team["id"]
            )

            away_name = (
                away_team[
                    "displayName"
                ]
            )

            home_name = (
                home_team[
                    "displayName"
                ]
            )

            game_date = format_date(
                game["date"]
            )

            game_time = format_time(
                game["date"]
            )

            # =================================================
            # MODELO
            # =================================================

            model = calculate_model(
                away_id,
                home_id
            )

            away_probability = (
                model[
                    "away_probability"
                ]
            )

            home_probability = (
                model[
                    "home_probability"
                ]
            )

            away_fair_odds = (
                american_odds(
                    away_probability
                )
            )

            home_fair_odds = (
                american_odds(
                    home_probability
                )
            )

            # =================================================
            # FAVORITO
            # =================================================

            if (
                away_probability >
                home_probability
            ):

                favorite = (
                    away_name
                )

                favorite_probability = (
                    away_probability
                )

                favorite_odds = (
                    away_fair_odds
                )

            else:

                favorite = (
                    home_name
                )

                favorite_probability = (
                    home_probability
                )

                favorite_odds = (
                    home_fair_odds
                )

            # =================================================
            # CARD
            # =================================================

            st.markdown(
                '<div class="game-card">',
                unsafe_allow_html=True
            )

            st.markdown(
                f"# 🏈 {away_name}"
            )

            st.markdown(
                f"# @ {home_name}"
            )

            st.markdown(
                f"""
                📅 **{game_date}**

                🕐 **Hora Dallas:
                {game_time}**
                """
            )

            st.divider()

            col1, col2 = st.columns(2)

            # =================================================
            # AWAY
            # =================================================

            with col1:

                st.markdown(
                    f"### ✈️ {away_name}"
                )

                st.markdown(
                    """
                    <div class="label">
                    Probabilidad modelo
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                st.markdown(
                    f"""
                    <div class="prob">
                    {away_probability * 100:.1f}%
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                st.markdown(
                    f"""
                    🎯 <b>Cuota justa:
                    {away_fair_odds:+d}</b>
                    """,
                    unsafe_allow_html=True
                )

                away_data = (
                    model[
                        "away_data"
                    ]
                )

                st.caption(
                    f"Rating modelo: "
                    f"{away_data['rating']:.2f}"
                )

                st.caption(
                    f"2025: "
                    f"{away_data['wins']}-"
                    f"{away_data['losses']} | "
                    f"Margen promedio: "
                    f"{away_data['avg_margin']:+.1f}"
                )

                st.caption(
                    f"Últimos 8: "
                    f"{away_data['recent_win_rate'] * 100:.1f}%"
                )

            # =================================================
            # HOME
            # =================================================

            with col2:

                st.markdown(
                    f"### 🏠 {home_name}"
                )

                st.markdown(
                    """
                    <div class="label">
                    Probabilidad modelo
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                st.markdown(
                    f"""
                    <div class="prob">
                    {home_probability * 100:.1f}%
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                st.markdown(
                    f"""
                    🎯 <b>Cuota justa:
                    {home_fair_odds:+d}</b>
                    """,
                    unsafe_allow_html=True
                )

                home_data = (
                    model[
                        "home_data"
                    ]
                )

                st.caption(
                    f"Rating modelo: "
                    f"{home_data['rating']:.2f}"
                )

                st.caption(
                    f"2025: "
                    f"{home_data['wins']}-"
                    f"{home_data['losses']} | "
                    f"Margen promedio: "
                    f"{home_data['avg_margin']:+.1f}"
                )

                st.caption(
                    f"Últimos 8: "
                    f"{home_data['recent_win_rate'] * 100:.1f}%"
                )

            # =================================================
            # PROYECCIÓN
            # =================================================

            st.markdown(
                f"""
                <div class="green-box">

                🧠 <b>PROYECCIÓN DEL MODELO</b>

                <br><br>

                Favorito:
                <b>{favorite}</b>

                <br><br>

                Probabilidad estimada:
                <b>
                {favorite_probability * 100:.1f}%
                </b>

                <br><br>

                Cuota justa:
                <b>{favorite_odds:+d}</b>

                <br><br>

                Confianza:
                <b>{model['confidence']}</b>

                </div>
                """,
                unsafe_allow_html=True
            )

            # =================================================
            # COMPARACIÓN CASA
            # =================================================

            st.markdown(
                "## 🏦 COMPARACIÓN CON LA CASA"
            )

            market = extract_market(
                game
            )

            if market:

                if market[
                    "details"
                ]:

                    st.write(
                        f"Mercado: "
                        f"**{market['details']}**"
                    )

                if market[
                    "spread"
                ]:

                    st.write(
                        f"Spread: "
                        f"**{market['spread']}**"
                    )

                if market[
                    "over_under"
                ]:

                    st.write(
                        f"Total: "
                        f"**{market['over_under']}**"
                    )

            else:

                st.markdown(
                    """
                    <div class="blue-box">

                    🏦 No hay cuotas disponibles
                    en la fuente automática.

                    </div>
                    """,
                    unsafe_allow_html=True
                )

            # =================================================
            # INFORMACIÓN TÉCNICA
            # =================================================

            with st.expander(
                "🔧 Información técnica"
            ):

                st.write(
                    "### 📐 Componentes del modelo"
                )

                st.write(
                    """
                    **Récord histórico:** 60%

                    **Margen de puntos:** componente
                    limitado para evitar sobre-reacción.

                    **Forma reciente:** 20%.

                    **Localía:** +3 puntos de rating.

                    **Regresión:** 15% hacia 50%.

                    **Escala logística:** 40.
                    """
                )

                st.divider()

                st.write(
                    f"Diferencia de fuerza: "
                    f"**{model['strength_difference']:+.2f}**"
                )

                st.write(
                    f"Localía aplicada: "
                    f"**3.0**"
                )

                st.write(
                    f"Probabilidad visitante: "
                    f"**{away_probability * 100:.2f}%**"
                )

                st.write(
                    f"Probabilidad local: "
                    f"**{home_probability * 100:.2f}%**"
                )

                st.divider()

                st.write(
                    f"### {away_name}"
                )

                st.write(
                    f"Récord 2025: "
                    f"**{away_data['wins']}-"
                    f"{away_data['losses']}**"
                )

                st.write(
                    f"Win rate: "
                    f"**{away_data['win_rate'] * 100:.1f}%**"
                )

                st.write(
                    f"Margen promedio: "
                    f"**{away_data['avg_margin']:+.2f}**"
                )

                st.write(
                    f"Rating: "
                    f"**{away_data['rating']:.2f}**"
                )

                st.divider()

                st.write(
                    f"### {home_name}"
                )

                st.write(
                    f"Récord 2025: "
                    f"**{home_data['wins']}-"
                    f"{home_data['losses']}**"
                )

                st.write(
                    f"Win rate: "
                    f"**{home_data['win_rate'] * 100:.1f}%**"
                )

                st.write(
                    f"Margen promedio: "
                    f"**{home_data['avg_margin']:+.2f}**"
                )

                st.write(
                    f"Rating: "
                    f"**{home_data['rating']:.2f}**"
                )

            st.markdown(
                "</div>",
                unsafe_allow_html=True
            )


# ============================================================
# VALIDACIÓN
# ============================================================

with tab_validation:

    st.markdown(
        "## 🧪 VALIDACIÓN DEL MODELO"
    )

    st.markdown(
        """
        La validación es la parte más importante del proyecto.

        No vamos a asumir que una probabilidad alta significa
        que el modelo es bueno.

        Vamos a comprobarlo contra partidos históricos.
        """
    )

    st.markdown(
        """
        <div class="yellow-box">

        🎯 El objetivo será medir:

        <br><br>

        • Porcentaje de aciertos

        • Brier Score

        • ROI

        • Yield

        • Calibración

        • Rendimiento por rango de probabilidad

        • Rendimiento contra la línea de la casa

        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown(
        "### 📊 Próximo módulo"

    )

    st.write(
        """
        El siguiente módulo debe probar automáticamente
        cientos de partidos históricos.

        Por ejemplo:

        50–55%
        55–60%
        60–65%
        65–70%
        70–75%
        75%+

        Así podremos saber si cuando el modelo dice 65%,
        realmente gana cerca del 65% de las veces.
        """
    )


# ============================================================
# INFORMACIÓN
# ============================================================

with tab_info:

    st.markdown(
        "## 📊 INFORMACIÓN"
    )

    st.markdown(
        """
        ### 🧠 Modelo actual

        El modelo utiliza:

        **1. Récord 2025**

        Mide el rendimiento general.

        **2. Margen promedio**

        Mide cuánto domina o pierde un equipo.

        **3. Últimos 8 partidos**

        Añade información de forma reciente.

        **4. Localía**

        Se aplica una ventaja pequeña al equipo local.

        **5. Regresión hacia 50%**

        Evita probabilidades exageradas cuando tenemos
        pocos datos.

        **6. Función logística**

        Convierte la diferencia de fuerza en probabilidad.
        """
    )

    st.divider()

    st.markdown(
        "### 🔬 Flujo del modelo"
    )

    st.code(
        """
CALENDARIO NFL
      ↓
EQUIPOS
      ↓
HISTORIAL 2025
      ↓
RÉCORD
      ↓
MARGEN
      ↓
ÚLTIMOS 8
      ↓
RATING
      ↓
LOCALÍA
      ↓
FUNCIÓN LOGÍSTICA
      ↓
REGRESIÓN 15%
      ↓
PROBABILIDAD
      ↓
CUOTA JUSTA
      ↓
COMPARACIÓN CASA
      ↓
VALIDACIÓN HISTÓRICA
      ↓
ROI / BRIER / CALIBRACIÓN
        """,
        language="text"
    )

    st.divider()

    st.markdown(
        """
        ### ⚠️ Estado del proyecto

        El modelo todavía es experimental.

        Una probabilidad de 70% no significa que un partido
        vaya a ganar necesariamente.

        La verdadera prueba será el backtesting.
        """
    )


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.markdown(
    """
    <div class="small-text">

    Monitor NFL — herramienta experimental de análisis
    estadístico. Las probabilidades son estimaciones y no
    garantizan resultados futuros.

    </div>
    """,
    unsafe_allow_html=True
)
