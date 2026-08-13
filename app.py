import streamlit as st
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
    font-size: 1.3rem;
}

.card {
    padding: 25px;
    border-radius: 18px;
    background-color: #171922;
    border: 1px solid #30333d;
    margin-bottom: 20px;
}

.blue-card {
    padding: 22px;
    border-radius: 18px;
    background-color: #192c43;
    border: 1px solid #294b70;
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

.red-card {
    padding: 22px;
    border-radius: 18px;
    background-color: #402020;
    border: 1px solid #713636;
    margin-bottom: 20px;
}

.big-number {
    font-size: 3rem;
    font-weight: 700;
}

</style>
""", unsafe_allow_html=True)


# ============================================================
# FUNCIONES
# ============================================================

def encontrar_columna(df, opciones):

    columnas = {
        str(c).strip().lower(): c
        for c in df.columns
    }

    for opcion in opciones:

        opcion = opcion.lower()

        if opcion in columnas:
            return columnas[opcion]

    return None


# ============================================================
# PREPARAR DATOS
# ============================================================

def preparar_datos(df):

    # --------------------------------------------------------
    # BUSCAR COLUMNA DE PROBABILIDAD
    # --------------------------------------------------------

    col_prob = encontrar_columna(
        df,
        [
            "probabilidad",
            "prob",
            "model_probability",
            "model_prob",
            "probability",
            "predicted_probability"
        ]
    )

    # --------------------------------------------------------
    # BUSCAR COLUMNA DE RESULTADO
    # --------------------------------------------------------

    col_resultado = encontrar_columna(
        df,
        [
            "resultado",
            "result",
            "ganador",
            "win",
            "won",
            "outcome",
            "target"
        ]
    )

    if col_prob is None:
        raise ValueError(
            "No encontré una columna de probabilidad. "
            "Debe llamarse, por ejemplo, "
            "'probabilidad' o 'prob'."
        )

    if col_resultado is None:
        raise ValueError(
            "No encontré una columna de resultado. "
            "Debe llamarse, por ejemplo, "
            "'resultado' o 'result'."
        )

    datos = df.copy()

    # --------------------------------------------------------
    # CONVERTIR PROBABILIDAD
    # --------------------------------------------------------

    datos["prob_modelo"] = pd.to_numeric(
        datos[col_prob],
        errors="coerce"
    )

    # Si viene como 70 en vez de 0.70
    datos.loc[
        datos["prob_modelo"] > 1,
        "prob_modelo"
    ] = (
        datos.loc[
            datos["prob_modelo"] > 1,
            "prob_modelo"
        ] / 100
    )

    # --------------------------------------------------------
    # CONVERTIR RESULTADO
    # --------------------------------------------------------

    def convertir_resultado(valor):

        if pd.isna(valor):
            return np.nan

        if isinstance(valor, str):

            texto = valor.strip().lower()

            if texto in [
                "win",
                "won",
                "w",
                "1",
                "true",
                "yes",
                "y",
                "ganada",
                "ganado",
                "g"
            ]:
                return 1

            if texto in [
                "loss",
                "lost",
                "l",
                "0",
                "false",
                "no",
                "n",
                "perdida",
                "perdido",
                "p"
            ]:
                return 0

            return np.nan

        try:

            numero = float(valor)

            if numero == 1:
                return 1

            if numero == 0:
                return 0

        except:
            pass

        return np.nan

    datos["resultado_real"] = (
        datos[col_resultado]
        .apply(convertir_resultado)
    )

    # --------------------------------------------------------
    # LIMPIAR
    # --------------------------------------------------------

    datos = datos[
        [
            "prob_modelo",
            "resultado_real"
        ]
    ].dropna()

    datos = datos[
        (datos["prob_modelo"] >= 0) &
        (datos["prob_modelo"] <= 1)
    ]

    return datos


# ============================================================
# CREAR RANGOS DE CALIBRACIÓN
# ============================================================

def crear_calibracion(datos):

    # Rangos de probabilidad del modelo

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
        "50–54%",
        "55–59%",
        "60–64%",
        "65–69%",
        "70–74%",
        "75–79%",
        "80–84%",
        "85–89%",
        "90%+"
    ]

    datos = datos.copy()

    datos["rango"] = pd.cut(
        datos["prob_modelo"],
        bins=bins,
        labels=etiquetas,
        right=False
    )

    tabla = (
        datos
        .groupby(
            "rango",
            observed=False
        )
        .agg(
            partidos=("resultado_real", "count"),
            aciertos=("resultado_real", "sum"),
            prob_modelo_promedio=("prob_modelo", "mean"),
            acierto_real=("resultado_real", "mean")
        )
        .reset_index()
    )

    tabla["aciertos"] = (
        tabla["aciertos"]
        .fillna(0)
        .astype(int)
    )

    tabla["partidos"] = (
        tabla["partidos"]
        .fillna(0)
        .astype(int)
    )

    tabla["acierto_real"] = (
        tabla["acierto_real"]
        .fillna(0)
    )

    tabla["prob_modelo_promedio"] = (
        tabla["prob_modelo_promedio"]
        .fillna(0)
    )

    # Diferencia entre lo que decía el modelo
    # y lo que realmente ocurrió

    tabla["diferencia"] = (
        tabla["acierto_real"]
        - tabla["prob_modelo_promedio"]
    )

    return tabla


# ============================================================
# CALIBRACIÓN POR UMBRALES
# ============================================================

def crear_umbrales(datos):

    umbrales = [
        0.55,
        0.60,
        0.65,
        0.70,
        0.75,
        0.80,
        0.85,
        0.90
    ]

    resultados = []

    for umbral in umbrales:

        subset = datos[
            datos["prob_modelo"] >= umbral
        ]

        partidos = len(subset)

        if partidos == 0:
            continue

        aciertos = int(
            subset["resultado_real"].sum()
        )

        acierto_real = (
            aciertos / partidos
        )

        prob_promedio = (
            subset["prob_modelo"].mean()
        )

        diferencia = (
            acierto_real - prob_promedio
        )

        resultados.append({

            "Probabilidad mínima":
                f"{umbral:.0%}",

            "Partidos":
                partidos,

            "Aciertos":
                aciertos,

            "Acierto real":
                acierto_real,

            "Prob. promedio modelo":
                prob_promedio,

            "Diferencia":
                diferencia
        })

    return pd.DataFrame(resultados)


# ============================================================
# MÉTRICAS GENERALES
# ============================================================

def calcular_metricas(datos):

    if len(datos) == 0:

        return {
            "partidos": 0,
            "aciertos": 0,
            "acierto": 0,
            "prob_promedio": 0,
            "error": 0
        }

    partidos = len(datos)

    aciertos = int(
        datos["resultado_real"].sum()
    )

    acierto = (
        aciertos / partidos
    )

    prob_promedio = (
        datos["prob_modelo"].mean()
    )

    error = (
        acierto - prob_promedio
    )

    return {
        "partidos": partidos,
        "aciertos": aciertos,
        "acierto": acierto,
        "prob_promedio": prob_promedio,
        "error": error
    }


# ============================================================
# ENCABEZADO
# ============================================================

st.markdown(
    '<div class="title">🏈 Monitor NFL</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtitle">'
    'Modelo propio — análisis y calibración'
    '</div>',
    unsafe_allow_html=True
)

st.markdown("""
<div class="blue-card">

🧠 <b>Objetivo:</b>

Medir qué tan confiables son las probabilidades
que genera nuestro modelo y convertirlas en
probabilidades históricamente calibradas.

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

    st.header("🏈 NFL DE HOY")

    st.info(
        "Aquí posteriormente mostraremos los partidos "
        "actuales y la probabilidad generada por nuestro modelo."
    )

    st.markdown("""
    <div class="green-card">

    <b>Próximo objetivo</b><br><br>

    Para cada partido tendremos:

    <br>• Probabilidad original del modelo
    <br>• Probabilidad calibrada
    <br>• Línea/cuota de la casa
    <br>• Probabilidad implícita de la casa
    <br>• Diferencia entre nuestro modelo y la casa

    </div>
    """, unsafe_allow_html=True)


# ============================================================
# TAB 2
# ============================================================

with tab2:

    st.header(
        "🧪 ¿Qué tan bueno es nuestro modelo?"
    )

    st.write(
        "Aquí medimos si las probabilidades que nuestro "
        "modelo genera antes de cada partido realmente "
        "corresponden con lo que ocurrió."
    )

    st.markdown("""
    <div class="yellow-card">

    🎯 <b>Importante:</b>

    El objetivo NO es demostrar que el modelo dice
    90% y acierta 90%.

    El objetivo es descubrir qué porcentaje real
    corresponde a cada nivel de confianza.

    </div>
    """, unsafe_allow_html=True)

    # --------------------------------------------------------
    # CARGAR CSV
    # --------------------------------------------------------

    st.subheader(
        "📂 Datos históricos"
    )

    archivo = st.file_uploader(
        "Sube el CSV histórico del modelo",
        type=["csv"],
        key="calibracion_csv"
    )

    st.caption(
        "El CSV debe contener una columna de probabilidad "
        "y otra con el resultado real."
    )

    if archivo is not None:

        try:

            df_original = pd.read_csv(
                archivo
            )

            datos = preparar_datos(
                df_original
            )

            st.success(
                f"Se analizaron {len(datos):,} partidos válidos."
            )

            # ------------------------------------------------
            # MÉTRICAS
            # ------------------------------------------------

            metricas = calcular_metricas(
                datos
            )

            st.divider()

            c1, c2, c3, c4 = st.columns(4)

            with c1:

                st.metric(
                    "🏈 Partidos",
                    f'{metricas["partidos"]:,}'
                )

            with c2:

                st.metric(
                    "✅ Aciertos",
                    f'{metricas["aciertos"]:,}'
                )

            with c3:

                st.metric(
                    "🎯 Acierto real",
                    f'{metricas["acierto"]:.1%}'
                )

            with c4:

                st.metric(
                    "🧠 Prob. promedio",
                    f'{metricas["prob_promedio"]:.1%}'
                )

            # ------------------------------------------------
            # ERROR GENERAL
            # ------------------------------------------------

            diferencia = metricas["error"]

            if abs(diferencia) <= 0.03:

                st.markdown("""
                <div class="green-card">

                🟢 <b>El modelo está relativamente bien calibrado
                en promedio.</b>

                </div>
                """, unsafe_allow_html=True)

            elif diferencia < 0:

                st.markdown(f"""
                <div class="red-card">

                🔴 <b>El modelo está sobreestimando su confianza.</b>

                <br><br>

                En promedio el modelo dice
                <b>{metricas["prob_promedio"]:.1%}</b>,
                pero el resultado real es
                <b>{metricas["acierto"]:.1%}</b>.

                <br><br>

                Diferencia:
                <b>{diferencia:.1%}</b>

                </div>
                """, unsafe_allow_html=True)

            else:

                st.markdown(f"""
                <div class="yellow-card">

                🟡 <b>El modelo está subestimando ligeramente
                sus probabilidades.</b>

                <br><br>

                Diferencia:
                <b>+{diferencia:.1%}</b>

                </div>
                """, unsafe_allow_html=True)

            # ------------------------------------------------
            # TABLA PRINCIPAL
            # ------------------------------------------------

            st.subheader(
                "🎯 Probabilidad del modelo vs realidad"
            )

            calibracion = crear_calibracion(
                datos
            )

            tabla_visual = calibracion.copy()

            tabla_visual[
                "Prob. promedio modelo"
            ] = (
                tabla_visual[
                    "prob_modelo_promedio"
                ].map(
                    lambda x: f"{x:.1%}"
                    if x > 0
                    else "—"
                )
            )

            tabla_visual[
                "Acierto real"
            ] = (
                tabla_visual[
                    "acierto_real"
                ].map(
                    lambda x: f"{x:.1%}"
                    if x > 0
                    else "—"
                )
            )

            tabla_visual[
                "Diferencia"
            ] = (
                tabla_visual[
                    "diferencia"
                ].map(
                    lambda x: f"{x:+.1%}"
                    if x != 0
                    else "—"
                )
            )

            tabla_visual = tabla_visual[
                [
                    "rango",
                    "partidos",
                    "aciertos",
                    "Prob. promedio modelo",
                    "Acierto real",
                    "Diferencia"
                ]
            ]

            tabla_visual.columns = [
                "Rango modelo",
                "Partidos",
                "Aciertos",
                "Prob. promedio modelo",
                "Acierto real",
                "Diferencia"
            ]

            st.dataframe(
                tabla_visual,
                use_container_width=True,
                hide_index=True
            )

            # ------------------------------------------------
            # UMBRALES
            # ------------------------------------------------

            st.subheader(
                "📊 Rendimiento por nivel de confianza"
            )

            st.write(
                "Esta tabla muestra qué ocurre cuando exigimos "
                "una probabilidad mínima determinada."
            )

            umbrales = crear_umbrales(
                datos
            )

            if not umbrales.empty:

                umbrales_visual = umbrales.copy()

                umbrales_visual[
                    "Acierto real"
                ] = (
                    umbrales_visual[
                        "Acierto real"
                    ].map(
                        lambda x: f"{x:.1%}"
                    )
                )

                umbrales_visual[
                    "Prob. promedio modelo"
                ] = (
                    umbrales_visual[
                        "Prob. promedio modelo"
                    ].map(
                        lambda x: f"{x:.1%}"
                    )
                )

                umbrales_visual[
                    "Diferencia"
                ] = (
                    umbrales_visual[
                        "Diferencia"
                    ].map(
                        lambda x: f"{x:+.1%}"
                    )
                )

                st.dataframe(
                    umbrales_visual,
                    use_container_width=True,
                    hide_index=True
                )

            # ------------------------------------------------
            # MEJOR ZONA
            # ------------------------------------------------

            st.subheader(
                "⭐ Zona de mayor rendimiento"
            )

            tabla_con_datos = calibracion[
                calibracion["partidos"] >= 30
            ].copy()

            if not tabla_con_datos.empty:

                mejor = tabla_con_datos.loc[
                    tabla_con_datos[
                        "acierto_real"
                    ].idxmax()
                ]

                st.markdown(f"""
                <div class="green-card">

                ⭐ <b>Mejor rango observado:</b>
                {mejor["rango"]}

                <br><br>

                Partidos:
                <b>{int(mejor["partidos"])}</b>

                <br>

                Probabilidad promedio del modelo:
                <b>{mejor["prob_modelo_promedio"]:.1%}</b>

                <br>

                Acierto real:
                <b>{mejor["acierto_real"]:.1%}</b>

                <br>

                Diferencia:
                <b>{mejor["diferencia"]:+.1%}</b>

                </div>
                """, unsafe_allow_html=True)

            # ------------------------------------------------
            # CONCLUSIÓN
            # ------------------------------------------------

            st.subheader(
                "🧠 Conclusión"
            )

            st.write(
                "La finalidad de esta sección es descubrir "
                "la relación histórica entre la confianza "
                "del modelo y el resultado real."
            )

            st.write(
                "Una vez tengamos suficiente información, "
                "podremos utilizar esa relación para obtener "
                "una probabilidad calibrada."
            )

            st.markdown("""
            <div class="blue-card">

            🔥 <b>Siguiente etapa:</b>

            <br><br>

            Probabilidad original del modelo

            <br>⬇️

            Calibración histórica

            <br>⬇️

            <b>Probabilidad real estimada</b>

            <br>⬇️

            Comparación contra la probabilidad implícita
            de la casa.

            </div>
            """, unsafe_allow_html=True)

        except Exception as e:

            st.error(
                "No se pudo procesar el archivo."
            )

            st.exception(e)


# ============================================================
# TAB 3
# ============================================================

with tab3:

    st.header(
        "📊 Información del modelo"
    )

    st.markdown("""
    <div class="card">

    <h3>¿Qué estamos intentando conseguir?</h3>

    <p>
    No buscamos simplemente que el modelo tenga un
    porcentaje alto de aciertos.
    </p>

    <p>
    Buscamos que cuando diga 70%, 80% o 90%,
    esas cifras tengan un significado estadístico real.
    </p>

    <p>
    Después podremos comparar esa probabilidad
    calibrada contra la probabilidad implícita
    de una casa de apuestas.
    </p>

    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="blue-card">

    <b>Ejemplo:</b>

    <br><br>

    El modelo dice: <b>85%</b>

    <br><br>

    Históricamente descubrimos que partidos
    de esa zona ganan: <b>68%</b>

    <br><br>

    Entonces nuestra probabilidad calibrada
    será aproximadamente: <b>68%</b>

    </div>
    """, unsafe_allow_html=True)

    st.warning(
        "Una muestra histórica no garantiza resultados futuros. "
        "La calibración debe validarse con datos suficientes."
    )


# ============================================================
# FINAL
# ============================================================

st.markdown("---")

st.caption(
    "Monitor NFL — herramienta de análisis estadístico. "
    "No garantiza resultados futuros."
)
