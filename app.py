import streamlit as st
import requests
import pandas as pd
import numpy as np
from datetime import datetime
from zoneinfo import ZoneInfo
import math

# ============================================================
# CONFIGURACIÓN
# ============================================================

st.set_page_config(
    page_title="Monitor NFL",
    page_icon="🏈",
    layout="wide"
)

ESPN_SCOREBOARD = (
    "https://site.api.espn.com/apis/site/v2/sports/"
    "football/nfl/scoreboard"
)

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
    margin-bottom: 20px;
}

.green-card {
    padding: 22px;
    border-radius: 18px;
    background-color: #193426;
    border: 1px solid #356b4c;
    margin-bottom: 20px;
}

.yellow-card {
    padding: 22px;
    border-radius: 18px;
    background-color: #40371d;
    border: 1px solid #6c5c2a;
    margin-bottom: 20px;
}

.blue-card {
    padding: 22px;
    border-radius: 18px;
    background-color: #192c43;
    border: 1px solid #294b70;
    margin-bottom: 20px;
}

.red-card {
    padding: 22px;
    border-radius: 18px;
    background-color: #402126;
    border: 1px solid #74353e;
    margin-bottom: 20px;
}

.big-number {
    font-size: 3rem;
    font-weight: 700;
}

.edge-positive {
    color: #4ade80;
    font-size: 1.5rem;
    font-weight: 800;
}

.edge-negative {
    color: #f87171;
    font-size: 1.5rem;
    font-weight: 800;
}

</style>
""", unsafe_allow_html=True)


# ============================================================
# UTILIDADES
# ============================================================

def american_to_decimal(odds):

    try:

        odds = float(odds)

        if odds > 0:
            return 1 + odds / 100

        return 1 + 100 / abs(odds)

    except:

        return np.nan


def american_to_probability(odds):

    try:

        odds = float(odds)

        if odds > 0:
            return 100 / (odds + 100)

        return abs(odds) / (abs(odds) + 100)

    except:

        return np.nan


def probability_to_american(prob):

    if prob <= 0 or prob >= 1:
        return None

    if prob >= 0.5:

        return round(
            -100 * prob / (1 - prob)
        )

    else:

        return round(
            100 * (1 - prob) / prob
        )


# ============================================================
# MODELO ELO
# ============================================================

INITIAL_ELO = 1500

HOME_ADVANTAGE = 55

ELO_SCALE = 400

K_FACTOR = 22


def elo_probability(
    home_elo,
    away_elo
):

    diferencia = (
        home_elo
        + HOME_ADVANTAGE
        - away_elo
    )

    return 1 / (
        1
        + 10 ** (-diferencia / ELO_SCALE)
    )


def update_elo(
    winner_elo,
    loser_elo,
    winner_score,
    loser_score
):

    expected = 1 / (
        1
        + 10 ** (
            (loser_elo - winner_elo)
            / ELO_SCALE
        )
    )

    margin = abs(
        winner_score - loser_score
    )

    margin_multiplier = (
        math.log(max(margin, 1) + 1)
    )

    change = (
        K_FACTOR
        * margin_multiplier
        * (1 - expected)
    )

    return (
        winner_elo + change,
        loser_elo - change
    )


# ============================================================
# OBTENER PARTIDOS HISTÓRICOS
# ============================================================

@st.cache_data(ttl=3600)
def obtener_historial_elo():

    equipos = {}

    temporadas = [
        2024,
        2025
    ]

    for temporada in temporadas:

        url = ESPN_SCOREBOARD

        params = {
            "dates": str(temporada),
            "limit": 1000
        }

        try:

            respuesta = requests.get(
                url,
                params=params,
                timeout=20,
                headers={
                    "User-Agent": "Mozilla/5.0"
                }
            )

            if respuesta.status_code != 200:
                continue

            data = respuesta.json()

        except:

            continue

        eventos = data.get(
            "events",
            []
        )

        for evento in eventos:

            try:

                competencia = evento[
                    "competitions"
                ][0]

                if not competencia.get(
                    "status",
                    {}
                ).get(
                    "type",
                    {}
                ).get(
                    "completed",
                    False
                ):
                    continue

                participantes = competencia[
                    "competitors"
                ]

                if len(participantes) != 2:
                    continue

                home = None
                away = None

                for equipo in participantes:

                    if equipo.get(
                        "homeAway"
                    ) == "home":

                        home = equipo

                    else:

                        away = equipo

                if home is None or away is None:
                    continue

                home_name = home[
                    "team"
                ][
                    "displayName"
                ]

                away_name = away[
                    "team"
                ][
                    "displayName"
                ]

                home_score = float(
                    home.get(
                        "score",
                        0
                    )
                )

                away_score = float(
                    away.get(
                        "score",
                        0
                    )
                )

                if home_name not in equipos:
                    equipos[home_name] = INITIAL_ELO

                if away_name not in equipos:
                    equipos[away_name] = INITIAL_ELO

                home_elo = equipos[home_name]
                away_elo = equipos[away_name]

                if home_score > away_score:

                    nuevo_home, nuevo_away = update_elo(
                        home_elo,
                        away_elo,
                        home_score,
                        away_score
                    )

                elif away_score > home_score:

                    nuevo_away, nuevo_home = update_elo(
                        away_elo,
                        home_elo,
                        away_score,
                        home_score
                    )

                else:

                    nuevo_home = home_elo
                    nuevo_away = away_elo

                equipos[home_name] = nuevo_home
                equipos[away_name] = nuevo_away

            except:

                continue

    return equipos


# ============================================================
# PARTIDOS DE HOY
# ============================================================

@st.cache_data(ttl=300)
def obtener_partidos():

    hoy = datetime.now(
        ZoneInfo("America/Chicago")
    ).strftime("%Y%m%d")

    try:

        respuesta = requests.get(
            ESPN_SCOREBOARD,
            params={
                "dates": hoy
            },
            timeout=20,
            headers={
                "User-Agent": "Mozilla/5.0"
            }
        )

        if respuesta.status_code != 200:

            return [], (
                f"HTTP {respuesta.status_code}"
            )

        data = respuesta.json()

        return (
            data.get(
                "events",
                []
            ),
            None
        )

    except Exception as e:

        return [], str(e)


# ============================================================
# EXTRAER CUOTAS
# ============================================================

def extraer_moneylines(evento):

    resultado = {}

    try:

        competencia = evento[
            "competitions"
        ][0]

        odds_list = competencia.get(
            "odds",
            []
        )

        if not odds_list:

            return resultado

        # Tomamos el primer proveedor disponible
        odds = odds_list[0]

        details = odds.get(
            "details"
        )

        if not details:
            return resultado

        # Ejemplo típico:
        # "GB -120"
        # "PIT +100"

        partes = details.split()

        for parte in partes:

            if parte.startswith("+") or parte.startswith("-"):

                try:

                    valor = float(
                        parte
                    )

                    # Se asigna después
                    resultado[
                        "raw"
                    ] = details

                except:

                    pass

    except:

        pass

    return resultado


# ============================================================
# EXTRAER EQUIPOS
# ============================================================

def obtener_equipos_evento(evento):

    competencia = evento[
        "competitions"
    ][0]

    participantes = competencia[
        "competitors"
    ]

    home = None
    away = None

    for equipo in participantes:

        if equipo.get(
            "homeAway"
        ) == "home":

            home = equipo

        else:

            away = equipo

    if home is None or away is None:

        return None

    return {
        "home": home,
        "away": away
    }


# ============================================================
# MODELO PARA PARTIDO
# ============================================================

def calcular_modelo(
    home_name,
    away_name,
    elos
):

    home_elo = elos.get(
        home_name,
        INITIAL_ELO
    )

    away_elo = elos.get(
        away_name,
        INITIAL_ELO
    )

    prob_home = elo_probability(
        home_elo,
        away_elo
    )

    prob_away = (
        1 - prob_home
    )

    return {
        "home_elo": home_elo,
        "away_elo": away_elo,
        "home_probability": prob_home,
        "away_probability": prob_away
    }


# ============================================================
# HEADER
# ============================================================

st.markdown(
    '<div class="title">🏈 Monitor NFL</div>',
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

tab1, tab2, tab3 = st.tabs([
    "🏈 NFL DE HOY",
    "🧪 VALIDACIÓN DEL MODELO",
    "📊 INFORMACIÓN"
])


# ============================================================
# TAB 1
# ============================================================

with tab1:

    st.header("🏈 NFL DE HOY")

    if st.button(
        "🔄 ACTUALIZAR PARTIDOS",
        use_container_width=True
    ):

        st.cache_data.clear()

        st.rerun()

    # --------------------------------------------------------
    # HISTORIAL ELO
    # --------------------------------------------------------

    with st.spinner(
        "Construyendo ratings NFL..."
    ):

        elos = obtener_historial_elo()

    # --------------------------------------------------------
    # PARTIDOS
    # --------------------------------------------------------

    eventos, error = obtener_partidos()

    if error:

        st.error(
            "No se pudo obtener el calendario NFL."
        )

        st.code(
            str(error)
        )

    if not eventos:

        st.warning(
            "No hay partidos NFL disponibles para esta fecha."
        )

    # --------------------------------------------------------
    # PROCESAR PARTIDOS
    # --------------------------------------------------------

    oportunidades = []

    for evento in eventos:

        try:

            equipos = obtener_equipos_evento(
                evento
            )

            if equipos is None:
                continue

            home = equipos["home"]
            away = equipos["away"]

            home_name = home[
                "team"
            ][
                "displayName"
            ]

            away_name = away[
                "team"
            ][
                "displayName"
            ]

            modelo = calcular_modelo(
                home_name,
                away_name,
                elos
            )

            prob_home = modelo[
                "home_probability"
            ]

            prob_away = modelo[
                "away_probability"
            ]

            cuota_home = probability_to_american(
                prob_home
            )

            cuota_away = probability_to_american(
                prob_away
            )

            # ------------------------------------------------
            # HORA
            # ------------------------------------------------

            fecha = evento.get(
                "date"
            )

            try:

                fecha_dt = datetime.fromisoformat(
                    fecha.replace(
                        "Z",
                        "+00:00"
                    )
                )

                fecha_dallas = fecha_dt.astimezone(
                    ZoneInfo(
                        "America/Chicago"
                    )
                )

                hora = fecha_dallas.strftime(
                    "%I:%M %p"
                )

            except:

                hora = "Hora no disponible"

            # ------------------------------------------------
            # CARD
            # ------------------------------------------------

            st.markdown(
                '<div class="card">',
                unsafe_allow_html=True
            )

            st.subheader(
                f"🏈 {away_name} @ {home_name}"
            )

            st.info(
                f"🕐 Hora Dallas: {hora}"
            )

            c1, c2 = st.columns(2)

            # =================================================
            # VISITANTE
            # =================================================

            with c1:

                st.markdown(
                    f"### ✈️ {away_name}"
                )

                st.caption(
                    f"Elo: {modelo['away_elo']:.0f}"
                )

                st.metric(
                    "Probabilidad modelo",
                    f"{prob_away:.1%}"
                )

                st.write(
                    f"🎯 **Cuota justa: "
                    f"{cuota_away:+d}**"
                )

            # =================================================
            # LOCAL
            # =================================================

            with c2:

                st.markdown(
                    f"### 🏠 {home_name}"
                )

                st.caption(
                    f"Elo: {modelo['home_elo']:.0f}"
                )

                st.metric(
                    "Probabilidad modelo",
                    f"{prob_home:.1%}"
                )

                st.write(
                    f"🎯 **Cuota justa: "
                    f"{cuota_home:+d}**"
                )

            # ------------------------------------------------
            # CUOTAS
            # ------------------------------------------------

            odds = extraer_moneylines(
                evento
            )

            if odds.get("raw"):

                st.markdown(
                    '<div class="blue-card">',
                    unsafe_allow_html=True
                )

                st.markdown(
                    "🏦 **Cuotas disponibles**"
                )

                st.write(
                    odds["raw"]
                )

                st.markdown(
                    '</div>',
                    unsafe_allow_html=True
                )

            else:

                st.info(
                    "🏦 La fuente no proporcionó "
                    "cuotas para este partido."
                )

            st.markdown(
                '</div>',
                unsafe_allow_html=True
            )

        except Exception as e:

            st.warning(
                f"No se pudo procesar un partido: {e}"
            )


# ============================================================
# TAB 2
# ============================================================

with tab2:

    st.header(
        "🧪 Validación del modelo"
    )

    st.markdown("""
    <div class="yellow-card">

    🎯 <b>¿Qué estamos comprobando?</b>

    <br><br>

    Nuestro modelo genera una probabilidad
    antes del partido.

    <br><br>

    Si dice 70%, queremos comprobar históricamente
    si aproximadamente 70 de cada 100 partidos
    terminan ganándose.

    <br><br>

    Esto permite comprobar si las probabilidades
    están correctamente calibradas.

    </div>
    """, unsafe_allow_html=True)

    st.subheader(
        "📊 Ratings actuales"
    )

    try:

        elos = obtener_historial_elo()

        tabla_elo = pd.DataFrame(
            [
                {
                    "Equipo": equipo,
                    "Elo": round(elo)
                }
                for equipo, elo
                in elos.items()
            ]
        ).sort_values(
            "Elo",
            ascending=False
        )

        st.dataframe(
            tabla_elo,
            use_container_width=True,
            hide_index=True
        )

    except:

        st.warning(
            "No se pudieron cargar los ratings."
        )


# ============================================================
# TAB 3
# ============================================================

with tab3:

    st.header(
        "📊 Información del modelo"
    )

    st.markdown("""
    <div class="green-card">

    <h3>🧠 Modelo actual</h3>

    El sistema utiliza un rating Elo para estimar
    la fuerza relativa de cada equipo.

    <br><br>

    También incorpora ventaja de local.

    <br><br>

    La probabilidad resultante se transforma
    en una cuota justa.

    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="blue-card">

    <h3>🏦 Comparación con la casa</h3>

    El siguiente objetivo es comparar:

    <br><br>

    • Probabilidad de nuestro modelo<br>
    • Probabilidad implícita de la casa<br>
    • Diferencia entre ambas<br>
    • EDGE<br>
    • Cuota justa<br>
    • Cuota disponible

    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="yellow-card">

    ⚠️ <b>Importante</b>

    <br><br>

    Una probabilidad alta no significa automáticamente
    que exista una apuesta rentable.

    <br><br>

    Lo que queremos encontrar es una diferencia
    entre nuestra probabilidad estimada y la probabilidad
    que representa la cuota disponible.

    </div>
    """, unsafe_allow_html=True)


# ============================================================
# FOOTER
# ============================================================

st.markdown("---")

st.caption(
    "Monitor NFL — herramienta experimental de análisis "
    "estadístico. Las probabilidades son estimaciones y "
    "no garantizan resultados futuros."
)
