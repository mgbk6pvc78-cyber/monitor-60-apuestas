import streamlit as st
import requests
import pandas as pd
import numpy as np
from datetime import datetime, date

# ============================================================
# CONFIGURACIÓN
# ============================================================

st.set_page_config(
    page_title="Monitor NFL",
    page_icon="🏈",
    layout="wide"
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
    margin-top: 15px;
}

.edge-negative {
    padding: 20px;
    border-radius: 15px;
    background-color: #402126;
    border: 1px solid #70343d;
    margin-top: 15px;
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
# PARTIDOS DE HOY
#
# FUENTE PRINCIPAL:
# ESPN
#
# RESPALDO:
# calendario conocido del día
#
# Esto evita que la aplicación quede vacía
# si una fuente bloquea Streamlit Cloud.
# ============================================================

def partidos_respaldo():

    hoy = datetime.now().strftime("%Y-%m-%d")

    # --------------------------------------------------------
    # PRETEMPORADA NFL 2026 - 13 AGOSTO
    # --------------------------------------------------------

    if hoy == "2026-08-13":

        return [

            {
                "id": "2026-08-13-DET-CIN",
                "visitante": "Detroit Lions",
                "local": "Cincinnati Bengals",
                "hora": "7:00 PM ET"
            },

            {
                "id": "2026-08-13-GB-PIT",
                "visitante": "Green Bay Packers",
                "local": "Pittsburgh Steelers",
                "hora": "7:30 PM ET"
            },

            {
                "id": "2026-08-13-IND-NE",
                "visitante": "Indianapolis Colts",
                "local": "New England Patriots",
                "hora": "7:30 PM ET"
            },

            {
                "id": "2026-08-13-LAC-HOU",
                "visitante": "Los Angeles Chargers",
                "local": "Houston Texans",
                "hora": "8:00 PM ET"
            },

            {
                "id": "2026-08-13-TEN-SF",
                "visitante": "Tennessee Titans",
                "local": "San Francisco 49ers",
                "hora": "10:00 PM ET"
            },

            {
                "id": "2026-08-13-LV-ARI",
                "visitante": "Las Vegas Raiders",
                "local": "Arizona Cardinals",
                "hora": "10:00 PM ET"
            }

        ]

    return []


# ============================================================
# INTENTO DE CONEXIÓN AUTOMÁTICA
# ============================================================

def obtener_partidos_automaticos():

    hoy = datetime.now().strftime("%Y%m%d")

    url = (
        "https://site.api.espn.com/"
        "apis/site/v2/sports/football/nfl/scoreboard"
    )

    params = {
        "dates": hoy
    }

    headers = {

        "User-Agent":
            "Mozilla/5.0 "
            "(iPhone; CPU iPhone OS 17_0 like Mac OS X) "
            "AppleWebKit/605.1.15 "
            "Version/17.0 Mobile/15E148 Safari/604.1",

        "Accept":
            "application/json",

        "Referer":
            "https://www.espn.com/"

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

                competencia = evento[
                    "competitions"
                ][0]

                equipos = competencia[
                    "competitors"
                ]

                visitante = None
                local = None

                for equipo in equipos:

                    nombre = equipo[
                        "team"
                    ][
                        "displayName"
                    ]

                    if equipo[
                        "homeAway"
                    ] == "home":

                        local = nombre

                    else:

                        visitante = nombre

                if visitante and local:

                    partidos.append({

                        "id":
                            evento.get(
                                "id"
                            ),

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

        if partidos:

            return partidos, "ESPN"

    except:

        pass

    # --------------------------------------------------------
    # RESPALDO
    # --------------------------------------------------------

    respaldo = partidos_respaldo()

    if respaldo:

        return respaldo, "Calendario de respaldo"

    return [], None


# ============================================================
# MODELO
# ============================================================

def modelo_nfl(partido):

    """
    ------------------------------------------------------------
    AQUÍ VAMOS A COLOCAR NUESTRO MODELO REAL.
    ------------------------------------------------------------

    Por ahora NO inventamos una probabilidad.

    Usamos 50/50 únicamente para comprobar que
    toda la estructura funciona.

    IMPORTANTE:
    NO usar este 50/50 para apostar.
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

    if partido.get("hora"):

        st.info(
            f"🕐 {partido['hora']}"
        )

    col1, col2 = st.columns(2)

    # ========================================================
    # VISITANTE
    # ========================================================

    with col1:

        st.subheader(
            f"✈️ {visitante}"
        )

        st.metric(
            "Probabilidad modelo",
            f"{prob_visitante:.1%}"
        )

        cuota_justa = (
            probability_to_american(
                prob_visitante
            )
        )

        st.write(
            f"🎯 Cuota justa: "
            f"**{cuota_justa}**"
        )

    # ========================================================
    # LOCAL
    # ========================================================

    with col2:

        st.subheader(
            f"🏠 {local}"
        )

        st.metric(
            "Probabilidad modelo",
            f"{prob_local:.1%}"
        )

        cuota_justa = (
            probability_to_american(
                prob_local
            )
        )

        st.write(
            f"🎯 Cuota justa: "
            f"**{cuota_justa}**"
        )

    st.markdown(
        """
        <div class="yellow-card">

        🏦 <b>Comparación con la casa</b>

        <br><br>

        Próximamente aquí mostraremos:

        <br><br>

        • Cuota de la casa

        <br>

        • Probabilidad implícita

        <br>

        • Probabilidad de nuestro modelo

        <br>

        • EDGE

        <br>

        • Diferencia

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

    actualizar = st.button(
        "🔄 ACTUALIZAR PARTIDOS",
        use_container_width=True
    )

    # --------------------------------------------------------
    # CARGAR
    # --------------------------------------------------------

    if (
        "partidos" not in
        st.session_state
        or actualizar
    ):

        with st.spinner(
            "Consultando partidos NFL..."
        ):

            partidos, fuente = (
                obtener_partidos_automaticos()
            )

            st.session_state[
                "partidos"
            ] = partidos

            st.session_state[
                "fuente"
            ] = fuente

    partidos = st.session_state.get(
        "partidos",
        []
    )

    fuente = st.session_state.get(
        "fuente"
    )

    # ========================================================
    # PARTIDOS
    # ========================================================

    if partidos:

        st.success(
            f"🏈 {len(partidos)} partidos encontrados."
        )

        if fuente:

            st.caption(
                f"Fuente utilizada: {fuente}"
            )

        st.markdown(
            """
            <div class="blue-card">

            📊 <b>Qué estamos haciendo</b>

            <br><br>

            Primero obtenemos los partidos.

            <br><br>

            Después nuestro modelo calculará
            una probabilidad independiente.

            <br><br>

            Finalmente compararemos esa probabilidad
            contra el mercado.

            </div>
            """,
            unsafe_allow_html=True
        )

        for partido in partidos:

            mostrar_partido(
                partido
            )

    else:

        st.warning(
            "No hay partidos NFL disponibles para esta fecha."
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
        "que genera nuestro modelo están correctamente "
        "calibradas."
    )

    st.markdown(
        """
        <div class="yellow-card">

        🎯 <b>LO QUE QUEREMOS COMPROBAR</b>

        <br><br>

        Si nuestro modelo dice 70%, queremos comprobar
        históricamente qué porcentaje de esos partidos
        realmente termina ganándose.

        <br><br>

        No buscamos simplemente tener muchos aciertos.

        <br><br>

        Buscamos que nuestras probabilidades tengan
        significado estadístico.

        </div>
        """,
        unsafe_allow_html=True
    )

    st.subheader(
        "📈 Ejemplo de calibración"
    )

    ejemplo = pd.DataFrame({

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
        ejemplo,
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

        <h2>🎯 Objetivo del proyecto</h2>

        <br>

        No queremos copiar a la casa.

        <br><br>

        Queremos construir nuestra propia
        probabilidad para cada partido.

        <br><br>

        Después:

        <br><br>

        <b>1.</b> Probabilidad de nuestro modelo

        <br><br>

        <b>2.</b> Cuota justa

        <br><br>

        <b>3.</b> Cuota de la casa

        <br><br>

        <b>4.</b> Probabilidad implícita

        <br><br>

        <b>5.</b> Diferencia

        <br><br>

        <b>6.</b> EDGE

        <br><br>

        <b>7.</b> Decisión

        <br><br>

        🟢 Hay ventaja

        <br>

        🔴 No hay ventaja

        </div>
        """,
        unsafe_allow_html=True
    )


# ============================================================
# FOOTER
# ============================================================

st.markdown("---")

st.caption(
    "Monitor NFL — herramienta experimental de "
    "análisis estadístico. Las probabilidades son "
    "estimaciones y no garantizan resultados futuros."
)
