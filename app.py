import streamlit as st
import requests
from datetime import datetime, timezone


# =========================================================
# CONFIGURACIÓN
# =========================================================

st.set_page_config(
    page_title="Monitor 60%",
    page_icon="🎯",
    layout="centered"
)

API_KEY = st.secrets.get("ODDS_API_KEY", "")

SPORTS = {
    "🏈 NFL": "americanfootball_nfl_preseason",
}


# =========================================================
# FUNCIONES
# =========================================================

def american_to_decimal(american):
    """Convierte cuota americana a cuota decimal."""

    if american > 0:
        return 1 + (american / 100)

    return 1 + (100 / abs(american))


def get_odds():
    """Obtiene partidos y cuotas desde The Odds API."""

    if not API_KEY:
        return None, "No se encontró ODDS_API_KEY en Secrets."

    sport = SPORTS["🏈 NFL"]

    url = f"https://api.the-odds-api.com/v4/sports/{sport}/odds"

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
            timeout=20
        )

        if response.status_code != 200:
            return None, (
                f"Error de API: {response.status_code}"
            )

        return response.json(), None

    except Exception as e:

        return None, (
            f"No se pudo conectar con The Odds API: {e}"
        )


def calculate_opportunities(games):
    """
    Calcula una probabilidad estimada a partir del consenso
    de las casas de apuestas.

    Después calcula el valor estimado usando la mejor cuota
    disponible.

    IMPORTANTE:
    Esto NO es una garantía ni un modelo predictivo.
    Es una primera versión basada en mercado.
    """

    opportunities = []

    now = datetime.now(timezone.utc)

    for game in games:

        # -------------------------------------------------
        # Fecha del partido
        # -------------------------------------------------

        try:

            commence = datetime.fromisoformat(
                game["commence_time"].replace(
                    "Z",
                    "+00:00"
                )
            )

        except Exception:
            continue

        # No mostrar partidos que ya comenzaron
        if commence < now:
            continue

        home = game.get(
            "home_team",
            "Local"
        )

        away = game.get(
            "away_team",
            "Visitante"
        )

        # -------------------------------------------------
        # Datos de las casas
        # -------------------------------------------------

        team_probabilities = {}
        team_best_odds = {}

        for bookmaker in game.get(
            "bookmakers",
            []
        ):

            for market in bookmaker.get(
                "markets",
                []
            ):

                if market.get("key") != "h2h":
                    continue

                outcomes = market.get(
                    "outcomes",
                    []
                )

                if len(outcomes) < 2:
                    continue

                raw_probs = []

                # -----------------------------------------
                # Probabilidades implícitas
                # -----------------------------------------

                for outcome in outcomes:

                    price = outcome.get(
                        "price"
                    )

                    if price is None:
                        continue

                    decimal = american_to_decimal(
                        price
                    )

                    if decimal <= 1:
                        continue

                    raw_probability = 1 / decimal

                    raw_probs.append(
                        (
                            outcome["name"],
                            raw_probability,
                            decimal,
                            price
                        )
                    )

                if len(raw_probs) < 2:
                    continue

                # -----------------------------------------
                # Ajustamos el margen de la casa
                # -----------------------------------------

                total_probability = sum(
                    x[1]
                    for x in raw_probs
                )

                for (
                    name,
                    raw_probability,
                    decimal,
                    price
                ) in raw_probs:

                    fair_probability = (
                        raw_probability
                        / total_probability
                    )

                    if name not in team_probabilities:
                        team_probabilities[name] = []

                    team_probabilities[name].append(
                        fair_probability
                    )

                    # -------------------------------------
                    # Guardar mejor cuota disponible
                    # -------------------------------------

                    if (
                        name not in team_best_odds
                        or decimal
                        > team_best_odds[name]["decimal"]
                    ):

                        team_best_odds[name] = {
                            "decimal": decimal,
                            "american": price,
                            "bookmaker": bookmaker.get(
                                "title",
                                "Casa"
                            )
                        }

        # -------------------------------------------------
        # Crear oportunidades
        # -------------------------------------------------

        for team, probabilities in (
            team_probabilities.items()
        ):

            if not probabilities:
                continue

            # Promedio del mercado
            estimated_probability = (
                sum(probabilities)
                / len(probabilities)
            )

            best = team_best_odds.get(
                team
            )

            if not best:
                continue

            decimal = best["decimal"]

            # -------------------------------------------------
            # Valor esperado
            # -------------------------------------------------

            expected_value = (
                estimated_probability
                * decimal
            ) - 1

            opportunities.append({

                "team": team,

                "opponent": (
                    away
                    if team == home
                    else home
                ),

                "home": home,

                "away": away,

                "probability": (
                    estimated_probability
                    * 100
                ),

                "decimal": decimal,

                "american": best["american"],

                "bookmaker": best["bookmaker"],

                "expected_value": (
                    expected_value
                    * 100
                ),

                "commence": commence
            })

    # =====================================================
    # ORDENAR
    # =====================================================

    opportunities.sort(
        key=lambda x: x["expected_value"],
        reverse=True
    )

    return opportunities


# =========================================================
# INTERFAZ
# =========================================================

st.title("🎯 Monitor 60%")

st.write(
    "Encuentra las mejores oportunidades deportivas del día."
)

st.divider()

st.header("Selecciona el deporte")

sport_name = st.selectbox(
    "Deporte",
    list(SPORTS.keys())
)

minimum_probability = st.slider(
    "Probabilidad mínima",
    min_value=50,
    max_value=80,
    value=60,
    step=1
)

st.caption(
    f"Probabilidad mínima seleccionada: "
    f"{minimum_probability}%"
)

st.divider()

scan = st.button(
    "🔎 ESCANEAR HOY",
    use_container_width=True
)


# =========================================================
# ESCANEAR
# =========================================================

if scan:

    with st.spinner(
        "🔎 Analizando partidos y cuotas actuales..."
    ):

        games, error = get_odds()

    # -----------------------------------------------------
    # ERROR
    # -----------------------------------------------------

    if error:

        st.error(error)

    # -----------------------------------------------------
    # SIN PARTIDOS
    # -----------------------------------------------------

    elif not games:

        st.info(
            "😴 No encontramos partidos disponibles "
            "para este deporte."
        )

    else:

        opportunities = calculate_opportunities(
            games
        )

        # =================================================
        # FILTRO PRINCIPAL
        # =================================================
        #
        # Para ser recomendada necesita:
        #
        # 1. Probabilidad >= mínimo seleccionado
        # 2. Valor estimado > 0
        #
        # =================================================

        filtered = [

            opportunity

            for opportunity in opportunities

            if (
                opportunity["probability"]
                >= minimum_probability
            )

            and

            (
                opportunity["expected_value"]
                > 0
            )

        ]

        # Máximo 3
        top_three = filtered[:3]

        st.divider()

        st.header(
            "🏆 Mejores oportunidades — NFL"
        )

        # -------------------------------------------------
        # NO HAY APUESTAS
        # -------------------------------------------------

        if not top_three:

            st.error(
                "🔴 NO HAY APUESTAS RECOMENDADAS"
            )

            st.write(
                f"No encontramos una oportunidad que "
                f"cumpla simultáneamente con:"
            )

            st.write(
                f"• Probabilidad mínima: "
                f"{minimum_probability}%"
            )

            st.write(
                "• Valor estimado: positivo"
            )

            st.caption(
                "Es mejor no apostar que forzar una "
                "selección que no cumple los filtros."
            )

        # -------------------------------------------------
        # MOSTRAR LAS MEJORES
        # -------------------------------------------------

        else:

            st.success(
                f"Encontramos {len(top_three)} "
                f"oportunidad(es) que cumplen los filtros."
            )

            for index, bet in enumerate(
                top_three,
                start=1
            ):

                st.subheader(
                    f"{index}. {bet['team']}"
                )

                st.write(
                    f"🏈 **{bet['away']} "
                    f"vs {bet['home']}**"
                )

                st.success(
                    "🟢 APUESTA RECOMENDADA"
                )

                col1, col2 = st.columns(2)

                with col1:

                    st.metric(
                        "Probabilidad",
                        f"{bet['probability']:.1f}%"
                    )

                with col2:

                    st.metric(
                        "Valor estimado",
                        f"+{bet['expected_value']:.1f}%"
                    )

                st.write(
                    f"💰 Cuota: "
                    f"**{bet['american']:+}**"
                )

                st.write(
                    f"🏦 Mejor cuota: "
                    f"**{bet['bookmaker']}**"
                )

                st.divider()


# =========================================================
# INFORMACIÓN
# =========================================================

st.caption(
    "La probabilidad mostrada es una estimación basada "
    "en el consenso de cuotas disponibles. "
    "No garantiza el resultado de una apuesta."
)
