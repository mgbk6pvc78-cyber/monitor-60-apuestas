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

TZ_DALLAS = ZoneInfo("America/Chicago")

MAX_PICKS = 3
MIN_PROBABILITY = 0.60


# ============================================================
# DEPORTES
# ============================================================

SPORTS = {
    "🏈 NFL": {
        "keys": [
            "americanfootball_nfl_preseason",
            "americanfootball_nfl"
        ],
        "name": "NFL",
        "emoji": "🏈"
    },

    "⚾ MLB": {
        "keys": [
            "baseball_mlb"
        ],
        "name": "MLB",
        "emoji": "⚾"
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
        "name": "Soccer",
        "emoji": "⚽"
    },

    "🎾 Tenis": {
        "keys": [
            "tennis_atp",
            "tennis_wta"
        ],
        "name": "Tenis",
        "emoji": "🎾"
    },

    "🏀 NBA": {
        "keys": [
            "basketball_nba"
        ],
        "name": "NBA",
        "emoji": "🏀"
    }
}


# ============================================================
# CUOTAS
# ============================================================

def american_to_decimal(odds):

    try:
        odds = float(odds)

        if odds > 0:
            return 1 + odds / 100

        return 1 + 100 / abs(odds)

    except:
        return None


def implied_probability(odds):

    decimal = american_to_decimal(odds)

    if not decimal or decimal <= 1:
        return None

    return 1 / decimal


def format_odds(odds):

    try:
        odds = int(round(float(odds)))

        if odds > 0:
            return f"+{odds}"

        return str(odds)

    except:
        return "N/A"


# ============================================================
# FECHAS
# ============================================================

def local_datetime(event):

    try:

        dt = datetime.fromisoformat(
            event["commence_time"].replace(
                "Z",
                "+00:00"
            )
        )

        return dt.astimezone(TZ_DALLAS)

    except:

        return None


def is_today(event):

    dt = local_datetime(event)

    if not dt:
        return False

    today = datetime.now(
        TZ_DALLAS
    ).date()

    return dt.date() == today


# ============================================================
# OBTENER PARTIDOS
# ============================================================

def get_events(sport_key):

    url = (
        f"{BASE_URL}/"
        f"{sport_key}/odds"
    )

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

            return [], (
                f"{response.status_code}: "
                f"{response.text}"
            )

        data = response.json()

        today_events = []

        for event in data:

            if is_today(event):
                today_events.append(event)

        return today_events, None

    except Exception as e:

        return [], str(e)


def scan_sport(config):

    events = []
    errors = []

    for key in config["keys"]:

        data, error = get_events(key)

        if error:

            errors.append(
                f"{key}: {error}"
            )

        events.extend(data)

    # Eliminar duplicados
    unique = {}

    for event in events:

        event_id = event.get("id")

        if event_id:
            unique[event_id] = event

    return list(unique.values()), errors


# ============================================================
# ANALIZAR UN PARTIDO
# ============================================================

def analyze_event(event):

    bookmakers = []

    for bookmaker in event.get(
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

            converted = []

            raw_total = 0

            for outcome in outcomes:

                price = outcome.get(
                    "price"
                )

                probability = implied_probability(
                    price
                )

                if probability is None:
                    continue

                raw_total += probability

                converted.append({
                    "name": outcome.get(
                        "name"
                    ),
                    "price": price,
                    "probability": probability
                })

            if len(converted) < 2:
                continue

            # Quitar aproximadamente el margen
            for outcome in converted:

                outcome["fair_probability"] = (
                    outcome["probability"]
                    / raw_total
                )

            bookmakers.append({
                "name": bookmaker.get(
                    "title",
                    "Casa"
                ),
                "outcomes": converted
            })

    if not bookmakers:
        return []

    # ========================================================
    # CONSENSO
    # ========================================================

    teams = set()

    for bookmaker in bookmakers:

        for outcome in bookmaker["outcomes"]:

            teams.add(
                outcome["name"]
            )

    results = []

    for team in teams:

        probabilities = []

        best_price = None
        best_book = None

        for bookmaker in bookmakers:

            for outcome in bookmaker["outcomes"]:

                if outcome["name"] != team:
                    continue

                probabilities.append(
                    outcome[
                        "fair_probability"
                    ]
                )

                price = outcome["price"]

                if best_price is None:

                    best_price = price
                    best_book = bookmaker["name"]

                else:

                    current_decimal = (
                        american_to_decimal(
                            price
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

                        best_price = price
                        best_book = bookmaker["name"]

        if not probabilities:
            continue

        # Mediana = menos sensible a una casa
        # con una línea extraña
        probability = median(
            probabilities
        )

        decimal = american_to_decimal(
            best_price
        )

        if decimal:

            value = (
                probability * decimal
            ) - 1

        else:

            value = 0

        # ====================================================
        # CONSISTENCIA
        # ====================================================

        if len(probabilities) >= 2:

            avg = (
                sum(probabilities)
                / len(probabilities)
            )

            spread = max(
                probabilities
            ) - min(
                probabilities
            )

            consistency = max(
                0,
                1 - spread
            )

        else:

            consistency = 0.50

        # ====================================================
        # SCORE
        #
        # Probabilidad = principal
        # Valor = importante pero NO elimina
        # Consistencia = pequeña ventaja
        # ====================================================

        probability_score = (
            probability * 100
        )

        value_score = max(
            -5,
            min(
                10,
                value * 100
            )
        )

        consistency_score = (
            consistency * 5
        )

        score = (
            probability_score * 0.75
            + value_score * 0.15
            + consistency_score * 0.10
        )

        results.append({

            "team": team,

            "probability": probability,

            "price": best_price,

            "bookmaker": best_book,

            "value": value,

            "consistency": consistency,

            "score": score,

            "books": len(probabilities)
        })

    return results


# ============================================================
# CREAR TOP
# ============================================================

def build_opportunities(events):

    opportunities = []

    for event in events:

        analyzed = analyze_event(
            event
        )

        dt = local_datetime(
            event
        )

        if not dt:
            continue

        for selection in analyzed:

            # ------------------------------------------------
            # SOLO FILTRO REAL:
            # mínimo 60%
            # ------------------------------------------------

            if (
                selection["probability"]
                < MIN_PROBABILITY
            ):
                continue

            opportunities.append({

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

                "score":
                    selection["score"],

                "books":
                    selection["books"],

                "datetime":
                    dt
            })

    # ========================================================
    # ORDEN
    # ========================================================

    opportunities.sort(
        key=lambda x: (
            x["score"],
            x["probability"],
            x["value"]
        ),
        reverse=True
    )

    return opportunities


# ============================================================
# ETIQUETA
# ============================================================

def label(probability, value):

    if (
        probability >= 0.70
        and value >= 0
    ):

        return "🟢 MUY BUENA"

    if probability >= 0.65:

        if value >= 0:
            return "🟢 BUENA CON VALOR"

        return "🟡 PROBABILIDAD ALTA"

    if value >= 0:

        return "🟡 VALOR INTERESANTE"

    return "🟠 PROBABILIDAD MODERADA"


# ============================================================
# INTERFAZ
# ============================================================

st.title("🎯 Monitor 60%")

st.write(
    "Scanner sencillo de las mejores "
    "oportunidades deportivas de HOY."
)

st.divider()

sport_selected = st.selectbox(
    "🏆 Selecciona el deporte",
    list(SPORTS.keys())
)

config = SPORTS[
    sport_selected
]

st.caption(
    "📅 Solo analizamos partidos que "
    "se juegan HOY en horario de Dallas."
)

st.divider()

scan = st.button(
    "🔎 ESCANEAR HOY",
    use_container_width=True
)


# ============================================================
# ESCANEAR
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

    st.info(
        f"📅 HOY: "
        f"{now.strftime('%m/%d/%Y')} "
        f"— Dallas"
    )

    with st.spinner(
        "🔎 Buscando partidos de HOY..."
    ):

        events, errors = scan_sport(
            config
        )

    # ========================================================
    # ERRORES
    # ========================================================

    if errors:

        with st.expander(
            "Detalles de conexión"
        ):

            for error in errors:
                st.write(error)

    # ========================================================
    # PARTIDOS
    # ========================================================

    if not events:

        st.warning(
            f"No encontramos partidos de "
            f"{config['name']} para HOY."
        )

        st.stop()

    events.sort(
        key=lambda e:
        local_datetime(e)
    )

    st.header(
        f"📅 PARTIDOS DE HOY — "
        f"{config['name']}"
    )

    st.success(
        f"Encontramos "
        f"{len(events)} partido(s) hoy."
    )

    for index, event in enumerate(
        events,
        1
    ):

        home = event.get(
            "home_team",
            "Local"
        )

        away = event.get(
            "away_team",
            "Visitante"
        )

        dt = local_datetime(
            event
        )

        st.write(
            f"**{index}. "
            f"{away} vs {home}**"
        )

        if dt:

            st.caption(
                f"🕒 HOY — "
                f"{dt.strftime('%I:%M %p')}"
            )

    # ========================================================
    # OPORTUNIDADES
    # ========================================================

    opportunities = (
        build_opportunities(
            events
        )
    )

    st.divider()

    st.header(
        f"🏆 TOP {MAX_PICKS} — "
        f"APUESTAS DE HOY"
    )

    if not opportunities:

        st.warning(
            "No encontramos ninguna selección "
            "con al menos 60% de probabilidad."
        )

        st.caption(
            "El sistema no inventa apuestas."
        )

    else:

        top = opportunities[
            :MAX_PICKS
        ]

        st.success(
            f"Encontramos "
            f"{len(top)} oportunidad(es)."
        )

        for index, pick in enumerate(
            top,
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

            st.subheader(
                f"#{index} "
                f"{pick['team']}"
            )

            st.write(
                f"{config['emoji']} "
                f"{away} vs {home}"
            )

            # -----------------------------------------------
            # CLASIFICACIÓN
            # -----------------------------------------------

            st.success(
                label(
                    pick["probability"],
                    pick["value"]
                )
            )

            # -----------------------------------------------
            # DATOS PRINCIPALES
            # -----------------------------------------------

            col1, col2 = st.columns(2)

            with col1:

                st.metric(
                    "Probabilidad",
                    f"{pick['probability'] * 100:.1f}%"
                )

            with col2:

                st.metric(
                    "Valor",
                    f"{pick['value'] * 100:+.1f}%"
                )

            st.write(
                f"💰 **Cuota:** "
                f"{format_odds(pick['price'])}"
            )

            st.write(
                f"🏦 **Mejor cuota:** "
                f"{pick['bookmaker']}"
            )

            st.write(
                f"🏪 **Casas analizadas:** "
                f"{pick['books']}"
            )

            st.write(
                f"🕒 **Partido:** "
                f"HOY — "
                f"{pick['datetime'].strftime('%I:%M %p')}"
            )

            st.divider()


# ============================================================
# PIE
# ============================================================

st.caption(
    "🎯 El objetivo es encontrar las mejores "
    "oportunidades disponibles de HOY."
)

st.caption(
    "El valor positivo es una señal adicional; "
    "NO elimina automáticamente una apuesta."
)

st.caption(
    "⚠️ Una probabilidad estimada no garantiza "
    "el resultado de una apuesta."
)
