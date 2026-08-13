import streamlit as st
import requests
from datetime import datetime
from zoneinfo import ZoneInfo
from statistics import mean


# ============================================================
# CONFIGURACIÓN
# ============================================================

st.set_page_config(
    page_title="Monitor 60% NFL",
    page_icon="🏈",
    layout="centered"
)

# ============================================================
# API
# ============================================================

API_KEY = st.secrets.get("ODDS_API_KEY", "")

ODDS_URL = (
    "https://api.the-odds-api.com/v4/sports/"
    "americanfootball_nfl/odds"
)

DALLAS_TZ = ZoneInfo("America/Chicago")


# ============================================================
# ESTILO
# ============================================================

st.markdown(
    """
    <style>

    .stApp {
        background-color: #0d0f14;
    }

    .big-title {
        font-size: 42px;
        font-weight: 800;
        margin-bottom: 5px;
    }

    .subtitle {
        font-size: 20px;
        color: #9ca3af;
        margin-bottom: 30px;
    }

    .game-card {
        background: #15181d;
        border: 1px solid #292d35;
        border-radius: 18px;
        padding: 22px;
        margin-bottom: 20px;
    }

    .team {
        font-size: 21px;
        font-weight: 700;
    }

    .small {
        color: #9ca3af;
        font-size: 15px;
    }

    .prob {
        font-size: 38px;
        font-weight: 800;
    }

    .value {
        font-size: 30px;
        font-weight: 700;
    }

    .green-box {
        background: #163a29;
        border-radius: 15px;
        padding: 18px;
        color: #72e39b;
        font-size: 20px;
        font-weight: 700;
        margin: 15px 0;
    }

    .yellow-box {
        background: #3a3216;
        border-radius: 15px;
        padding: 18px;
        color: #f4d35e;
        font-size: 20px;
        font-weight: 700;
        margin: 15px 0;
    }

    .red-box {
        background: #3a1e22;
        border-radius: 15px;
        padding: 18px;
        color: #ff7373;
        font-size: 20px;
        font-weight: 700;
        margin: 15px 0;
    }

    </style>
    """,
    unsafe_allow_html=True
)


# ============================================================
# FUNCIONES DE CUOTAS
# ============================================================

def american_to_decimal(american):

    american = float(american)

    if american > 0:
        return 1 + (american / 100)

    return 1 + (100 / abs(american))


def american_to_implied_probability(american):

    decimal = american_to_decimal(american)

    return 1 / decimal


def decimal_to_american(decimal):

    if decimal >= 2:
        return int(round((decimal - 1) * 100))

    return int(round(-100 / (decimal - 1)))


def format_american(odds):

    odds = int(odds)

    if odds > 0:
        return f"+{odds}"

    return str(odds)


# ============================================================
# OBTENER PARTIDOS DE HOY
# ============================================================

@st.cache_data(ttl=60)
def get_today_games():

    if not API_KEY:

        return None, (
            "No se encontró ODDS_API_KEY en "
            "Streamlit Secrets."
        )

    params = {
        "apiKey": API_KEY,
        "regions": "us",
        "markets": "h2h",
        "oddsFormat": "american"
    }

    try:

        response = requests.get(
            ODDS_URL,
            params=params,
            timeout=30
        )

        if response.status_code != 200:

            return None, (
                f"Error The Odds API "
                f"{response.status_code}: "
                f"{response.text[:500]}"
            )

        games = response.json()

        now_dallas = datetime.now(DALLAS_TZ)

        today = now_dallas.date()

        today_games = []

        for game in games:

            commence = game.get("commence_time")

            if not commence:
                continue

            try:

                dt = datetime.fromisoformat(
                    commence.replace("Z", "+00:00")
                )

                local_dt = dt.astimezone(
                    DALLAS_TZ
                )

            except Exception:

                continue

            # =================================================
            # SOLO HOY
            # =================================================

            if local_dt.date() != today:
                continue

            game["local_datetime"] = local_dt

            today_games.append(game)

        # Orden cronológico

        today_games.sort(
            key=lambda x: x["local_datetime"]
        )

        return today_games, None

    except requests.exceptions.Timeout:

        return None, (
            "The Odds API tardó demasiado "
            "en responder."
        )

    except requests.exceptions.RequestException as e:

        return None, (
            f"Error de conexión: {e}"
        )

    except Exception as e:

        return None, (
            f"Error procesando partidos: {e}"
        )


# ============================================================
# ANALIZAR CUOTAS DE UN PARTIDO
# ============================================================

def analyze_game(game):

    home_team = game.get(
        "home_team",
        "Home"
    )

    away_team = game.get(
        "away_team",
        "Away"
    )

    bookmakers = game.get(
        "bookmakers",
        []
    )

    # --------------------------------------------------------
    # Guardamos todas las cuotas por equipo
    # --------------------------------------------------------

    odds_by_team = {
        home_team: [],
        away_team: []
    }

    bookmaker_count = 0

    for bookmaker in bookmakers:

        markets = bookmaker.get(
            "markets",
            []
        )

        for market in markets:

            if market.get("key") != "h2h":
                continue

            outcomes = market.get(
                "outcomes",
                []
            )

            valid_outcomes = 0

            for outcome in outcomes:

                name = outcome.get("name")
                price = outcome.get("price")

                if name not in odds_by_team:
                    continue

                if price is None:
                    continue

                odds_by_team[name].append(
                    {
                        "price": float(price),
                        "bookmaker": bookmaker.get(
                            "title",
                            bookmaker.get(
                                "key",
                                "Casa"
                            )
                        )
                    }
                )

                valid_outcomes += 1

            if valid_outcomes >= 2:

                bookmaker_count += 1

            break

    # --------------------------------------------------------
    # Si no tenemos cuotas suficientes
    # --------------------------------------------------------

    if (
        not odds_by_team[home_team]
        or not odds_by_team[away_team]
    ):

        return None

    # --------------------------------------------------------
    # Mejor cuota de cada equipo
    # --------------------------------------------------------

    best_home = max(
        odds_by_team[home_team],
        key=lambda x: x["price"]
    )

    best_away = max(
        odds_by_team[away_team],
        key=lambda x: x["price"]
    )

    # --------------------------------------------------------
    # Probabilidades implícitas de todas las casas
    # --------------------------------------------------------

    home_probs = [
        american_to_implied_probability(
            x["price"]
        )
        for x in odds_by_team[home_team]
    ]

    away_probs = [
        american_to_implied_probability(
            x["price"]
        )
        for x in odds_by_team[away_team]
    ]

    raw_home = mean(home_probs)
    raw_away = mean(away_probs)

    # --------------------------------------------------------
    # Quitamos el margen promedio del mercado
    # --------------------------------------------------------

    total_raw = raw_home + raw_away

    if total_raw <= 0:
        return None

    fair_home = raw_home / total_raw
    fair_away = raw_away / total_raw

    # --------------------------------------------------------
    # Elegimos el lado con mayor probabilidad
    # --------------------------------------------------------

    if fair_home >= fair_away:

        recommended_team = home_team

        estimated_probability = fair_home

        best_odds = best_home["price"]

        best_bookmaker = best_home[
            "bookmaker"
        ]

    else:

        recommended_team = away_team

        estimated_probability = fair_away

        best_odds = best_away["price"]

        best_bookmaker = best_away[
            "bookmaker"
        ]

    # --------------------------------------------------------
    # Probabilidad implícita de la mejor cuota
    # --------------------------------------------------------

    best_implied_probability = (
        american_to_implied_probability(
            best_odds
        )
    )

    # --------------------------------------------------------
    # VALUE / EDGE
    #
    # Si nuestra probabilidad estimada es mayor
    # que la probabilidad implícita de la cuota,
    # existe edge matemático según este modelo.
    # --------------------------------------------------------

    value = (
        estimated_probability
        - best_implied_probability
    )

    value_percentage = value * 100

    # --------------------------------------------------------
    # CLASIFICACIÓN
    # --------------------------------------------------------

    probability_percentage = (
        estimated_probability * 100
    )

    if probability_percentage >= 70:

        label = "🟢 PROBABILIDAD ALTA"

        level = 3

    elif probability_percentage >= 60:

        label = "🟡 PROBABILIDAD MEDIA"

        level = 2

    else:

        label = "🟠 PROBABILIDAD MODERADA"

        level = 1

    # Si además existe edge positivo,
    # lo destacamos.

    if value_percentage > 0:

        value_label = "VALUE POSITIVO"

    elif value_percentage > -2:

        value_label = "VALUE CERCANO A 0"

    else:

        value_label = "SIN VALUE"

    return {

        "home_team": home_team,

        "away_team": away_team,

        "recommended_team": recommended_team,

        "probability": probability_percentage,

        "best_odds": best_odds,

        "best_bookmaker": best_bookmaker,

        "implied_probability":
            best_implied_probability * 100,

        "value": value_percentage,

        "bookmakers": bookmaker_count,

        "label": label,

        "level": level,

        "value_label": value_label,

        "local_datetime":
            game["local_datetime"]

    }


# ============================================================
# MOSTRAR PARTIDO
# ============================================================

def show_game(game):

    result = analyze_game(game)

    if not result:
        return

    dt = result["local_datetime"]

    time_string = dt.strftime(
        "%I:%M %p"
    ).lstrip("0")

    # --------------------------------------------------------
    # Título
    # --------------------------------------------------------

    st.markdown(
        f"""
        <div class="game-card">

        <div class="team">
        🏈 {result["away_team"]}
        </div>

        <div class="small">
        vs
        </div>

        <div class="team">
        {result["home_team"]}
        </div>

        <br>

        <div class="small">
        🕐 HOY — {time_string}
        </div>

        </div>
        """,
        unsafe_allow_html=True
    )

    # --------------------------------------------------------
    # Oportunidad
    # --------------------------------------------------------

    if result["level"] >= 3:

        st.markdown(
            f"""
            <div class="green-box">
            🟢 {result["label"]}
            </div>
            """,
            unsafe_allow_html=True
        )

    elif result["level"] == 2:

        st.markdown(
            f"""
            <div class="yellow-box">
            🟡 {result["label"]}
            </div>
            """,
            unsafe_allow_html=True
        )

    else:

        st.markdown(
            f"""
            <div class="yellow-box">
            🟠 {result["label"]}
            </div>
            """,
            unsafe_allow_html=True
        )

    # --------------------------------------------------------
    # Probabilidad
    # --------------------------------------------------------

    st.markdown(
        "### Probabilidad estimada"
    )

    st.markdown(
        f"""
        <div class="prob">
        {result["probability"]:.1f}%
        </div>
        """,
        unsafe_allow_html=True
    )

    # --------------------------------------------------------
    # Equipo recomendado
    # --------------------------------------------------------

    st.markdown(
        f"""
        **🏆 Lado recomendado:**  
        {result["recommended_team"]}
        """
    )

    # --------------------------------------------------------
    # Cuota
    # --------------------------------------------------------

    st.markdown(
        f"""
        💰 **Mejor cuota:**  
        {format_american(result["best_odds"])}
        """
    )

    # --------------------------------------------------------
    # Casa
    # --------------------------------------------------------

    st.markdown(
        f"""
        🏦 **Mejor casa:**  
        {result["best_bookmaker"]}
        """
    )

    # --------------------------------------------------------
    # Casas analizadas
    # --------------------------------------------------------

    st.markdown(
        f"""
        🏪 **Casas analizadas:**  
        {result["bookmakers"]}
        """
    )

    # --------------------------------------------------------
    # VALUE
    # --------------------------------------------------------

    if result["value"] > 0:

        st.success(
            f"📈 VALUE: +{result['value']:.1f}%"
        )

    else:

        st.info(
            f"📊 VALUE: {result['value']:.1f}%"
        )

    st.caption(
        f"Probabilidad implícita de la mejor cuota: "
        f"{result['implied_probability']:.1f}%"
    )

    st.divider()


# ============================================================
# HEADER
# ============================================================

st.markdown(
    """
    <div class="big-title">
    🏈 Monitor 60% NFL
    </div>

    <div class="subtitle">
    Modelo independiente — solo partidos de HOY
    </div>
    """,
    unsafe_allow_html=True
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

    # Limpiar cache para obtener cuotas nuevas

    get_today_games.clear()

    with st.spinner(
        "Buscando partidos NFL de hoy..."
    ):

        games, error = get_today_games()

    # --------------------------------------------------------
    # ERROR
    # --------------------------------------------------------

    if error:

        st.error(error)

        st.stop()

    # --------------------------------------------------------
    # SIN PARTIDOS
    # --------------------------------------------------------

    if not games:

        now = datetime.now(
            DALLAS_TZ
        )

        st.warning(
            "⚠️ La API no devolvió partidos "
            "NFL para hoy."
        )

        st.write(
            f"Fecha buscada en Dallas: "
            f"**{now.strftime('%m/%d/%Y')}**"
        )

        st.info(
            "Si sabes que hay partidos hoy, "
            "el siguiente paso es revisar "
            "la respuesta exacta de The Odds API."
        )

        st.stop()

    # ========================================================
    # PARTIDOS DE HOY
    # ========================================================

    st.markdown(
        f"""
        ## 📅 Partidos de HOY — NFL

        **{len(games)} partidos encontrados**
        """
    )

    st.caption(
        "Todos los horarios están convertidos "
        "a hora de Dallas."
    )

    # --------------------------------------------------------
    # LISTA DE PARTIDOS
    # --------------------------------------------------------

    for index, game in enumerate(
        games,
        start=1
    ):

        dt = game["local_datetime"]

        time_string = dt.strftime(
            "%I:%M %p"
        ).lstrip("0")

        away = game.get(
            "away_team",
            "Away"
        )

        home = game.get(
            "home_team",
            "Home"
        )

        st.markdown(
            f"""
            **{index}. {away} vs {home}**  
            🕐 {time_string}
            """
        )

    st.divider()

    # ========================================================
    # ANALISIS
    # ========================================================

    st.markdown(
        """
        ## 🏆 Mejores oportunidades de HOY
        """
    )

    analyzed = []

    for game in games:

        result = analyze_game(game)

        if result:

            analyzed.append(result)

    # --------------------------------------------------------
    # ORDENAR
    # Primero mayor probabilidad,
    # después mayor value.
    # --------------------------------------------------------

    analyzed.sort(
        key=lambda x: (
            x["probability"],
            x["value"]
        ),
        reverse=True
    )

    # --------------------------------------------------------
    # Mostrar máximo 3
    # --------------------------------------------------------

    if not analyzed:

        st.warning(
            "No pudimos analizar las cuotas "
            "de los partidos de hoy."
        )

    else:

        for result in analyzed[:3]:

            # Reconstruimos un objeto mínimo
            # para reutilizar show_game.

            fake_game = {
                "home_team":
                    result["home_team"],

                "away_team":
                    result["away_team"],

                "local_datetime":
                    result["local_datetime"],

                "bookmakers": []
            }

            # ------------------------------------------------
            # En lugar de volver a pedir la API,
            # mostramos directamente el resultado.
            # ------------------------------------------------

            dt = result["local_datetime"]

            time_string = dt.strftime(
                "%I:%M %p"
            ).lstrip("0")

            st.markdown(
                f"""
                ### 🏈 {result["recommended_team"]}

                **{result["away_team"]} vs
                {result["home_team"]}**

                🕐 HOY — {time_string}
                """
            )

            if result["level"] >= 3:

                st.markdown(
                    """
                    <div class="green-box">
                    🟢 PROBABILIDAD ALTA
                    </div>
                    """,
                    unsafe_allow_html=True
                )

            elif result["level"] == 2:

                st.markdown(
                    """
                    <div class="yellow-box">
                    🟡 PROBABILIDAD MEDIA
                    </div>
                    """,
                    unsafe_allow_html=True
                )

            else:

                st.markdown(
                    """
                    <div class="yellow-box">
                    🟠 PROBABILIDAD MODERADA
                    </div>
                    """,
                    unsafe_allow_html=True
                )

            st.markdown(
                f"""
                **Probabilidad**

                ## {result["probability"]:.1f}%

                **Valor / Edge**

                ## {result["value"]:+.1f}%

                💰 **Cuota:**  
                {format_american(result["best_odds"])}

                🏦 **Mejor casa:**  
                {result["best_bookmaker"]}

                🏪 **Casas analizadas:**  
                {result["bookmakers"]}
                """
            )

            if result["value"] > 0:

                st.success(
                    f"📈 VALUE POSITIVO "
                    f"+{result['value']:.1f}%"
                )

            else:

                st.info(
                    f"📊 VALUE "
                    f"{result['value']:.1f}%"
                )

            st.caption(
                "La probabilidad es una estimación "
                "basada en las cuotas disponibles. "
                "No garantiza el resultado."
            )

            st.divider()


# ============================================================
# MENSAJE INICIAL
# ============================================================

else:

    st.info(
        "Presiona **🔎 ESCANEAR NFL DE HOY** "
        "para consultar los partidos y cuotas "
        "actuales."
    )

    st.caption(
        "El sistema solamente considera eventos "
        "cuya fecha local en Dallas coincide "
        "exactamente con HOY."
    )
