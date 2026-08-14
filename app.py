import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from io import StringIO

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
    padding-bottom: 3rem;
}

h1, h2, h3 {
    color: #f5f5f5;
}

.team-card {
    background: #15161d;
    border: 1px solid #30323b;
    border-radius: 18px;
    padding: 25px;
    margin-bottom: 20px;
}

.info-box {
    background: #1d314b;
    border-radius: 14px;
    padding: 22px;
    margin: 15px 0;
    color: #64a9ff;
}

.warning-box {
    background: #403b20;
    border: 1px solid #857525;
    border-radius: 16px;
    padding: 25px;
    margin: 20px 0;
    color: #fff7bf;
}

.error-box {
    background: #402126;
    border-radius: 16px;
    padding: 25px;
    margin: 20px 0;
    color: #ff8585;
}

.success-box {
    background: #173626;
    border-radius: 16px;
    padding: 25px;
    margin: 20px 0;
    color: #8ff0b0;
}

.probability {
    font-size: 45px;
    font-weight: 600;
    color: #ffffff;
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

st.subheader("Modelo propio — análisis NFL automático")


# ============================================================
# FUNCIONES
# ============================================================

@st.cache_data(ttl=300)
def descargar_calendario():

    """
    Descarga el calendario desde nflverse.

    NO usamos ESPN.
    """

    urls = [

        # Fuente principal
        "https://github.com/nflverse/nfldata/raw/refs/heads/master/data/games.csv",

        # Alternativa
        "https://raw.githubusercontent.com/nflverse/nfldata/master/data/games.csv"
    ]

    ultimo_error = None

    for url in urls:

        try:

            response = requests.get(
                url,
                timeout=20,
                headers={
                    "User-Agent": "Mozilla/5.0"
                }
            )

            response.raise_for_status()

            df = pd.read_csv(
                StringIO(response.text)
            )

            if len(df) > 0:
                return df, None

        except Exception as e:

            ultimo_error = str(e)

    return None, ultimo_error


# ============================================================
# NORMALIZAR DATOS
# ============================================================

def preparar_calendario(df):

    df = df.copy()

    # --------------------------------------------------------
    # Normalizar nombres
    # --------------------------------------------------------

    df.columns = [
        str(c).strip().lower()
        for c in df.columns
    ]

    # --------------------------------------------------------
    # Buscar columna de fecha
    # --------------------------------------------------------

    posibles_fechas = [
        "gameday",
        "game_date",
        "date"
    ]

    fecha_col = None

    for c in posibles_fechas:

        if c in df.columns:
            fecha_col = c
            break

    if fecha_col is None:
        raise ValueError(
            "No se encontró una columna de fecha."
        )

    df["fecha"] = pd.to_datetime(
        df[fecha_col],
        errors="coerce"
    )

    # --------------------------------------------------------
    # Normalizar temporada
    # --------------------------------------------------------

    if "season" in df.columns:

        df["season"] = pd.to_numeric(
            df["season"],
            errors="coerce"
        )

    # --------------------------------------------------------
    # Tipo de partido
    # --------------------------------------------------------

    if "game_type" in df.columns:

        df["game_type"] = (
            df["game_type"]
            .astype(str)
            .str.upper()
            .str.strip()
        )

    return df


# ============================================================
# BUSCAR PARTIDOS
# ============================================================

def buscar_partidos(df):

    hoy = datetime.now(
        ZoneInfo("America/Chicago")
    ).date()

    fecha_final = hoy + timedelta(days=7)

    # --------------------------------------------------------
    # Temporada 2026
    # --------------------------------------------------------

    if "season" in df.columns:

        df = df[
            df["season"] == 2026
        ].copy()

    # --------------------------------------------------------
    # Pretemporada
    # --------------------------------------------------------

    if "game_type" in df.columns:

        # Intentamos primero PRE
        pre = df[
            df["game_type"].isin(
                ["PRE", "PRESEASON"]
            )
        ].copy()

        # Si existen partidos PRE, usamos esos
        if len(pre) > 0:
            df = pre

    # --------------------------------------------------------
    # Fechas
    # --------------------------------------------------------

    df = df[
        (df["fecha"].dt.date >= hoy) &
        (df["fecha"].dt.date <= fecha_final)
    ].copy()

    # --------------------------------------------------------
    # Ordenar
    # --------------------------------------------------------

    if len(df) > 0:

        df = df.sort_values(
            ["fecha"]
        )

    return df


# ============================================================
# HORA DALLAS
# ============================================================

def convertir_hora_dallas(row):

    # Si tenemos gametime
    if "gametime" in row.index:

        hora = row["gametime"]

        if pd.notna(hora):

            try:

                hora_texto = str(hora)

                if len(hora_texto) >= 5:

                    dt = datetime.strptime(
                        hora_texto[:5],
                        "%H:%M"
                    )

                    # nflverse normalmente representa
                    # gametime en ET.
                    #
                    # Convertimos manualmente ET -> CT
                    hora_ct = dt - timedelta(
                        hours=1
                    )

                    return hora_ct.strftime(
                        "%-I:%M %p"
                    )

            except Exception:
                pass

    return "Hora no disponible"


# ============================================================
# MODELO SIMPLE
# ============================================================

def probabilidad_base():

    """
    Esta función es provisional.

    NO queremos que el calendario se mezcle
    todavía con el modelo estadístico.

    Posteriormente aquí conectaremos:

    - rendimiento ofensivo
    - rendimiento defensivo
    - QB
    - lesiones
    - turnovers
    - EPA
    - eficiencia
    - localía
    - descanso
    - matchup
    - mercado
    """

    return 50.0


def cuota_justa(probabilidad):

    if probabilidad <= 0:
        return None

    if probabilidad >= 100:
        return None

    if probabilidad == 50:
        return -100

    if probabilidad > 50:

        return round(
            -(probabilidad / (100 - probabilidad)) * 100
        )

    return round(
        ((100 - probabilidad) / probabilidad) * 100
    )


# ============================================================
# PESTAÑAS
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

    actualizar = st.button(
        "🔄 ACTUALIZAR PARTIDOS",
        use_container_width=True
    )

    if actualizar:
        st.cache_data.clear()
        st.rerun()

    # --------------------------------------------------------
    # Descargar calendario
    # --------------------------------------------------------

    datos, error = descargar_calendario()

    if datos is None:

        st.markdown(
            f"""
            <div class="error-box">
            ⚠️ No se pudo descargar el calendario NFL.
            </div>
            """,
            unsafe_allow_html=True
        )

        with st.expander("🔧 Información técnica"):

            st.write(error)

        st.stop()

    # --------------------------------------------------------
    # Preparar
    # --------------------------------------------------------

    try:

        calendario = preparar_calendario(
            datos
        )

        partidos = buscar_partidos(
            calendario
        )

    except Exception as e:

        st.markdown(
            """
            <div class="error-box">
            ⚠️ Se descargó el calendario,
            pero ocurrió un problema al procesarlo.
            </div>
            """,
            unsafe_allow_html=True
        )

        with st.expander("🔧 Información técnica"):
            st.exception(e)

        st.stop()

    # --------------------------------------------------------
    # RESULTADO
    # --------------------------------------------------------

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

        st.info(
            "Esto significa que la fuente respondió correctamente, "
            "pero no devolvió partidos compatibles con los filtros."
        )

        # Mostrar diagnóstico
        with st.expander("🔧 Información técnica"):

            st.write(
                "Filas descargadas:",
                len(datos)
            )

            if "season" in datos.columns:

                st.write(
                    "Temporadas disponibles:",
                    sorted(
                        datos["season"]
                        .dropna()
                        .unique()
                        .tolist()
                    )[-10:]
                )

            if "game_type" in datos.columns:

                st.write(
                    "Tipos de partido:",
                    sorted(
                        datos["game_type"]
                        .dropna()
                        .astype(str)
                        .unique()
                        .tolist()
                    )
                )

            st.write(
                "Columnas:",
                list(datos.columns)
            )

    else:

        st.markdown(
            f"""
            <div class="success-box">
            ✅ Se encontraron {len(partidos)}
            partidos en la fuente.
            </div>
            """,
            unsafe_allow_html=True
        )

        # ----------------------------------------------------
        # Mostrar partidos
        # ----------------------------------------------------

        for _, partido in partidos.iterrows():

            visitante = partido.get(
                "away_team",
                "VISITANTE"
            )

            local = partido.get(
                "home_team",
                "LOCAL"
            )

            fecha = partido[
                "fecha"
            ].strftime(
                "%d/%m/%Y"
            )

            hora = convertir_hora_dallas(
                partido
            )

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
            # Modelo
            # ------------------------------------------------

            col1, col2 = st.columns(2)

            prob_visitante = probabilidad_base()
            prob_local = 100 - prob_visitante

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
                    {prob_visitante:.1f}%
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                st.write(
                    f"🎯 Cuota justa: "
                    f"{cuota_justa(prob_visitante)}"
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
                    {prob_local:.1f}%
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                st.write(
                    f"🎯 Cuota justa: "
                    f"{cuota_justa(prob_local)}"
                )

            st.divider()


# ============================================================
# TAB 2 — VALIDACIÓN
# ============================================================

with tab2:

    st.header("🧪 Validación del modelo")

    st.write(
        """
        Aquí comprobaremos si las probabilidades que
        genera nuestro modelo están correctamente calibradas.
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

        No buscamos simplemente tener muchos aciertos.

        <br><br>

        Buscamos que una probabilidad del modelo
        tenga significado estadístico.

        </div>
        """,
        unsafe_allow_html=True
    )

    st.subheader(
        "📈 Ejemplo de calibración"
    )

    calibracion = pd.DataFrame({

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

    st.table(
        calibracion
    )

    st.info(
        """
        La validación histórica real se conectará
        cuando tengamos nuestro conjunto de datos
        históricos.
        """
    )


# ============================================================
# TAB 3
# ============================================================

with tab3:

    st.header("📊 Información")

    st.subheader(
        "🏈 Fuente del calendario"
    )

    st.write(
        """
        La aplicación utiliza nflverse como fuente
        para el calendario NFL.
        """
    )

    st.subheader(
        "🧠 Modelo"
    )

    st.write(
        """
        El cálculo de probabilidades que aparece actualmente
        es solamente una base temporal.

        No debe utilizarse todavía para apostar.

        El siguiente paso será conectar el calendario
        con datos históricos y construir el modelo real.
        """
    )

    st.subheader(
        "🔬 Validación"
    )

    st.write(
        """
        Antes de confiar en cualquier pick debemos comprobar:

        • precisión histórica

        • calibración

        • rendimiento por rango de probabilidad

        • rendimiento contra la cuota

        • ROI

        • drawdown

        • tamaño de muestra

        • estabilidad fuera de muestra
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
