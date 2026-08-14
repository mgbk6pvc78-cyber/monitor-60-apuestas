import streamlit as st
import requests
import math
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# ============================================================
# MONITOR NFL
# Modelo estadístico + calendario automático
# ============================================================

st.set_page_config(
    page_title="Monitor NFL",
    page_icon="🏈",
    layout="wide"
)

# ------------------------------------------------------------
# CONFIGURACIÓN
# ------------------------------------------------------------

ESPN_SCOREBOARD = (
    "https://site.api.espn.com/apis/site/v2/"
    "sports/football/nfl/scoreboard"
)

ESPN_TEAM = (
    "https://site.api.espn.com/apis/site/v2/"
    "sports/football/nfl/teams"
)

TIMEZONE = "America/Chicago"

# Cuánto pesa cada componente del modelo
WEIGHT_RECORD = 0.35
WEIGHT_RECENT = 0.35
WEIGHT_HOME = 0.15
WEIGHT_RATING = 0.15

# Ventana de partidos futuros
DAYS_AHEAD = 7


# ------------------------------------------------------------
# ESTILO
# ------------------------------------------------------------

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
        font-size: 1.25rem;
        margin-bottom: 1.5rem;
    }

    .game-card {
        background: #171820;
        border: 1px solid #343641;
        border-radius: 22px;
        padding: 28px;
        margin-top: 25px;
        margin-bottom: 30px;
    }

    .team-name {
        font-size: 1.65rem;
        font-weight: 700;
        color: #f5f5f5;
        margin-top: 8px;
    }

    .prob {
        font-size: 3rem;
        font-weight: 700;
        color: #ffffff;
        margin-top: 5px;
        margin-bottom: 10px;
    }

    .label {
        color: #a9abb4;
        font-size: 1rem;
    }

    .blue-box {
        background: #1c3049;
        border-radius: 18px;
        padding: 20px;
        color: #61a8ff;
        margin-top: 20px;
    }

    .green-box {
        background: #193526;
        border: 1px solid #367c53;
        border-radius: 18px;
        padding: 20px;
        color: #a8e6bd;
        margin-top: 20px;
    }

    .yellow-box {
        background: #3b351c;
        border: 1px solid #827126;
        border-radius: 18px;
        padding: 20px;
        color: #fff0a0;
        margin-top: 20px;
    }

    .red-box {
        background: #422329;
        border: 1px solid #793b45;
        border-radius: 18px;
        padding: 20px;
        color: #ff9a9a;
        margin-top: 20px;
    }

    .fair-odds {
        font-size: 1.2rem;
        font-weight: 600;
        color: #ffffff;
    }

    .small-text {
        color: #92949d;
        font-size: 0.9rem;
    }

    </style>
    """,
    unsafe_allow_html=True
)


# ------------------------------------------------------------
# FUNCIONES GENERALES
# ------------------------------------------------------------

def safe_float(value, default=0.0):
    try:
        if value is None:
            return default
        return float(value)
    except:
        return default


def clamp(value, minimum, maximum):
    return max(minimum, min(maximum, value))


def american_odds(probability):
    """
    Convierte probabilidad decimal a cuota americana justa.
    """

    probability = clamp(probability, 0.001, 0.999)

    if probability >= 0.5:
        odds = -(probability / (1 - probability)) * 100
    else:
        odds = ((1 - probability) / probability) * 100

    return int(round(odds))


def implied_probability(american):
    """
    Convierte cuota americana a probabilidad implícita.
    """

    try:
        odds = float(american)

        if odds < 0:
            return abs(odds) / (abs(odds) + 100)

        return 100 / (odds + 100)

    except:
        return None


# ------------------------------------------------------------
# PETICIONES ESPN
# ------------------------------------------------------------

@st.cache_data(ttl=300)
def get_json(url, params=None):

    try:

        headers = {
            "User-Agent": (
                "Mozilla/5.0 "
                "(iPhone; CPU iPhone OS 18_0 like Mac OS X) "
                "AppleWebKit/605.1.15"
            ),
            "Accept": "application/json",
        }

        response = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=15
        )

        response.raise_for_status()

        return response.json()

    except Exception as e:

        return {
            "_error": str(e)
        }


# ------------------------------------------------------------
# CALENDARIO NFL
# ------------------------------------------------------------

@st.cache_data(ttl=300)
def get_nfl_schedule():

    today = datetime.now(
        ZoneInfo(TIMEZONE)
    ).date()

    end_date = today + timedelta(days=DAYS_AHEAD)

    start_string = today.strftime("%Y%m%d")
    end_string = end_date.strftime("%Y%m%d")

    params = {
        "dates": f"{start_string}-{end_string}"
    }

    data = get_json(
        ESPN_SCOREBOARD,
        params
    )

    if "_error" in data:
        return [], data["_error"]

    events = data.get("events", [])

    games = []

    for event in events:

        try:

            competition = event["competitions"][0]

            competitors = competition["competitors"]

            if len(competitors) != 2:
                continue

            away = None
            home = None

            for team in competitors:

                if team.get("homeAway") == "home":
                    home = team

                elif team.get("homeAway") == "away":
                    away = team

            if not away or not home:
                continue

            event_date = event.get("date")

            games.append(
                {
                    "id": event.get("id"),

                    "date": event_date,

                    "name": event.get(
                        "name",
                        f"{away['team']['displayName']} @ "
                        f"{home['team']['displayName']}"
                    ),

                    "short_name": event.get(
                        "shortName",
                        ""
                    ),

                    "away": away,

                    "home": home,

                    "status": event.get(
                        "status",
                        {}
                    ),

                    "odds": competition.get(
                        "odds",
                        []
                    )
                }
            )

        except Exception:
            continue

    games.sort(
        key=lambda x: x.get("date", "")
    )

    return games, None


# ------------------------------------------------------------
# DATOS DEL EQUIPO
# ------------------------------------------------------------

@st.cache_data(ttl=1800)
def get_team_data(team_id):

    url = f"{ESPN_TEAM}/{team_id}"

    data = get_json(
        url,
        {
            "enable": "roster,stats,projection"
        }
    )

    if "_error" in data:
        return {
            "error": data["_error"]
        }

    return data


# ------------------------------------------------------------
# RÉCORD DEL EQUIPO
# ------------------------------------------------------------

def extract_record(team):

    try:

        records = team.get(
            "records",
            []
        )

        for record in records:

            if record.get("type") in (
                "total",
                "overall"
            ):

                summary = record.get(
                    "summary",
                    ""
                )

                if "-" in summary:

                    parts = summary.split("-")

                    wins = int(parts[0])
                    losses = int(parts[1])

                    return wins, losses

    except:
        pass

    return 0, 0


# ------------------------------------------------------------
# HISTORIAL DEL EQUIPO
# ------------------------------------------------------------

@st.cache_data(ttl=1800)
def get_team_schedule(team_id):

    url = f"{ESPN_TEAM}/{team_id}/schedule"

    data = get_json(url)

    if "_error" in data:
        return []

    events = data.get(
        "events",
        []
    )

    return events


# ------------------------------------------------------------
# RENDIMIENTO RECIENTE
# ------------------------------------------------------------

def recent_performance(team_id, games_to_use=8):

    schedule = get_team_schedule(team_id)

    finished = []

    for event in schedule:

        try:

            competitions = event.get(
                "competitions",
                []
            )

            if not competitions:
                continue

            competition = competitions[0]

            if not competition.get("status", {}).get(
                "type", {}
            ).get("completed", False):
                continue

            competitors = competition.get(
                "competitors",
                []
            )

            my_team = None
            opponent = None

            for c in competitors:

                if str(
                    c.get("team", {}).get("id")
                ) == str(team_id):

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

            result = (
                1 if my_score > opp_score
                else 0
            )

            margin = my_score - opp_score

            finished.append(
                {
                    "result": result,
                    "margin": margin
                }
            )

        except:
            continue

    finished = finished[-games_to_use:]

    if not finished:

        return {
            "wins": 0,
            "games": 0,
            "win_rate": 0.5,
            "avg_margin": 0
        }

    wins = sum(
        x["result"]
        for x in finished
    )

    avg_margin = sum(
        x["margin"]
        for x in finished
    ) / len(finished)

    return {
        "wins": wins,
        "games": len(finished),
        "win_rate": wins / len(finished),
        "avg_margin": avg_margin
    }


# ------------------------------------------------------------
# RATING DEL EQUIPO
# ------------------------------------------------------------

def team_rating(team_id):

    data = get_team_data(team_id)

    if not data or "error" in data:
        return 0.0

    rating = 0.0

    # --------------------------------------------------------
    # 1. RECORD
    # --------------------------------------------------------

    wins, losses = extract_record(data)

    total = wins + losses

    if total > 0:

        win_rate = wins / total

        record_component = (
            (win_rate - 0.5) * 100
        )

        rating += (
            record_component *
            WEIGHT_RECORD
        )

    # --------------------------------------------------------
    # 2. FORMA RECIENTE
    # --------------------------------------------------------

    recent = recent_performance(
        team_id
    )

    recent_component = (
        (recent["win_rate"] - 0.5) * 100
    )

    # Ajuste pequeño por diferencia promedio
    margin_component = clamp(
        recent["avg_margin"] / 2,
        -10,
        10
    )

    recent_component += margin_component

    rating += (
        recent_component *
        WEIGHT_RECENT
    )

    # --------------------------------------------------------
    # 3. RATING ESTADÍSTICO ESPN SI EXISTE
    # --------------------------------------------------------

    try:

        stats = data.get(
            "statistics",
            []
        )

        for stat in stats:

            name = str(
                stat.get("name", "")
            ).lower()

            if name in (
                "rating",
                "powerindex",
                "power_index"
            ):

                value = safe_float(
                    stat.get("value")
                )

                if value:

                    rating += (
                        value *
                        WEIGHT_RATING
                    )

                    break

    except:
        pass

    return rating


# ------------------------------------------------------------
# PROBABILIDAD DEL MODELO
# ------------------------------------------------------------

@st.cache_data(ttl=900)
def calculate_game_probability(
    away_id,
    home_id
):

    away_rating = team_rating(
        away_id
    )

    home_rating = team_rating(
        home_id
    )

    # --------------------------------------------------------
    # DIFERENCIA DE PODER
    # --------------------------------------------------------

    difference = (
        home_rating -
        away_rating
    )

    # --------------------------------------------------------
    # LOCALÍA NFL
    #
    # Aproximadamente +2.5 a +3 puntos de ventaja.
    # Lo traducimos a una pequeña ventaja probabilística.
    # --------------------------------------------------------

    home_field = 3.0

    adjusted_difference = (
        difference +
        home_field
    )

    # --------------------------------------------------------
    # FUNCIÓN LOGÍSTICA
    # --------------------------------------------------------

    probability_home = (
        1 /
        (
            1 +
            math.exp(
                -adjusted_difference / 12
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

    return {
        "away_probability": probability_away,
        "home_probability": probability_home,
        "away_rating": away_rating,
        "home_rating": home_rating,
        "difference": difference
    }


# ------------------------------------------------------------
# OBTENER ODDS DEL PARTIDO
# ------------------------------------------------------------

def get_market_odds(game):

    odds_list = game.get(
        "odds",
        []
    )

    if not odds_list:
        return None

    odds = odds_list[0]

    result = {
        "details": odds.get(
            "details"
        ),
        "over_under": odds.get(
            "overUnder"
        ),
        "spread": odds.get(
            "spread"
        ),
    }

    return result


# ------------------------------------------------------------
# COMPARACIÓN CON LA CASA
# ------------------------------------------------------------

def market_edge(
    model_probability,
    market_probability
):

    if market_probability is None:
        return None

    return (
        model_probability -
        market_probability
    )


# ------------------------------------------------------------
# FORMATO FECHA
# ------------------------------------------------------------

def format_game_date(date_string):

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

        return date_string


def format_game_time(date_string):

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
            "%-I:%M %p"
        )

    except:

        return "N/A"


# ------------------------------------------------------------
# HEADER
# ------------------------------------------------------------

st.markdown(
    "# 🏈 Monitor NFL"
)

st.markdown(
    '<div class="subtitle">'
    "Modelo propio — análisis NFL automático"
    "</div>",
    unsafe_allow_html=True
)


# ------------------------------------------------------------
# TABS
# ------------------------------------------------------------

tab_today, tab_validation, tab_info = st.tabs(
    [
        "🏈 NFL DE HOY",
        "🧪 VALIDACIÓN DEL MODELO",
        "📊 INFORMACIÓN"
    ]
)


# ============================================================
# TAB NFL
# ============================================================

with tab_today:

    st.markdown(
        "## 🏈 NFL DE HOY"
    )

    if st.button(
        "🔄 ACTUALIZAR PARTIDOS",
        use_container_width=True
    ):

        st.cache_data.clear()
        st.rerun()

    games, error = get_nfl_schedule()

    # --------------------------------------------------------
    # ERROR
    # --------------------------------------------------------

    if error:

        st.markdown(
            f"""
            <div class="red-box">
            ⚠️ La fuente automática presentó un problema
            al consultar el calendario.
            <br><br>
            <b>{error}</b>
            </div>
            """,
            unsafe_allow_html=True
        )

    # --------------------------------------------------------
    # PARTIDOS
    # --------------------------------------------------------

    if not games:

        st.markdown(
            """
            <div class="yellow-box">
            ⚠️ No se encontraron partidos NFL
            en los próximos 7 días.
            </div>
            """,
            unsafe_allow_html=True
        )

        st.markdown(
            """
            <div class="blue-box">
            Esto puede significar que no hay partidos
            programados en la ventana consultada o que
            la fuente todavía no publicó todos los eventos.
            </div>
            """,
            unsafe_allow_html=True
        )

    else:

        st.success(
            f"Se encontraron {len(games)} partido(s) NFL."
        )

        # ----------------------------------------------------
        # CADA PARTIDO
        # ----------------------------------------------------

        for game in games:

            away = game["away"]
            home = game["home"]

            away_team = away["team"]
            home_team = home["team"]

            away_id = away_team["id"]
            home_id = home_team["id"]

            away_name = away_team[
                "displayName"
            ]

            home_name = home_team[
                "displayName"
            ]

            game_date = format_game_date(
                game["date"]
            )

            game_time = format_game_time(
                game["date"]
            )

            # ------------------------------------------------
            # MODELO
            # ------------------------------------------------

            model = calculate_game_probability(
                away_id,
                home_id
            )

            away_prob = (
                model["away_probability"]
            )

            home_prob = (
                model["home_probability"]
            )

            away_odds = american_odds(
                away_prob
            )

            home_odds = american_odds(
                home_prob
            )

            # ------------------------------------------------
            # CARD
            # ------------------------------------------------

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

            # ------------------------------------------------
            # COLUMNAS
            # ------------------------------------------------

            col1, col2 = st.columns(2)

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
                    🎯 **Cuota justa: {away_odds:+d}**
                    """
                )

                st.caption(
                    f"Rating modelo: "
                    f"{model['away_rating']:.2f}"
                )

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
                    🎯 **Cuota justa: {home_odds:+d}**
                    """
                )

                st.caption(
                    f"Rating modelo: "
                    f"{model['home_rating']:.2f}"
                )

            # ------------------------------------------------
            # FAVORITO DEL MODELO
            # ------------------------------------------------

            if away_prob > home_prob:

                favorite = away_name
                favorite_probability = away_prob

            else:

                favorite = home_name
                favorite_probability = home_prob

            st.markdown(
                f"""
                <div class="green-box">
                🧠 <b>PROYECCIÓN DEL MODELO</b><br><br>
                Favorito: <b>{favorite}</b><br>
                Probabilidad estimada:
                <b>{favorite_probability * 100:.1f}%</b>
                </div>
                """,
                unsafe_allow_html=True
            )

            # ------------------------------------------------
            # ODDS DE LA CASA
            # ------------------------------------------------

            market = get_market_odds(
                game
            )

            if market:

                st.markdown(
                    "### 🏦 COMPARACIÓN CON LA CASA"
                )

                details = market.get(
                    "details"
                )

                if details:

                    st.write(
                        f"Mercado: **{details}**"
                    )

                if market.get(
                    "spread"
                ) is not None:

                    st.write(
                        f"Spread: "
                        f"**{market['spread']}**"
                    )

                if market.get(
                    "over_under"
                ) is not None:

                    st.write(
                        f"Total: "
                        f"**{market['over_under']}**"
                    )

            else:

                st.markdown(
                    """
                    <div class="blue-box">
                    🏦 Todavía no hay cuotas de mercado
                    disponibles en la fuente automática.
                    </div>
                    """,
                    unsafe_allow_html=True
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
        Esta sección sirve para comprobar si las
        probabilidades generadas por el modelo realmente
        corresponden con los resultados observados.
        """
    )

    st.markdown(
        """
        <div class="yellow-box">
        🎯 <b>LO QUE QUEREMOS COMPROBAR</b><br><br>
        Si el modelo dice 70%, queremos comprobar
        históricamente qué porcentaje de esos partidos
        realmente termina ganándose.
        <br><br>
        No buscamos simplemente tener muchos aciertos.
        Buscamos probabilidades correctamente calibradas.
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown(
        "### 📈 Ejemplo de calibración"
    )

    validation_data = {
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

    st.table(
        validation_data
    )

    st.markdown(
        """
        <div class="blue-box">
        La validación histórica real se ejecutará sobre
        partidos terminados y comparará la probabilidad
        generada por el modelo contra el resultado real.
        </div>
        """,
        unsafe_allow_html=True
    )


# ============================================================
# INFORMACIÓN
# ============================================================

with tab_info:

    st.markdown(
        "## 📊 Información del modelo"
    )

    st.markdown(
        """
        ### 🧠 ¿Qué analiza?

        El modelo utiliza:

        - Récord del equipo.
        - Rendimiento reciente.
        - Diferencia promedio de puntos.
        - Ventaja de jugar como local.
        - Rating estadístico disponible.
        - Conversión de la probabilidad a cuota justa.

        ### 🎯 Objetivo

        No queremos simplemente decir:

        **"Este equipo probablemente gane."**

        Queremos obtener:

        **Probabilidad → cuota justa → comparación con mercado → EDGE.**

        ### ⚠️ Importante

        Una probabilidad del modelo NO significa que el resultado
        esté garantizado.

        El objetivo es encontrar probabilidades que estén
        correctamente calibradas después de suficientes
        pruebas históricas.
        """
    )

    st.divider()

    st.markdown(
        "### 🔬 Arquitectura"
    )

    st.code(
        """
Calendario NFL
      ↓
Equipos
      ↓
Récord
      ↓
Rendimiento reciente
      ↓
Diferencia de puntos
      ↓
Ventaja de local
      ↓
Rating
      ↓
Modelo probabilístico
      ↓
Probabilidad %
      ↓
Cuota justa
      ↓
Comparación con sportsbook
      ↓
EDGE
      ↓
Validación histórica
        """,
        language="text"
    )


# ------------------------------------------------------------
# FOOTER
# ------------------------------------------------------------

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
