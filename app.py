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

API_URL = "https://api.nfldata.org/v1/games"

DALLAS_TZ = ZoneInfo("America/Chicago")


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

h1, h2, h3 {
    color: #f5f5f5;
}

.card {
    padding: 25px;
    border-radius: 18px;
    background-color: #171922;
    border: 1px solid #30333d;
    margin-bottom: 25px;
}

.green-card {
    padding: 25px;
    border-radius: 18px;
    background-color: #193426;
    border: 1px solid #356b4c;
    margin-bottom: 25px;
}

.yellow-card {
    padding: 25px;
    border-radius: 18px;
    background-color: #40371d;
    border: 1px solid #6c5c2a;
    margin-bottom: 25px;
}

.blue-card {
    padding: 25px;
    border-radius: 18px;
    background-color: #192c43;
    border: 1px solid #294b70;
    margin-bottom: 25px;
}

.red-card {
    padding: 25px;
    border-radius: 18px;
    background-color: #402126;
    border: 1px solid #74353e;
    margin-bottom: 25px;
}

.big-number {
    font-size: 3rem;
    font-weight: 700;
}

.edge-good {
    padding: 18px;
    border-radius: 15px;
    background-color: #193426;
    border: 1px solid #356b4c;
    margin-top: 15px;
}

.edge-bad {
    padding: 18px;
    border-radius: 15px;
    background-color: #402126;
    border: 1px solid #74353e;
    margin-top: 15px;
}

.edge-neutral {
    padding: 18px;
    border-radius: 15px;
    background-color: #40371d;
    border: 1px solid #6c5c2a;
    margin-top: 15px;
}

</style>
""", unsafe_allow_html=True)


# ============================================================
# FUNCIONES GENERALES
# ============================================================

def obtener_valor(diccionario, nombres):

    if not isinstance(diccionario, dict):
        return None

    for nombre in nombres:

        if nombre in diccionario:

            valor = diccionario[nombre]

            if valor is None:
                continue

            try:
                if pd.isna(valor):
                    continue
            except Exception:
                pass

            if str(valor).strip() != "":
                return valor

    return None


def convertir_fecha(valor):

    if valor is None:
        return None

    try:

        fecha = pd.to_datetime(
            valor,
            utc=True,
            errors="coerce"
        )

        if pd.isna(fecha):
            return None

        return fecha.to_pydatetime().astimezone(
            DALLAS_TZ
        )

    except Exception:
        return None


# ============================================================
# CUOTAS
# ============================================================

def american_to_probability(odds):

    try:

        odds = float(odds)

        if odds > 0:

            return 100 / (odds + 100)

        return abs(odds) / (
            abs(odds) + 100
        )

    except Exception:

        return None


def probability_to_american(prob):

    try:

        prob = float(prob)

        if prob <= 0 or prob >= 1:
            return None

        if prob >= 0.50:

            return round(
                -100 * prob / (1 - prob)
            )

        return round(
            100 * (1 - prob) / prob
        )

    except Exception:

        return None


def mostrar_cuota(odds):

    if odds is None:
        return "N/D"

    try:

        odds = float(odds)

        if odds > 0:
            return f"+{odds:.0f}"

        return f"{odds:.0f}"

    except Exception:

        return "N/D"


# ============================================================
# DESCARGAR DATOS NFL
# ============================================================

@st.cache_data(ttl=600)
def descargar_partidos():

    temporada = datetime.now(
        DALLAS_TZ
    ).year

    try:

        respuesta = requests.get(
            API_URL,
            params={
                "season": temporada
            },
            timeout=30
        )

    except Exception as error:

        return [], f"Error de conexión: {error}"

    if respuesta.status_code != 200:

        return [], (
            f"HTTP {respuesta.status_code}"
        )

    try:

        datos = respuesta.json()

    except Exception:

        return [], (
            "La fuente no devolvió JSON válido."
        )

    # --------------------------------------------------------
    # NORMALIZAR RESPUESTA
    # --------------------------------------------------------

    if isinstance(datos, list):

        lista = datos

    elif isinstance(datos, dict):

        lista = datos.get("data")

        if lista is None:
            lista = datos.get("games")

        if lista is None:
            lista = datos.get("results")

        if lista is None:
            lista = []

    else:

        lista = []

    partidos = []

    for item in lista:

        if not isinstance(item, dict):
            continue

        fecha_raw = obtener_valor(
            item,
            [
                "game_date",
                "gameday",
                "date",
                "datetime",
                "start_time",
                "gameDate"
            ]
        )

        fecha = convertir_fecha(
            fecha_raw
        )

        if fecha is None:
            continue

        visitante = obtener_valor(
            item,
            [
                "away_team",
                "awayTeam",
                "away"
            ]
        )

        local = obtener_valor(
            item,
            [
                "home_team",
                "homeTeam",
                "home"
            ]
        )

        if isinstance(
            visitante,
            dict
        ):

            visitante = (
                visitante.get("full")
                or visitante.get("name")
                or visitante.get("abbr")
                or visitante.get("team")
            )

        if isinstance(
            local,
            dict
        ):

            local = (
                local.get("full")
                or local.get("name")
                or local.get("abbr")
                or local.get("team")
            )

        if not visitante or not local:
            continue

        partidos.append(
            {
                "raw": item,
                "fecha": fecha,
                "away": str(visitante),
                "home": str(local)
            }
        )

    partidos.sort(
        key=lambda x: x["fecha"]
    )

    return partidos, None


# ============================================================
# RESULTADOS HISTÓRICOS
# ============================================================

def obtener_resultados_terminados(partidos):

    resultados = []

    for partido in partidos:

        raw = partido["raw"]

        away_score = obtener_valor(
            raw,
            [
                "away_score",
                "awayScore",
                "score_away"
            ]
        )

        home_score = obtener_valor(
            raw,
            [
                "home_score",
                "homeScore",
                "score_home"
            ]
        )

        if (
            away_score is None
            or home_score is None
        ):
            continue

        try:

            away_score = float(
                away_score
            )

            home_score = float(
                home_score
            )

        except Exception:

            continue

        resultados.append(
            (
                partido,
                away_score,
                home_score
            )
        )

    resultados.sort(
        key=lambda x: x[0]["fecha"]
    )

    return resultados


# ============================================================
# MODELO ELO
# ============================================================

ELO_INICIAL = 1500

VENTAJA_LOCAL = 55

K_FACTOR = 22

ESCALA_ELO = 400


def calcular_probabilidad_elo(
    elo_local,
    elo_visitante
):

    diferencia = (
        elo_local
        + VENTAJA_LOCAL
        - elo_visitante
    )

    return 1 / (
        1
        + 10 ** (
            -diferencia / ESCALA_ELO
        )
    )


def actualizar_elo(
    ganador,
    perdedor,
    diferencia_puntos
):

    expectativa = 1 / (
        1
        + 10 ** (
            (
                perdedor
                - ganador
            ) / ESCALA_ELO
        )
    )

    margen = max(
        abs(diferencia_puntos),
        1
    )

    multiplicador = math.log(
        margen + 1
    )

    cambio = (
        K_FACTOR
        * multiplicador
        * (1 - expectativa)
    )

    nuevo_ganador = (
        ganador + cambio
    )

    nuevo_perdedor = (
        perdedor - cambio
    )

    return (
        nuevo_ganador,
        nuevo_perdedor
    )


def construir_ratings(partidos):

    ratings = {}

    resultados = (
        obtener_resultados_terminados(
            partidos
        )
    )

    for (
        partido,
        away_score,
        home_score
    ) in resultados:

        away = partido["away"]
        home = partido["home"]

        if away not in ratings:
            ratings[away] = ELO_INICIAL

        if home not in ratings:
            ratings[home] = ELO_INICIAL

        away_elo = ratings[away]
        home_elo = ratings[home]

        if home_score > away_score:

            nuevo_home, nuevo_away = (
                actualizar_elo(
                    home_elo,
                    away_elo,
                    home_score - away_score
                )
            )

            ratings[home] = nuevo_home
            ratings[away] = nuevo_away

        elif away_score > home_score:

            nuevo_away, nuevo_home = (
                actualizar_elo(
                    away_elo,
                    home_elo,
                    away_score - home_score
                )
            )

            ratings[away] = nuevo_away
            ratings[home] = nuevo_home

    return ratings


# ============================================================
# MODELO PARA UN PARTIDO
# ============================================================

def calcular_modelo(
    home,
    away,
    ratings
):

    elo_home = ratings.get(
        home,
        ELO_INICIAL
    )

    elo_away = ratings.get(
        away,
        ELO_INICIAL
    )

    prob_home = (
        calcular_probabilidad_elo(
            elo_home,
            elo_away
        )
    )

    prob_away = (
        1 - prob_home
    )

    return {
        "home_elo": elo_home,
        "away_elo": elo_away,
        "home_prob": prob_home,
        "away_prob": prob_away
    }


# ============================================================
# CUOTAS DEL PARTIDO
# ============================================================

def obtener_cuotas(partido):

    raw = partido["raw"]

    home_ml = obtener_valor(
        raw,
        [
            "home_moneyline",
            "home_ml",
            "homeMoneyline",
            "moneyline_home",
            "home_odds"
        ]
    )

    away_ml = obtener_valor(
        raw,
        [
            "away_moneyline",
            "away_ml",
            "awayMoneyline",
            "moneyline_away",
            "away_odds"
        ]
    )

    spread = obtener_valor(
        raw,
        [
            "spread",
            "home_spread"
        ]
    )

    total = obtener_valor(
        raw,
        [
            "total",
            "over_under",
            "overUnder"
        ]
    )

    odds = raw.get("odds")

    if isinstance(odds, dict):

        if home_ml is None:

            home_ml = obtener_valor(
                odds,
                [
                    "home_moneyline",
                    "home_ml",
                    "homeMoneyline"
                ]
            )

        if away_ml is None:

            away_ml = obtener_valor(
                odds,
                [
                    "away_moneyline",
                    "away_ml",
                    "awayMoneyline"
                ]
            )

        if spread is None:
            spread = odds.get("spread")

        if total is None:
            total = odds.get("total")

    return {
        "home_ml": home_ml,
        "away_ml": away_ml,
        "spread": spread,
        "total": total
    }


# ============================================================
# EDGE
# ============================================================

def calcular_edge(
    prob_modelo,
    cuota
):

    prob_casa = (
        american_to_probability(
            cuota
        )
    )

    if prob_casa is None:
        return None

    return {
        "prob_casa": prob_casa,
        "edge": (
            prob_modelo
            - prob_casa
        ),
        "cuota_justa": (
            probability_to_american(
                prob_modelo
            )
        )
    }


# ============================================================
# HEADER
# ============================================================

st.markdown(
    "# 🏈 Monitor NFL"
)

st.markdown(
    "### Modelo propio — análisis NFL automático"
)


# ============================================================
# TABS
# ============================================================

tab_hoy, tab_validacion, tab_info = st.tabs(
    [
        "🏈 NFL DE HOY",
        "🧪 VALIDACIÓN DEL MODELO",
        "📊 INFORMACIÓN"
    ]
)


# ============================================================
# TAB NFL DE HOY
# ============================================================

with tab_hoy:

    st.header(
        "🏈 NFL DE HOY"
    )

    if st.button(
        "🔄 ACTUALIZAR PARTIDOS",
        use_container_width=True
    ):

        st.cache_data.clear()

        st.rerun()

    with st.spinner(
        "Consultando calendario NFL..."
    ):

        partidos, error = descargar_partidos()

    # --------------------------------------------------------
    # ERROR
    # --------------------------------------------------------

    if error:

        st.error(
            "No se pudo obtener el calendario NFL."
        )

        st.code(
            error
        )

        st.info(
            "La aplicación no va a inventar partidos "
            "si la fuente no responde."
        )

    # --------------------------------------------------------
    # SIN DATOS
    # --------------------------------------------------------

    elif not partidos:

        st.warning(
            "La fuente no devolvió partidos."
        )

    # --------------------------------------------------------
    # DATOS OK
    # --------------------------------------------------------

    else:

        ratings = construir_ratings(
            partidos
        )

        ahora = datetime.now(
            DALLAS_TZ
        )

        hoy = ahora.date()

        partidos_hoy = []

        proximos = []

        for partido in partidos:

            fecha = partido["fecha"]

            if fecha.date() == hoy:

                partidos_hoy.append(
                    partido
                )

            elif (
                fecha > ahora
                and
                fecha <= (
                    ahora
                    + timedelta(days=7)
                )
            ):

                proximos.append(
                    partido
                )

        # ----------------------------------------------------
        # QUÉ MOSTRAR
        # ----------------------------------------------------

        if partidos_hoy:

            lista = partidos_hoy

            st.success(
                f"🏈 Hay {len(lista)} partido(s) "
                "NFL hoy."
            )

        elif proximos:

            lista = proximos

            st.warning(
                "No hay partidos NFL hoy. "
                "Mostrando los próximos 7 días."
            )

        else:

            lista = []

            st.info(
                "No hay partidos NFL disponibles "
                "para esta fecha ni los próximos 7 días."
            )

        # ----------------------------------------------------
        # MOSTRAR PARTIDOS
        # ----------------------------------------------------

        for partido in lista:

            home = partido["home"]
            away = partido["away"]
            fecha = partido["fecha"]

            modelo = calcular_modelo(
                home,
                away,
                ratings
            )

            cuotas = obtener_cuotas(
                partido
            )

            home_edge = calcular_edge(
                modelo["home_prob"],
                cuotas["home_ml"]
            )

            away_edge = calcular_edge(
                modelo["away_prob"],
                cuotas["away_ml"]
            )

            # ------------------------------------------------
            # CARD
            # ------------------------------------------------

            st.markdown(
                '<div class="card">',
                unsafe_allow_html=True
            )

            st.subheader(
                f"🏈 {away} @ {home}"
            )

            st.info(
                "🕐 Hora Dallas: "
                + fecha.strftime(
                    "%m/%d/%Y — %I:%M %p"
                )
            )

            # ------------------------------------------------
            # EQUIPOS
            # ------------------------------------------------

            col1, col2 = st.columns(2)

            with col1:

                st.markdown(
                    f"## ✈️ {away}"
                )

                st.caption(
                    f"Elo: "
                    f"{modelo['away_elo']:.0f}"
                )

                st.metric(
                    "Probabilidad modelo",
                    f"{modelo['away_prob']:.1%}"
                )

                st.write(
                    "🎯 Cuota justa: "
                    f"**{mostrar_cuota(away_edge['cuota_justa'] if away_edge else probability_to_american(modelo['away_prob']))}**"
                )

            with col2:

                st.markdown(
                    f"## 🏠 {home}"
                )

                st.caption(
                    f"Elo: "
                    f"{modelo['home_elo']:.0f}"
                )

                st.metric(
                    "Probabilidad modelo",
                    f"{modelo['home_prob']:.1%}"
                )

                st.write(
                    "🎯 Cuota justa: "
                    f"**{mostrar_cuota(home_edge['cuota_justa'] if home_edge else probability_to_american(modelo['home_prob']))}**"
                )

            st.divider()

            # ------------------------------------------------
            # CASA
            # ------------------------------------------------

            st.subheader(
                "🏦 Comparación con la casa"
            )

            if (
                home_edge is None
                and
                away_edge is None
            ):

                st.info(
                    "La fuente no proporcionó "
                    "moneylines para este partido."
                )

            else:

                c1, c2 = st.columns(2)

                # --------------------------------------------
                # HOME
                # --------------------------------------------

                with c1:

                    st.markdown(
                        f"### 🏠 {home}"
                    )

                    if home_edge:

                        st.write(
                            "Cuota casa: "
                            f"**{mostrar_cuota(cuotas['home_ml'])}**"
                        )

                        st.write(
                            "Prob. implícita: "
                            f"**{home_edge['prob_casa']:.1%}**"
                        )

                        edge = home_edge["edge"]

                        if edge >= 0.03:

                            st.markdown(
                                f"""
                                <div class="edge-good">
                                🔥 <b>EDGE +{edge:.1%}</b>
                                <br><br>
                                El modelo ve más
                                probabilidad que la casa.
                                </div>
                                """,
                                unsafe_allow_html=True
                            )

                        elif edge <= -0.03:

                            st.markdown(
                                f"""
                                <div class="edge-bad">
                                ⚠️ <b>EDGE {edge:.1%}</b>
                                <br><br>
                                La casa ve más probabilidad
                                que nuestro modelo.
                                </div>
                                """,
                                unsafe_allow_html=True
                            )

                        else:

                            st.markdown(
                                f"""
                                <div class="edge-neutral">
                                EDGE <b>{edge:+.1%}</b>
                                <br><br>
                                Sin diferencia significativa.
                                </div>
                                """,
                                unsafe_allow_html=True
                            )

                    else:

                        st.info(
                            "Sin cuota disponible."
                        )

                # --------------------------------------------
                # AWAY
                # --------------------------------------------

                with c2:

                    st.markdown(
                        f"### ✈️ {away}"
                    )

                    if away_edge:

                        st.write(
                            "Cuota casa: "
                            f"**{mostrar_cuota(cuotas['away_ml'])}**"
                        )

                        st.write(
                            "Prob. implícita: "
                            f"**{away_edge['prob_casa']:.1%}**"
                        )

                        edge = away_edge["edge"]

                        if edge >= 0.03:

                            st.markdown(
                                f"""
                                <div class="edge-good">
                                🔥 <b>EDGE +{edge:.1%}</b>
                                <br><br>
                                El modelo ve más
                                probabilidad que la casa.
                                </div>
                                """,
                                unsafe_allow_html=True
                            )

                        elif edge <= -0.03:

                            st.markdown(
                                f"""
                                <div class="edge-bad">
                                ⚠️ <b>EDGE {edge:.1%}</b>
                                <br><br>
                                La casa ve más probabilidad
                                que nuestro modelo.
                                </div>
                                """,
                                unsafe_allow_html=True
                            )

                        else:

                            st.markdown(
                                f"""
                                <div class="edge-neutral">
                                EDGE <b>{edge:+.1%}</b>
                                <br><br>
                                Sin diferencia significativa.
                                </div>
                                """,
                                unsafe_allow_html=True
                            )

                    else:

                        st.info(
                            "Sin cuota disponible."
                        )

            # ------------------------------------------------
            # MERCADO
            # ------------------------------------------------

            if (
                cuotas["spread"] is not None
                or
                cuotas["total"] is not None
            ):

                st.divider()

                st.subheader(
                    "📋 Mercado"
                )

                m1, m2 = st.columns(2)

                with m1:

                    st.write(
                        "Spread: "
                        f"**{cuotas['spread'] if cuotas['spread'] is not None else 'N/D'}**"
                    )

                with m2:

                    st.write(
                        "Total: "
                        f"**{cuotas['total'] if cuotas['total'] is not None else 'N/D'}**"
                    )

            st.markdown(
                "</div>",
                unsafe_allow_html=True
            )


# ============================================================
# TAB VALIDACIÓN
# ============================================================

with tab_validacion:

    st.header(
        "🧪 Validación del modelo"
    )

    st.markdown(
        """
        <div class="yellow-card">

        🎯 <b>OBJETIVO</b>

        <br><br>

        No queremos simplemente demostrar que
        el modelo tiene muchos aciertos.

        <br><br>

        Queremos comprobar si sus probabilidades
        están correctamente calibradas.

        <br><br>

        Por ejemplo:

        <br><br>

        Si el modelo dice <b>70%</b> en 100 partidos,
        queremos observar aproximadamente
        70 victorias.

        <br><br>

        Eso nos permitirá saber si el 70% del modelo
        realmente significa algo.

        </div>
        """,
        unsafe_allow_html=True
    )

    with st.spinner(
        "Cargando histórico..."
    ):

        partidos, error = descargar_partidos()

    if error:

        st.error(
            error
        )

    elif partidos:

        resultados = (
            obtener_resultados_terminados(
                partidos
            )
        )

        st.success(
            f"Se encontraron "
            f"{len(resultados)} partidos "
            "con resultado."
        )

        ratings = construir_ratings(
            partidos
        )

        # ----------------------------------------------------
        # TABLA ELO
        # ----------------------------------------------------

        st.subheader(
            "📊 Ratings actuales"
        )

        tabla = pd.DataFrame(
            [
                {
                    "Equipo": equipo,
                    "Elo": round(elo)
                }
                for equipo, elo
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

        # ----------------------------------------------------
        # CALIBRACIÓN SIMPLE
        # ----------------------------------------------------

        st.subheader(
            "📈 Calibración"
        )

        datos_calibracion = []

        for (
            partido,
            away_score,
            home_score
        ) in resultados:

            # Para esta primera versión
            # usamos ratings disponibles.
            home = partido["home"]
            away = partido["away"]

            modelo = calcular_modelo(
                home,
                away,
                ratings
            )

            if home_score > away_score:

                real_home = 1

            elif home_score < away_score:

                real_home = 0

            else:

                real_home = 0.5

            datos_calibracion.append(
                {
                    "probabilidad_modelo":
                        modelo["home_prob"],

                    "resultado":
                        real_home
                }
            )

        if datos_calibracion:

            df = pd.DataFrame(
                datos_calibracion
            )

            bins = [
                0.50,
                0.55,
                0.60,
                0.65,
                0.70,
                0.75,
                0.80,
                0.85,
                0.90,
                1.01
            ]

            etiquetas = [
                "50-55%",
                "55-60%",
                "60-65%",
                "65-70%",
                "70-75%",
                "75-80%",
                "80-85%",
                "85-90%",
                "90%+"
            ]

            df["grupo"] = pd.cut(
                df["probabilidad_modelo"],
                bins=bins,
                labels=etiquetas,
                right=False
            )

            resumen = (
                df
                .groupby(
                    "grupo",
                    observed=False
                )
                .agg(
                    partidos=(
                        "resultado",
                        "count"
                    ),
                    aciertos=(
                        "resultado",
                        "sum"
                    ),
                    prob_media=(
                        "probabilidad_modelo",
                        "mean"
                    )
                )
                .reset_index()
            )

            resumen["acierto_real"] = (
                resumen["aciertos"]
                / resumen["partidos"]
            )

            resumen["diferencia"] = (
                resumen["acierto_real"]
                - resumen["prob_media"]
            )

            resumen = resumen.rename(
                columns={
                    "grupo":
                        "Probabilidad mínima",

                    "partidos":
                        "Partidos",

                    "aciertos":
                        "Aciertos",

                    "prob_media":
                        "Prob. promedio modelo",

                    "acierto_real":
                        "Acierto real",

                    "diferencia":
                        "Diferencia"
                }
            )

            resumen["Prob. promedio modelo"] = (
                resumen[
                    "Prob. promedio modelo"
                ].map(
                    lambda x:
                    f"{x:.1%}"
                    if pd.notna(x)
                    else "-"
                )
            )

            resumen["Acierto real"] = (
                resumen[
                    "Acierto real"
                ].map(
                    lambda x:
                    f"{x:.1%}"
                    if pd.notna(x)
                    else "-"
                )
            )

            resumen["Diferencia"] = (
                resumen[
                    "Diferencia"
                ].map(
                    lambda x:
                    f"{x:+.1%}"
                    if pd.notna(x)
                    else "-"
                )
            )

            st.dataframe(
                resumen,
                use_container_width=True,
                hide_index=True
            )

    else:

        st.warning(
            "No hay datos históricos disponibles."
        )


# ============================================================
# TAB INFORMACIÓN
# ============================================================

with tab_info:

    st.header(
        "📊 Información"
    )

    st.markdown(
        """
        <div class="blue-card">

        <h3>🧠 ¿Qué estamos construyendo?</h3>

        <br>

        Un sistema que transforme información
        histórica NFL en probabilidades.

        <br><br>

        El primer motor es Elo.

        <br><br>

        Después iremos incorporando:

        <br><br>

        • Fuerza ofensiva<br>
        • Fuerza defensiva<br>
        • Quarterback<br>
        • Lesiones<br>
        • Forma reciente<br>
        • Descanso<br>
        • Localía<br>
        • Eficiencia<br>
        • Mercado<br>
        • Movimiento de líneas

        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown(
        """
        <div class="green-card">

        <h3>🎯 Objetivo final</h3>

        <br>

        <b>Probabilidad del modelo</b>

        <br><br>

        ↓

        <br><br>

        <b>Cuota justa</b>

        <br><br>

        ↓

        <br><br>

        <b>Cuota de la casa</b>

        <br><br>

        ↓

        <br><br>

        <b>Probabilidad implícita</b>

        <br><br>

        ↓

        <br><br>

        <b>EDGE</b>

        <br><br>

        La diferencia entre nuestra probabilidad
        y la probabilidad implícita del mercado.

        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown(
        """
        <div class="yellow-card">

        ⚠️ <b>IMPORTANTE</b>

        <br><br>

        Una probabilidad del modelo NO significa
        que el resultado esté garantizado.

        <br><br>

        Primero necesitamos validar históricamente
        que las probabilidades tengan valor predictivo.

        <br><br>

        El objetivo es encontrar una ventaja
        estadística consistente, no simplemente
        acertar algunos partidos.

        </div>
        """,
        unsafe_allow_html=True
    )


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    "Monitor NFL — herramienta experimental "
    "de análisis estadístico. Las probabilidades "
    "son estimaciones y no garantizan resultados futuros."
)
