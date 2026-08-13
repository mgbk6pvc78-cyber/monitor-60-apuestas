import streamlit as st
import requests
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from statistics import median

# ============================================================
# CONFIGURACIÓN
# ============================================================

st.set_page_config(
    page_title="Monitor 60%",
    page_icon="🎯",
    layout="centered"
)

API_KEY = st.secrets.get("ODDS_API_KEY", "")

BASE_URL = "https://api.the-odds-api.com/v4/sports"

TZ_DALLAS = ZoneInfo("America/Chicago")


# ============================================================
# DEPORTES
# ============================================================

SPORTS = {
    "🏈 NFL": {
        "keys": [
            "americanfootball_nfl_preseason",
            "americanfootball_nfl"
        ],
        "emoji": "🏈",
        "name": "NFL"
    },

    "🏀 NBA": {
        "keys": [
            "basketball_nba"
        ],
        "emoji": "🏀",
        "name": "NBA"
    },

    "⚾ MLB": {
        "keys": [
            "baseball_mlb"
        ],
        "emoji": "⚾",
        "name": "MLB"
    },

    "⚽ Soccer": {
        "keys": [
            "soccer_epl",
            "soccer_spain_la_liga",
            "soccer_italy_serie_a",
            "soccer_germany_bundesliga",
            "soccer_france_ligue_one",
            "soccer_usa_mls",
            "soccer_mexico_ligamx"
        ],
        "emoji": "⚽",
        "name": "Soccer"
    },

    "🎾 Tenis": {
        "keys": [
            "tennis_atp",
            "tennis_wta"
        ],
        "emoji": "🎾",
        "name": "Tenis"
    }
}


# ============================================================
# FUNCIONES
# ============================================================

def american_to_decimal(odds):
    """Convierte cuota americana a decimal."""
    try:
        odds = float(odds)

        if odds > 0:
            return 1 + odds / 100

        return 1 + 100 / abs(odds)

    except:
        return None


def implied_probability(odds):
    """Probabilidad implícita de una cuota americana."""
    decimal = american_to_decimal(odds)

    if not decimal or decimal <= 1:
        return None

    return 1 / decimal


def format_american(odds):
    """Formatea cuota americana."""
    try:
        odds = int(round(float(odds)))

        if odds > 0:
            return f"+{odds}"

        return str(odds)

    except:
        return "N/A"


def event_is_today(event):
    """
    MUY IMPORTANTE:
    Solo acepta eventos cuya fecha local en Dallas
    sea exactamente HOY.
    """

    try:
        commence = event.get("commence_time")

        if not commence:
            return False

        dt_utc = datetime.fromisoformat(
            commence.replace("Z", "+00:00")
        )

        dt_local = dt_utc.astimezone(TZ_DALLAS)

        today = datetime.now(TZ_DALLAS).date()

        return dt_local.date() == today

    except:
        return False


def get_local_datetime(event):
    """Convierte la hora del evento a Dallas."""

    try:
        commence = event.get("commence_time")

        dt_utc = datetime.fromisoformat(
            commence.replace("Z", "+00:00")
        )

        return dt_utc.astimezone(TZ_DALLAS)

    except:
        return None


def get_best_market(event):
    """
    Busca el mercado h2h y obtiene consenso de las cuotas.
    """

    bookmaker_data = []

    for bookmaker in event.get("bookmakers", []):

        for market in bookmaker.get("markets", []):

            if market.get("key") != "h2h":
                continue

            outcomes = market.get("outcomes", [])

            if len(outcomes) < 2:
                continue

            probabilities = []

            for outcome in outcomes:

                p = implied_probability(
                    outcome.get("price")
                )

                if p:
                    probabilities.append(p)

            if len(probabilities) < 2:
                continue

            # Quitamos aproximadamente el margen de la casa.
            total_probability = sum(probabilities)

            normalized = []

            for outcome in outcomes:

                p = implied_probability(
                    outcome.get("price")
                )

                if p:
                    fair_probability = p / total_probability

                    normalized.append({
                        "name": outcome.get("name"),
                        "price": outcome.get("price"),
                        "probability": fair_probability
                    })

            bookmaker_data.append({
                "bookmaker": bookmaker.get("title", "Casa"),
                "outcomes": normalized
            })

    if not bookmaker_data:
        return None

    # --------------------------------------------------------
    # CONSENSO ENTRE CASAS
    # --------------------------------------------------------

    outcome_names = set()

    for book in bookmaker_data:
        for outcome in book["outcomes"]:
            outcome_names.add(outcome["name"])

    consensus = []

    for name in outcome_names:

        values = []

        for book in bookmaker_data:

            for outcome in book["outcomes"]:

                if outcome["name"] == name:
                    values.append(outcome["probability"])

        if not values:
            continue

        probability = median(values)

        # Encontrar la mejor cuota disponible
        best_price = None
        best_book = None

        for book in bookmaker_data:

            for outcome in book["outcomes"]:

                if outcome["name"] == name:

                    price = outcome["price"]

                    if best_price is None:
                        best_price = price
                        best_book = book["bookmaker"]

                    else:

                        # Cuota decimal mayor = mejor
                        current_decimal = american_to_decimal(price)
                        best_decimal = american_to_decimal(best_price)

                        if (
                            current_decimal
                            and best_decimal
                            and current_decimal > best_decimal
                        ):
                            best_price = price
                            best_book = book["bookmaker"]

        if best_price is None:
            continue

        decimal = american_to_decimal(best_price)

        value = None

        if decimal:
            value = (probability * decimal) - 1

        consensus.append({
            "team": name,
            "probability": probability,
            "price": best_price,
            "bookmaker": best_book,
            "value": value
        })

    return consensus


def get_today_events(sport_key):
    """
    Obtiene eventos y FILTRA EXCLUSIVAMENTE HOY.
    """

    url = f"{BASE_URL}/{sport_key}/odds"

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
            return [], response.text

        events = response.json()

        today_events = []

        for event in events:

            if event_is_today(event):
                today_events.append(event)

        return today_events, None

    except Exception as e:

        return [], str(e)


def scan_sport(sport_config):
    """
    Escanea los sport keys disponibles.
    """

    all_events = []
    errors = []

    for sport_key in sport_config["keys"]:

        events, error = get_today_events(sport_key)

        if error:
            errors.append(
                f"{sport_key}: {error}"
            )

        all_events.extend(events)

    # --------------------------------------------------------
    # ELIMINAR DUPLICADOS
    # --------------------------------------------------------

    unique = {}

    for event in all_events:

        event_id = event.get("id")

        if event_id:
            unique[event_id] = event

    return list(unique.values()), errors


def build_opportunities(events):
    """
    Construye todas las oportunidades de hoy.
    """

    opportunities = []

    for event in events:

        market = get_best_market(event)

        if not market:
            continue

        local_dt = get_local_datetime(event)

        if not local_dt:
            continue

        for selection in market:

            # Solo apuestas con probabilidad razonable
            if selection["probability"] < 0.50:
                continue

            opportunities.append({
                "event": event,
                "team": selection["team"],
                "probability": selection["probability"],
                "price": selection["price"],
                "bookmaker": selection["bookmaker"],
                "value": selection["value"],
                "datetime": local_dt
            })

    # --------------------------------------------------------
    # ORDENAR
    #
    # Primero probabilidad.
    # Luego valor.
    # --------------------------------------------------------

    opportunities.sort(
        key=lambda x: (
            x["probability"],
            x["value"] if x["value"] is not None else -999
        ),
        reverse=True
    )

    return opportunities


def opportunity_label(probability):
    """
    Clasificación visual.
    """

    if probability >= 0.75:
        return "🟢 OPORTUNIDAD FUERTE"

    if probability >= 0.65:
        return "🟡 OPORTUNIDAD BUENA"

    return "🟠 OPORTUNIDAD MODERADA"


def display_probability(probability):
    return f"{probability * 100:.1f}%"


def display_value(value):
    if value is None:
        return "N/A"

    return f"{value * 100:+.1f}%"


# ============================================================
# INTERFAZ
# ============================================================

st.title("🎯 Monitor 60%")

st.write(
    "Encuentra las mejores oportunidades deportivas del día."
)

st.divider()

st.header("Selecciona el deporte")

sport_selected = st.selectbox(
    "Deporte",
    list(SPORTS.keys())
)

sport_config = SPORTS[sport_selected]

st.caption(
    "📅 El escaneo está limitado exclusivamente a partidos "
    "que comienzan HOY en horario de Dallas."
)

st.divider()

# ============================================================
# BOTÓN
# ============================================================

scan = st.button(
    "🔎 ESCANEAR HOY",
    use_container_width=True
)


# ============================================================
# ESCANEO
# ============================================================

if scan:

    if not API_KEY:

        st.error(
            "❌ No encontramos ODDs_API_KEY en Secrets."
        )

        st.stop()

    # --------------------------------------------------------
    # HORA ACTUAL
    # --------------------------------------------------------

    now = datetime.now(TZ_DALLAS)

    st.info(
        f"📅 Hoy: {now.strftime('%m/%d/%Y')} "
        f"— Dallas, Texas"
    )

    with st.spinner(
        "🔎 Buscando únicamente partidos de HOY..."
    ):

        events, errors = scan_sport(
            sport_config
        )

    # --------------------------------------------------------
    # ERRORES
    # --------------------------------------------------------

    if errors:

        with st.expander("Detalles técnicos"):

            for error in errors:
                st.write(error)

    # --------------------------------------------------------
    # NO HAY PARTIDOS
    # --------------------------------------------------------

    if not events:

        st.warning(
            f"No encontramos partidos de "
            f"{sport_config['name']} para HOY."
        )

        st.caption(
            "No mostramos partidos de mañana ni de fechas futuras."
        )

        st.stop()

    # --------------------------------------------------------
    # MOSTRAR PARTIDOS DE HOY
    # --------------------------------------------------------

    st.success(
        f"✅ Encontramos {len(events)} partido(s) de "
        f"{sport_config['name']} para HOY."
    )

    st.divider()

    st.header(
        f"📅 Partidos de HOY — {sport_config['name']}"
    )

    # Orden cronológico
    events.sort(
        key=lambda x: get_local_datetime(x)
    )

    for index, event in enumerate(events, 1):

        local_dt = get_local_datetime(event)

        home = event.get(
            "home_team",
            "Equipo local"
        )

        away = event.get(
            "away_team",
            "Equipo visitante"
        )

        st.subheader(
            f"{index}. {away} vs {home}"
        )

        if local_dt:

            st.write(
                f"🕒 {local_dt.strftime('%I:%M %p')}"
            )

        st.write(
            f"🏟️ {event.get('sport_title', sport_config['name'])}"
        )

        st.divider()

    # ========================================================
    # OPORTUNIDADES
    # ========================================================

    opportunities = build_opportunities(events)

    st.header(
        f"🏆 Mejores oportunidades — "
        f"{sport_config['name']}"
    )

    if not opportunities:

        st.warning(
            "No encontramos una apuesta que cumpla "
            "los criterios mínimos."
        )

        st.caption(
            "Es mejor no apostar que forzar una selección."
        )

    else:

        # Máximo 3
        top_3 = opportunities[:3]

        for index, pick in enumerate(top_3, 1):

            event = pick["event"]

            home = event.get(
                "home_team",
                ""
            )

            away = event.get(
                "away_team",
                ""
            )

            local_dt = pick["datetime"]

            st.subheader(
                f"{index}. {pick['team']}"
            )

            st.write(
                f"{sport_config['emoji']} "
                f"{away} vs {home}"
            )

            st.success(
                opportunity_label(
                    pick["probability"]
                )
            )

            st.metric(
                "Probabilidad estimada",
                display_probability(
                    pick["probability"]
                )
            )

            st.metric(
                "Valor estimado",
                display_value(
                    pick["value"]
                )
            )

            st.write(
                f"💰 **Cuota:** "
                f"{format_american(pick['price'])}"
            )

            st.write(
                f"🏦 **Mejor cuota:** "
                f"{pick['bookmaker']}"
            )

            st.write(
                f"🕒 **Partido:** "
                f"{local_dt.strftime('%m/%d %I:%M %p')}"
            )

            st.divider()

    # ========================================================
    # EXPLICACIÓN
    # ========================================================

    st.caption(
        "El Monitor 60% utiliza las cuotas actuales disponibles "
        "en el mercado para estimar probabilidades y ordenar "
        "las oportunidades. Una probabilidad estimada no "
        "garantiza el resultado de una apuesta."
    )

    st.caption(
        "📅 Solo se consideran eventos cuya fecha local "
        "en Dallas coincide exactamente con HOY."
    )
