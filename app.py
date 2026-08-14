import streamlit as st
import requests
import pandas as pd
import numpy as np

from datetime import datetime
from zoneinfo import ZoneInfo


# ============================================================
# CONFIGURACIÓN
# ============================================================

st.set_page_config(
    page_title="Monitor NFL",
    page_icon="🏈",
    layout="wide"
)


# ============================================================
# FECHA ACTUAL — DALLAS / CENTRAL
# ============================================================

def fecha_dallas():

    return datetime.now(
        ZoneInfo("America/Chicago")
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

.blue-card {
    padding: 25px;
    border-radius: 18px;
    background-color: #192c43;
    border: 1px solid #294b70;
    margin-bottom: 20px;
}

.green-card {
    padding: 25px;
    border-radius: 18px;
    background-color: #193426;
    border: 1px solid #356b4c;
    margin-bottom: 20px;
}

.yellow-card {
    padding: 25px;
    border-radius: 18px;
    background-color: #40371d;
    border: 1px solid #6c5c2a;
    margin-bottom: 20px;
}

.red-card {
    padding: 25px;
    border-radius: 18px;
    background-color: #402126;
    border: 1px solid #70343d;
    margin-bottom: 20px;
}

.game-card {
    padding: 25px;
    border-radius: 18px;
    background-color: #171922;
    border: 1px solid #30333d;
    margin-bottom: 25px;
}

.edge-positive {
    padding: 20px;
    border-radius: 15px;
    background-color: #193426;
    border: 1px solid #356b4c;
}

.edge-negative {
    padding: 20px;
    border-radius: 15px;
    background-color: #402126;
    border: 1px solid #70343d;
}

</style>
""", unsafe_allow_html=True)


# ============================================================
# CUOTAS
# ============================================================

def american_to_probability(odds):

    try:

        odds = float(odds)

        if odds > 0:
            return 100 / (odds + 100)

        return abs(odds) / (abs(odds) + 100)

    except:

        return None


def probability_to_american(prob):

    if prob <= 0 or prob >= 1:
        return None

    if prob >= 0.5:

        return round(
            -100 * prob / (1 - prob)
        )

    return round(
        100 * (1 - prob) / prob
    )


# ============================================================
# CALENDARIO DE RESPALDO
# ============================================================

def calendario_respaldo():

    fecha = fecha_dallas()

    fecha_texto = fecha.strftime(
        "%Y-%m-%d"
    )

    # ========================================================
    # JUEVES 13 DE AGOSTO 2026
    # ========================================================

    if fecha_texto == "2026-08-13":

        return [

            {
                "id": "DET-CIN",
                "visitante": "Detroit Lions",
                "local": "Cincinnati Bengals",
                "hora": "6:00 PM",
                "zona": "Dallas"
            },

            {
                "id": "GB-PIT",
                "visitante": "Green Bay Packers",
                "local": "Pittsburgh Steelers",
                "hora": "6:30 PM",
                "zona": "Dallas"
            },

            {
                "id": "IND-NE",
                "visitante": "Indianapolis Colts",
                "local": "New England Patriots",
                "hora": "6:30 PM",
                "zona": "Dallas"
            },

            {
                "id": "LAC-HOU",
                "visitante": "Los Angeles Chargers",
                "local": "Houston Texans",
                "hora": "7:00 PM",
                "zona": "Dallas"
            },

            {
                "id": "TEN-SF",
                "visitante": "Tennessee Titans",
                "local": "San Francisco 49ers",
                "hora": "8:00 PM",
                "zona": "Dallas"
            },

            {
                "id": "ARI-LV",
                "visitante": "Arizona Cardinals",
                "local": "Las Vegas Raiders",
                "hora": "9:00 PM",
                "zona": "Dallas"
            }

        ]

    return []


# ============================================================
# ESPN — SOLO COMO INTENTO AUTOMÁTICO
# ============================================================

def obtener_espn():

    fecha = fecha_dallas().strftime(
        "%Y%m%d"
    )

    url = (
        "https://site.api.espn.com/"
        "apis/site/v2/sports/"
        "football/nfl/scoreboard"
    )

    params = {
        "dates": fecha
    }

    headers = {

        "User-Agent":
            "Mozilla/5.0",

        "Accept":
            "application/json"

    }

    try:

        respuesta = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=10
        )

        respuesta.raise_for_status()

        datos = respuesta.json()

        partidos = []

        for evento in datos.get(
            "events",
            []
        ):

            try:

                competencia = (
                    evento["competitions"][0]
                )

                equipos = (
                    competencia["competitors"]
                )

                visitante = None
                local = None

                for equipo in equipos:

                    nombre = (
                        equipo["team"]
                        ["displayName"]
                    )

                    if (
                        equipo["homeAway"]
                        == "home"
                    ):

                        local = nombre

                    else:

                        visitante = nombre

                if visitante and local:

                    partidos.append({

                        "id":
                            evento.get("id"),

                        "visitante":
                            visitante,

                        "local":
                            local,

                        "hora":
                            evento.get(
                                "date",
                                ""
                            )

                    })

            except:

                continue

        return partidos

    except:

        return []


# ============================================================
# OBTENER PARTIDOS
# ============================================================

def obtener_partidos():

    # Primero intentamos fuente automática

    partidos = obtener_espn()

    if partidos:

        return partidos, "Fuente automática"

    # Si falla, utilizamos calendario de respaldo

    partidos = calendario_respaldo()

    if partidos:

        return partidos, "Calendario NFL de respaldo"

    return [], "Sin datos"


# ============================================================
# MODELO
# ============================================================

def modelo_nfl(partido):

    """
    ------------------------------------------------------------
    PRUEBA TEMPORAL
    ------------------------------------------------------------

    Aquí todavía no está nuestro modelo estadístico real.

    Usamos 50/50 únicamente para comprobar que:

    PARTIDO
       ↓
    MODELO
       ↓
    PROBABILIDAD
       ↓
    CUOTA JUSTA

    funciona correctamente.

    NO UTILIZAR ESTE 50/50 PARA APOSTAR.
    """

    return {

        "visitante": 0.50,

        "local": 0.50

    }


# ============================================================
# MOSTRAR PARTIDO
# ============================================================

def mostrar_partido(partido):

    visitante = partido[
        "visitante"
    ]

    local = partido[
        "local"
    ]

    modelo = modelo_nfl(
        partido
    )

    prob_visitante = modelo[
        "visitante"
    ]

    prob_local = modelo[
        "local"
    ]

    # ========================================================
    # TÍTULO
    # ========================================================

    st.markdown(
        f"""
        <div class="game-card">

        <h2>
        🏈 {visitante}
        @
        {local}
        </h2>

        </div>
        """,
        unsafe_allow_html=True
    )

    # ========================================================
    # HORA
    # ========================================================

    if partido.get("hora"):

        st.info(
            f"🕐 Hora Dallas: "
            f"{partido['hora']}"
        )

    # ========================================================
    # EQUIPOS
    # ========================================================

    col1, col2 = st.columns(2)

    # --------------------------------------------------------
    # VISITANTE
    # --------------------------------------------------------

    with col1:

        st.subheader(
            f"✈️ {visitante}"
        )

        st.metric(
            "Probabilidad modelo",
            f"{prob_visitante:.1%}"
        )

        cuota = (
            probability_to_american(
                prob_visitante
            )
        )

        st.write(
            f"🎯 Cuota justa: **{cuota}**"
        )

    # --------------------------------------------------------
    # LOCAL
    # --------------------------------------------------------

    with col2:

        st.subheader(
            f"🏠 {local}"
        )

        st.metric(
            "Probabilidad modelo",
            f"{prob_local:.1%}"
        )

        cuota = (
            probability_to_american(
                prob_local
            )
        )

        st.write(
            f"🎯 Cuota justa: **{cuota}**"
        )

    # ========================================================
    # COMPARACIÓN FUTURA
    # ========================================================

    st.markdown(
        """
        <div class="yellow-card">

        🏦 <b>COMPARACIÓN CON LA CASA</b>

        <br><br>

        Próximo paso:

        <br><br>

        🧠 Probabilidad de nuestro modelo

        <br>

        🏦 Probabilidad implícita de la casa

        <br>

        📈 Diferencia

        <br>

        💰 EDGE

        <br>

        🎯 Cuota justa

        </div>
        """,
        unsafe_allow_html=True
    )

    st.divider()


# ============================================================
# ENCABEZADO
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
# NFL DE HOY
# ============================================================

with tab1:

    st.header(
        "🏈 NFL DE HOY"
    )

    # --------------------------------------------------------
    # FECHA
    # --------------------------------------------------------

    fecha_actual = fecha_dallas()

    st.caption(
        "Fecha Dallas: "
        + fecha_actual.strftime(
            "%d/%m/%Y %I:%M %p"
        )
    )

    # --------------------------------------------------------
    # BOTÓN
    # --------------------------------------------------------

    actualizar = st.button(
        "🔄 ACTUALIZAR PARTIDOS",
        use_container_width=True
    )

    # --------------------------------------------------------
    # CARGA
    # --------------------------------------------------------

    if (
        "partidos_nfl" not in
        st.session_state
        or actualizar
    ):

        with st.spinner(
            "Buscando partidos NFL..."
        ):

            partidos, fuente = (
                obtener_partidos()
            )

            st.session_state[
                "partidos_nfl"
            ] = partidos

            st.session_state[
                "fuente_nfl"
            ] = fuente

    partidos = st.session_state.get(
        "partidos_nfl",
        []
    )

    fuente = st.session_state.get(
        "fuente_nfl",
        ""
    )

    # ========================================================
    # MOSTRAR PARTIDOS
    # ========================================================

    if partidos:

        st.success(
            f"🏈 {len(partidos)} partidos encontrados."
        )

        st.caption(
            f"Fuente: {fuente}"
        )

        st.markdown(
            """
            <div class="blue-card">

            📊 <b>Datos del día</b>

            <br><br>

            Los partidos aparecen automáticamente.

            <br><br>

            No necesitas subir ningún CSV.

            </div>
            """,
            unsafe_allow_html=True
        )

        for partido in partidos:

            mostrar_partido(
                partido
            )

    else:

        st.error(
            "No se encontraron partidos."
        )

        st.info(
            "Pulsa ACTUALIZAR PARTIDOS."
        )


# ============================================================
# VALIDACIÓN
# ============================================================

with tab2:

    st.header(
        "🧪 Validación del modelo"
    )

    st.write(
        "Aquí comprobaremos si las probabilidades "
        "de nuestro modelo están correctamente "
        "calibradas."
    )

    st.markdown(
        """
        <div class="yellow-card">

        🎯 <b>LO QUE QUEREMOS COMPROBAR</b>

        <br><br>

        Si el modelo dice 70%, queremos comprobar
        históricamente qué porcentaje de esos partidos
        realmente termina ganándose.

        <br><br>

        No buscamos solamente una tasa alta de aciertos.

        <br><br>

        Buscamos probabilidades correctamente calibradas.

        </div>
        """,
        unsafe_allow_html=True
    )

    st.subheader(
        "📈 Ejemplo"
    )

    tabla = pd.DataFrame({

        "Probabilidad modelo": [

            "55%",
            "60%",
            "65%",
            "70%",
            "75%",
            "80%",
            "85%",
            "90%"

        ],

        "Objetivo real": [

            "≈55%",
            "≈60%",
            "≈65%",
            "≈70%",
            "≈75%",
            "≈80%",
            "≈85%",
            "≈90%"

        ]

    })

    st.dataframe(
        tabla,
        use_container_width=True,
        hide_index=True
    )


# ============================================================
# INFORMACIÓN
# ============================================================

with tab3:

    st.header(
        "📊 Información"
    )

    st.markdown(
        """
        <div class="green-card">

        <h2>🎯 OBJETIVO DEL PROYECTO</h2>

        <br>

        No queremos copiar las cuotas de la casa.

        <br><br>

        Queremos construir nuestra propia
        probabilidad.

        <br><br>

        Después compararemos:

        <br><br>

        🧠 Probabilidad del modelo

        <br>

        🏦 Probabilidad implícita de la casa

        <br>

        🎯 Cuota justa

        <br>

        📈 Diferencia

        <br>

        💰 EDGE

        <br><br>

        La idea es encontrar situaciones donde
        nuestra estimación sea significativamente
        diferente a la del mercado.

        </div>
        """,
        unsafe_allow_html=True
    )


# ============================================================
# FOOTER
# ============================================================

st.markdown("---")

st.caption(
    "Monitor NFL — herramienta experimental "
    "de análisis estadístico. Las probabilidades "
    "son estimaciones y no garantizan resultados futuros."
)
