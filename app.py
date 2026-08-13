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

DALLAS_TZ = ZoneInfo("America/Chicago")

API_KEY = st.secrets.get("ODDS_API_KEY", "")


# ============================================================
# ENDPOINTS NFL
# ============================================================

NFL_URLS = [
    (
        "NFL Preseason",
        "https://api.the-odds-api.com/v4/sports/"
        "americanfootball_nfl_preseason/odds"
    ),
    (
        "NFL",
        "https://api.the-odds-api.com/v4/sports/"
        "americanfootball_nfl/odds"
    )
]


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

    .prob {
        font-size: 42px;
        font-weight: 800;
    }

    .value {
        font-size: 32px;
        font-weight: 800;
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

    .orange-box {
        background: #3a2916;
        border-radius: 15px;
        padding: 18px;
        color: #ffb45c;
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
# CONVERSIÓN DE CUOTAS
# ============================================================

def american_to_decimal(american):

    american = float(american)

    if american > 0:
        return 1 + (american / 100)

    return 1 + (100 / abs(american))


def american_to_probability(american):

    decimal = american_to_decimal(american)

    return 1 / decimal


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
            "No se encontró ODDS_API_KEY "
            "en Streamlit Secrets."
        )

    now_dallas = datetime.now(DALLAS_TZ)

    today = now_dallas.date()

    all_today_games = []

    errors = []

    # --------------------------------------------------------
    # Consultamos NFL PRESEASON + NFL
    # --------------------------------------------------------

    for league_name, url in NFL_URLS:

        params = {
            "apiKey": API_KEY,
            "regions": "us",
            "markets": "h2h",
            "oddsFormat": "american"
        }

        try:

            response = requests.get(
                url,
                params=params,
                timeout=30
            )

            if response.status_code != 200:

                errors.append(
                    f"{league_name}: "
                    f"{response.status_code}"
                )

                continue

            games = response.json()

            if not isinstance(games, list):

                continue

            for game in games:

                commence = game.get(
                    "commence_time"
                )

                if not commence:
                    continue

                try:

                    dt = datetime.fromisoformat(
                        commence.replace(
                            "Z",
                            "+00:00"
                        )
                    )

                    local_dt = dt.astimezone(
                        DALLAS_TZ
                    )

                except Exception:

                    continue

                # =================================================
                # SOLO PARTIDOS DE HOY
                # =================================================

                if local_dt.date() != today:
                    continue

                game["local_datetime"] = local_dt

                game["league_source"] = (
                    league_name
                )

                all_today_games.append(game)

        except requests.exceptions.Timeout:

            errors.append(
                f"{league_name}: timeout"
            )

        except requests.exceptions.RequestException as e:

            errors.append(
                f"{league_name}: {str(e)}"
            )

        except Exception as e:

            errors.append(
                f"{league_name}: {str(e)}"
            )

    # ========================================================
    # ELIMINAR DUPLICADOS
    # ========================================================

    unique_games = {}

    for game in all_today_games:

        game_id = game.get("id")

        if game_id:

            unique_games[game_id] = game

        else:

            key = (
                game.get("home_team"),
                game.get("away_team"),
                game.get(
                    "commence_time"
                )
            )

            unique_games[key] = game

    all_today_games = list(
        unique_games.values()
    )

    # ========================================================
    # ORDENAR POR HORA
    # ========================================================

    all_today_games.sort(
        key=lambda x: x["local_datetime"]
    )

    if not all_today_games:

        error_text = (
            "La API no devolvió partidos NFL "
            "para hoy."
        )

        if errors:

            error_text += (
                "\n\nDetalles: "
                + " | ".join(errors)
            )

        return [], error_text

    return all_today_games, None


# ============================================================
# ANALIZAR UN PARTIDO
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
    # CUOTAS POR EQUIPO
    # --------------------------------------------------------

    odds_by_team = {
        home_team: [],
        away_team: []
    }

    bookmakers_used = set()

    for bookmaker in bookmakers:

        bookmaker_name = bookmaker.get(
            "title",
            bookmaker.get(
                "key",
                "Casa"
            )
        )

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

            valid = 0

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
                        "bookmaker":
                            bookmaker_name
                    }
                )

                valid += 1

            if valid >= 2:

                bookmakers_used.add(
                    bookmaker_name
                )

            break

    # --------------------------------------------------------
    # NECESITAMOS LOS DOS EQUIPOS
    # --------------------------------------------------------

    if (
        not odds_by_team[home_team]
        or not odds_by_team[away_team]
    ):

        return None

    # --------------------------------------------------------
    # MEJOR CUOTA DISPONIBLE
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
    # PROBABILIDADES IMPLÍCITAS
    # DE TODAS LAS CASAS
    # --------------------------------------------------------

    home_probs = [
        american_to_probability(
            x["price"]
        )
        for x in odds_by_team[home_team]
    ]

    away_probs = [
        american_to_probability(
            x["price"]
        )
        for x in odds_by_team[away_team]
    ]

    raw_home = mean(home_probs)
    raw_away = mean(away_probs)

    total = raw_home + raw_away

    if total <= 0:
        return None

    # --------------------------------------------------------
    # QUITAR MARGEN DEL BOOKMAKER
    # --------------------------------------------------------

    fair_home = raw_home / total
    fair_away = raw_away / total

    # --------------------------------------------------------
    # EQUIPO CON MAYOR PROBABILIDAD
    # --------------------------------------------------------

    if fair_home >= fair_away:

        recommended_team = home_team

        probability = fair_home

        best_odds = best_home["price"]

        best_bookmaker = best_home[
            "bookmaker"
        ]

    else:

        recommended_team = away_team

        probability = fair_away

        best_odds = best_away["price"]

        best_bookmaker = best_away[
            "bookmaker"
        ]

    # --------------------------------------------------------
    # PROBABILIDAD IMPLÍCITA DE LA MEJOR CUOTA
    # --------------------------------------------------------

    implied_probability = (
        american_to_probability(
            best_odds
        )
    )

    # --------------------------------------------------------
    # EDGE / VALUE
    # --------------------------------------------------------

    value = (
        probability
        - implied_probability
    )

    probability_pct = probability * 100

    implied_pct = (
        implied_probability * 100
    )

    value_pct = value * 100

    # --------------------------------------------------------
    # CLASIFICACIÓN
    # --------------------------------------------------------

    if probability_pct >= 70:

        label = "🟢 PROBABILIDAD ALTA"

        level = 3

    elif probability_pct >= 60:

        label = "🟡 PROBABILIDAD MEDIA"

        level = 2

    else:

        label = "🟠 PROBABILIDAD MODERADA"

        level = 1

    # --------------------------------------------------------
    # VALUE LABEL
    # --------------------------------------------------------

    if value_pct > 0:

        value_label = "VALUE POSITIVO"

    elif value_pct >= -2:

        value_label = "VALUE CERCANO"

    else:

        value_label = "VALUE NEGATIVO"

    return {

        "home_team": home_team,

        "away_team": away_team,

        "recommended_team":
            recommended_team,

        "probability":
            probability_pct,

        "implied_probability":
            implied_pct,

        "value":
            value_pct,

        "best_odds":
            best_odds,

        "best_bookmaker":
            best_bookmaker,

        "bookmakers":
            len(bookmakers_used),

        "label":
            label,

        "level":
            level,

        "value_label":
            value_label,

        "local_datetime":
            game["local_datetime"],

        "league":
            game.get(
                "league_source",
                "NFL"
            )
    }


# ============================================================
# MOSTRAR RESULTADO
# ============================================================

def display_result(result, ranking):

    dt = result["local_datetime"]

    time_string = dt.strftime(
        "%I:%M %p"
    ).lstrip("0")

    st.markdown(
        f"""
        ## #{ranking} {result["recommended_team"]}

        🏈 **{result["away_team"]} vs
        {result["home_team"]}**

        🕐 **HOY — {time_string}**
        """
    )

    # --------------------------------------------------------
    # COLOR SEGÚN PROBABILIDAD
    # --------------------------------------------------------

    if result["level"] == 3:

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
            <div class="orange-box">
            🟠 PROBABILIDAD MODERADA
            </div>
            """,
            unsafe_allow_html=True
        )

    # --------------------------------------------------------
    # PROBABILIDAD
    # --------------------------------------------------------

    st.markdown(
        "### Probabilidad"
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
    # VALUE
    # --------------------------------------------------------

    st.markdown(
        "### Valor / Edge"
    )

    st.markdown(
        f"""
        <div class="value">
        {result["value"]:+.1f}%
        </div>
        """,
        unsafe_allow_html=True
    )

    # --------------------------------------------------------
    # INFORMACIÓN
    # --------------------------------------------------------

    st.markdown(
        f"""
        💰 **Cuota:**  
        {format_american(result["best_odds"])}

        🏦 **Mejor cuota:**  
        {result["best_bookmaker"]}

        🏪 **Casas analizadas:**  
        {result["bookmakers"]}

        📊 **Probabilidad implícita de la cuota:**  
        {result["implied_probability"]:.1f}%
        """
    )

    # --------------------------------------------------------
    # VALUE
    # --------------------------------------------------------

    if result["value"] > 0:

        st.success(
            f"📈 VALUE POSITIVO: "
            f"+{result['value']:.1f}%"
        )

    elif result["value"] >= -2:

        st.info(
            f"📊 VALUE CERCANO: "
            f"{result['value']:+.1f}%"
        )

    else:

        st.warning(
            f"📉 VALUE NEGATIVO: "
            f"{result['value']:+.1f}%"
        )

    st.caption(
        "La probabilidad es una estimación "
        "basada en las cuotas actuales del "
        "mercado. No garantiza el resultado."
    )

    st.divider()


# ============================================================
# ENCABEZADO
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
# ESCANEAR
# ============================================================

if scan:

    get_today_games.clear()

    with st.spinner(
        "Consultando NFL y NFL Preseason..."
    ):

        games, error = get_today_games()

    # --------------------------------------------------------
    # ERROR
    # --------------------------------------------------------

    if error and not games:

        st.warning(
            "⚠️ " + error
        )

        now = datetime.now(
            DALLAS_TZ
        )

        st.write(
            f"Fecha buscada en Dallas: "
            f"**{now.strftime('%m/%d/%Y')}**"
        )

        st.stop()

    # ========================================================
    # PARTIDOS DE HOY
    # ========================================================

    st.markdown(
        f"""
        # 📅 Partidos de HOY — NFL

        **{len(games)} partidos encontrados**
        """
    )

    st.caption(
        "Solo se muestran partidos cuya fecha "
        "local en Dallas coincide exactamente "
        "con HOY."
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

        league = game.get(
            "league_source",
            "NFL"
        )

        st.markdown(
            f"""
            **{index}. {away} vs {home}**

            🕐 {time_string}

            🏈 {league}
            """
        )

    st.divider()

    # ========================================================
    # ANALIZAR TODOS
    # ========================================================

    analyzed = []

    for game in games:

        result = analyze_game(game)

        if result:

            analyzed.append(result)

    # --------------------------------------------------------
    # ORDEN
    #
    # Primero probabilidad.
    # En empate, mejor value.
    # --------------------------------------------------------

    analyzed.sort(
        key=lambda x: (
            x["probability"],
            x["value"]
        ),
        reverse=True
    )

    # ========================================================
    # MEJORES OPORTUNIDADES
    # ========================================================

    st.markdown(
        """
        # 🏆 Mejores oportunidades de HOY
        """
    )

    if not analyzed:

        st.error(
            "Encontramos los partidos, pero "
            "no encontramos suficientes cuotas "
            "moneyline para analizarlos."
        )

    else:

        # Máximo 3 recomendaciones

        top_results = analyzed[:3]

        for ranking, result in enumerate(
            top_results,
            start=1
        ):

            display_result(
                result,
                ranking
            )

    # ========================================================
    # TODOS LOS PARTIDOS ANALIZADOS
    # ========================================================

    with st.expander(
        "📊 Ver análisis de todos los partidos"
    ):

        for ranking, result in enumerate(
            analyzed,
            start=1
        ):

            dt = result[
                "local_datetime"
            ]

            time_string = dt.strftime(
                "%I:%M %p"
            ).lstrip("0")

            st.write(
                f"""
                **#{ranking} "
                f"{result['recommended_team']}**
                — {result['probability']:.1f}%
                — Value {result['value']:+.1f}%
                — {format_american(result['best_odds'])}
                — {time_string}
                """
            )

            st.caption(
                f"{result['away_team']} vs "
                f"{result['home_team']} | "
                f"{result['best_bookmaker']}"
            )


# ============================================================
# PANTALLA INICIAL
# ============================================================

else:

    st.info(
        "Presiona **🔎 ESCANEAR NFL DE HOY** "
        "para consultar los partidos y cuotas "
        "actuales."
    )

    now = datetime.now(DALLAS_TZ)

    st.caption(
        f"Hoy en Dallas: "
        f"{now.strftime('%m/%d/%Y')}"
    )

    st.caption(
        "El sistema consulta NFL Preseason y NFL "
        "y filtra automáticamente solamente "
        "los partidos de HOY."
    )
