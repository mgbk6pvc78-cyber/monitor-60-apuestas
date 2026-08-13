import streamlit as st
import pandas as pd
import numpy as np
import requests
from datetime import datetime

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

.red-card {
    padding: 25px;
    border-radius: 18px;
    background-color: #402126;
    border: 1px solid #71343d;
    margin-bottom: 20px;
}

.big-number {
    font-size: 3rem;
    font-weight: 700;
}

</style>
""", unsafe_allow_html=True)


# ============================================================
# CONSTANTES
# ============================================================

ESPN_SCOREBOARD = (
    "https://site.api.espn.com/apis/site/v2/sports/"
    "football/nfl/scoreboard"
)

ESPN_STANDINGS = (
    "https://site.api.espn.com/apis/v2/sports/"
    "football/leagues/nfl/standings"
)


# ============================================================
# FUNCIONES DE INTERNET
# ============================================================

@st.cache_data(ttl=300)
def obtener_partidos(fecha=None):

    try:

        params = {}

        if fecha:
            params["dates"] = fecha

        response = requests.get(
            ESPN_SCOREBOARD,
            params=params,
            timeout=15
        )

        response.raise_for_status()

        data = response.json()

        return data.get("events", [])

    except Exception as e:

        st.error(
            f"No se pudieron obtener los partidos: {e}"
        )

        return []


@st.cache_data(ttl=3600)
def obtener_records_2025():

    try:

        response = requests.get(
            ESPN_STANDINGS,
            params={"season": 2025},
            timeout=15
        )

        response.raise_for_status()

        data = response.json()

        records = {}

        def recorrer_grupos(obj):

            if isinstance(obj, dict):

                entries = obj.get("standings", {}).get(
                    "entries", []
                )

                for entry in entries:

                    team = entry.get("team", {})

                    nombre = team.get("displayName")

                    if not nombre:
                        continue

                    wins = None
                    losses = None

                    for stat in entry.get(
                        "stats", []
                    ):

                        nombre_stat = stat.get(
                            "name",
                            ""
                        )

                        if nombre_stat == "wins":
                            wins = float(
                                stat.get("value", 0)
                            )

                        elif nombre_stat == "losses":
                            losses = float(
                                stat.get("value", 0)
                            )

                    if wins is not None and losses is not None:

                        total = wins + losses

                        if total > 0:

                            records[nombre] = {
                                "wins": wins,
                                "losses": losses,
                                "win_pct": wins / total
                            }

                for value in obj.values():

                    if isinstance(value, (dict, list)):

                        recorrer_grupos(value)

            elif isinstance(obj, list):

                for item in obj:

                    recorrer_grupos(item)

        recorrer_grupos(data)

        return records

    except Exception:

        return {}


# ============================================================
# NORMALIZAR NOMBRES
# ============================================================

def normalizar_nombre(nombre):

    nombre = nombre.lower().strip()

    reemplazos = {
        "los angeles rams": "los angeles rams",
        "la rams": "los angeles rams",
        "los angeles chargers": "los angeles chargers",
        "la chargers": "los angeles chargers",
        "new england patriots": "new england patriots",
        "new york giants": "new york giants",
        "new york jets": "new york jets",
        "san francisco 49ers": "san francisco 49ers",
        "tampa bay buccaneers": "tampa bay buccaneers",
        "kansas city chiefs": "kansas city chiefs",
        "las vegas raiders": "las vegas raiders",
        "green bay packers": "green bay packers",
        "pittsburgh steelers": "pittsburgh steelers",
        "indianapolis colts": "indianapolis colts",
        "tennessee titans": "tennessee titans",
        "arizona cardinals": "arizona cardinals",
        "detroit lions": "detroit lions",
        "cincinnati bengals": "cincinnati bengals",
        "houston texans": "houston texans",
        "dallas cowboys": "dallas cowboys",
        "seattle seahawks": "seattle seahawks",
        "miami dolphins": "miami dolphins",
        "washington commanders": "washington commanders",
        "atlanta falcons": "atlanta falcons",
        "denver broncos": "denver broncos",
        "baltimore ravens": "baltimore ravens",
        "philadelphia eagles": "philadelphia eagles",
        "chicago bears": "chicago bears",
        "cleveland browns": "cleveland browns",
        "jacksonville jaguars": "jacksonville jaguars",
        "minnesota vikings": "minnesota vikings",
        "new orleans saints": "new orleans saints",
        "carolina panthers": "carolina panthers",
        "buffalo bills": "buffalo bills"
    }

    return reemplazos.get(
        nombre,
        nombre
    )


# ============================================================
# EXTRAER EQUIPOS
# ============================================================

def obtener_equipos_evento(evento):

    try:

        competencia = evento["competitions"][0]

        competidores = competencia["competitors"]

        home = None
        away = None

        for equipo in competidores:

            info = equipo.get("team", {})

            nombre = info.get(
                "displayName",
                "Desconocido"
            )

            if equipo.get("homeAway") == "home":

                home = nombre

            else:

                away = nombre

        return home, away

    except:

        return None, None


# ============================================================
# EXTRAER CUOTAS
# ============================================================

def obtener_odds_evento(evento):

    try:

        competencia = evento["competitions"][0]

        odds = competencia.get(
            "odds",
            []
        )

        if not odds:
            return None

        odd = odds[0]

        return {
            "provider": odd.get(
                "provider",
                {}
            ).get(
                "name",
                "Casa"
            ),

            "spread": odd.get(
                "spread"
            ),

            "overUnder": odd.get(
                "overUnder"
            ),

            "details": odd.get(
                "details"
            )
        }

    except:

        return None


# ============================================================
# MODELO BASE
# ============================================================

def calcular_probabilidad_modelo(
    home,
    away,
    records
):

    home_key = normalizar_nombre(home)
    away_key = normalizar_nombre(away)

    home_data = records.get(
        home_key
    )

    away_data = records.get(
        away_key
    )

    # --------------------------------------------------------
    # Si tenemos records reales
    # --------------------------------------------------------

    if home_data and away_data:

        home_pct = home_data["win_pct"]
        away_pct = away_data["win_pct"]

        # Ventaja de local
        ventaja_local = 0.035

        diferencia = (
            home_pct
            - away_pct
            + ventaja_local
        )

        prob_home = (
            0.50
            + diferencia * 0.75
        )

        prob_home = max(
            0.15,
            min(
                0.85,
                prob_home
            )
        )

    else:

        # ----------------------------------------------------
        # Si todavía no encontramos los records
        # ----------------------------------------------------

        prob_home = 0.50

    prob_away = 1 - prob_home

    return prob_home, prob_away


# ============================================================
# CONVERTIR PROBABILIDAD A CUOTA AMERICANA
# ============================================================

def probabilidad_a_americana(prob):

    if prob <= 0 or prob >= 1:

        return None

    if prob >= 0.50:

        return round(
            -100 * prob / (1 - prob)
        )

    else:

        return round(
            100 * (1 - prob) / prob
        )


# ============================================================
# CONVERTIR CUOTA AMERICANA A PROBABILIDAD
# ============================================================

def americana_a_probabilidad(odds):

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


# ============================================================
# ENCABEZADO
# ============================================================

st.markdown(
    '<div class="title">🏈 Monitor NFL</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtitle">'
    'Modelo propio — análisis automático'
    '</div>',
    unsafe_allow_html=True
)

st.markdown("""
<div class="blue-card">

🧠 <b>El sistema obtiene automáticamente los partidos.</b>

<br><br>

No necesitas subir un CSV para consultar los partidos
actuales.

<br><br>

El modelo utiliza información histórica disponible
para generar una probabilidad estimada.

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
# NFL DE HOY
# ============================================================

with tab1:

    st.header("🏈 NFL DE HOY")

    ahora = datetime.now()

    fecha_actual = ahora.strftime(
        "%Y%m%d"
    )

    col1, col2 = st.columns([3, 1])

    with col1:

        st.write(
            "Partidos obtenidos automáticamente."
        )

    with col2:

        actualizar = st.button(
            "🔄 ACTUALIZAR",
            use_container_width=True
        )

        if actualizar:

            st.cache_data.clear()

            st.rerun()

    eventos = obtener_partidos(
        fecha_actual
    )

    records = obtener_records_2025()

    if not eventos:

        st.warning(
            "No se encontraron partidos para hoy."
        )

        st.info(
            "También puedes consultar los próximos "
            "partidos de pretemporada."
        )

        eventos = obtener_partidos()

    # --------------------------------------------------------
    # PARTIDOS
    # --------------------------------------------------------

    if eventos:

        st.success(
            f"🏈 {len(eventos)} partido(s) encontrado(s)"
        )

        for evento in eventos:

            home, away = obtener_equipos_evento(
                evento
            )

            if not home or not away:

                continue

            prob_home, prob_away = (
                calcular_probabilidad_modelo(
                    home,
                    away,
                    records
                )
            )

            odds = obtener_odds_evento(
                evento
            )

            # ------------------------------------------------
            # TARJETA
            # ------------------------------------------------

            st.markdown("---")

            st.subheader(
                f"🏈 {away} @ {home}"
            )

            col1, col2 = st.columns(2)

            with col1:

                st.markdown(
                    f"### 🏠 {home}"
                )

                st.metric(
                    "Probabilidad modelo",
                    f"{prob_home:.1%}"
                )

                st.caption(
                    f"Cuota justa: "
                    f"{probabilidad_a_americana(prob_home)}"
                )

            with col2:

                st.markdown(
                    f"### ✈️ {away}"
                )

                st.metric(
                    "Probabilidad modelo",
                    f"{prob_away:.1%}"
                )

                st.caption(
                    f"Cuota justa: "
                    f"{probabilidad_a_americana(prob_away)}"
                )

            # ------------------------------------------------
            # CUOTAS
            # ------------------------------------------------

            if odds:

                st.markdown(
                    f"""
                    <div class="yellow-card">

                    🏦 <b>Cuotas disponibles</b>

                    <br><br>

                    Casa:
                    {odds["provider"]}

                    <br>

                    Línea:
                    {odds["details"]}

                    <br>

                    Spread:
                    {odds["spread"]}

                    <br>

                    Total:
                    {odds["overUnder"]}

                    </div>
                    """,
                    unsafe_allow_html=True
                )

            else:

                st.info(
                    "La fuente no proporcionó cuotas "
                    "para este partido."
                )

            # ------------------------------------------------
            # COMPARACIÓN
            # ------------------------------------------------

            st.markdown(
                """
                <div class="green-card">

                🎯 <b>Qué buscamos</b>

                <br><br>

                Nuestro modelo debe generar una probabilidad
                diferente a la que implica la cuota de la casa.

                <br><br>

                Si nuestro modelo dice 65% y la casa implica
                55%, existe una diferencia de 10 puntos
                porcentuales que merece ser investigada.

                </div>
                """,
                unsafe_allow_html=True
            )

    else:

        st.info(
            "No hay partidos disponibles en la fuente."
        )


# ============================================================
# VALIDACIÓN
# ============================================================

with tab2:

    st.header(
        "🧪 ¿Qué tan bueno es nuestro modelo?"
    )

    st.write(
        "Aquí medimos si las probabilidades generadas "
        "por nuestro modelo realmente corresponden "
        "con los resultados observados."
    )

    st.markdown("""
    <div class="yellow-card">

    🎯 <b>Objetivo</b>

    <br><br>

    No queremos simplemente decir:

    <br><br>

    <b>"El modelo dice 70%, por lo tanto debe acertar 70%."</b>

    <br><br>

    Queremos comprobar históricamente qué porcentaje
    real corresponde a cada nivel de confianza.

    </div>
    """, unsafe_allow_html=True)

    st.subheader(
        "📌 Validación histórica"
    )

    st.info(
        "Esta sección puede utilizar posteriormente "
        "los datos históricos generados por nuestro "
        "propio sistema. No afecta la consulta "
        "automática de los partidos actuales."
    )

    st.markdown("---")

    st.subheader(
        "🎯 Niveles de confianza"
    )

    niveles = [
        0.55,
        0.60,
        0.65,
        0.70,
        0.75,
        0.80,
        0.85,
        0.90
    ]

    tabla = pd.DataFrame({
        "Probabilidad mínima": [
            f"{x:.0%}"
            for x in niveles
        ],
        "Objetivo": [
            "Validar modelo"
            for _ in niveles
        ]
    })

    st.dataframe(
        tabla,
        use_container_width=True,
        hide_index=True
    )


# ============================================================
# INFORMACIÓN
# ============================================================

with tab3:

    st.header(
        "📊 Información del sistema"
    )

    st.markdown("""
    <div class="card">

    <h3>🏈 ¿Qué hace esta aplicación?</h3>

    <br>

    <b>1. Obtiene los partidos automáticamente</b>

    <br><br>

    Ya no necesitamos cargar un CSV para consultar
    los partidos actuales.

    <br><br>

    <b>2. Obtiene información histórica</b>

    <br><br>

    El sistema utiliza datos históricos para construir
    una probabilidad base.

    <br><br>

    <b>3. Genera nuestra probabilidad</b>

    <br><br>

    Para cada partido mostramos:

    <br><br>

    • Probabilidad local
    <br>
    • Probabilidad visitante
    <br>
    • Cuota justa de nuestro modelo

    <br><br>

    <b>4. Comparamos contra la casa</b>

    <br><br>

    El objetivo final será identificar diferencias
    entre nuestra probabilidad y la probabilidad
    implícita de la casa.

    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="red-card">

    ⚠️ <b>Importante</b>

    <br><br>

    Esta primera versión utiliza un modelo base.
    No debemos considerar sus probabilidades como
    definitivas.

    <br><br>

    El siguiente paso será mejorar el modelo con
    variables deportivas más importantes.

    </div>
    """, unsafe_allow_html=True)


# ============================================================
# PIE
# ============================================================

st.markdown("---")

st.caption(
    "Monitor NFL — herramienta de análisis estadístico. "
    "Las probabilidades son estimaciones y no garantizan "
    "resultados futuros."
)
