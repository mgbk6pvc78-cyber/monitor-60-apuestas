import streamlit as st
import requests
from datetime import datetime
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

# Dallas / Texas
TZ_DALLAS = ZoneInfo("America/Chicago")

# Mínimo absoluto para considerar una apuesta
MIN_PROBABILITY = 0.60

# Máximo de recomendaciones
MAX_PICKS = 3


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
            "soccer_usa_mls",
            "soccer_mexico_ligamx",
            "soccer_epl",
            "soccer_spain_la_liga",
            "soccer_italy_serie_a",
            "soccer_germany_bundesliga",
            "soccer_france_ligue_one"
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
# CONVERSIÓN DE CUOTAS
# ============================================================

def american_to_decimal(odds):
    try:
        odds = float(odds)

        if odds > 0:
            return 1 + (odds / 100)

        return 1 + (100 / abs(odds))

    except:
        return None


def implied_probability(odds):
    decimal = american_to_decimal(odds)

    if not decimal or decimal <= 1:
        return None

    return 1 / decimal


def format_american(odds):
    try:
        odds = int(round(float(odds)))

        if odds > 0:
            return f"+{odds}"

        return str(odds)

    except:
        return "N/A"


# ============================================================
# FECHA / HORA
# ============================================================

def get_local_datetime(event):

    try:

        commence = event.get("commence_time")

        if not commence:
            return None

        dt = datetime.fromisoformat(
            commence.replace("Z", "+00:00")
        )

        return dt.astimezone(TZ_DALLAS)

    except:
        return None


def event_is_today(event):

    local_dt = get_local_datetime(event)

    if not local_dt:
        return False

    today = datetime.now(TZ_DALLAS).date()

    return local_dt.date() == today


# ============================================================
# OBTENER PARTIDOS
# ============================================================

def get_today_events(sport_key):

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

        data = response.json()

        today_events = []

        for event in data:

            if event_is_today(event):
                today_events.append(event)

        return today_events, None

    except Exception as e:

        return [], str(e)


def scan_sport(sport_config):

    all_events = []
    errors = []

    for sport_key in sport_config["keys"]:

        events, error = get_today_events(
            sport_key
        )

        if error:
            errors.append(
                f"{sport_key}: {error}"
            )

        all_events.extend(events)

    # --------------------------------------------------------
    # ELIMINAR DUPLICADOS
    # --------------------------------------------------------

    unique_events = {}

    for event in all_events:

        event_id = event.get("id")

        if event_id:
            unique_events[event_id] = event

    return list(unique_events.values()), errors


# ============================================================
# ANALIZAR CUOTAS
# ============================================================

def analyze_event(event):

    bookmakers = []

    for bookmaker in event.get("bookmakers", []):

        for market in bookmaker.get("markets", []):

            if market.get("key") != "h2h":
                continue

            outcomes = market.get("outcomes", [])

            if len(outcomes) < 2:
                continue

            bookmaker_outcomes = []

            raw_probs = []

            for outcome in outcomes:

                price = outcome.get("price")

                probability = implied_probability(
                    price
                )

                if probability:

                    raw_probs.append(probability)

                    bookmaker_outcomes.append({
                        "name": outcome.get("name"),
                        "price": price,
                        "raw_probability": probability
                    })

            if len(bookmaker_outcomes) < 2:
                continue

            total = sum(raw_probs)

            for outcome in bookmaker_outcomes:

                outcome["fair_probability"] = (
                    outcome["raw_probability"] / total
                )

            bookmakers.append({
                "name": bookmaker.get(
                    "title",
                    "Casa"
                ),
                "outcomes": bookmaker_outcomes
            })

    if not bookmakers:
        return []

    # ========================================================
    # CONSENSO
    # ========================================================

    team_names = set()

    for bookmaker in bookmakers:

        for outcome in bookmaker["outcomes"]:

            team_names.add(
                outcome["name"]
            )

    results = []

    for team in team_names:

        probabilities = []

        best_price = None
        best_book = None

        prices_found = []

        for bookmaker in bookmakers:

            for outcome in bookmaker["outcomes"]:

                if outcome["name"] != team:
                    continue

                probabilities.append(
                    outcome["fair_probability"]
                )

                prices_found.append(
                    outcome["price"]
                )

                # Mejor cuota disponible
                if best_price is None:

                    best_price = outcome["price"]
                    best_book = bookmaker["name"]

                else:

                    current_decimal = (
                        american_to_decimal(
                            outcome["price"]
                        )
                    )

                    best_decimal = (
                        american_to_decimal(
                            best_price
                        )
                    )

                    if (
                        current_decimal
                        and best_decimal
                        and current_decimal > best_decimal
                    ):

                        best_price = outcome["price"]
                        best_book = bookmaker["name"]

        if not probabilities:
            continue

        # ====================================================
        # PROBABILIDAD DE CONSENSO
        # ====================================================

        consensus_probability = median(
            probabilities
        )

        # ====================================================
        # VALOR CON LA MEJOR CUOTA
        # ====================================================

        decimal = american_to_decimal(
            best_price
        )

        if decimal:

            expected_value = (
                consensus_probability * decimal
            ) - 1

        else:

            expected_value = -1

        # ====================================================
        # CONSISTENCIA ENTRE CASAS
        # ====================================================

        if len(probabilities) >= 2:

            average = (
                sum(probabilities)
                / len(probabilities)
            )

            variance = sum(
                (p - average) ** 2
                for p in probabilities
            ) / len(probabilities)

            consistency = max(
                0,
                1 - (variance * 100)
            )

        else:

            consistency = 0.50

        # ====================================================
        # SCORE INTERNO
        #
        # NO SE MUESTRA AL USUARIO.
        #
        # Probabilidad = factor principal
        # Valor = segundo factor
        # Consistencia = tercer factor
        # ====================================================

        probability_score = (
            consensus_probability * 100
        )

        value_score = (
            max(-0.10, min(0.10, expected_value))
            * 100
        )

        consistency_score = (
            consistency * 10
        )

        ranking_score = (
            probability_score * 0.70
            + value_score * 0.20
            + consistency_score * 0.10
        )

        results.append({

            "team": team,

            "probability":
                consensus_probability,

            "price":
                best_price,

            "bookmaker":
                best_book,

            "value":
                expected_value,

            "consistency":
                consistency,

            "ranking_score":
                ranking_score,

            "number_of_books":
                len(probabilities)
        })

    return results


# ============================================================
# CREAR OPORTUNIDADES
# ============================================================

def build_opportunities(events):

    opportunities = []

    for event in events:

        analyzed = analyze_event(event)

        local_dt = get_local_datetime(event)

        if not local_dt:
            continue

        for selection in analyzed:

            # ------------------------------------------------
            # FILTRO PRINCIPAL
            # ------------------------------------------------

            if (
                selection["probability"]
                < MIN_PROBABILITY
            ):
                continue

            opportunity = {

                "event": event,

                "team":
                    selection["team"],

                "probability":
                    selection["probability"],

                "price":
                    selection["price"],

                "bookmaker":
                    selection["bookmaker"],

                "value":
                    selection["value"],

                "consistency":
                    selection["consistency"],

                "ranking_score":
                    selection["ranking_score"],

                "number_of_books":
                    selection["number_of_books"],

                "datetime":
                    local_dt
            }

            opportunities.append(
                opportunity
            )

    # ========================================================
    # ORDEN FINAL
    # ========================================================

    opportunities.sort(
        key=lambda x: (
            x["ranking_score"],
            x["probability"],
            x["value"]
        ),
        reverse=True
    )

    return opportunities


# ============================================================
# ETIQUETAS
# ============================================================

def opportunity_label(probability, value):

    if (
        probability >= 0.75
        and value >= 0
    ):
        return "🟢 OPORTUNIDAD FUERTE"

    if (
        probability >= 0.65
    ):
        return "🟡 OPORTUNIDAD BUENA"

    return "🟠 OPORTUNIDAD MODERADA"


def display_probability(probability):

    return (
        f"{probability * 100:.1f}%"
    )


def display_value(value):

    return (
        f"{value * 100:+.1f}%"
    )


# ============================================================
# INTERFAZ
# ============================================================

st.title("🎯 Monitor 60%")

st.write(
    "Encuentra las mejores oportunidades "
    "deportivas del día."
)

st.divider()

st.header("Selecciona el deporte")

sport_selected = st.selectbox(
    "Deporte",
    list(SPORTS.keys())
)

sport_config = SPORTS[
    sport_selected
]

st.caption(
    "📅 Solo se analizarán partidos "
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
            "❌ No encontramos "
            "ODDS_API_KEY en Secrets."
        )

        st.stop()

    now = datetime.now(
        TZ_DALLAS
    )

    today_text = now.strftime(
        "%m/%d/%Y"
    )

    st.info(
        f"📅 HOY: {today_text} "
        f"— Dallas, Texas"
    )

    with st.spinner(
        "🔎 Buscando partidos y cuotas de HOY..."
    ):

        events, errors = scan_sport(
            sport_config
        )

    # ========================================================
    # ERRORES
    # ========================================================

    if errors:

        with st.expander(
            "Detalles técnicos"
        ):

            for error in errors:

                st.write(error)

    # ========================================================
    # NO HAY PARTIDOS
    # ========================================================

    if not events:

        st.warning(
            f"No encontramos partidos de "
            f"{sport_config['name']} para HOY."
        )

        st.caption(
            "No se muestran partidos de "
            "mañana ni de fechas futuras."
        )

        st.stop()

    # ========================================================
    # PARTIDOS DE HOY
    # ========================================================

    events.sort(
        key=lambda event:
            get_local_datetime(event)
    )

    st.header(
        f"📅 Partidos de HOY — "
        f"{sport_config['name']}"
    )

    st.success(
        f"✅ {len(events)} partido(s) "
        f"encontrado(s) para HOY."
    )

    for index, event in enumerate(
        events,
        1
    ):

        local_dt = get_local_datetime(
            event
        )

        home = event.get(
            "home_team",
            "Equipo local"
        )

        away = event.get(
            "away_team",
            "Equipo visitante"
        )

        st.subheader(
            f"{index}. "
            f"{away} vs {home}"
        )

        if local_dt:

            st.write(
                f"🕒 "
                f"{local_dt.strftime('%I:%M %p')}"
            )

        st.write(
            f"🏟️ "
            f"{event.get('sport_title', sport_config['name'])}"
        )

        st.divider()

    # ========================================================
    # OPORTUNIDADES
    # ========================================================

    opportunities = (
        build_opportunities(events)
    )

    st.header(
        f"🏆 Mejores oportunidades — "
        f"{sport_config['name']}"
    )

    # ========================================================
    # NO HAY APUESTAS
    # ========================================================

    if not opportunities:

        st.error(
            "🔴 NO HAY APUESTAS RECOMENDADAS"
        )

        st.write(
            "Ninguna selección de hoy alcanzó "
            f"el mínimo de "
            f"{MIN_PROBABILITY * 100:.0f}% "
            "de probabilidad estimada."
        )

        st.caption(
            "Es mejor no apostar que forzar "
            "una selección solamente para llenar "
            "el TOP 3."
        )

    else:

        # ====================================================
        # TOP 3
        # ====================================================

        top_picks = opportunities[
            :MAX_PICKS
        ]

        for index, pick in enumerate(
            top_picks,
            1
        ):

            event = pick["event"]

            home = event.get(
                "home_team",
                ""
            )

            away = event.get(
                "away_team",
                ""
            )

            local_dt = pick[
                "datetime"
            ]

            st.subheader(
                f"{index}. "
                f"{pick['team']}"
            )

            st.write(
                f"{sport_config['emoji']} "
                f"{away} vs {home}"
            )

            st.success(
                opportunity_label(
                    pick["probability"],
                    pick["value"]
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
                f"🏪 **Casas analizadas:** "
                f"{pick['number_of_books']}"
            )

            st.write(
                f"🕒 **Partido:** "
                f"HOY — "
                f"{local_dt.strftime('%I:%M %p')}"
            )

            st.divider()


# ============================================================
# PIE DE PÁGINA
# ============================================================

st.caption(
    "El Monitor 60% utiliza cuotas actuales del mercado "
    "para estimar probabilidades y ordenar oportunidades. "
    "La probabilidad estimada no garantiza el resultado."
)

st.caption(
    "📅 El filtro de fecha utiliza horario de Dallas "
    "y solo permite eventos cuya fecha local coincide "
    "exactamente con HOY."
)
