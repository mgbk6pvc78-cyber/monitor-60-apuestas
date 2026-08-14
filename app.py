import streamlit as st
import requests
import pandas as pd
import numpy as np
import math

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


# ============================================================
# CONFIGURACIÓN
# ============================================================

st.set_page_config(
    page_title="Monitor NFL",
    page_icon="🏈",
    layout="wide"
)

NFLDATA_URL = "https://api.nfldata.org/v1/games"

TZ_DALLAS = ZoneInfo("America/Chicago")


# ============================================================
# ESTILO
# ============================================================

st.markdown("""
<style>

.main {
    background-color: #0e0f14;
}

.block-container {
    padding-top: 2rem;
    padding-bottom: 4rem;
}

.title {
    font-size: 3rem;
    font-weight: 800;
}

.subtitle {
    color: #9ca3af;
    font-size: 1.25rem;
}

.card {
    padding: 25px;
    border-radius: 18px;
    background-color: #171922;
    border: 1px solid #30333d;
    margin-bottom: 22px;
}

.green-card {
    padding: 22px;
    border-radius: 18px;
    background-color: #193426;
    border: 1px solid #356b4c;
    margin-bottom: 22px;
}

.yellow-card {
    padding: 22px;
    border-radius: 18px;
    background-color: #40371d;
    border: 1px solid #6c5c2a;
    margin-bottom: 22px;
}

.blue-card {
    padding: 22px;
    border-radius: 18px;
    background-color: #192c43;
    border: 1px solid #294b70;
    margin-bottom: 22px;
}

.red-card {
    padding: 22px;
    border-radius: 18px;
    background-color: #402126;
    border: 1px solid #74353e;
    margin-bottom: 22px;
}

.edge-good {
    padding: 18px;
    border-radius: 15px;
    background-color: #193426;
    border: 1px solid #356b4c;
    margin-top: 15px;
}

.edge-neutral {
    padding: 18px;
    border-radius: 15px;
    background-color: #40371d;
    border: 1px solid #6c5c2a;
    margin-top: 15px;
}

.big-number {
    font-size: 3rem;
    font-weight: 700;
}

</style>
""", unsafe_allow_html=True)


# ============================================================
# CONVERSIONES DE CUOTAS
# ============================================================

def american_to_probability(odds):

    try:

        odds = float(odds)

        if odds > 0:

            return 100 / (odds + 100)

        else:

            return abs(odds) / (
                abs(odds) + 100
            )

    except:

        return np.nan


def probability_to_american(probability):

    try:

        probability = float(probability)

    except:

        return None

    if probability <= 0 or probability >= 1:

        return None

    if probability >= 0.50:

        return round(
            -100 * probability
            / (1 - probability)
        )

    else:

        return round(
            100 * (1 - probability)
            / probability
        )


def format_american(odds):

    if odds is None:

        return "N/D"

    try:

        odds = float(odds)

        if odds > 0:

            return f"+{odds:.0f}"

        return f"{odds:.0f}"

    except:

        return "N/D"


# ============================================================
# FUNCIONES AUXILIARES
# ============================================================

def first_value(row, possible_columns):

    for column in possible_columns:

        if column in row:

            value = row[column]

            if value is not None:

                try:

                    if pd.isna(value):

                        continue

                except:

                    pass

                if str(value).strip() != "":

                    return value

    return None


def find_column(df, possible_columns):

    lower_columns = {
        str(c).lower(): c
        for c in df.columns
    }

    for column in possible_columns:

        if column.lower() in lower_columns:

            return lower_columns[
                column.lower()
            ]

    return None


# ============================================================
# FECHAS
# ============================================================

def parse_date(value):

    if value is None:

        return None

    try:

        timestamp = pd.to_datetime(
            value,
            utc=True,
            errors="coerce"
        )

        if pd.isna(timestamp):

            return None

        return timestamp.to_pydatetime().astimezone(
            TZ_DALLAS
        )

    except:

        return None


# ============================================================
# NFL DATA — OBTENER JUEGOS
# ============================================================

@st.cache_data(ttl=900)
def descargar_nfl_data(season):

    try:

        response = requests.get(
            NFLDATA_URL,
            params={
                "season": season
            },
            timeout=30,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 "
                    "(compatible; MonitorNFL/1.0)"
                ),
                "Accept": "application/json"
            }
        )

    except requests.exceptions.RequestException as e:

        return None, f"ERROR DE CONEXIÓN: {e}"

    if response.status_code != 200:

        return None, (
            f"HTTP {response.status_code}"
        )

    try:

        data = response.json()

    except:

        return None, (
            "La fuente respondió, "
            "pero no devolvió JSON válido."
        )

    # --------------------------------------------------------
    # DIFERENTES FORMATOS POSIBLES
    # --------------------------------------------------------

    if isinstance(data, list):

        juegos = data

    elif isinstance(data, dict):

        juegos = data.get(
            "data"
        )

        if juegos is None:

            juegos = data.get(
                "games"
            )

        if juegos is None:

            juegos = data.get(
                "results"
            )

        if juegos is None:

            juegos = []

    else:

        juegos = []

    if not isinstance(
        juegos,
        list
    ):

        juegos = []

    return juegos, None


# ============================================================
# OBTENER TODOS LOS PARTIDOS DE LA TEMPORADA
# ============================================================

def obtener_partidos_temporada():

    año = datetime.now(
        TZ_DALLAS
    ).year

    juegos, error = descargar_nfl_data(
        año
    )

    if error:

        return [], error

    partidos = []

    for juego in juegos:

        if not isinstance(
            juego,
            dict
        ):

            continue

        fecha_raw = first_value(
            juego,
            [
                "game_date",
                "gameday",
                "game_date_time",
                "date",
                "datetime",
                "gameDate",
                "start_time"
            ]
        )

        fecha = parse_date(
            fecha_raw
        )

        if fecha is None:

            continue

        home = first_value(
            juego,
            [
                "home_team",
                "homeTeam",
                "home",
                "home_team_abbr",
                "home_team_name"
            ]
        )

        away = first_value(
            juego,
            [
                "away_team",
                "awayTeam",
                "away",
                "away_team_abbr",
                "away_team_name"
            ]
        )

        # ----------------------------------------------------
        # SI HOME/AWAY VIENEN COMO OBJETOS
        # ----------------------------------------------------

        if isinstance(
            home,
            dict
        ):

            home = (
                home.get("name")
                or home.get("team")
                or home.get("abbr")
                or home.get("displayName")
            )

        if isinstance(
            away,
            dict
        ):

            away = (
                away.get("name")
                or away.get("team")
                or away.get("abbr")
                or away.get("displayName")
            )

        if not home or not away:

            continue

        juego_normalizado = {
            "raw": juego,
            "fecha": fecha,
            "home": str(home),
            "away": str(away)
        }

        partidos.append(
            juego_normalizado
        )

    partidos.sort(
        key=lambda x: x["fecha"]
    )

    return partidos, None


# ============================================================
# PARTIDOS DE HOY
# ============================================================

def partidos_de_hoy(
    partidos
):

    ahora = datetime.now(
        TZ_DALLAS
    )

    hoy = ahora.date()

    resultado = [
        p for p in partidos
        if p["fecha"].date() == hoy
    ]

    return resultado


# ============================================================
# PRÓXIMOS PARTIDOS
# ============================================================

def proximos_partidos(
    partidos,
    dias=7
):

    ahora = datetime.now(
        TZ_DALLAS
    )

    fecha_limite = (
        ahora
        + timedelta(days=dias)
    )

    resultado = [
        p for p in partidos
        if (
            p["fecha"] >= ahora
            and
            p["fecha"] <= fecha_limite
        )
    ]

    return resultado


# ============================================================
# EXTRAER CUOTAS DEL JUEGO
# ============================================================

def extraer_odds(
    juego
):

    raw = juego.get(
        "raw",
        {}
    )

    if not isinstance(
        raw,
        dict
    ):

        return {
            "home_ml": None,
            "away_ml": None,
            "spread": None,
            "total": None
        }

    # --------------------------------------------------------
    # MONEYLINES
    # --------------------------------------------------------

    home_ml = first_value(
        raw,
        [
            "home_moneyline",
            "home_ml",
            "homeMoneyline",
            "moneyline_home",
            "home_odds"
        ]
    )

    away_ml = first_value(
        raw,
        [
            "away_moneyline",
            "away_ml",
            "awayMoneyline",
            "moneyline_away",
            "away_odds"
        ]
    )

    spread = first_value(
        raw,
        [
            "spread",
            "home_spread",
            "line"
        ]
    )

    total = first_value(
        raw,
        [
            "total",
            "over_under",
            "overUnder"
        ]
    )

    # --------------------------------------------------------
    # ODDS COMO OBJETO
    # --------------------------------------------------------

    odds_object = raw.get(
        "odds"
    )

    if isinstance(
        odds_object,
        dict
    ):

        if home_ml is None:

            home_ml = (
                odds_object.get(
                    "home_moneyline"
                )
                or odds_object.get(
                    "home_ml"
                )
                or odds_object.get(
                    "homeMoneyline"
                )
            )

        if away_ml is None:

            away_ml = (
                odds_object.get(
                    "away_moneyline"
                )
                or odds_object.get(
                    "away_ml"
                )
                or odds_object.get(
                    "awayMoneyline"
                )
            )

        if spread is None:

            spread = odds_object.get(
                "spread"
            )

        if total is None:

            total = odds_object.get(
                "total"
            )

    return {
        "home_ml": home_ml,
        "away_ml": away_ml,
        "spread": spread,
        "total": total
    }


# ============================================================
# ELO
# ============================================================

INITIAL_ELO = 1500

HOME_ADVANTAGE = 55

ELO_SCALE = 400

K_FACTOR = 22


def elo_probability(
    home_elo,
    away_elo
):

    difference = (
        home_elo
        + HOME_ADVANTAGE
        - away_elo
    )

    return 1 / (
        1
        + 10 ** (
            -difference
            / ELO_SCALE
        )
    )


def elo_update(
    winner_elo,
    loser_elo,
    margin
):

    expected = (
        1
        / (
            1
            + 10 ** (
                (
                    loser_elo
                    - winner_elo
                )
                / ELO_SCALE
            )
        )
    )

    margin = max(
        abs(float(margin)),
        1
    )

    multiplier = math.log(
        margin + 1
    )

    change = (
        K_FACTOR
        * multiplier
        * (1 - expected)
    )

    return (
        winner_elo + change,
        loser_elo - change
    )


# ============================================================
# CONSTRUIR ELO HISTÓRICO
# ============================================================

def construir_elo(
    partidos
):

    ratings = {}

    # --------------------------------------------------------
    # ORDEN CRONOLÓGICO
    # --------------------------------------------------------

    partidos_terminados = []

    for partido in partidos:

        raw = partido["raw"]

        home_score = first_value(
            raw,
            [
                "home_score",
                "homeScore",
                "score_home"
            ]
        )

        away_score = first_value(
            raw,
            [
                "away_score",
                "awayScore",
                "score_away"
            ]
        )

        if (
            home_score is None
            or away_score is None
        ):

            continue

        try:

            home_score = float(
                home_score
            )

            away_score = float(
                away_score
            )

        except:

            continue

        # Partido terminado

        if (
            home_score == 0
            and away_score == 0
        ):

            # No descartamos automáticamente,
            # podría ser un 0-0 real.
            pass

        partidos_terminados.append(
            (
                partido,
                home_score,
                away_score
            )
        )

    partidos_terminados.sort(
        key=lambda x: x[0]["fecha"]
    )

    # --------------------------------------------------------
    # ELO
    # --------------------------------------------------------

    for (
        partido,
        home_score,
        away_score
    ) in partidos_terminados:

        home = partido["home"]
        away = partido["away"]

        if home not in ratings:

            ratings[home] = INITIAL_ELO

        if away not in ratings:

            ratings[away] = INITIAL_ELO

        home_elo = ratings[home]
        away_elo = ratings[away]

        if home_score > away_score:

            nuevo_home, nuevo_away = (
                elo_update(
                    home_elo,
                    away_elo,
                    home_score
                    - away_score
                )
            )

        elif away_score > home_score:

            nuevo_away, nuevo_home = (
                elo_update(
                    away_elo,
                    home_elo,
                    away_score
                    - home_score
                )
            )

        else:

            nuevo_home = home_elo
            nuevo_away = away_elo

        ratings[home] = nuevo_home
        ratings[away] = nuevo_away

    return ratings


# ============================================================
# PROBABILIDAD DEL MODELO
# ============================================================

def modelo_partido(
    home,
    away,
    ratings
):

    home_elo = ratings.get(
        home,
        INITIAL_ELO
    )

    away_elo = ratings.get(
        away,
        INITIAL_ELO
    )

    home_probability = (
        elo_probability(
            home_elo,
            away_elo
        )
    )

    away_probability = (
        1 - home_probability
    )

    return {
        "home_elo": home_elo,
        "away_elo": away_elo,
        "home_probability": home_probability,
        "away_probability": away_probability
    }


# ============================================================
# COMPARACIÓN MODELO VS CASA
# ============================================================

def comparar(
    model_probability,
    american_odds
):

    if american_odds is None:

        return None

    try:

        odds = float(
            american_odds
        )

    except:

        return None

    market_probability = (
        american_to_probability(
            odds
        )
    )

    if pd.isna(
        market_probability
    ):

        return None

    edge = (
        model_probability
        - market_probability
    )

    fair_odds = (
        probability_to_american(
            model_probability
        )
    )

    return {
        "market_probability":
            market_probability,

        "edge":
            edge,

        "fair_odds":
            fair_odds
    }


# ============================================================
# HEADER
# ============================================================

st.markdown(
    '<div class="title">'
    '🏈 Monitor NFL'
    '</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtitle">'
    'Modelo propio — análisis NFL automático'
    '</div>',
    unsafe_allow_html=True
)


# ============================================================
# TABS
# ============================================================

tab1, tab2, tab3 = st.tabs(
    [
        "🏈 NFL DE HOY",
        "🧪 VALIDACIÓN DEL MODELO",
        "📊 INFORMACIÓN"
    ]
)


# ============================================================
# TAB 1
# ============================================================

with tab1:

    st.header(
        "🏈 NFL DE HOY"
    )

    if st.button(
        "🔄 ACTUALIZAR PARTIDOS",
        use_container_width=True
    ):

        st.cache_data.clear()

        st.rerun()

    # --------------------------------------------------------
    # DESCARGAR TEMPORADA
    # --------------------------------------------------------

    with st.spinner(
        "Consultando calendario NFL..."
    ):

        partidos,
        error = (
            obtener_partidos_temporada()
        )

    if error:

        st.error(
            "No se pudo obtener "
            "el calendario NFL."
        )

        st.code(
            str(error)
        )

        st.info(
            "La fuente utilizada es NFLData. "
            "No necesita API key."
        )

    elif not partidos:

        st.warning(
            "La fuente no devolvió partidos."
        )

        st.info(
            "Esto puede ocurrir si la API "
            "está temporalmente fuera de servicio."
        )

    else:

        # ----------------------------------------------------
        # ELO
        # ----------------------------------------------------

        ratings = construir_elo(
            partidos
        )

        # ----------------------------------------------------
        # HOY
        # ----------------------------------------------------

        hoy = partidos_de_hoy(
            partidos
        )

        # ----------------------------------------------------
        # PRÓXIMOS
        # ----------------------------------------------------

        proximos = proximos_partidos(
            partidos,
            dias=7
        )

        if hoy:

            lista_mostrar = hoy

            st.success(
                f"🏈 {len(hoy)} partido(s) "
                "para hoy."
            )

        elif proximos:

            lista_mostrar = proximos

            st.warning(
                "No hay partidos hoy. "
                "Mostrando los próximos partidos."
            )

        else:

            lista_mostrar = []

            st.warning(
                "No hay partidos para "
                "hoy ni próximos 7 días."
            )

        # ----------------------------------------------------
        # PARTIDOS
        # ----------------------------------------------------

        for partido in lista_mostrar:

            home = partido["home"]

            away = partido["away"]

            fecha = partido["fecha"]

            modelo = modelo_partido(
                home,
                away,
                ratings
            )

            home_prob = (
                modelo[
                    "home_probability"
                ]
            )

            away_prob = (
                modelo[
                    "away_probability"
                ]
            )

            home_fair = (
                probability_to_american(
                    home_prob
                )
            )

            away_fair = (
                probability_to_american(
                    away_prob
                )
            )

            odds = extraer_odds(
                partido
            )

            home_comparison = (
                comparar(
                    home_prob,
                    odds["home_ml"]
                )
            )

            away_comparison = (
                comparar(
                    away_prob,
                    odds["away_ml"]
                )
            )

            # =================================================
            # PARTIDO
            # =================================================

            st.markdown(
                '<div class="card">',
                unsafe_allow_html=True
            )

            st.subheader(
                f"🏈 {away} @ {home}"
            )

            st.info(
                f"📅 {fecha.strftime('%m/%d/%Y')}"
                f"   •   🕐 Hora Dallas: "
                f"{fecha.strftime('%I:%M %p')}"
            )

            # =================================================
            # EQUIPOS
            # =================================================

            col1, col2 = st.columns(2)

            # -------------------------------------------------
            # VISITANTE
            # -------------------------------------------------

            with col1:

                st.markdown(
                    f"### ✈️ {away}"
                )

                st.caption(
                    f"Elo: "
                    f"{modelo['away_elo']:.0f}"
                )

                st.metric(
                    "Probabilidad modelo",
                    f"{away_prob:.1%}"
                )

                st.write(
                    f"🎯 **Cuota justa: "
                    f"{format_american(away_fair)}**"
                )

            # -------------------------------------------------
            # LOCAL
            # -------------------------------------------------

            with col2:

                st.markdown(
                    f"### 🏠 {home}"
                )

                st.caption(
                    f"Elo: "
                    f"{modelo['home_elo']:.0f}"
                )

                st.metric(
                    "Probabilidad modelo",
                    f"{home_prob:.1%}"
                )

                st.write(
                    f"🎯 **Cuota justa: "
                    f"{format_american(home_fair)}**"
                )

            st.divider()

            # =================================================
            # CASA
            # =================================================

            st.markdown(
                "### 🏦 Comparación con la casa"
            )

            if (
                home_comparison is None
                and away_comparison is None
            ):

                st.info(
                    "La fuente de datos no "
                    "proporcionó moneylines "
                    "para este partido."
                )

            else:

                c1, c2 = st.columns(2)

                # ------------------------------------------------
                # CASA LOCAL
                # ------------------------------------------------

                with c1:

                    st.markdown(
                        f"**🏠 {home}**"
                    )

                    if home_comparison:

                        st.write(
                            "Cuota casa: "
                            f"**{format_american(odds['home_ml'])}**"
                        )

                        st.write(
                            "Prob. implícita: "
                            f"**{home_comparison['market_probability']:.1%}**"
                        )

                        edge = (
                            home_comparison[
                                "edge"
                            ]
                        )

                        if edge > 0.03:

                            st.markdown(
                                '<div class="edge-good">'
                                f"🔥 EDGE: "
                                f"<b>+{edge:.1%}</b>"
                                "<br><br>"
                                "El modelo ve más "
                                "probabilidad que la casa."
                                "</div>",
                                unsafe_allow_html=True
                            )

                        elif edge < -0.03:

                            st.markdown(
                                '<div class="red-card">'
                                f"EDGE: "
                                f"<b>{edge:.1%}</b>"
                                "<br><br>"
                                "La casa asigna más "
                                "probabilidad que nuestro modelo."
                                "</div>",
                                unsafe_allow_html=True
                            )

                        else:

                            st.markdown(
                                '<div class="edge-neutral">'
                                f"EDGE: "
                                f"<b>{edge:+.1%}</b>"
                                "<br><br>"
                                "Sin ventaja clara."
                                "</div>",
                                unsafe_allow_html=True
                            )

                    else:

                        st.info(
                            "No hay cuota disponible."
                        )

                # ------------------------------------------------
                # CASA VISITANTE
                # ------------------------------------------------

                with c2:

                    st.markdown(
                        f"**✈️ {away}**"
                    )

                    if away_comparison:

                        st.write(
                            "Cuota casa: "
                            f"**{format_american(odds['away_ml'])}**"
                        )

                        st.write(
                            "Prob. implícita: "
                            f"**{away_comparison['market_probability']:.1%}**"
                        )

                        edge = (
                            away_comparison[
                                "edge"
                            ]
                        )

                        if edge > 0.03:

                            st.markdown(
                                '<div class="edge-good">'
                                f"🔥 EDGE: "
                                f"<b>+{edge:.1%}</b>"
                                "<br><br>"
                                "El modelo ve más "
                                "probabilidad que la casa."
                                "</div>",
                                unsafe_allow_html=True
                            )

                        elif edge < -0.03:

                            st.markdown(
                                '<div class="red-card">'
                                f"EDGE: "
                                f"<b>{edge:.1%}</b>"
                                "<br><br>"
                                "La casa asigna más "
                                "probabilidad que nuestro modelo."
                                "</div>",
                                unsafe_allow_html=True
                            )

                        else:

                            st.markdown(
                                '<div class="edge-neutral">'
                                f"EDGE: "
                                f"<b>{edge:+.1%}</b>"
                                "<br><br>"
                                "Sin ventaja clara."
                                "</div>",
                                unsafe_allow_html=True
                            )

                    else:

                        st.info(
                            "No hay cuota disponible."
                        )

            # =================================================
            # OTROS DATOS
            # =================================================

            spread = odds.get(
                "spread"
            )

            total = odds.get(
                "total"
            )

            if (
                spread is not None
                or total is not None
            ):

                st.markdown(
                    "### 📋 Mercado"
                )

                mc1, mc2 = st.columns(2)

                with mc1:

                    st.write(
                        f"Spread: "
                        f"**{spread if spread is not None else 'N/D'}**"
                    )

                with mc2:

                    st.write(
                        f"Total: "
                        f"**{total if total is not None else 'N/D'}**"
                    )

            st.markdown(
                '</div>',
                unsafe_allow_html=True
            )


# ============================================================
# TAB 2 — VALIDACIÓN
# ============================================================

with tab2:

    st.header(
        "🧪 Validación del modelo"
    )

    st.markdown("""
    <div class="yellow-card">

    🎯 <b>Lo que queremos comprobar</b>

    <br><br>

    No queremos simplemente que el modelo
    tenga muchos aciertos.

    <br><br>

    Queremos saber si una probabilidad de
    60%, 70%, 80%, etc. realmente representa
    aproximadamente esa frecuencia de victorias.

    <br><br>

    Por ejemplo:

    <br><br>

    Si el modelo dice <b>70%</b> para un grupo
    de partidos, queremos comprobar que
    aproximadamente 70 de cada 100 realmente
    terminan ganándose.

    </div>
    """, unsafe_allow_html=True)

    # --------------------------------------------------------
    # DATOS
    # --------------------------------------------------------

    with st.spinner(
        "Cargando histórico NFL..."
    ):

        partidos,
        error = (
            obtener_partidos_temporada()
        )

    if error:

        st.error(
            str(error)
        )

    elif partidos:

        ratings = construir_elo(
            partidos
        )

        st.success(
            f"Se cargaron "
            f"{len(partidos)} registros "
            "de la fuente."
        )

        # ----------------------------------------------------
        # RATINGS
        # ----------------------------------------------------

        st.subheader(
            "📊 Ratings Elo actuales"
        )

        tabla = pd.DataFrame(
            [
                {
                    "Equipo": equipo,
                    "Elo": round(rating)
                }
                for equipo, rating
                in ratings.items()
            ]
        )

        if not tabla.empty:

            tabla = tabla.sort_values(
                "Elo",
                ascending=False
            )

            st.dataframe(
                tabla,
                use_container_width=True,
                hide_index=True
            )

    else:

        st.warning(
            "No hay datos históricos disponibles."
        )


# ============================================================
# TAB 3
# ============================================================

with tab3:

    st.header(
        "📊 Información"
    )

    st.markdown("""
    <div class="blue-card">

    <h3>🧠 ¿Cómo funciona?</h3>

    <br>

    El sistema construye un rating Elo para
    cada equipo utilizando resultados históricos.

    <br><br>

    Después incorpora una ventaja de local
    y transforma la diferencia de fuerza en
    una probabilidad.

    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="green-card">

    <h3>🎯 Lo que realmente buscamos</h3>

    <br>

    No buscamos simplemente encontrar al
    equipo que creemos que va a ganar.

    <br><br>

    Buscamos encontrar situaciones donde:

    <br><br>

    <b>Nuestra probabilidad</b>

    sea mayor que

    <br>

    <b>La probabilidad implícita de la cuota.</b>

    <br><br>

    Esa diferencia es nuestro <b>EDGE</b>.

    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="yellow-card">

    <h3>🏦 Próximo nivel</h3>

    <br>

    La siguiente evolución del sistema será
    incorporar múltiples factores:

    <br><br>

    • Elo<br>
    • Forma reciente<br>
    • Ataque<br>
    • Defensa<br>
    • Localía<br>
    • Descanso<br>
    • Lesiones<br>
    • Quarterback<br>
    • Eficiencia<br>
    • Mercado de apuestas

    <br><br>

    Después podremos comparar el modelo
    contra las cuotas reales.

    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="red-card">

    ⚠️ <b>Importante</b>

    <br><br>

    Una probabilidad del modelo no garantiza
    que una apuesta vaya a ganar.

    <br><br>

    El objetivo es medir estadísticamente
    si el modelo tiene una ventaja consistente
    sobre la probabilidad implícita del mercado.

    </div>
    """, unsafe_allow_html=True)


# ============================================================
# FOOTER
# ============================================================

st.markdown("---")

st.caption(
    "Monitor NFL — herramienta experimental "
    "de análisis estadístico. Las probabilidades "
    "son estimaciones y no garantizan resultados futuros."
)
