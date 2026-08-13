import streamlit as st
import requests
from datetime import datetime
from zoneinfo import ZoneInfo


# =========================================================
# CONFIGURACIÓN
# =========================================================

st.set_page_config(
    page_title="Monitor 60%",
    page_icon="🎯",
    layout="centered"
)

API_BASE = "https://api.balldontlie.io"
API_KEY = st.secrets.get("BALLDONTLIE_API_KEY", "")

MIN_PROBABILITY = 60
MAX_PICKS = 3


# =========================================================
# FUNCIONES
# =========================================================

def get_today():
    """
    Fecha actual en Dallas.
    """
    return datetime.now(
        ZoneInfo("America/Chicago")
    ).date().isoformat()


def api_get(endpoint, params=None):
    """
    Consulta BALLDONTLIE.
    """
    if not API_KEY:
        return None, "No encontramos BALLDONTLIE_API_KEY en Secrets."

    headers = {
        "Authorization": API_KEY
    }

    try:
        response = requests.get(
            f"{API_BASE}{endpoint}",
            headers=headers,
            params=params,
            timeout=15
        )

        if response.status_code == 401:
            return None, "API key inválida o no autorizada."

        if response.status_code == 403:
            return None, "Tu plan actual no tiene acceso a este endpoint."

        if response.status_code == 429:
            return None, "Se alcanzó el límite de solicitudes de la API."

        if response.status_code != 200:
            return None, f"Error de API: {response.status_code}"

        return response.json(), None

    except requests.RequestException as e:
        return None, f"No se pudo conectar con BALLDONTLIE: {e}"


def get_nba_games():
    """
    Obtiene los partidos NBA del día.
    """
    today = get_today()

    data, error = api_get(
        "/v1/games",
        params={
            "dates[]": today,
            "per_page": 100
        }
    )

    if error:
        return [], error

    return data.get("data", []), None


def get_nba_odds():
    """
    Obtiene las cuotas NBA del día.
    """
    today = get_today()

    data, error = api_get(
        "/v2/odds",
        params={
            "dates[]": today,
            "per_page": 100
        }
    )

    if error:
        return [], error

    return data.get("data", []), None


def american_to_probability(odds):
    """
    Convierte cuota americana a probabilidad implícita.
    """
    try:
        odds = float(odds)

        if odds < 0:
            return (-odds) / ((-odds) + 100) * 100

        return 100 / (odds + 100) * 100

    except (TypeError, ValueError):
        return None


def build_opportunities(games, odds):
    """
    Construye las mejores oportunidades usando
    las cuotas disponibles.

    Por ahora usamos la probabilidad implícita del mercado.
    Más adelante podemos incorporar nuestro propio modelo.
    """

    odds_by_game = {}

    for odd in odds:
        game_id = odd.get("game_id")

        if game_id is None:
            continue

        # Preferimos DraftKings si está disponible.
        vendor = str(odd.get("vendor", "")).lower()

        if game_id not in odds_by_game:
            odds_by_game[game_id] = odd
        elif vendor == "draftkings":
            odds_by_game[game_id] = odd

    opportunities = []

    for game in games:

        game_id = game.get("id")

        if game_id not in odds_by_game:
            continue

        odd = odds_by_game[game_id]

        home = game.get("home_team", {})
        away = game.get("visitor_team", {})

        home_name = home.get("full_name", "Local")
        away_name = away.get("full_name", "Visitante")

        home_ml = odd.get("moneyline_home_odds")
        away_ml = odd.get("moneyline_away_odds")

        home_prob = american_to_probability(home_ml)
        away_prob = american_to_probability(away_ml)

        if home_prob is not None:
            opportunities.append({
                "game_id": game_id,
                "game": f"{away_name} vs {home_name}",
                "pick": home_name,
                "probability": home_prob,
                "odds": home_ml,
                "side": "Local",
                "vendor": odd.get("vendor", "Mercado")
            })

        if away_prob is not None:
            opportunities.append({
                "game_id": game_id,
                "game": f"{away_name} vs {home_name}",
                "pick": away_name,
                "probability": away_prob,
                "odds": away_ml,
                "side": "Visitante",
                "vendor": odd.get("vendor", "Mercado")
            })

    # Ordenar de mayor a menor probabilidad
    opportunities.sort(
        key=lambda x: x["probability"],
        reverse=True
    )

    # Solo probabilidades >= mínimo
    opportunities = [
        x for x in opportunities
        if x["probability"] >= MIN_PROBABILITY
    ]

    return opportunities[:MAX_PICKS]


def show_opportunity(number, opportunity):

    probability = opportunity["probability"]

    if probability >= 70:
        level = "🔥 MUY BUENA"
    elif probability >= 65:
        level = "🟢 BUENA"
    else:
        level = "🟡 INTERESANTE"

    st.markdown(
        f"""
        <div style="
            border:1px solid #333;
            border-radius:15px;
            padding:20px;
            margin-bottom:15px;
            background:#171820;
        ">
            <h3>#{number} {level}</h3>

            <p style="font-size:18px;">
                <b>{opportunity['game']}</b>
            </p>

            <p>
                🎯 <b>Apostar:</b> {opportunity['pick']}
            </p>

            <p>
                📊 <b>Probabilidad:</b>
                {probability:.1f}%
            </p>

            <p>
                💰 <b>Cuota:</b>
                {opportunity['odds']}
            </p>

            <p>
                🏦 <b>Fuente:</b>
                {opportunity['vendor']}
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )


# =========================================================
# INTERFAZ
# =========================================================

st.title("🎯 Monitor 60%")

st.write(
    "Encuentra las mejores oportunidades deportivas del día."
)

st.divider()

st.subheader("Selecciona el deporte")

sport = st.selectbox(
    "Deporte",
    [
        "🏀 NBA",
        "🏈 NFL",
        "⚾ MLB",
        "⚽ Soccer",
        "🎾 Tenis"
    ]
)

st.slider(
    "Probabilidad mínima",
    min_value=50,
    max_value=90,
    value=60,
    step=1,
    key="minimum_probability"
)

MIN_PROBABILITY = st.session_state.minimum_probability

st.caption(
    f"Solo mostraremos oportunidades con una probabilidad "
    f"de {MIN_PROBABILITY}% o superior."
)

st.divider()


# =========================================================
# BOTÓN ESCANEAR
# =========================================================

if st.button(
    "🔎 ESCANEAR HOY",
    use_container_width=True
):

    if sport != "🏀 NBA":

        st.info(
            f"🚧 {sport} será conectado después de terminar "
            "y probar correctamente el módulo NBA."
        )

    else:

        with st.spinner("🔎 Escaneando partidos NBA de hoy..."):

            games, games_error = get_nba_games()

            if games_error:
                st.error(games_error)
                st.stop()

            if not games:
                st.info(
                    "💤 No hay partidos NBA disponibles para hoy."
                )
                st.stop()

            odds, odds_error = get_nba_odds()

        st.divider()

        st.header("🏆 Mejores oportunidades — NBA")

        if odds_error:

            st.warning(
                "Los partidos fueron encontrados, pero no "
                "pudimos obtener las cuotas de apuestas."
            )

            st.caption(
                odds_error
            )

            st.info(
                "Necesitamos acceso al endpoint de cuotas "
                "para calcular las oportunidades."
            )

        else:

            opportunities = build_opportunities(
                games,
                odds
            )

            if not opportunities:

                st.info(
                    f"No encontramos oportunidades con "
                    f"probabilidad de {MIN_PROBABILITY}% o superior."
                )

            else:

                for index, opportunity in enumerate(
                    opportunities,
                    start=1
                ):
                    show_opportunity(
                        index,
                        opportunity
                    )

                st.divider()

                st.caption(
                    "⚠️ La probabilidad mostrada es una "
                    "probabilidad implícita derivada de la cuota "
                    "disponible. No garantiza el resultado."
                )


# =========================================================
# PIE
# =========================================================

st.divider()

st.caption(
    "Monitor 60% — máximo 3 oportunidades por deporte."
)

st.caption(
    "La herramienta es informativa y no garantiza resultados."
)
