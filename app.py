import streamlit as st
import pandas as pd
import numpy as np
import requests
import math
from datetime import datetime, timezone

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
    max-width: 1200px;
}

.title {
    font-size: 3rem;
    font-weight: 800;
}

.subtitle {
    color: #9ca3af;
    font-size: 1.25rem;
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

.red-card {
    padding: 25px;
    border-radius: 18px;
    background-color: #3b2024;
    border: 1px solid #71353c;
    margin-bottom: 20px;
}

.team-name {
    font-size: 2rem;
    font-weight: 800;
}

.prob {
    font-size: 3.5rem;
    font-weight: 800;
}

.value-positive {
    color: #4ade80;
    font-size: 1.6rem;
    font-weight: 800;
}

.value-negative {
    color: #f87171;
    font-size: 1.4rem;
    font-weight: 700;
}

.small-gray {
    color: #9ca3af;
}

</style>
""", unsafe_allow_html=True)


# ============================================================
# CONFIG API
# ============================================================

ESPN_BASE = (
    "https://site.api.espn.com/apis/site/v2/sports/"
    "football/nfl"
)

SCOREBOARD_URL = ESPN_BASE + "/scoreboard"

# ============================================================
# REQUEST HELPER
# ============================================================

@st.cache_data(ttl=300)
def get_json(url, params=None):

    try:

        response = requests.get(
            url,
            params=params,
            timeout=15,
            headers={
                "User-Agent": "Mozilla/5.0"
            }
        )

        response.raise_for_status()

        return response.json()

    except Exception as e:

        return None


# ============================================================
# NFL DE HOY
# ============================================================

@st.cache_data(ttl=300)
def obtener_partidos_hoy():

    hoy = datetime.now(timezone.utc).strftime("%Y%m%d")

    data = get_json(
        SCOREBOARD_URL,
        {
            "dates": hoy,
            "limit": 100
        }
    )

    if not data:
        return []

    partidos = []

    for event in data.get("events", []):

        try:

            competition = event["competitions"][0]

            competitors = competition["competitors"]

            if len(competitors) < 2:
                continue

            home = None
            away = None

            for team in competitors:

                if team.get("homeAway") == "home":
                    home = team

                elif team.get("homeAway") == "away":
                    away = team

            if home is None or away is None:
                continue

            partidos.append({
                "id": event.get("id"),
                "name": event.get("name"),
                "date": event.get("date"),
                "home": {
                    "id": home["team"]["id"],
                    "name": home["team"]["displayName"],
                    "abbrev": home["team"].get("abbreviation")
                },
                "away": {
                    "id": away["team"]["id"],
                    "name": away["team"]["displayName"],
                    "abbrev": away["team"].get("abbreviation")
                }
            })

        except Exception:
            continue

    return partidos


# ============================================================
# DATOS DE EQUIPO
# ============================================================

@st.cache_data(ttl=1800)
def obtener_datos_equipo(team_id):

    url = f"{ESPN_BASE}/teams/{team_id}"

    data = get_json(url)

    if not data:
        return None

    team = data.get("team", data)

    resultado = {
        "id": team_id,
        "name": team.get("displayName", "Unknown"),
        "record": 0.50,
        "wins": 0,
        "losses": 0,
        "points_for": 22.0,
        "points_against": 22.0,
        "point_diff": 0.0
    }

    # --------------------------------------------------------
    # RECORD
    # --------------------------------------------------------

    try:

        records = team.get("record", {}).get("items", [])

        for record in records:

            if record.get("type") in ["total", "ytd"]:

                summary = record.get("summary", "")

                if "-" in summary:

                    parts = summary.split("-")

                    wins = int(parts[0])
                    losses = int(parts[1])

                    resultado["wins"] = wins
                    resultado["losses"] = losses

                    if wins + losses > 0:

                        resultado["record"] = (
                            wins / (wins + losses)
                        )

                    break

    except Exception:
        pass

    # --------------------------------------------------------
    # ESTADÍSTICAS
    # --------------------------------------------------------

    stats = team.get("statistics", [])

    for stat in stats:

        try:

            name = str(stat.get("name", "")).lower()

            value = float(stat.get("value"))

            if "pointsfor" in name or name == "pointsfor":
                resultado["points_for"] = value

            elif "pointsagainst" in name or name == "pointsagainst":
                resultado["points_against"] = value

        except Exception:
            continue

    resultado["point_diff"] = (
        resultado["points_for"]
        - resultado["points_against"]
    )

    return resultado


# ============================================================
# DATOS DE STANDINGS
# ============================================================

@st.cache_data(ttl=1800)
def obtener_standings():

    url = (
        "https://site.api.espn.com/apis/site/v2/"
        "sports/football/nfl/standings"
    )

    data = get_json(url)

    standings = {}

    if not data:
        return standings

    def recorrer(obj):

        if isinstance(obj, dict):

            # ------------------------------------------------
            # Encontrar entradas de equipo
            # ------------------------------------------------

            if "team" in obj and isinstance(obj["team"], dict):

                team = obj["team"]

                team_id = team.get("id")

                if team_id:

                    info = {
                        "record": 0.50,
                        "wins": 0,
                        "losses": 0,
                        "point_diff": 0
                    }

                    for stat in obj.get("stats", []):

                        name = str(
                            stat.get("name", "")
                        ).lower()

                        value = stat.get("value")

                        try:
                            value = float(value)
                        except:
                            continue

                        if name in [
                            "wins",
                            "win"
                        ]:
                            info["wins"] = value

                        elif name in [
                            "losses",
                            "loss"
                        ]:
                            info["losses"] = value

                        elif "differential" in name:

                            info["point_diff"] = value

                    total = (
                        info["wins"]
                        + info["losses"]
                    )

                    if total > 0:

                        info["record"] = (
                            info["wins"] / total
                        )

                    standings[str(team_id)] = info

            for value in obj.values():
                recorrer(value)

        elif isinstance(obj, list):

            for item in obj:
                recorrer(item)

    recorrer(data)

    return standings


# ============================================================
# MODELO
# ============================================================

def sigmoid(x):

    return 1 / (1 + math.exp(-x))


def calcular_probabilidades(
    home,
    away,
    standings
):

    # --------------------------------------------------------
    # Buscar standings
    # --------------------------------------------------------

    h = standings.get(
        str(home["id"]),
        {}
    )

    a = standings.get(
        str(away["id"]),
        {}
    )

    # --------------------------------------------------------
    # Récord
    # --------------------------------------------------------

    home_record = h.get(
        "record",
        home.get("record", 0.50)
    )

    away_record = a.get(
        "record",
        away.get("record", 0.50)
    )

    # --------------------------------------------------------
    # Diferencia de puntos
    # --------------------------------------------------------

    home_pd = h.get(
        "point_diff",
        home.get("point_diff", 0)
    )

    away_pd = a.get(
        "point_diff",
        away.get("point_diff", 0)
    )

    # --------------------------------------------------------
    # Diferencia de fuerza
    # --------------------------------------------------------

    record_difference = (
        home_record - away_record
    )

    point_difference = (
        home_pd - away_pd
    )

    # --------------------------------------------------------
    # MODELO
    #
    # Localía:
    # aproximadamente +2.5 puntos
    #
    # Récord:
    # peso importante
    #
    # Diferencia de puntos:
    # peso secundario
    # --------------------------------------------------------

    score = (
        2.5
        + (record_difference * 7.0)
        + (point_difference * 0.08)
    )

    home_probability = sigmoid(
        score / 4.5
    )

    away_probability = (
        1 - home_probability
    )

    # --------------------------------------------------------
    # Limitar probabilidades absurdas
    # --------------------------------------------------------

    home_probability = min(
        max(home_probability, 0.05),
        0.95
    )

    away_probability = (
        1 - home_probability
    )

    return {
        "home_probability": home_probability,
        "away_probability": away_probability,
        "record_difference": record_difference,
        "point_difference": point_difference
    }


# ============================================================
# CUOTA AMERICANA
# ============================================================

def american_to_implied(odds):

    try:

        odds = float(odds)

        if odds > 0:

            return 100 / (
                odds + 100
            )

        return abs(odds) / (
            abs(odds) + 100
        )

    except:

        return None


def probability_to_fair_odds(prob):

    if prob <= 0 or prob >= 1:
        return None

    if prob >= 0.50:

        return -round(
            (prob / (1 - prob)) * 100
        )

    else:

        return round(
            ((1 - prob) / prob) * 100
        )


# ============================================================
# ENCONTRAR ODDS EN EVENTO
# ============================================================

def extraer_odds_evento(event_id):

    url = (
        f"{ESPN_BASE}/summary"
    )

    data = get_json(
        url,
        {
            "event": event_id
        }
    )

    if not data:
        return []

    odds_result = []

    # --------------------------------------------------------
    # Buscar recursivamente cualquier objeto "odds"
    # --------------------------------------------------------

    def recorrer(obj):

        if isinstance(obj, dict):

            if "odds" in obj:

                odds = obj["odds"]

                if isinstance(odds, list):

                    for odd in odds:

                        if isinstance(odd, dict):

                            odds_result.append(
                                odd
                            )

            for value in obj.values():
                recorrer(value)

        elif isinstance(obj, list):

            for item in obj:
                recorrer(item)

    recorrer(data)

    return odds_result


# ============================================================
# CARD DE PARTIDO
# ============================================================

def mostrar_partido(partido, standings):

    home_id = partido["home"]["id"]
    away_id = partido["away"]["id"]

    home_data = obtener_datos_equipo(
        home_id
    )

    away_data = obtener_datos_equipo(
        away_id
    )

    if home_data is None:
        home_data = {}

    if away_data is None:
        away_data = {}

    model = calcular_probabilidades(
        {
            **partido["home"],
            **home_data
        },
        {
            **partido["away"],
            **away_data
        },
        standings
    )

    home_prob = model[
        "home_probability"
    ]

    away_prob = model[
        "away_probability"
    ]

    # ========================================================
    # PARTIDO
    # ========================================================

    st.markdown("---")

    st.markdown(
        f"""
        <div class="team-name">
        🏈 {partido["away"]["name"]} @ {partido["home"]["name"]}
        </div>
        """,
        unsafe_allow_html=True
    )

    st.write("")

    col1, col2 = st.columns(2)

    # ========================================================
    # VISITANTE
    # ========================================================

    with col1:

        st.markdown(
            f"### ✈️ {partido['away']['name']}"
        )

        st.caption(
            "Probabilidad de nuestro modelo"
        )

        st.markdown(
            f"""
            <div class="prob">
            {away_prob:.1%}
            </div>
            """,
            unsafe_allow_html=True
        )

        fair_away = probability_to_fair_odds(
            away_prob
        )

        if fair_away is not None:

            st.write(
                f"**Cuota justa:** {fair_away:+d}"
            )

        away_record = away_data.get(
            "record",
            0.50
        )

        st.caption(
            f"Récord usado: {away_record:.1%}"
        )

    # ========================================================
    # LOCAL
    # ========================================================

    with col2:

        st.markdown(
            f"### 🏠 {partido['home']['name']}"
        )

        st.caption(
            "Probabilidad de nuestro modelo"
        )

        st.markdown(
            f"""
            <div class="prob">
            {home_prob:.1%}
            </div>
            """,
            unsafe_allow_html=True
        )

        fair_home = probability_to_fair_odds(
            home_prob
        )

        if fair_home is not None:

            st.write(
                f"**Cuota justa:** {fair_home:+d}"
            )

        home_record = home_data.get(
            "record",
            0.50
        )

        st.caption(
            f"Récord usado: {home_record:.1%}"
        )

    # ========================================================
    # DATOS DEL MODELO
    # ========================================================

    st.markdown(
        f"""
        <div class="blue-card">

        <b>🧠 Componentes utilizados</b><br><br>

        Localía: +2.5 puntos<br>

        Diferencia de récord:
        {model["record_difference"]:+.3f}<br>

        Diferencia de rendimiento:
        {model["point_difference"]:+.2f}

        </div>
        """,
        unsafe_allow_html=True
    )

    # ========================================================
    # ODDS DE LA CASA
    # ========================================================

    odds = extraer_odds_evento(
        partido["id"]
    )

    if odds:

        st.markdown(
            """
            <div class="yellow-card">
            <h3>🏦 Cuotas disponibles</h3>
            """,
            unsafe_allow_html=True
        )

        for odd in odds[:5]:

            provider = odd.get(
                "provider",
                {}
            )

            provider_name = provider.get(
                "name",
                "Casa"
            )

            details = odd.get(
                "details",
                ""
            )

            if details:

                st.write(
                    f"**Casa:** {provider_name}"
                )

                st.write(
                    f"**Línea:** {details}"
                )

        st.markdown(
            "</div>",
            unsafe_allow_html=True
        )

    else:

        st.info(
            "La fuente no proporcionó cuotas "
            "para este partido."
        )

    # ========================================================
    # INTERPRETACIÓN
    # ========================================================

    if home_prob >= 0.60:

        st.success(
            f"🟢 Nuestro modelo favorece a "
            f"{partido['home']['name']}."
        )

    elif away_prob >= 0.60:

        st.success(
            f"🟢 Nuestro modelo favorece a "
            f"{partido['away']['name']}."
        )

    else:

        st.warning(
            "🟡 El modelo considera este partido "
            "demasiado parejo."
        )


# ============================================================
# ENCABEZADO
# ============================================================

st.markdown(
    '<div class="title">🏈 Monitor NFL</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtitle">'
    'Modelo propio — probabilidades independientes'
    '</div>',
    unsafe_allow_html=True
)

st.markdown(
    """
    <div class="blue-card">

    🧠 <b>Objetivo del sistema</b><br><br>

    Calcular nuestra propia probabilidad de ganar
    y después compararla contra la probabilidad
    implícita de la casa de apuestas.

    <br><br>

    <b>La cuota NO se utiliza para fabricar nuestra
    probabilidad.</b>

    </div>
    """,
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
# TAB 1 — NFL DE HOY
# ============================================================

with tab1:

    st.header("🏈 NFL DE HOY")

    if st.button(
        "🔄 ACTUALIZAR PARTIDOS",
        use_container_width=True
    ):

        st.cache_data.clear()

        st.rerun()

    partidos = obtener_partidos_hoy()

    standings = obtener_standings()

    # --------------------------------------------------------
    # ERROR API
    # --------------------------------------------------------

    if partidos is None:

        st.error(
            "No fue posible obtener los partidos."
        )

    # --------------------------------------------------------
    # SIN PARTIDOS
    # --------------------------------------------------------

    elif len(partidos) == 0:

        st.info(
            "No hay partidos NFL programados para hoy."
        )

        st.markdown(
            """
            <div class="green-card">

            📅 El sistema consulta automáticamente
            el calendario NFL.

            <br><br>

            Cuando existan partidos programados,
            aparecerán aquí sin necesidad de subir
            ningún CSV.

            </div>
            """,
            unsafe_allow_html=True
        )

    # --------------------------------------------------------
    # PARTIDOS
    # --------------------------------------------------------

    else:

        st.success(
            f"🏈 {len(partidos)} partido(s) encontrado(s)."
        )

        for partido in partidos:

            mostrar_partido(
                partido,
                standings
            )


# ============================================================
# TAB 2 — VALIDACIÓN
# ============================================================

with tab2:

    st.header(
        "🧪 Validación del modelo"
    )

    st.write(
        """
        Esta sección sirve para comprobar si las
        probabilidades que genera el modelo realmente
        corresponden con los resultados observados.
        """
    )

    st.markdown(
        """
        <div class="yellow-card">

        🎯 <b>Lo importante</b><br><br>

        Si nuestro modelo dice 70%, queremos comprobar
        históricamente si aproximadamente 70 de cada
        100 partidos terminan ganándose.

        <br><br>

        No buscamos simplemente una tasa de aciertos alta.
        Buscamos <b>probabilidades bien calibradas</b>.

        </div>
        """,
        unsafe_allow_html=True
    )

    st.subheader(
        "📂 Datos históricos"
    )

    archivo = st.file_uploader(
        "CSV opcional para validar el modelo",
        type=["csv"]
    )

    if archivo is not None:

        try:

            df = pd.read_csv(
                archivo
            )

            st.success(
                f"{len(df)} registros cargados."
            )

            # ------------------------------------------------
            # DETECTAR PROBABILIDAD
            # ------------------------------------------------

            prob_col = None

            for col in [
                "probabilidad",
                "prob",
                "model_probability",
                "probability"
            ]:

                if col in df.columns:

                    prob_col = col
                    break

            # ------------------------------------------------
            # DETECTAR RESULTADO
            # ------------------------------------------------

            result_col = None

            for col in [
                "resultado",
                "result",
                "ganador",
                "win"
            ]:

                if col in df.columns:

                    result_col = col
                    break

            if (
                prob_col is None
                or result_col is None
            ):

                st.error(
                    "El CSV necesita una columna de "
                    "probabilidad y otra de resultado."
                )

            else:

                datos = df[
                    [
                        prob_col,
                        result_col
                    ]
                ].copy()

                datos.columns = [
                    "probabilidad",
                    "resultado"
                ]

                datos["probabilidad"] = pd.to_numeric(
                    datos["probabilidad"],
                    errors="coerce"
                )

                datos["resultado"] = pd.to_numeric(
                    datos["resultado"],
                    errors="coerce"
                )

                datos = datos.dropna()

                datos.loc[
                    datos["probabilidad"] > 1,
                    "probabilidad"
                ] /= 100

                # ------------------------------------------------
                # TABLA DE CALIBRACIÓN
                # ------------------------------------------------

                filas = []

                for threshold in [
                    0.55,
                    0.60,
                    0.65,
                    0.70,
                    0.75,
                    0.80,
                    0.85,
                    0.90
                ]:

                    subset = datos[
                        datos["probabilidad"]
                        >= threshold
                    ]

                    if len(subset) == 0:
                        continue

                    real = subset[
                        "resultado"
                    ].mean()

                    promedio = subset[
                        "probabilidad"
                    ].mean()

                    diferencia = (
                        real - promedio
                    )

                    filas.append(
                        {
                            "Probabilidad mínima":
                                f"{threshold:.0%}",

                            "Partidos":
                                len(subset),

                            "Aciertos":
                                int(
                                    subset[
                                        "resultado"
                                    ].sum()
                                ),

                            "Acierto real":
                                f"{real:.1%}",

                            "Prob. promedio modelo":
                                f"{promedio:.1%}",

                            "Diferencia":
                                f"{diferencia:+.1%}"
                        }
                    )

                if filas:

                    tabla = pd.DataFrame(
                        filas
                    )

                    st.subheader(
                        "🎯 Probabilidad vs realidad"
                    )

                    st.dataframe(
                        tabla,
                        use_container_width=True,
                        hide_index=True
                    )

                    # ------------------------------------------------
                    # RESUMEN
                    # ------------------------------------------------

                    mae = np.mean(
                        np.abs(
                            datos["probabilidad"]
                            - datos["resultado"]
                        )
                    )

                    brier = np.mean(
                        (
                            datos["probabilidad"]
                            - datos["resultado"]
                        ) ** 2
                    )

                    c1, c2 = st.columns(2)

                    with c1:

                        st.metric(
                            "Error absoluto medio",
                            f"{mae:.3%}"
                        )

                    with c2:

                        st.metric(
                            "Brier Score",
                            f"{brier:.4f}"
                        )

        except Exception as e:

            st.error(
                "Error leyendo el CSV."
            )

            st.exception(e)


# ============================================================
# TAB 3
# ============================================================

with tab3:

    st.header(
        "📊 Información del modelo"
    )

    st.markdown(
        """
        <div class="green-card">

        <h3>🧠 ¿Qué estamos intentando conseguir?</h3>

        <br>

        No queremos copiar la probabilidad de la casa.

        <br><br>

        Queremos producir una estimación independiente:

        <br><br>

        <b>Nuestro modelo → Probabilidad propia</b>

        <br><br>

        Después:

        <br>

        <b>Casa → Probabilidad implícita</b>

        <br><br>

        Y finalmente:

        <br>

        <b>
        Nuestra probabilidad − Probabilidad de la casa
        </b>

        <br><br>

        Esa diferencia es la que posteriormente
        utilizaremos para investigar posibles situaciones
        de VALUE.

        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown(
        """
        <div class="blue-card">

        <h3>📐 Variables actuales</h3>

        • Localía<br>
        • Récord de los equipos<br>
        • Diferencia de rendimiento<br>
        • Fuerza relativa<br>
        • Probabilidad matemática independiente

        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown(
        """
        <div class="yellow-card">

        ⚠️ <b>IMPORTANTE</b>

        <br><br>

        Esta primera versión es la base del modelo.
        No debemos asumir que ya es rentable.

        <br><br>

        Primero necesitamos comprobarlo con una muestra
        histórica suficientemente grande y después mejorar
        las variables que realmente aporten capacidad
        predictiva.

        </div>
        """,
        unsafe_allow_html=True
    )


# ============================================================
# FOOTER
# ============================================================

st.markdown("---")

st.caption(
    "Monitor NFL — herramienta experimental de análisis "
    "estadístico. Las probabilidades son estimaciones y "
    "no garantizan resultados futuros."
)
