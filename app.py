import streamlit as st
import requests
from datetime import datetime, timezone

# ============================================================
# CONFIGURACIÓN
# ============================================================

st.set_page_config(
    page_title="Monitor 60%",
    page_icon="🎯",
    layout="centered"
)

API_KEY = st.secrets.get("ODDS_API_KEY", "")

SPORT_KEY = "americanfootball_nfl"

API_URL = (
    f"https://api.the-odds-api.com/v4/sports/"
    f"{SPORT_KEY}/odds"
)

# ============================================================
# FUNCIONES
# ============================================================

def american_to_probability(american):
    """
    Convierte una cuota americana a probabilidad implícita.
    """

    if american is None:
        return 0

    try:
        american = float(american)

        if american > 0:
            return 100 / (american + 100)

        return abs(american) / (abs(american) + 100)

    except:
        return 0


def remove_vig(probabilities):
    """
    Normaliza las probabilidades para reducir el margen
    de la casa.
    """

    total = sum(probabilities)

    if total <= 0:
        return probabilities

    return [p / total for p in probabilities]


def get_nfl_games():
    """
    Obtiene los partidos NFL y sus cuotas actuales.
    """

    if not API_KEY:
        return None, "No encontramos la API KEY."

    params = {
        "regions": "us",
        "markets": "h2h",
        "oddsFormat": "american",
        "apiKey": API_KEY
    }

    try:

        response = requests.get(
            API_URL,
            params=params,
            timeout=15
        )

        if response.status_code != 200:

            try:
                error_data = response.json()

                message = error_data.get(
                    "message",
                    "Error desconocido de la API."
                )

            except:
                message = response.text

            return None, (
                f"Error de The Odds API "
                f"({response.status_code}): {message}"
            )

        return response.json(), None

    except requests.exceptions.Timeout:

        return None, "La API tardó demasiado en responder."

    except requests.exceptions.RequestException as e:

        return None, f"Error de conexión: {e}"


def analyze_games(games):
    """
    Analiza los partidos y genera candidatos.
    """

    opportunities = []

    for game in games:

        home_team = game.get("home_team", "Equipo local")
        away_team = game.get("away_team", "Equipo visitante")

        commence_time = game.get("commence_time", "")

        bookmakers = game.get("bookmakers", [])

        if not bookmakers:
            continue

        # ----------------------------------------------------
        # Recopilar cuotas de todos los bookmakers
        # ----------------------------------------------------

        team_prices = {}

        best_bookmaker = {}

        for bookmaker in bookmakers:

            bookmaker_name = bookmaker.get(
                "title",
                bookmaker.get("key", "Casa")
            )

            markets = bookmaker.get("markets", [])

            for market in markets:

                if market.get("key") != "h2h":
                    continue

                outcomes = market.get("outcomes", [])

                for outcome in outcomes:

                    team = outcome.get("name")
                    price = outcome.get("price")

                    if team is None or price is None:
                        continue

                    try:
                        price = float(price)
                    except:
                        continue

                    if team not in team_prices:
                        team_prices[team] = []

                    team_prices[team].append(price)

                    # Mejor cuota disponible
                    if (
                        team not in best_bookmaker
                        or price > best_bookmaker[team]["price"]
                    ):

                        best_bookmaker[team] = {
                            "price": price,
                            "bookmaker": bookmaker_name
                        }

        if len(team_prices) < 2:
            continue

        # ----------------------------------------------------
        # Promedio de probabilidad implícita
        # ----------------------------------------------------

        raw_probabilities = {}

        for team, prices in team_prices.items():

            probabilities = []

            for price in prices:

                probability = american_to_probability(price)

                if probability > 0:
                    probabilities.append(probability)

            if probabilities:

                average_probability = (
                    sum(probabilities)
                    / len(probabilities)
                )

                raw_probabilities[team] = average_probability

        if len(raw_probabilities) < 2:
            continue

        # ----------------------------------------------------
        # Quitar aproximadamente el margen de la casa
        # ----------------------------------------------------

        teams = list(raw_probabilities.keys())

        raw_values = [
            raw_probabilities[team]
            for team in teams
        ]

        normalized = remove_vig(raw_values)

        probabilities = {}

        for i, team in enumerate(teams):

            probabilities[team] = normalized[i]

        # ----------------------------------------------------
        # Crear oportunidades
        # ----------------------------------------------------

        for team in teams:

            probability = probabilities[team]

            best = best_bookmaker.get(team)

            if not best:
                continue

            decimal_odds = american_to_decimal(
                best["price"]
            )

            # Valor esperado aproximado
            expected_value = (
                probability * decimal_odds
            ) - 1

            opportunities.append({

                "team": team,

                "game": (
                    f"{away_team} vs {home_team}"
                ),

                "probability": probability * 100,

                "american_odds": best["price"],

                "decimal_odds": decimal_odds,

                "expected_value": expected_value * 100,

                "bookmaker": best["bookmaker"],

                "commence_time": commence_time

            })

    return opportunities


def american_to_decimal(american):

    try:

        american = float(american)

        if american > 0:
            return 1 + (american / 100)

        return 1 + (100 / abs(american))

    except:

        return 0


def format_game_time(time_string):

    if not time_string:
        return "Horario no disponible"

    try:

        dt = datetime.fromisoformat(
            time_string.replace("Z", "+00:00")
        )

        local_time = dt.astimezone()

        return local_time.strftime(
            "%m/%d %I:%M %p"
        )

    except:

        return "Horario no disponible"


# ============================================================
# INTERFAZ
# ============================================================

st.title("🎯 Monitor 60%")

st.write(
    "Encuentra las mejores oportunidades deportivas del día."
)

st.divider()

st.header("Selecciona el deporte")

sport = st.selectbox(
    "Deporte",
    [
        "🏈 NFL"
    ]
)

# ------------------------------------------------------------
# FILTRO
# ------------------------------------------------------------

minimum_probability = st.slider(
    "Probabilidad mínima",
    min_value=50,
    max_value=80,
    value=60,
    step=1
)

st.caption(
    f"Solo mostraremos oportunidades con una "
    f"probabilidad estimada de {minimum_probability}% "
    f"o superior."
)

st.divider()

# ------------------------------------------------------------
# BOTÓN
# ------------------------------------------------------------

scan = st.button(
    "🔎 ESCANEAR HOY",
    use_container_width=True
)

# ============================================================
# ESCANEAR
# ============================================================

if scan:

    with st.spinner("Analizando partidos y cuotas..."):

        games, error = get_nfl_games()

    if error:

        st.error(error)

    elif not games:

        st.info(
            "😴 No hay partidos NFL disponibles "
            "para analizar en este momento."
        )

    else:

        opportunities = analyze_games(games)

        # ----------------------------------------------------
        # FILTRO DE PROBABILIDAD
        # ----------------------------------------------------

        filtered = [

            opportunity

            for opportunity in opportunities

            if (
                opportunity["probability"]
                >= minimum_probability
            )

        ]

        # ----------------------------------------------------
        # ORDENAR POR PROBABILIDAD
        # ----------------------------------------------------

        filtered.sort(
            key=lambda x: (
                x["probability"],
                x["expected_value"]
            ),
            reverse=True
        )

        # ----------------------------------------------------
        # SOLO LAS 3 MEJORES
        # ----------------------------------------------------

        top_three = filtered[:3]

        st.divider()

        st.header(
            f"🏆 Mejores oportunidades — {sport}"
        )

        # ----------------------------------------------------
        # NO HAY APUESTAS
        # ----------------------------------------------------

        if not top_three:

            st.error(
                "🔴 NO HAY APUESTAS RECOMENDADAS"
            )

            st.write(
                f"No encontramos una oportunidad "
                f"que alcance el filtro de "
                f"{minimum_probability}%."
            )

            st.caption(
                "Es mejor no apostar que forzar "
                "una selección que no cumple el filtro."
            )

        # ----------------------------------------------------
        # MOSTRAR LAS 3 MEJORES
        # ----------------------------------------------------

        else:

            st.success(
                f"Encontramos {len(top_three)} "
                f"oportunidad(es) que cumplen el filtro."
            )

            for index, opportunity in enumerate(
                top_three,
                start=1
            ):

                st.divider()

                st.subheader(
                    f"{index}. {opportunity['team']}"
                )

                st.write(
                    f"🏈 {opportunity['game']}"
                )

                probability = (
                    opportunity["probability"]
                )

                # ------------------------------------------------
                # NIVEL DE OPORTUNIDAD
                # ------------------------------------------------

                if probability >= 70:

                    st.success(
                        "🟢 OPORTUNIDAD FUERTE"
                    )

                elif probability >= 65:

                    st.success(
                        "🟡 OPORTUNIDAD BUENA"
                    )

                else:

                    st.info(
                        "🟠 OPORTUNIDAD MODERADA"
                    )

                # ------------------------------------------------
                # PROBABILIDAD
                # ------------------------------------------------

                st.metric(
                    "Probabilidad estimada",
                    f"{probability:.1f}%"
                )

                # ------------------------------------------------
                # VALOR
                # ------------------------------------------------

                expected_value = (
                    opportunity["expected_value"]
                )

                st.metric(
                    "Valor estimado",
                    f"{expected_value:+.1f}%"
                )

                # ------------------------------------------------
                # CUOTA
                # ------------------------------------------------

                st.write(
                    f"💰 **Cuota:** "
                    f"{opportunity['american_odds']:+.0f}"
                )

                st.write(
                    f"🏦 **Mejor cuota:** "
                    f"**{opportunity['bookmaker']}**"
                )

                st.write(
                    f"🕐 **Partido:** "
                    f"{format_game_time(opportunity['commence_time'])}"
                )

                st.caption(
                    "La probabilidad es una estimación "
                    "basada en el consenso de cuotas "
                    "disponibles. No garantiza el resultado."
                )

# ============================================================
# INFORMACIÓN
# ============================================================

st.divider()

st.caption(
    "El Monitor 60% utiliza cuotas actuales del mercado "
    "para ordenar oportunidades. El objetivo es mostrar "
    "hasta 3 selecciones por deporte, no forzar apuestas "
    "cuando no existen oportunidades suficientes."
)
