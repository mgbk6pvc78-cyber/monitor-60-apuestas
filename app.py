import streamlit as st
import requests
from datetime import datetime
import pandas as pd
import numpy as np

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
    font-size: 1.2rem;
}

.card {
    padding: 25px;
    border-radius: 18px;
    background-color: #171922;
    border: 1px solid #30333d;
    margin-bottom: 20px;
}

.green-card {
    padding: 25px;
    border-radius: 18px;
    background-color: #193426;
    border: 1px solid #356b4c;
    margin-bottom: 20px;
}

.blue-card {
    padding: 25px;
    border-radius: 18px;
    background-color: #192c43;
    border: 1px solid #294b70;
    margin-bottom: 20px;
}

.yellow-card {
    padding: 25px;
    border-radius: 18px;
    background-color: #40371d;
    border: 1px solid #6c5c2a;
    margin-bottom: 20px;
}

.game-card {
    padding: 25px;
    border-radius: 18px;
    background-color: #171922;
    border: 1px solid #30333d;
    margin-bottom: 25px;
}

.big-number {
    font-size: 3rem;
    font-weight: 700;
}

</style>
""", unsafe_allow_html=True)


# ============================================================
# CONVERSIÓN DE CUOTAS
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

        return round(-100 * prob / (1 - prob))

    else:

        return round(100 * (1 - prob) / prob)


# ============================================================
# OBTENER PARTIDOS NFL
# ============================================================

def obtener_partidos_nfl():

    fecha = datetime.now().strftime("%Y%m%d")

    url = (
        "https://site.api.espn.com/"
        "apis/site/v2/sports/football/nfl/scoreboard"
    )

    params = {
        "dates": fecha
    }

    headers = {
        "User-Agent": (
            "Mozilla/5.0 "
            "(iPhone; CPU iPhone OS 17_0 like Mac OS X) "
            "AppleWebKit/605.1.15 "
            "Version/17.0 Mobile/15E148 Safari/604.1"
        ),
        "Accept": "application/json",
        "Referer": "https://www.espn.com/"
    }

    try:

        response = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=15
        )

        response.raise_for_status()

        data = response.json()

        return data, None

    except Exception as e:

        return None, str(e)


# ============================================================
# PROCESAR PARTIDOS
# ============================================================

def procesar_partidos(data):

    partidos = []

    if not data:
        return partidos

    eventos = data.get("events", [])

    for evento in eventos:

        try:

            competencia = evento["competitions"][0]

            equipos = competencia["competitors"]

            if len(equipos) < 2:
                continue

            visitante = None
            local = None

            for equipo in equipos:

                nombre = (
                    equipo.get("team", {})
                    .get("displayName", "Equipo")
                )

                abreviatura = (
                    equipo.get("team", {})
                    .get("abbreviation", "")
                )

                if equipo.get("homeAway") == "home":

                    local = {
                        "nombre": nombre,
                        "abreviatura": abreviatura
                    }

                else:

                    visitante = {
                        "nombre": nombre,
                        "abreviatura": abreviatura
                    }

            if not visitante or not local:
                continue

            fecha = evento.get("date", "")

            # ------------------------------------------------
            # ODDS
            # ------------------------------------------------

            odds_data = None

            odds_array = competencia.get("odds", [])

            if odds_array:

                odds_data = odds_array[0]

            partidos.append({

                "id": evento.get("id"),

                "visitante": visitante["nombre"],

                "local": local["nombre"],

                "visitante_abbr": visitante["abreviatura"],

                "local_abbr": local["abreviatura"],

                "fecha": fecha,

                "odds": odds_data

            })

        except:

            continue

    return partidos


# ============================================================
# MODELO INICIAL
# ============================================================

def calcular_probabilidad_modelo(partido):

    """
    TEMPORALMENTE usamos 50/50.

    IMPORTANTE:
    Esta función será reemplazada por nuestro modelo real.
    """

    return 0.50


# ============================================================
# MOSTRAR PARTIDO
# ============================================================

def mostrar_partido(partido):

    visitante = partido["visitante"]

    local = partido["local"]

    prob_visitante = calcular_probabilidad_modelo(
        partido
    )

    prob_local = 1 - prob_visitante

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

    col1, col2 = st.columns(2)

    with col1:

        st.subheader(
            f"✈️ {visitante}"
        )

        st.metric(
            "Probabilidad modelo",
            f"{prob_visitante:.1%}"
        )

        cuota_justa = probability_to_american(
            prob_visitante
        )

        st.caption(
            f"Cuota justa: "
            f"{cuota_justa if cuota_justa else 'N/A'}"
        )

    with col2:

        st.subheader(
            f"🏠 {local}"
        )

        st.metric(
            "Probabilidad modelo",
            f"{prob_local:.1%}"
        )

        cuota_justa = probability_to_american(
            prob_local
        )

        st.caption(
            f"Cuota justa: "
            f"{cuota_justa if cuota_justa else 'N/A'}"
        )

    # ========================================================
    # CUOTAS
    # ========================================================

    odds_data = partido.get("odds")

    if odds_data:

        st.markdown(
            """
            <div class="yellow-card">
            🏦 <b>Cuotas disponibles</b>
            </div>
            """,
            unsafe_allow_html=True
        )

        st.write(
            odds_data
        )

    else:

        st.info(
            "La fuente no proporcionó cuotas para este partido."
        )

    st.divider()


# ============================================================
# ENCABEZADO
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
# NFL DE HOY
# ============================================================

with tab1:

    st.header("🏈 NFL DE HOY")

    actualizar = st.button(
        "🔄 ACTUALIZAR PARTIDOS",
        use_container_width=True
    )

    # Ejecutar automáticamente al abrir
    if (
        "partidos_nfl" not in st.session_state
        or actualizar
    ):

        with st.spinner(
            "Consultando calendario NFL..."
        ):

            data, error = obtener_partidos_nfl()

            if error:

                st.error(
                    "No se pudo conectar con la fuente NFL."
                )

                st.code(error)

                st.session_state["partidos_nfl"] = []

            else:

                partidos = procesar_partidos(
                    data
                )

                st.session_state[
                    "partidos_nfl"
                ] = partidos

    partidos = st.session_state.get(
        "partidos_nfl",
        []
    )

    # ========================================================
    # RESULTADO
    # ========================================================

    if partidos:

        st.success(
            f"🏈 {len(partidos)} partidos encontrados."
        )

        st.markdown(
            """
            <div class="blue-card">

            <b>Datos automáticos</b>

            <br><br>

            El sistema está obteniendo los partidos
            directamente de una fuente externa.

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

        st.warning(
            "No se encontraron partidos NFL para hoy."
        )

        st.info(
            "Si sabes que existen partidos hoy, "
            "pulsa nuevamente ACTUALIZAR PARTIDOS."
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
        "generadas por nuestro modelo están "
        "correctamente calibradas."
    )

    st.markdown(
        """
        <div class="yellow-card">

        🎯 <b>Objetivo</b>

        <br><br>

        Si nuestro modelo dice 70%, queremos comprobar
        históricamente qué porcentaje de esos partidos
        realmente termina ganándose.

        <br><br>

        No buscamos solamente muchos aciertos.

        <br><br>

        Buscamos probabilidades que tengan
        significado estadístico.

        </div>
        """,
        unsafe_allow_html=True
    )

    st.subheader(
        "📊 Ejemplo de calibración"
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

        <h3>🎯 ¿Qué estamos construyendo?</h3>

        <br>

        El objetivo NO es copiar las cuotas de la casa.

        <br><br>

        Queremos calcular nuestra propia probabilidad
        para cada resultado.

        <br><br>

        Después compararemos:

        <br><br>

        • Probabilidad de nuestro modelo

        <br>

        • Probabilidad implícita de la casa

        <br>

        • Diferencia entre ambas

        <br>

        • Cuota justa

        <br>

        • EDGE

        <br><br>

        <b>
        La decisión final se basará en la diferencia
        entre nuestra estimación y el mercado.
        </b>

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
