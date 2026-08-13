import streamlit as st

st.set_page_config(
    page_title="Monitor 60%",
    page_icon="🎯",
    layout="centered"
)

st.title("🎯 Monitor 60%")
st.write("Monitor sencillo de probabilidades para apuestas deportivas")

st.divider()

st.subheader("Analizar apuesta")

equipo = st.text_input(
    "Partido",
    placeholder="Ej: Lakers vs Celtics"
)

mercado = st.text_input(
    "Mercado",
    placeholder="Ej: Lakers gana"
)

cuota = st.number_input(
    "Cuota decimal",
    min_value=1.01,
    value=2.00,
    step=0.01
)

st.subheader("Estadísticas básicas")

col1, col2 = st.columns(2)

with col1:
    porcentaje_temporada = st.number_input(
        "Victorias temporada (%)",
        min_value=0,
        max_value=100,
        value=60,
        step=1
    )

with col2:
    victorias_recientes = st.number_input(
        "Victorias últimos 5",
        min_value=0,
        max_value=5,
        value=3,
        step=1
    )

local = st.checkbox("Juega como local")

st.divider()

if st.button("ANALIZAR APUESTA", use_container_width=True):

    # Convertimos los últimos 5 partidos a porcentaje
    forma_reciente = (victorias_recientes / 5) * 100

    # Probabilidad base:
    # 60% estadísticas de temporada
    # 40% forma reciente
    probabilidad = (
        porcentaje_temporada * 0.60
        + forma_reciente * 0.40
    )

    # Pequeño ajuste por jugar como local
    if local:
        probabilidad += 3

    # Limitamos la probabilidad
    probabilidad = max(1, min(probabilidad, 99))

    # Probabilidad implícita de la cuota
    probabilidad_implicita = (1 / cuota) * 100

    # Ventaja sobre la cuota
    ventaja = probabilidad - probabilidad_implicita

    st.divider()

    if ventaja >= 8:
        st.success("🟢 BUENA OPORTUNIDAD")
    elif ventaja >= 3:
        st.warning("🟡 VENTAJA PEQUEÑA")
    else:
        st.error("🔴 NO APOSTAR")

    st.metric(
        "Probabilidad estimada",
        f"{probabilidad:.1f}%"
    )

    st.metric(
        "Probabilidad implícita de la cuota",
        f"{probabilidad_implicita:.1f}%"
    )

    st.metric(
        "Ventaja estimada",
        f"{ventaja:+.1f}%"
    )

    st.write("---")

    st.write("### Resumen")

    if equipo:
        st.write(f"**Partido:** {equipo}")

    if mercado:
        st.write(f"**Mercado:** {mercado}")

    st.write(f"**Cuota:** {cuota:.2f}")

    st.write(
        "La probabilidad es una estimación estadística simple, "
        "no una garantía de resultado."
    )
