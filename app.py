import streamlit as st
import requests
import math
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# ============================================================
# 🏈 MONITOR NFL
# Modelo estadístico NFL
# Calendario + histórico + probabilidades + cuotas
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

TEAM_STATS_URL = (
    "https://site.api.espn.com/apis/site/v2/"
    "sports/football/nfl/teams/{team_id}/statistics"
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

    .team-name {
        font-size: 1.5rem;
        font-weight: 700;
        color: #f5f5f5;
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

    .edge-positive {
        color: #7ee2a2;
        font-size: 1.2rem;
        font-weight: 700;
    }

    .edge-negative {
        color: #ff9292;
        font-size: 1.2rem;
        font-weight: 700;
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
        return float(value)
    except:
        return default


def clamp(value, minimum, maximum):
    return max(minimum, min(maximum, value))


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

    return int(round(odds))


def implied_probability(odds):

    try:

        odds = float(odds)

        if odds < 0:
            return abs(odds) / (
                abs(odds) + 100
            )

        return 100 / (
            odds + 100
        )

    except:

        return None


# ============================================================
# REQUEST
# ============================================================

@st.cache_data(ttl=300)
def get_json(url, params=None):

    headers = {
        "User-Agent":
            "Mozilla/5.0 "
            "(iPhone; CPU iPhone OS 18_0 like Mac OS X) "
            "AppleWebKit/605.1.15",
        "Accept": "application/json",
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
# CALENDARIO ACTUAL
# ============================================================

@st.cache_data(ttl=300)
def get_nfl_schedule():

    today = datetime.now(
        ZoneInfo(TIMEZONE)
    ).date()

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
                    "id": event.get("id"),

                    "date": event.get(
                        "date"
                    ),

                    "name": event.get(
                        "name"
                    ),

                    "short_name": event.get(
                        "shortName"
                    ),

                    "away": away,

                    "home": home,

                    "odds": competition.get(
                        "odds",
                        []
                    ),

                    "status": event.get(
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
# HISTORIAL DEL EQUIPO
# ============================================================

@st.cache_data(ttl=3600)
def get_historical_schedule(team_id):

    url = TEAM_SCHEDULE_URL.format(
        team_id=team_id
    )

    data = get_json(
        url,
        {
            "season": HISTORICAL_SEASON,
            "seasontype": 2
        }
    )

    if "_error" in data:
        return [], data["_error"]

    return (
        data.get("events", []),
        None
    )


# ============================================================
# ANALIZAR HISTORIAL
# ============================================================

def analyze_team_history(team_id):

    events, error = (
        get_historical_schedule(
            team_id
        )
    )

    if error:

        return {
            "available": False,
            "wins": 0,
            "losses": 0,
            "games": 0,
            "win_rate": 0.5,
            "avg_margin": 0,
            "recent_win_rate": 0.5,
            "recent_margin": 0,
            "rating": 0,
            "error": error
        }

    completed_games = []

    for event in events:

        try:

            competition = (
                event["competitions"][0]
            )

            status = (
                competition
                .get("status", {})
                .get("type", {})
            )

            if not status.get(
                "completed",
                False
            ):
                continue

            competitors = (
                competition["competitors"]
            )

            my_team = None
            opponent = None

            for c in competitors:

                team_id_event = str(
                    c.get(
                        "team",
                        {}
                    ).get("id")
                )

                if team_id_event == str(
                    team_id
                ):

                    my_team = c

                else:

                    opponent = c

            if not my_team or not opponent:
                continue

            my_score = safe_float(
                my_team.get("score")
            )

            opp_score = safe_float(
                opponent.get("score")
            )

            margin = (
                my_score -
                opp_score
            )

            win = (
                1 if margin > 0
                else 0
            )

            completed_games.append(
                {
                    "date":
                        event.get(
                            "date",
                            ""
                        ),
                    "win": win,
                    "margin": margin,
                    "points_for":
                        my_score,
                    "points_against":
                        opp_score
                }
            )

        except Exception:
            continue

    completed_games.sort(
        key=lambda x:
            x["date"]
    )

    if not completed_games:

        return {
            "available": False,
            "wins": 0,
            "losses": 0,
            "games": 0,
            "win_rate": 0.5,
            "avg_margin": 0,
            "recent_win_rate": 0.5,
            "recent_margin": 0,
            "rating": 0,
            "error":
                "No se encontraron partidos "
                "históricos."
        }

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
        ) /
        games
    )

    # --------------------------------------------------------
    # ÚLTIMOS 8 PARTIDOS
    # --------------------------------------------------------

    recent = completed_games[-8:]

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
        else 0.5
    )

    recent_margin = (
        sum(
            x["margin"]
            for x in recent
        ) /
        recent_games
        if recent_games
        else 0
    )

    # --------------------------------------------------------
    # RATING PROPIO
    #
    # No usamos el rating ESPN.
    # Construimos uno con:
    #
    # 45% récord
    # 35% margen de puntos
    # 20% forma reciente
    # --------------------------------------------------------

    record_score = (
        win_rate -
        0.5
    ) * 100

    margin_score = clamp(
        avg_margin *
        2.5,
        -25,
        25
    )

    recent_score = (
        (recent_win_rate - 0.5)
        * 100
    )

    recent_score += clamp(
        recent_margin *
        1.5,
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
        "available": True,
        "wins": wins,
        "losses": losses,
        "games": games,
        "win_rate": win_rate,
        "avg_margin": avg_margin,
        "recent_win_rate":
            recent_win_rate,
        "recent_margin":
            recent_margin,
        "rating": rating,
        "error": None
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

    # --------------------------------------------------------
    # RATINGS
    # --------------------------------------------------------

    away_rating = (
        away["rating"]
    )

    home_rating = (
        home["rating"]
    )

    # --------------------------------------------------------
    # DIFERENCIA
    # --------------------------------------------------------

    rating_difference = (
        home_rating -
        away_rating
    )

    # --------------------------------------------------------
    # LOCALÍA
    #
    # Aproximación inicial:
    # +2.5 puntos para el local.
    # --------------------------------------------------------

    home_field_advantage = 2.5

    adjusted_difference = (
        rating_difference +
        home_field_advantage
    )

    # --------------------------------------------------------
    # LOGÍSTICA
    # --------------------------------------------------------

    probability_home = (
        1 /
        (
            1 +
            math.exp(
                -adjusted_difference /
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

    # --------------------------------------------------------
    # CONFIANZA
    # --------------------------------------------------------

    data_available = (
        away["available"]
        and
        home["available"]
    )

    if data_available:

        confidence = "MEDIA"

        if (
            away["games"] >= 12
            and
            home["games"] >= 12
        ):
            confidence = "ALTA"

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
# ODDS
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

def format_date(date_string):

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


def format_time(date_string):

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
    '<div class="subtitle">'
    "Modelo propio — análisis NFL automático"
    "</div>",
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
            ⚠️ Error al consultar el
            calendario NFL.
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
            ⚠️ No se encontraron partidos NFL
            en los próximos días.
            </div>
            """,
            unsafe_allow_html=True
        )

    else:

        st.success(
            f"Se encontraron {len(games)} "
            "partidos."
        )

        for game in games:

            away = game["away"]
            home = game["home"]

            away_team = away["team"]
            home_team = home["team"]

            away_id = (
                away_team["id"]
            )

            home_id = (
                home_team["id"]
            )

            away_name = (
                away_team["displayName"]
            )

            home_name = (
                home_team["displayName"]
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
                model["away_probability"]
            )

            home_prob = (
                model["home_probability"]
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
                f"## 🏈 {away_name}"
            )

            st.markdown(
                f"## @ {home_name}"
            )

            st.markdown(
                f"""
                📅 **{game_date}**

                🕐 **Hora Dallas: {game_time}**
                """
            )

            st.divider()

            col1, col2 = st.columns(2)

            # =================================================
            # VISITANTE
            # =================================================

            with col1:

                st.markdown(
                    f"### ✈️ {away_name}"
                )

                st.markdown(
                    '<div class="label">'
                    "Probabilidad modelo"
                    "</div>",
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
                    🎯 **Cuota justa:
                    {away_fair_odds:+d}**
                    """
                )

                st.caption(
                    f"Rating: "
                    f"{model['away_rating']:.2f}"
                )

                data = (
                    model["away_data"]
                )

                st.caption(
                    f"2025: "
                    f"{data['wins']}-"
                    f"{data['losses']} | "
                    f"Margen promedio: "
                    f"{data['avg_margin']:+.1f}"
                )

            # =================================================
            # LOCAL
            # =================================================

            with col2:

                st.markdown(
                    f"### 🏠 {home_name}"
                )

                st.markdown(
                    '<div class="label">'
                    "Probabilidad modelo"
                    "</div>",
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
                    🎯 **Cuota justa:
                    {home_fair_odds:+d}**
                    """
                )

                st.caption(
                    f"Rating: "
                    f"{model['home_rating']:.2f}"
                )

                data = (
                    model["home_data"]
                )

                st.caption(
                    f"2025: "
                    f"{data['wins']}-"
                    f"{data['losses']} | "
                    f"Margen promedio: "
                    f"{data['avg_margin']:+.1f}"
                )

            # =================================================
            # PROYECCIÓN
            # =================================================

            if away_prob > home_prob:

                favorite = away_name
                favorite_probability = (
                    away_prob
                )
                favorite_odds = (
                    away_fair_odds
                )

            else:

                favorite = home_name
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

                <br>

                Probabilidad estimada:
                <b>{favorite_probability * 100:.1f}%</b>

                <br>

                Cuota justa:
                <b>{favorite_odds:+d}</b>

                <br><br>

                Confianza del dato:
                <b>{model['confidence']}</b>

                </div>
                """,
                unsafe_allow_html=True
            )

            # =================================================
            # DATOS DEL MERCADO
            # =================================================

            market = extract_market(
                game
            )

            st.markdown(
                "### 🏦 COMPARACIÓN CON LA CASA"
            )

            if market:

                if market["details"]:

                    st.write(
                        f"Mercado: "
                        f"**{market['details']}**"
                    )

                if market["spread"]:

                    st.write(
                        f"Spread: "
                        f"**{market['spread']}**"
                    )

                if market["over_under"]:

                    st.write(
                        f"Total: "
                        f"**{market['over_under']}**"
                    )

                st.caption(
                    "Las cuotas del mercado "
                    "pueden cambiar."
                )

            else:

                st.markdown(
                    """
                    <div class="blue-box">
                    🏦 No hay cuotas disponibles
                    en la fuente automática para
                    este partido.
                    </div>
                    """,
                    unsafe_allow_html=True
                )

            # =================================================
            # INFORMACIÓN DEL MODELO
            # =================================================

            with st.expander(
                "🔧 Ver datos utilizados por el modelo"
            ):

                away_data = (
                    model["away_data"]
                )

                home_data = (
                    model["home_data"]
                )

                st.write(
                    f"**{away_name}**"
                )

                st.write(
                    f"Récord 2025: "
                    f"{away_data['wins']}-"
                    f"{away_data['losses']}"
                )

                st.write(
                    f"Win rate: "
                    f"{away_data['win_rate'] * 100:.1f}%"
                )

                st.write(
                    f"Margen promedio: "
                    f"{away_data['avg_margin']:+.2f}"
                )

                st.write(
                    f"Últimos 8 — win rate: "
                    f"{away_data['recent_win_rate'] * 100:.1f}%"
                )

                st.divider()

                st.write(
                    f"**{home_name}**"
                )

                st.write(
                    f"Récord 2025: "
                    f"{home_data['wins']}-"
                    f"{home_data['losses']}"
                )

                st.write(
                    f"Win rate: "
                    f"{home_data['win_rate'] * 100:.1f}%"
                )

                st.write(
                    f"Margen promedio: "
                    f"{home_data['avg_margin']:+.2f}"
                )

                st.write(
                    f"Últimos 8 — win rate: "
                    f"{home_data['recent_win_rate'] * 100:.1f}%"
                )

                st.divider()

                st.write(
                    f"Diferencia de rating: "
                    f"{model['rating_difference']:+.2f}"
                )

                st.write(
                    "Ventaja local aplicada: "
                    "**+2.5**"
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
        "## 🧪 Validación del modelo"
    )

    st.write(
        """
        Esta sección será utilizada para medir si las
        probabilidades del modelo están correctamente
        calibradas.
        """
    )

    st.markdown(
        """
        <div class="yellow-box">

        🎯 <b>OBJETIVO</b>

        <br><br>

        Si el modelo genera una probabilidad de 70%,
        queremos comprobar históricamente que alrededor
        de 70 de cada 100 casos realmente ganen.

        <br><br>

        Una tasa de aciertos alta por sí sola NO es
        suficiente.

        <br><br>

        Necesitamos probabilidades calibradas.

        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown(
        "### 📈 Ejemplo de calibración"
    )

    st.table(
        {
            "Probabilidad modelo": [
                "55%",
                "60%",
                "65%",
                "70%",
                "75%",
                "80%",
                "85%",
                "90%"
            ],

            "Resultado esperado": [
                "≈55%",
                "≈60%",
                "≈65%",
                "≈70%",
                "≈75%",
                "≈80%",
                "≈85%",
                "≈90%"
            ]
        }
    )

    st.markdown(
        """
        <div class="blue-box">

        🔬 La siguiente etapa será ejecutar el modelo
        sobre partidos históricos y guardar:

        <br><br>

        <b>Probabilidad predicha → Resultado real</b>

        <br><br>

        Con suficientes observaciones podremos medir
        calibración, Brier Score, ROI y rendimiento
        contra la cuota de mercado.

        </div>
        """,
        unsafe_allow_html=True
    )


# ============================================================
# INFORMACIÓN
# ============================================================

with tab_info:

    st.markdown(
        "## 📊 Información"
    )

    st.markdown(
        """
        ### 🧠 Modelo actual

        Para cada equipo se analiza la temporada histórica
        disponible:

        **1. Récord**

        Victorias y derrotas.

        **2. Margen de puntos**

        Diferencia promedio entre puntos anotados y recibidos.

        **3. Forma reciente**

        Últimos 8 partidos.

        **4. Rating propio**

        El rating combina:

        - 45% récord
        - 35% margen de puntos
        - 20% forma reciente

        **5. Localía**

        Se añade una ventaja inicial de 2.5 puntos al equipo
        local.

        **6. Función probabilística**

        La diferencia final se transforma en una probabilidad
        mediante una función logística.

        **7. Cuota justa**

        La probabilidad se convierte a cuota americana.

        """

    )

    st.divider()

    st.markdown(
        "### 🔬 Flujo del sistema"
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
MARGEN DE PUNTOS
       ↓
ÚLTIMOS 8 PARTIDOS
       ↓
RATING PROPIO
       ↓
VENTAJA DE LOCAL
       ↓
PROBABILIDAD
       ↓
CUOTA JUSTA
       ↓
CUOTA DEL MERCADO
       ↓
EDGE
       ↓
VALIDACIÓN HISTÓRICA
       ↓
ROI / BRIER / CALIBRACIÓN
        """,
        language="text"
    )

    st.divider()

    st.markdown(
        "### ⚠️ Importante"
    )

    st.warning(
        """
        Durante la pretemporada 2026 el modelo utiliza
        principalmente el rendimiento histórico 2025 porque
        todavía no existen suficientes partidos de temporada
        2026 para construir una muestra nueva.

        Por eso estas probabilidades NO deben considerarse
        todavía la versión final del modelo.
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
