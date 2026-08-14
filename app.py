import streamlit as st
import json
from urllib.request import Request, urlopen
from urllib.parse import urlencode
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
    font-size: 1.3rem;
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

.yellow-card {
    padding: 25px;
    border-radius: 18px;
    background-color: #40371d;
    border: 1px solid #6c5c2a;
    margin-bottom: 20px;
}

.blue-card {
    padding: 25px;
    border-radius: 18px;
    background-color: #192c43;
    border: 1px solid #294b70;
    margin-bottom: 20px;
}

.game-card {
    padding: 25px;
    border-radius: 20px;
    background-color: #171922;
    border: 1px solid #343744;
    margin-bottom: 25px;
}

.big-number {
    font-size: 3rem;
    font-weight: 700;
}

.edge-positive {
    padding: 15px;
    border-radius: 12px;
    background-color: #193426;
    border: 1px solid #356b4c;
}

.edge-negative {
    padding: 15px;
    border-radius: 12px;
    background-color: #402020;
    border: 1px solid #703838;
}

</style>
""", unsafe_allow_html=True)


# ============================================================
# FUENTE NFL
# ============================================================

ESPN_URL = (
    "https://site.api.espn.com/apis/site/v2/sports/"
    "football/nfl/scoreboard"
)


# ============================================================
# CONSULTAR ESPN
# ============================================================

def consultar_espn(params):

    try:

        url = ESPN_URL + "?" + urlencode(params)

        request = Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0"
            }
        )

        with urlopen(
            request,
            timeout=20
        ) as response:

            contenido = response.read()

        return json.loads(
            contenido.decode("utf-8")
        )

    except Exception as e:

        st.error(
            "No se pudo conectar con la fuente NFL."
        )

        st.caption(
            str(e)
        )

        return None


# ============================================================
# OBTENER PARTIDOS
# ============================================================

def obtener_partidos():

    ahora = datetime.now(
        ZoneInfo("America/Chicago")
    )

    fecha = ahora.strftime(
        "%Y%m%d"
    )

    # --------------------------------------------------------
    # PRIMERO: TODOS LOS PARTIDOS DEL DÍA
    # --------------------------------------------------------

    data = consultar_espn({
        "dates": fecha,
        "limit": 100
    })

    if not data:
        return []

    eventos = data.get(
        "events",
        []
    )

    partidos = []

    for evento in eventos:

        try:

            competencia = evento[
                "competitions"
            ][0]

            equipos = competencia[
                "competitors"
            ]

            if len(equipos) != 2:
                continue

            visitante = None
            local = None

            for equipo in equipos:

                if equipo.get(
                    "homeAway"
                ) == "home":

                    local = equipo

                elif equipo.get(
                    "homeAway"
                ) == "away":

                    visitante = equipo

            if not visitante or not local:
                continue

            partidos.append({

                "id": evento.get(
                    "id"
                ),

                "nombre": evento.get(
                    "name",
                    ""
                ),

                "fecha": evento.get(
                    "date",
                    ""
                ),

                "estado": evento.get(
                    "status",
                    {}
                ),

                "visitante": visitante[
                    "team"
                ].get(
                    "displayName",
                    "Visitante"
                ),

                "local": local[
                    "team"
                ].get(
                    "displayName",
                    "Local"
                ),

                "visitante_abrev":
                    visitante[
                        "team"
                    ].get(
                        "abbreviation",
                        ""
                    ),

                "local_abrev":
                    local[
                        "team"
                    ].get(
                        "abbreviation",
                        ""
                    )
            })

        except Exception:

            continue

    return partidos


# ============================================================
# CONVERSIÓN DE PROBABILIDAD A CUOTA JUSTA
# ============================================================

def probabilidad_a_americana(prob):

    if prob <= 0:
        return None

    if prob >= 1:
        return None

    if prob >= 0.50:

        cuota = -100 * prob / (
            1 - prob
        )

    else:

        cuota = 100 * (
            1 - prob
        ) / prob

    return round(
        cuota
    )


# ============================================================
# PROBABILIDAD TEMPORAL
#
# IMPORTANTE:
# Esto es solamente una base.
# Después conectaremos el modelo real.
# ============================================================

def probabilidad_base():

    return 0.50


# ============================================================
# ENCABEZADO
# ============================================================

st.markdown(
    '<div class="title">🏈 Monitor NFL</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtitle">'
    'Modelo propio — análisis y comparación de mercado'
    '</div>',
    unsafe_allow_html=True
)

st.markdown("""
<div class="blue-card">

🧠 <b>Objetivo del sistema</b><br><br>

Obtener automáticamente los partidos NFL y posteriormente
comparar nuestra probabilidad contra la probabilidad implícita
de la casa de apuestas.

</div>
""", unsafe_allow_html=True)


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

    st.header(
        "🏈 NFL DE HOY"
    )

    if st.button(
        "🔄 ACTUALIZAR PARTIDOS",
        use_container_width=True
    ):

        st.rerun()

    # --------------------------------------------------------
    # OBTENER PARTIDOS
    # --------------------------------------------------------

    partidos = obtener_partidos()

    # --------------------------------------------------------
    # SIN PARTIDOS
    # --------------------------------------------------------

    if len(partidos) == 0:

        st.warning(
            "⚠️ No se encontraron partidos NFL para hoy."
        )

        ahora = datetime.now(
            ZoneInfo("America/Chicago")
        )

        st.info(
            "Fecha consultada: "
            + ahora.strftime(
                "%d/%m/%Y"
            )
        )

    # --------------------------------------------------------
    # PARTIDOS ENCONTRADOS
    # --------------------------------------------------------

    else:

        st.success(
            f"🏈 {len(partidos)} partidos encontrados"
        )

        for partido in partidos:

            st.markdown(
                '<div class="game-card">',
                unsafe_allow_html=True
            )

            st.subheader(
                "🏈 "
                + partido["visitante"]
                + " @ "
                + partido["local"]
            )

            # ------------------------------------------------
            # MODELO
            # ------------------------------------------------

            prob_visitante = (
                probabilidad_base()
            )

            prob_local = (
                1 - prob_visitante
            )

            cuota_visitante = (
                probabilidad_a_americana(
                    prob_visitante
                )
            )

            cuota_local = (
                probabilidad_a_americana(
                    prob_local
                )
            )

            col1, col2 = st.columns(2)

            # ------------------------------------------------
            # VISITANTE
            # ------------------------------------------------

            with col1:

                st.markdown(
                    "### ✈️ "
                    + partido["visitante"]
                )

                st.write(
                    "Probabilidad modelo"
                )

                st.markdown(
                    f'<div class="big-number">'
                    f'{prob_visitante:.1%}'
                    f'</div>',
                    unsafe_allow_html=True
                )

                st.write(
                    "Cuota justa:"
                )

                st.write(
                    f"**{cuota_visitante:+}**"
                )

            # ------------------------------------------------
            # LOCAL
            # ------------------------------------------------

            with col2:

                st.markdown(
                    "### 🏠 "
                    + partido["local"]
                )

                st.write(
                    "Probabilidad modelo"
                )

                st.markdown(
                    f'<div class="big-number">'
                    f'{prob_local:.1%}'
                    f'</div>',
                    unsafe_allow_html=True
                )

                st.write(
                    "Cuota justa:"
                )

                st.write(
                    f"**{cuota_local:+}**"
                )

            # ------------------------------------------------
            # ESTADO
            # ------------------------------------------------

            estado = partido[
                "estado"
            ]

            descripcion = estado.get(
                "type",
                {}
            ).get(
                "shortDetail",
                ""
            )

            if descripcion:

                st.caption(
                    "📅 " + descripcion
                )

            # ------------------------------------------------
            # MERCADO
            # ------------------------------------------------

            st.markdown("""
            <div class="yellow-card">

            💰 <b>Comparación contra la casa</b><br><br>

            Próximo paso: introducir automáticamente las
            cuotas actuales de las casas y calcular:

            <br><br>

            <b>Probabilidad modelo</b><br>
            −<br>
            <b>Probabilidad implícita de la casa</b><br>
            =<br>
            <b>EDGE</b>

            </div>
            """, unsafe_allow_html=True)

            st.markdown(
                "</div>",
                unsafe_allow_html=True
            )


# ============================================================
# TAB 2
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

    st.markdown("""
    <div class="yellow-card">

    🎯 <b>Lo que queremos comprobar</b><br><br>

    Si nuestro modelo dice 70%, queremos comprobar
    históricamente qué porcentaje de esos partidos
    realmente termina ganándose.

    <br><br>

    No buscamos simplemente tener muchos aciertos.

    <br><br>

    Buscamos que una probabilidad del modelo tenga
    significado estadístico.

    </div>
    """, unsafe_allow_html=True)

    st.subheader(
        "📈 Ejemplo de calibración"
    )

    datos = {

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
    }

    st.table(
        datos
    )

    st.info(
        "La validación histórica real se conectará "
        "cuando tengamos nuestro conjunto de datos "
        "históricos."
    )


# ============================================================
# TAB 3
# ============================================================

with tab3:

    st.header(
        "📊 Información"
    )

    st.markdown("""
    <div class="green-card">

    🎯 <b>Qué queremos construir</b>

    <br><br>

    1. Obtener automáticamente los partidos NFL.

    <br><br>

    2. Analizar cada equipo.

    <br><br>

    3. Generar nuestra propia probabilidad.

    <br><br>

    4. Obtener la cuota de la casa.

    <br><br>

    5. Convertir la cuota en probabilidad implícita.

    <br><br>

    6. Comparar ambas.

    <br><br>

    7. Mostrar únicamente las oportunidades donde
    exista una diferencia suficientemente grande.

    </div>
    """, unsafe_allow_html=True)

    st.subheader(
        "📐 Fórmula principal"
    )

    st.code(
        "EDGE = Probabilidad del modelo "
        "- Probabilidad implícita de la casa"
    )

    st.subheader(
        "Ejemplo"
    )

    st.write(
        "Modelo: 68%"
    )

    st.write(
        "Casa: -110"
    )

    st.write(
        "Probabilidad implícita: ≈52.4%"
    )

    st.write(
        "EDGE: ≈ +15.6 puntos porcentuales"
    )


# ============================================================
# PIE
# ============================================================

st.markdown("---")

st.caption(
    "Monitor NFL — herramienta experimental de análisis "
    "estadístico. Las probabilidades son estimaciones y "
    "no garantizan resultados futuros."
)
