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

CURRENT_SEASON = 2026

# Utilizamos la última temporada completa
# porque la temporada 2026 todavía está comenzando.
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

TEAM_RECORD_URL = (
    "https://sports.core.api.espn.com/v2/"
    "sports/football/leagues/nfl/seasons/"
    "{season}/types/2/teams/{team_id}/record"
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

        # ESPN puede devolver:
        #
        # "24"
        #
        # o:
        # {"value": 24}
        #
        # o:
        # {"displayValue": "24"}

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
        0.001,
        0.999
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

            competition = (
                event["competitions"][0]
            )

            competitors = (
                competition["competitors"]
            )

            if len(competitors) != 2:
                continue

            away = None
            home = None

            for competitor in competitors:

                if competitor.get(
                    "homeAway"
                ) == "away":

                    away = competitor

                elif competitor.get(
                    "homeAway"
                ) == "home":

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
# HISTORIAL DE TEMPORADA
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
# RÉCORD OFICIAL COMO RESPALDO
# ============================================================

@st.cache_data(ttl=3600)
def get_official_record(
    team_id
):

    url = TEAM_RECORD_URL.format(

        season=
            HISTORICAL_SEASON,

        team_id=
            team_id
    )

    data = get_json(url)

    if "_error" in data:

        return None

    items = data.get(
        "items",
        []
    )

    for item in items:

        if item.get(
            "type"
        ) == "total":

            summary = item.get(
                "summary"
            )

            if summary:

                parts = summary.split("-")

                if len(parts) >= 2:

                    try:

                        wins = int(
                            parts[0]
                        )

                        losses = int(
                            parts[1]
                        )

                        return {
                            "wins":
                                wins,

                            "losses":
                                losses,

                            "games":
                                wins + losses
                        }

                    except Exception:
                        pass

    return None


# ============================================================
# ANALIZAR HISTORIAL
# ============================================================

def analyze_team_history(
    team_id
):

    events, error = (
        get_historical_schedule(
            team_id
        )
    )

    completed_games = []

    if not error:

        for event in events:

            try:

                competition = (
                    event[
                        "competitions"
                    ][0]
                )

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
                    competition[
                        "competitors"
                    ]
                )

                my_team = None
                opponent = None

                for competitor in competitors:

                    team_data = (
                        competitor.get(
                            "team",
                            {}
                        )
                    )

                    competitor_id = str(
                        team_data.get(
                            "id"
                        )
                    )

                    if competitor_id == str(
                        team_id
                    ):

                        my_team = competitor

                    else:

                        opponent = competitor

                if not my_team or not opponent:
                    continue

                # ====================================================
                # 🔥 CORRECCIÓN IMPORTANTE
                #
                # ESPN puede mandar:
                #
                # score = "24"
                #
                # o:
                #
                # score = {"value": 24}
                #
                # o:
                #
                # score = {"displayValue": "24"}
                # ====================================================

                my_score = safe_float(
                    my_team.get(
                        "score"
                    )
                )

                opponent_score = safe_float(
                    opponent.get(
                        "score"
                    )
                )

                # Evitamos aceptar partidos donde
                # ambos scores quedaron en cero
                # por error de lectura.

                if (
                    my_score == 0
                    and
                    opponent_score == 0
                ):

                    continue

                margin = (
                    my_score -
                    opponent_score
                )

                win = (
                    1
                    if margin > 0
                    else 0
                )

                completed_games.append(
                    {
                        "date":
                            event.get(
                                "date",
                                ""
                            ),

                        "win":
                            win,

                        "margin":
                            margin,

                        "points_for":
                            my_score,

                        "points_against":
                            opponent_score
                    }
                )

            except Exception:

                continue

    # ========================================================
    # SI EL HISTORIAL NO FUNCIONÓ
    # USAMOS EL RECORD OFICIAL
    # ========================================================

    official_record = (
        get_official_record(
            team_id
        )
    )

    # ========================================================
    # CASO NORMAL
    # ========================================================

    if completed_games:

        completed_games.sort(
            key=lambda x:
                x["date"]
        )

        wins = sum(
            x["win"]
            for x in completed_games
        )

        games = len(
            completed_games
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
                for x in completed_games
            )
            /
            games
        )

        recent = (
            completed_games[-8:]
        )

        recent_wins = sum(
            x["win"]
            for x in recent
        )

        recent_games = len(
            recent
        )

        recent_win_rate = (
            recent_wins /
            recent_games
            if recent_games
            else win_rate
        )

        recent_margin = (
            sum(
                x["margin"]
                for x in recent
            )
            /
            recent_games
            if recent_games
            else avg_margin
        )

    # ========================================================
    # SI SOLO TENEMOS RECORD OFICIAL
    # ========================================================

    elif official_record:

        wins = (
            official_record["wins"]
        )

        losses = (
            official_record["losses"]
        )

        games = (
            official_record["games"]
        )

        win_rate = (
            wins /
            games
            if games
            else 0.5
        )

        # No inventamos margen.
        avg_margin = 0

        recent_win_rate = (
            win_rate
        )

        recent_margin = 0

    # ========================================================
    # SIN DATOS
    # ========================================================

    else:

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
                0,

            "recent_win_rate":
                0.5,

            "recent_margin":
                0,

            "rating":
                0,

            "error":
                "No se pudieron obtener "
                "datos históricos."
        }

    # ========================================================
    # RATING
    # ========================================================

    # Récord
    record_score = (
        (win_rate - 0.5)
        * 100
    )

    # Margen
    margin_score = clamp(
        avg_margin * 2.5,
        -25,
        25
    )

    # Forma reciente
    recent_score = (
        (recent_win_rate - 0.5)
        * 100
    )

    recent_score += clamp(
        recent_margin * 1.5,
        -15,
        15
    )

    rating = (

        record_score * 0.45

        +

        margin_score * 0.35

        +

        recent_score * 0.20
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

    # Diferencia
    rating_difference = (
        home_rating -
        away_rating
    )

    # Localía
    home_field_advantage = 2.5

    adjusted_difference = (
        rating_difference
        +
        home_field_advantage
    )

    # ========================================================
    # PROBABILIDAD
    # ========================================================

    probability_home = (

        1 /
        (
            1 +
            math.exp(
                -adjusted_difference
                /
                13
            )
        )
    )

    probability_home = clamp(
        probability_home,
        0.05,
        0.95
    )

    probability_away = (
        1 -
        probability_home
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
            away["games"] >= 12
            and
            home["games"] >= 12
        ):

            confidence = "ALTA"

        else:

            confidence = "MEDIA"

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

        "rating_difference":
            rating_difference,

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
# FECHA
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

    except:

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

    except:

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
# NFL
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

    if error:

        st.markdown(
            f"""
            <div class="red-box">

            ⚠️ Error al consultar
            el calendario NFL.

            <br><br>

            {error}

            </div>
            """,
            unsafe_allow_html=True
        )

    elif not games:

        st.markdown(
            """
            <div class="yellow-box">

            ⚠️ No se encontraron
            partidos NFL en los
            próximos días.

            </div>
            """,
            unsafe_allow_html=True
        )

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

            away_prob = (
                model[
                    "away_probability"
                ]
            )

            home_prob = (
                model[
                    "home_probability"
                ]
            )

            away_fair_odds = (
                american_odds(
                    away_prob
                )
            )

            home_fair_odds = (
                american_odds(
                    home_prob
                )
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
                    {away_prob * 100:.1f}%
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

                data = (
                    model[
                        "away_data"
                    ]
                )

                st.caption(
                    f"Rating: "
                    f"{data['rating']:.2f}"
                )

                st.caption(
                    f"2025: "
                    f"{data['wins']}-"
                    f"{data['losses']} | "
                    f"Margen promedio: "
                    f"{data['avg_margin']:+.1f}"
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
                    {home_prob * 100:.1f}%
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

                data = (
                    model[
                        "home_data"
                    ]
                )

                st.caption(
                    f"Rating: "
                    f"{data['rating']:.2f}"
                )

                st.caption(
                    f"2025: "
                    f"{data['wins']}-"
                    f"{data['losses']} | "
                    f"Margen promedio: "
                    f"{data['avg_margin']:+.1f}"
                )

            # =================================================
            # FAVORITO
            # =================================================

            if (
                away_prob >
                home_prob
            ):

                favorite = (
                    away_name
                )

                favorite_probability = (
                    away_prob
                )

                favorite_odds = (
                    away_fair_odds
                )

            else:

                favorite = (
                    home_name
                )

                favorite_probability = (
                    home_prob
                )

                favorite_odds = (
                    home_fair_odds
                )

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
            # CASA
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

                away_data = (
                    model[
                        "away_data"
                    ]
                )

                home_data = (
                    model[
                        "home_data"
                    ]
                )

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
                    f"Forma últimos 8: "
                    f"**{away_data['recent_win_rate'] * 100:.1f}%**"
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
                    f"Forma últimos 8: "
                    f"**{home_data['recent_win_rate'] * 100:.1f}%**"
                )

                st.divider()

                st.write(
                    f"Diferencia rating: "
                    f"**{model['rating_difference']:+.2f}**"
                )

                st.write(
                    "Ventaja de local: **+2.5**"
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
        Esta sección será utilizada para probar el modelo
        con partidos históricos.

        El objetivo no es simplemente conseguir muchos
        aciertos.

        Queremos comprobar que las probabilidades estén
        correctamente calibradas.
        """
    )

    st.markdown(
        """
        <div class="yellow-box">

        🎯 Ejemplo:

        <br><br>

        Si el modelo dice 70%, queremos comprobar que
        históricamente aproximadamente 70% de esos partidos
        hayan terminado ganándose.

        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown(
        "### 📊 Próxima etapa"

    )

    st.write(
        """
        Vamos a almacenar:

        • Probabilidad del modelo

        • Cuota de la casa

        • Resultado real

        • Edge

        • Ganancia/pérdida

        • Brier Score

        • ROI

        • Calibración
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
        ### 🧠 ¿Cómo funciona el modelo?

        El modelo utiliza la temporada 2025 como base
        histórica mientras la temporada 2026 todavía no
        tiene suficientes partidos.

        ### Variables principales

        **45% — Récord**

        Victorias y derrotas.

        **35% — Margen de puntos**

        Diferencia promedio entre puntos anotados y recibidos.

        **20% — Forma reciente**

        Últimos 8 partidos.

        Después se añade una ventaja inicial de localía de
        2.5 puntos.

        Finalmente la diferencia se transforma en una
        probabilidad mediante una función logística.

        ### 🔬 Importante

        Este todavía NO es el modelo final.

        La siguiente fase importante es probarlo contra
        cientos de partidos históricos y medir si realmente
        tiene ventaja sobre las cuotas de mercado.
        """
    )

    st.divider()

    st.code(
        """
CALENDARIO
     ↓
EQUIPOS
     ↓
HISTORIAL 2025
     ↓
RÉCORD
     ↓
MARGEN
     ↓
FORMA RECIENTE
     ↓
RATING
     ↓
LOCALÍA
     ↓
PROBABILIDAD
     ↓
CUOTA JUSTA
     ↓
CUOTA CASA
     ↓
EDGE
     ↓
RESULTADO REAL
     ↓
VALIDACIÓN
     ↓
ROI
        """,
        language="text"
    )


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.markdown(
    """
    <div class="small-text">

    Monitor NFL — herramienta experimental de análisis
    estadístico. Las probabilidades son estimaciones y
    no garantizan resultados futuros.

    </div>
    """,
    unsafe_allow_html=True
)
