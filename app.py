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

equipo = st.text_input("Partido", placeholder="Ej: Lakers vs Celtics")
mercado = st.text_input("Mercado", placeholder="Ej: Lakers gana")

probabilidad = st.slider(
    "Probabilidad estimada",
    min_value=0,
    max_value=100,
    value=60,
    step=1
)

cuota = st.number_input(
    "Cuota decimal",
    min_value=1.01,
    value=2.00,
    step=0.01
)

if st.button("ANALIZAR APUESTA", use_container_width=True):

    if probabilidad >= 60:
        st.success("🟢 APUESTA PERMITIDA")
    else:
        st.error("🔴 NO APOSTAR")

    st.metric("Probabilidad", f"{probabilidad}%")

    probabilidad_implicita = (1 / cuota) * 100

    st.metric(
        "Probabilidad implícita de la cuota",
        f"{probabilidad_implicita:.1f}%"
    )

    ventaja = probabilidad - probabilidad_implicita

    st.metric(
        "Ventaja estimada",
        f"{ventaja:+.1f}%"
    )
