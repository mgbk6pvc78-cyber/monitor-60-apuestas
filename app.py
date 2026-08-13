import streamlit as st
import requests
from datetime import date

st.set_page_config(
    page_title="Monitor 60%",
    page_icon="🎯",
    layout="centered"
)

# =========================
# CONFIGURACIÓN
# =========================

API_KEY = st.secrets.get("BALLDONTLIE_API_KEY", "")

st.title("🎯 Monitor 60%")
st.caption("Scanner sencillo de oportunidades deportivas")

st.divider()

# =========================
# SELECCIÓN DE DEPORTE
# =========================

deporte = st.selectbox(
    "Selecciona el deporte",
    [
        "🏀 NBA",
        "⚽ Soccer",
        "🎾 Tennis",
        "⚾ MLB",
        "🏈 NFL",
        "🔥 Todos"
    ]
)

st.write("")

# =========================
# FILTRO DE PROBABILIDAD
# =========================

min_probabilidad = st.slider(
    "Probabilidad mínima",
    min_value=60,
    max_value=80,
    value=60,
    step=1
)

st.caption(
    f"Solo mostraremos oportunidades con una probabilidad de "
    f"{min_probabilidad}% o superior."
)

st.divider()

# =========================
# FUNCIÓN PARA NBA
# =========================

def obtener_partidos_nba():
    if not API_KEY:
        return None, "No se encontró la API Key."

    url = "https://api.balldontlie.io/v1/games"

    headers = {
        "Authorization": API_KEY
    }

    params = {
        "dates[]": str(date.today())
    }

    try:
        respuesta = requests.get(
            url,
            headers=headers,
            params=params,
            timeout=10
        )

        if respuesta.status_code != 200:
            return None, f"Error de API: {respuesta.status_code}"

        datos = respuesta.json()

        return datos.get("data", []), None

    except Exception as e:
        return None, f"Error de conexión: {e}"


# =========================
# BOTÓN DE ESCANEO
# =========================

if st.button(
    "🔎 ESCANEAR HOY",
    use_container_width=True
):

    st.divider()

    st.subheader(
        f"🏆 Mejores oportunidades — {deporte}"
    )

    # -------------------------
    # NBA
    # -------------------------

    if deporte == "🏀 NBA":

        partidos, error = obtener_partidos_nba()

        if error:
            st.error(error)

        elif not partidos:
            st.info(
                "No hay partidos NBA disponibles para hoy."
            )

        else:

            st.success(
                f"Se encontraron {len(partidos)} partidos."
            )

            st.write("")

            for partido in partidos[:3]:

                visitante = partido["visitor_team"]["full_name"]
                local = partido["home_team"]["full_name"]

                hora = partido.get("status", "")

                st.markdown(
                    f"### 🏀 {visitante} vs {local}"
                )

                st.write(
                    f"Estado / hora: **{hora}**"
                )

                st.info(
                    "⏳ Analizando estadísticas..."
                )

                st.divider()

    # -------------------------
    # OTROS DEPORTES
    # -------------------------

    else:

        st.info(
            f"🔧 El scanner de {deporte} será conectado "
            "en la siguiente etapa."
        )

        st.write(
            "Primero estamos probando el sistema con NBA."
        )

# =========================
# INFORMACIÓN
# =========================

st.divider()

st.caption(
    "El Monitor 60% busca oportunidades con probabilidad "
    "mínima de 60%. Una probabilidad estimada no garantiza "
    "el resultado de una apuesta."
)
