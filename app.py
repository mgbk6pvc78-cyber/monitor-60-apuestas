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

    .green-card {
        padding: 20px;
        border-radius: 18px;
        background-color: #193426;
        border: 1px solid #356b4c;
        margin-bottom: 20px;
    }

    .yellow-card {
        padding: 20px;
        border-radius: 18px;
        background-color: #40371d;
        border: 1px solid #6c5c2a;
        margin-bottom: 20px;
    }

    .blue-card {
        padding: 20px;
        border-radius: 18px;
        background-color: #192c43;
        border: 1px solid #294b70;
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

def american_to_decimal(odds):
    """
    Convierte cuota americana a decimal.
    Ejemplo:
    -110 -> 1.9091
    +150 -> 2.50
    """
    try:
        odds = float(odds)

        if odds > 0:
            return 1 + odds / 100

        return 1 + 100 / abs(odds)

    except:
        return np.nan


def american_to_implied_probability(odds):
    """
    Convierte moneyline americana a probabilidad implícita.
    """
    try:
        odds = float(odds)

        if odds > 0:
            return 100 / (odds + 100)

        return abs(odds) / (abs(odds) + 100)

    except:
        return np.nan


def calcular_resultado_apuesta(odds, stake):
    """
    Calcula ganancia neta de una apuesta ganadora.
    """
    decimal = american_to_decimal(odds)

    if pd.isna(decimal):
        return np.nan

    return stake * (decimal - 1)


def ejecutar_backtest(
    df,
    prob_minima=0.70,
    apuesta=10.0
):

    resultados = []

    for _, row in df.iterrows():

        # ----------------------------------------------------
        # Probabilidad del modelo
        # ----------------------------------------------------

        if "probabilidad" in row:
            prob = row["probabilidad"]

        elif "prob" in row:
            prob = row["prob"]

        elif "model_probability" in row:
            prob = row["model_probability"]

        else:
            continue

        try:
            prob = float(prob)

            # Si viene como 70 en vez de 0.70
            if prob > 1:
                prob = prob / 100

        except:
            continue

        # ----------------------------------------------------
        # Filtrar por probabilidad mínima
        # ----------------------------------------------------

        if prob < prob_minima:
            continue

        # ----------------------------------------------------
        # Resultado real
        # ----------------------------------------------------

        if "resultado" in row:
            resultado = row["resultado"]

        elif "result" in row:
            resultado = row["result"]

        elif "ganador" in row:
            resultado = row["ganador"]

        else:
            continue

        # ----------------------------------------------------
        # Convertir resultado a WIN/LOSS
        # ----------------------------------------------------

        if isinstance(resultado, str):

            resultado_texto = resultado.strip().lower()

            if resultado_texto in [
                "win",
                "won",
                "w",
                "1",
                "true",
                "ganada",
                "ganó",
                "g"
            ]:
                win = True

            elif resultado_texto in [
                "loss",
                "lost",
                "l",
                "0",
                "false",
                "perdida",
                "p"
            ]:
                win = False

            else:
                continue

        else:

            try:
                win = float(resultado) == 1
            except:
                continue

        # ----------------------------------------------------
        # Cuota
        # ----------------------------------------------------

        if "moneyline" in row:
            odds = row["moneyline"]

        elif "odds" in row:
            odds = row["odds"]

        elif "cuota" in row:
            odds = row["cuota"]

        else:
            continue

        try:
            odds = float(odds)
        except:
            continue

        # ----------------------------------------------------
        # Resultado financiero
        # ----------------------------------------------------

        if win:

            ganancia = calcular_resultado_apuesta(
                odds,
                apuesta
            )

        else:

            ganancia = -apuesta

        resultados.append({
            "probabilidad": prob,
            "odds": odds,
            "win": win,
            "apuesta": apuesta,
            "ganancia": ganancia
        })

    return pd.DataFrame(resultados)


def resumen_backtest(df_resultados):

    if df_resultados.empty:

        return {
            "apuestas": 0,
            "aciertos": 0,
            "perdidas": 0,
            "win_rate": 0,
            "total_apostado": 0,
            "ganancia": 0,
            "roi": 0,
            "retorno": 0
        }

    apuestas = len(df_resultados)

    aciertos = int(
        df_resultados["win"].sum()
    )

    perdidas = apuestas - aciertos

    total_apostado = df_resultados["apuesta"].sum()

    ganancia = df_resultados["ganancia"].sum()

    retorno = total_apostado + ganancia

    win_rate = (
        aciertos / apuestas
        if apuestas > 0
        else 0
    )

    roi = (
        ganancia / total_apostado
        if total_apostado > 0
        else 0
    )

    return {
        "apuestas": apuestas,
        "aciertos": aciertos,
        "perdidas": perdidas,
        "win_rate": win_rate,
        "total_apostado": total_apostado,
        "ganancia": ganancia,
        "roi": roi,
        "retorno": retorno
    }


# ============================================================
# ENCABEZADO
# ============================================================

st.markdown(
    '<div class="title">🏈 Monitor NFL</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtitle">Modelo propio — análisis y backtest</div>',
    unsafe_allow_html=True
)

st.markdown("""
<div class="blue-card">
🧠 El backtest utiliza únicamente información disponible
ANTES de cada partido.
</div>
""", unsafe_allow_html=True)


# ============================================================
# TABS
# ============================================================

tab1, tab2, tab3 = st.tabs([
    "🏈 NFL DE HOY",
    "📈 BACKTEST ROI",
    "📊 DATOS"
])


# ============================================================
# TAB 1
# ============================================================

with tab1:

    st.header("🔎 NFL DE HOY")

    st.info(
        "Aquí aparecerán los partidos y las probabilidades "
        "generadas por el modelo."
    )

    st.button(
        "🔄 ACTUALIZAR PARTIDOS",
        use_container_width=True
    )

    st.markdown("""
    <div class="green-card">
    <b>Modelo NFL</b><br>
    El sistema está preparado para recibir las probabilidades
    generadas por tu modelo.
    </div>
    """, unsafe_allow_html=True)

    st.write("")


# ============================================================
# TAB 2 — BACKTEST
# ============================================================

with tab2:

    st.header("📈 Backtest realista")

    st.write(
        "Probamos el modelo partido por partido sin utilizar "
        "información futura."
    )

    st.markdown("""
    <div class="yellow-card">
    💰 Necesitamos cuotas históricas para calcular el dinero
    ganado o perdido.
    </div>
    """, unsafe_allow_html=True)

    # --------------------------------------------------------
    # CONTROLES
    # --------------------------------------------------------

    col1, col2 = st.columns(2)

    with col1:

        prob_minima = st.number_input(
            "Probabilidad mínima",
            min_value=0.50,
            max_value=0.99,
            value=0.70,
            step=0.01,
            format="%.2f"
        )

    with col2:

        apuesta = st.number_input(
            "Apuesta por partido ($)",
            min_value=1.0,
            max_value=10000.0,
            value=10.0,
            step=1.0,
            format="%.2f"
        )

    st.divider()

    # --------------------------------------------------------
    # CARGAR DATOS
    # --------------------------------------------------------

    st.subheader("📂 Datos para el backtest")

    archivo = st.file_uploader(
        "Sube un CSV con los datos históricos",
        type=["csv"]
    )

    st.caption(
        "El CSV debe contener como mínimo columnas equivalentes "
        "a probabilidad, resultado y moneyline/cuota."
    )

    # --------------------------------------------------------
    # EJECUTAR
    # --------------------------------------------------------

    ejecutar = st.button(
        "🚀 EJECUTAR BACKTEST",
        use_container_width=True
    )

    if ejecutar:

        if archivo is None:

            st.warning(
                "Primero debes subir el CSV histórico."
            )

        else:

            try:

                df = pd.read_csv(archivo)

                st.success(
                    f"Archivo cargado: {len(df)} registros."
                )

                resultados = ejecutar_backtest(
                    df,
                    prob_minima=prob_minima,
                    apuesta=apuesta
                )

                resumen = resumen_backtest(
                    resultados
                )

                # ------------------------------------------------
                # RESULTADOS
                # ------------------------------------------------

                st.markdown("---")

                st.subheader("🏆 RESULTADO")

                c1, c2, c3 = st.columns(3)

                with c1:

                    st.metric(
                        "🎯 Apuestas",
                        resumen["apuestas"]
                    )

                with c2:

                    st.metric(
                        "✅ Aciertos",
                        resumen["aciertos"]
                    )

                with c3:

                    st.metric(
                        "❌ Pérdidas",
                        resumen["perdidas"]
                    )

                c4, c5, c6 = st.columns(3)

                with c4:

                    st.metric(
                        "📈 Win Rate",
                        f'{resumen["win_rate"]:.1%}'
                    )

                with c5:

                    st.metric(
                        "💵 Total apostado",
                        f'${resumen["total_apostado"]:,.2f}'
                    )

                with c6:

                    st.metric(
                        "💰 Ganancia/Pérdida",
                        f'${resumen["ganancia"]:,.2f}'
                    )

                c7, c8 = st.columns(2)

                with c7:

                    st.metric(
                        "📊 ROI",
                        f'{resumen["roi"]:.2%}'
                    )

                with c8:

                    st.metric(
                        "🏦 Retorno",
                        f'${resumen["retorno"]:,.2f}'
                    )

                # ------------------------------------------------
                # TABLA
                # ------------------------------------------------

                st.subheader(
                    "📋 Apuestas realizadas"
                )

                if not resultados.empty:

                    tabla = resultados.copy()

                    tabla["probabilidad"] = (
                        tabla["probabilidad"] * 100
                    ).round(1)

                    tabla["ganancia"] = (
                        tabla["ganancia"]
                        .round(2)
                    )

                    tabla["apuesta"] = (
                        tabla["apuesta"]
                        .round(2)
                    )

                    tabla["resultado"] = np.where(
                        tabla["win"],
                        "✅ WIN",
                        "❌ LOSS"
                    )

                    tabla = tabla[
                        [
                            "probabilidad",
                            "odds",
                            "resultado",
                            "apuesta",
                            "ganancia"
                        ]
                    ]

                    tabla.columns = [
                        "Probabilidad %",
                        "Moneyline",
                        "Resultado",
                        "Apuesta",
                        "Ganancia/Pérdida"
                    ]

                    st.dataframe(
                        tabla,
                        use_container_width=True
                    )

                else:

                    st.warning(
                        "No se encontraron apuestas que "
                        "cumplan la probabilidad mínima."
                    )

            except Exception as e:

                st.error(
                    "Ocurrió un error al procesar el archivo."
                )

                st.exception(e)


# ============================================================
# TAB 3 — DATOS
# ============================================================

with tab3:

    st.header("📊 Datos")

    st.write(
        "Utiliza esta sección para revisar los datos "
        "históricos que vas a utilizar."
    )

    archivo_datos = st.file_uploader(
        "Subir CSV para revisar",
        type=["csv"],
        key="datos_csv"
    )

    if archivo_datos is not None:

        try:

            datos = pd.read_csv(
                archivo_datos
            )

            st.success(
                f"{len(datos)} registros cargados."
            )

            st.dataframe(
                datos,
                use_container_width=True
            )

            st.subheader("Columnas detectadas")

            st.write(
                list(datos.columns)
            )

        except Exception as e:

            st.error(
                "No se pudo leer el CSV."
            )

            st.exception(e)


# ============================================================
# INFORMACIÓN
# ============================================================

st.markdown("---")

st.caption(
    "⚠️ Este sistema es una herramienta de análisis "
    "estadístico. Los resultados históricos no garantizan "
    "resultados futuros."
)
