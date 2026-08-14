import streamlit as st
import pandas as pd
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

h1, h2, h3 {
    color: #f5f5f5;
}

.team-card {
    background: #15161d;
    border: 1px solid #30323b;
    border-radius: 18px;
    padding: 25px;
    margin: 20px 0;
}

.info-box {
    background: #1d314b;
    border-radius: 14px;
    padding: 22px;
    margin: 15px 0;
}

.warning-box {
    background: #403b20;
    border: 1px solid #857525;
    border-radius: 16px;
    padding: 25px;
    margin: 20px 0;
}

.error-box {
    background: #402126;
    border-radius: 16px;
    padding: 25px;
    margin: 20px 0;
}

.success-box {
    background: #173626;
    border-radius: 16px;
    padding: 25px;
    margin: 20px 0;
}

.probability {
    font-size: 46px;
    font-weight: 600;
    color: white;
}

.small-text {
    color: #a5a7b0;
}

</style>
""", unsafe_allow_html=True)


# ============================================================
# TÍTULO
# ============================================================

st.title("🏈 Monitor NFL")

st.subheader(
    "Modelo propio — análisis NFL automático"
)


# ============================================================
# CALENDARIO NFL 2026
#
# Esta lista se utiliza únicamente para el calendario.
# Los datos históricos y resultados se conectarán después.
# ============================================================

CALENDARIO_2026 = [

    # ========================================================
    # PRETEMPORADA - SEMANA 1
    # ========================================================

    {
        "fecha": "2026-08-13",
        "hora_ct": "18:00",
        "visitante": "Green Bay Packers",
        "local": "Pittsburgh Steelers",
        "tipo": "PRE",
    },

    {
        "fecha": "2026-08-13",
        "hora_ct": "18:00",
        "visitante": "Detroit Lions",
        "local": "Cincinnati Bengals",
        "tipo": "PRE",
    },

    {
        "fecha": "2026-08-13",
        "hora_ct": "18:00",
        "visitante": "Indianapolis Colts",
        "local": "New England Patriots",
        "tipo": "PRE",
    },

    {
        "fecha": "2026-08-13",
        "hora_ct": "18:00",
        "visitante": "Los Angeles Chargers",
        "local": "Houston Texans",
        "tipo": "PRE",
    },

    {
        "fecha": "2026-08-13",
        "hora_ct": "20:00",
        "visitante": "Arizona Cardinals",
        "local": "Las Vegas Raiders",
        "tipo": "PRE",
    },

    {
        "fecha": "2026-08-13",
        "hora_ct": "20:00",
        "visitante": "Tennessee Titans",
        "local": "San Francisco 49ers",
        "tipo": "PRE",
    },

    {
        "fecha": "2026-08-14",
        "hora_ct": "18:00",
        "visitante": "Denver Broncos",
        "local": "Atlanta Falcons",
        "tipo": "PRE",
    },

    {
        "fecha": "2026-08-14",
        "hora_ct": "18:00",
        "visitante": "Philadelphia Eagles",
        "local": "Baltimore Ravens",
        "tipo": "PRE",
    },

    {
        "fecha": "2026-08-14",
        "hora_ct": "18:00",
        "visitante": "Carolina Panthers",
        "local": "Buffalo Bills",
        "tipo": "PRE",
    },

    {
        "fecha": "2026-08-14",
        "hora_ct": "18:00",
        "visitante": "Jacksonville Jaguars",
        "local": "New Orleans Saints",
        "tipo": "PRE",
    },

    {
        "fecha": "2026-08-14",
        "hora_ct": "18:00",
        "visitante": "Minnesota Vikings",
        "local": "New York Giants",
        "tipo": "PRE",
    },

    {
        "fecha": "2026-08-14",
        "hora_ct": "18:00",
        "visitante": "Tampa Bay Buccaneers",
        "local": "New York Jets",
        "tipo": "PRE",
    },

    {
        "fecha": "2026-08-14",
        "hora_ct": "20:00",
        "visitante": "Dallas Cowboys",
        "local": "Seattle Seahawks",
        "tipo": "PRE",
    },

    {
        "fecha": "2026-08-14",
        "hora_ct": "20:00",
        "visitante": "Miami Dolphins",
        "local": "Washington Commanders",
        "tipo": "PRE",
    },


    # ========================================================
    # PRETEMPORADA - SEMANA 2
    # ========================================================

    {
        "fecha": "2026-08-20",
        "hora_ct": "18:00",
        "visitante": "Las Vegas Raiders",
        "local": "Houston Texans",
        "tipo": "PRE",
    },

    {
        "fecha": "2026-08-21",
        "hora_ct": "18:00",
        "visitante": "Dallas Cowboys",
        "local": "Arizona Cardinals",
        "tipo": "PRE",
    },

    {
        "fecha": "2026-08-21",
        "hora_ct": "18:00",
        "visitante": "Chicago Bears",
        "local": "Cincinnati Bengals",
        "tipo": "PRE",
    },

    {
        "fecha": "2026-08-21",
        "hora_ct": "18:00",
        "visitante": "Buffalo Bills",
        "local": "Cleveland Browns",
        "tipo": "PRE",
    },

    {
        "fecha": "2026-08-21",
        "hora_ct": "18:00",
        "visitante": "Green Bay Packers",
        "local": "Denver Broncos",
        "tipo": "PRE",
    },

    {
        "fecha": "2026-08-21",
        "hora_ct": "18:00",
        "visitante": "Washington Commanders",
        "local": "Detroit Lions",
        "tipo": "PRE",
    },

    {
        "fecha": "2026-08-21",
        "hora_ct": "18:00",
        "visitante": "Atlanta Falcons",
        "local": "Indianapolis Colts",
        "tipo": "PRE",
    },

    {
        "fecha": "2026-08-21",
        "hora_ct": "18:00",
        "visitante": "Carolina Panthers",
        "local": "Jacksonville Jaguars",
        "tipo": "PRE",
    },

    {
        "fecha": "2026-08-21",
        "hora_ct": "18:00",
        "visitante": "San Francisco 49ers",
        "local": "Los Angeles Chargers",
        "tipo": "PRE",
    },

    {
        "fecha": "2026-08-21",
        "hora_ct": "18:00",
        "visitante": "New Orleans Saints",
        "local": "Los Angeles Rams",
        "tipo": "PRE",
    },

    {
        "fecha": "2026-08-21",
        "hora_ct": "18:00",
        "visitante": "New York Giants",
        "local": "Miami Dolphins",
        "tipo": "PRE",
    },

    {
        "fecha": "2026-08-21",
        "hora_ct": "18:00",
        "visitante": "New York Jets",
        "local": "Pittsburgh Steelers",
        "tipo": "PRE",
    },

    {
        "fecha": "2026-08-21",
        "hora_ct": "18:00",
        "visitante": "Philadelphia Eagles",
        "local": "New England Patriots",
        "tipo": "PRE",
    },

    {
        "fecha": "2026-08-21",
        "hora_ct": "18:00",
        "visitante": "Kansas City Chiefs",
        "local": "Tampa Bay Buccaneers",
        "tipo": "PRE",
    },

    {
        "fecha": "2026-08-22",
        "hora_ct": "18:00",
        "visitante": "Carolina Panthers",
        "local": "Jacksonville Jaguars",
        "tipo": "PRE",
    },

    {
        "fecha": "2026-08-23",
        "hora_ct": "18:00",
        "visitante": "Seattle Seahawks",
        "local": "Tennessee Titans",
        "tipo": "PRE",
    },
]


# ============================================================
# DATAFRAME
# ============================================================

def obtener_calendario():

    df = pd.DataFrame(
        CALENDARIO_2026
    )

    df["fecha"] = pd.to_datetime(
        df["fecha"]
    ).dt.date

    return df


# ============================================================
# PARTIDOS PRÓXIMOS
# ============================================================

def obtener_proximos_partidos():

    df = obtener_calendario()

    ahora = datetime.now(
        TZ_DALLAS
    )

    hoy = ahora.date()

    limite = hoy + timedelta(
        days=7
    )

    df = df[
        (df["fecha"] >= hoy) &
        (df["fecha"] <= limite)
    ].copy()

    return df


# ============================================================
# MODELO
# ============================================================

def calcular_probabilidad(visitante, local):

    # --------------------------------------------------------
    # TEMPORAL
    #
    # Aquí después conectaremos el modelo verdadero.
    # --------------------------------------------------------

    prob_visitante = 50.0

    prob_local = 50.0

    return prob_visitante, prob_local


# ============================================================
# CUOTA JUSTA
# ============================================================

def cuota_justa(prob):

    if prob <= 0 or prob >= 100:
        return None

    if prob == 50:
        return -100

    if prob > 50:

        return round(
            -(prob / (100 - prob)) * 100
        )

    return round(
        ((100 - prob) / prob) * 100
    )


# ============================================================
# TABS
# ============================================================

tab1, tab2, tab3 = st.tabs(
    [
        "🏈 NFL DE HOY",
        "🧪 VALIDACIÓN DEL MODELO",
        "📊 INFORMACIÓN",
    ]
)


# ============================================================
# TAB NFL
# ============================================================

with tab1:

    st.header("🏈 NFL DE HOY")

    if st.button(
        "🔄 ACTUALIZAR PARTIDOS",
        use_container_width=True
    ):

        st.rerun()

    partidos = obtener_proximos_partidos()

    # ========================================================
    # SIN PARTIDOS
    # ========================================================

    if len(partidos) == 0:

        st.markdown(
            """
            <div class="warning-box">

            ⚠️ No se encontraron partidos NFL
            en los próximos 7 días.

            </div>
            """,
            unsafe_allow_html=True
        )

    # ========================================================
    # PARTIDOS
    # ========================================================

    else:

        st.markdown(
            f"""
            <div class="success-box">

            ✅ {len(partidos)}
            partidos encontrados en el calendario.

            </div>
            """,
            unsafe_allow_html=True
        )

        for _, partido in partidos.iterrows():

            visitante = partido[
                "visitante"
            ]

            local = partido[
                "local"
            ]

            fecha = partido[
                "fecha"
            ].strftime(
                "%d/%m/%Y"
            )

            hora = partido[
                "hora_ct"
            ]

            st.markdown(
                f"""
                <div class="team-card">

                <h2>
                🏈 {visitante}
                <br>
                @ {local}
                </h2>

                <p class="small-text">
                📅 {fecha}
                </p>

                <p class="small-text">
                🕐 Hora Dallas: {hora}
                </p>

                </div>
                """,
                unsafe_allow_html=True
            )

            # ------------------------------------------------
            # PROBABILIDADES
            # ------------------------------------------------

            prob_v, prob_l = calcular_probabilidad(
                visitante,
                local
            )

            col1, col2 = st.columns(2)

            with col1:

                st.subheader(
                    f"✈️ {visitante}"
                )

                st.write(
                    "Probabilidad modelo"
                )

                st.markdown(
                    f"""
                    <div class="probability">
                    {prob_v:.1f}%
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                st.write(
                    f"🎯 Cuota justa: "
                    f"{cuota_justa(prob_v)}"
                )

            with col2:

                st.subheader(
                    f"🏠 {local}"
                )

                st.write(
                    "Probabilidad modelo"
                )

                st.markdown(
                    f"""
                    <div class="probability">
                    {prob_l:.1f}%
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                st.write(
                    f"🎯 Cuota justa: "
                    f"{cuota_justa(prob_l)}"
                )

            st.divider()


# ============================================================
# VALIDACIÓN
# ============================================================

with tab2:

    st.header(
        "🧪 Validación del modelo"
    )

    st.write(
        """
        Aquí comprobaremos si las probabilidades que genera
        nuestro modelo realmente corresponden con los resultados
        observados.
        """
    )

    st.markdown(
        """
        <div class="warning-box">

        🎯 <b>Lo que queremos comprobar</b>

        <br><br>

        Si nuestro modelo dice 70%, queremos comprobar
        históricamente qué porcentaje de esos partidos
        realmente termina ganándose.

        <br><br>

        No buscamos simplemente una tasa de aciertos alta.

        <br><br>

        Buscamos probabilidades correctamente calibradas.

        </div>
        """,
        unsafe_allow_html=True
    )

    st.subheader(
        "📈 Ejemplo de calibración"
    )

    tabla = pd.DataFrame(
        {
            "Probabilidad modelo": [
                "55%",
                "60%",
                "65%",
                "70%",
                "75%",
                "80%",
                "85%",
                "90%",
            ],
            "Objetivo real": [
                "≈55%",
                "≈60%",
                "≈65%",
                "≈70%",
                "≈75%",
                "≈80%",
                "≈85%",
                "≈90%",
            ],
        }
    )

    st.table(tabla)

    st.info(
        """
        La validación histórica real se conectará
        cuando tengamos nuestro conjunto de datos históricos.
        """)


# ============================================================
# INFORMACIÓN
# ============================================================

with tab3:

    st.header(
        "📊 Información"
    )

    st.subheader(
        "📅 Calendario"
    )

    st.write(
        """
        El calendario se mantiene separado del modelo
        estadístico para evitar que una falla de una API
        afecte el análisis.
        """
    )

    st.subheader(
        "🧠 Modelo"
    )

    st.write(
        """
        Las probabilidades actuales de 50/50 son solamente
        una prueba de funcionamiento.

        NO son todavía los picks reales.
        """
    )

    st.subheader(
        "🔬 Próxima etapa"
    )

    st.write(
        """
        Una vez comprobado el calendario, conectaremos:

        • resultados históricos

        • estadísticas ofensivas

        • estadísticas defensivas

        • QB

        • lesiones

        • localía

        • descanso

        • eficiencia

        • matchup

        • cuotas de apuestas

        • probabilidad implícita

        • edge

        • ROI histórico

        • validación fuera de muestra
        """
    )

    st.divider()

    st.caption(
        """
        Monitor NFL — herramienta experimental de análisis
        estadístico. Las probabilidades son estimaciones y no
        garantizan resultados futuros.
        """
    )
