import streamlit as st
import pandas as pd
import numpy as np
import requests
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo
from math import log, exp

# ============================================================
# CONFIGURACIÓN
# ============================================================

st.set_page_config(
    page_title="Monitor NFL",
    page_icon="🏈",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ============================================================
# ESTILO
# ============================================================

st.markdown("""
<style>

.block-container {
    max-width: 1100px;
    padding-top: 2rem;
    padding-bottom: 3rem;
}

h1, h2, h3 {
    color: #f5f5f5;
}

body {
    background-color: #0e1016;
}

.stApp {
    background-color: #0e1016;
}

div[data-testid="stMetric"] {
    background-color: #171923;
    border-radius: 15px;
    padding: 15px;
}

.info-box {
    background: #1e3149;
    border-radius: 18px;
    padding: 25px;
    margin: 20px 0;
    color: #6eb1ff;
    font-size: 20px;
}

.green-box {
    background: #193225;
    border: 1px solid #39714d;
    border-radius: 20px;
    padding: 28px;
    margin: 20px 0;
}

.yellow-box {
    background: #3c351d;
    border: 1px solid #77651d;
    border-radius: 20px;
    padding: 28px;
    margin: 20px 0;
}

.red-box {
    background: #402329;
    border-radius: 18px;
    padding: 25px;
    margin: 20px 0;
    color: #ff7777;
}

.game-card {
    background: #171923;
    border: 1px solid #30333d;
    border-radius: 22px;
    padding: 28px;
    margin: 25px 0;
}

.team-name {
    font-size: 30px;
    font-weight: 700;
    margin-top: 12px;
}

.prob {
    font-size: 45px;
    font-weight: 700;
    margin: 5px 0 15px 0;
}

.small-gray {
    color: #a7a9b3;
    font-size: 17px;
}

.section-title {
    font-size: 40px;
    font-weight: 800;
    margin-top: 35px;
}

.footer {
    border-top: 1px solid #333640;
    margin-top: 50px;
    padding-top: 30px;
    color: #999ca6;
    font-size: 17px;
}

</style>
""", unsafe_allow_html=True)


# ============================================================
# CONSTANTES
# ============================================================

NFL_TEAMS = {
    "ARI": "Arizona Cardinals",
    "ATL": "Atlanta Falcons",
    "BAL": "Baltimore Ravens",
    "BUF": "Buffalo Bills",
    "CAR": "Carolina Panthers",
    "CHI": "Chicago Bears",
    "CIN": "Cincinnati Bengals",
    "CLE": "Cleveland Browns",
    "DAL": "Dallas Cowboys",
    "DEN": "Denver Broncos",
    "DET": "Detroit Lions",
    "GB": "Green Bay Packers",
    "HOU": "Houston Texans",
    "IND": "Indianapolis Colts",
    "JAX": "Jacksonville Jaguars",
    "KC": "Kansas City Chiefs",
    "LV": "Las Vegas Raiders",
    "LAC": "Los Angeles Chargers",
    "LA": "Los Angeles Rams",
    "MIA": "Miami Dolphins",
    "MIN": "Minnesota Vikings",
    "NE": "New England Patriots",
    "NO": "New Orleans Saints",
    "NYG": "New York Giants",
    "NYJ": "New York Jets",
    "PHI": "Philadelphia Eagles",
    "PIT": "Pittsburgh Steelers",
    "SF": "San Francisco 49ers",
    "SEA": "Seattle Seahawks",
    "TB": "Tampa Bay Buccaneers",
    "TEN": "Tennessee Titans",
    "WAS": "Washington Commanders",
}

TEAM_EMOJI = {
    "ARI": "🏜️",
    "ATL": "🦅",
    "BAL": "🐦‍⬛",
    "BUF": "🦬",
    "CAR": "🐆",
    "CHI": "🐻",
    "CIN": "🐯",
    "CLE": "🟤",
    "DAL": "⭐",
    "DEN": "🐴",
    "DET": "🦁",
    "GB": "🧀",
    "HOU": "🤘",
    "IND": "🐎",
    "JAX": "🐆",
    "KC": "🏹",
    "LV": "☠️",
    "LAC": "⚡",
    "LA": "🐏",
    "MIA": "🐬",
    "MIN": "⚔️",
    "NE": "🏈",
    "NO": "⚜️",
    "NYG": "🗽",
    "NYJ": "✈️",
    "PHI": "🦅",
    "PIT": "🏠",
    "SF": "🌉",
    "SEA": "🦅",
    "TB": "🏴‍☠️",
    "TEN": "⚔️",
    "WAS": "🏛️",
}

# Fuente histórica
HISTORICAL_URL = (
    "https://raw.githubusercontent.com/"
    "nflverse/nfldata/master/data/games.csv"
)

# ============================================================
# FUNCIONES DE UTILIDAD
# ============================================================

def team_name(code):
    return NFL_TEAMS.get(code, code)


def emoji(code):
    return TEAM_EMOJI.get(code, "🏈")


def american_to_implied(odds):
    """
    Convierte cuota americana a probabilidad implícita.
    """
    try:
        odds = float(odds)

        if odds < 0:
            return (-odds) / ((-odds) + 100)

        return 100 / (odds + 100)

    except Exception:
        return None


def prob_to_american(prob):
    """
    Convierte probabilidad a cuota americana justa.
    """
    if prob is None or prob <= 0 or prob >= 1:
        return None

    if prob >= 0.5:
        return int(round(-100 * prob / (1 - prob)))

    return int(round(100 * (1 - prob) / prob))


def normalize_team(code):
    """
    Normaliza algunos códigos que pueden aparecer
    diferentes entre fuentes.
    """

    replacements = {
        "JAC": "JAX",
        "LA": "LA",
        "LAR": "LA",
        "SD": "LAC",
        "OAK": "LV",
        "STL": "LA",
        "WSH": "WAS",
        "WAS": "WAS",
    }

    return replacements.get(code, code)


# ============================================================
# CARGA HISTÓRICA
# ============================================================

@st.cache_data(ttl=3600)
def cargar_historico():

    try:

        df = pd.read_csv(HISTORICAL_URL)

        if df.empty:
            return pd.DataFrame()

        df["season"] = pd.to_numeric(
            df["season"],
            errors="coerce"
        )

        df["gameday"] = pd.to_datetime(
            df["gameday"],
            errors="coerce"
        )

        return df

    except Exception as e:

        return pd.DataFrame()


# ============================================================
# ELO HISTÓRICO
# ============================================================

def construir_elo(df):

    ratings = {
        team: 1500.0
        for team in NFL_TEAMS.keys()
    }

    if df.empty:
        return ratings

    data = df.copy()

    data = data[
        data["game_type"].isin(["REG", "WC", "DIV", "CON", "SB"])
    ]

    data = data[
        data["away_score"].notna()
        & data["home_score"].notna()
    ]

    data = data.sort_values(
        ["season", "gameday"],
        ascending=True
    )

    K = 20

    for _, game in data.iterrows():

        away = normalize_team(str(game["away_team"]))
        home = normalize_team(str(game["home_team"]))

        if away not in ratings:
            ratings[away] = 1500.0

        if home not in ratings:
            ratings[home] = 1500.0

        ra = ratings[away]
        rh = ratings[home]

        expected_away = 1 / (
            1 + 10 ** ((rh - ra) / 400)
        )

        away_score = float(game["away_score"])
        home_score = float(game["home_score"])

        if away_score > home_score:
            actual_away = 1
        elif away_score < home_score:
            actual_away = 0
        else:
            actual_away = 0.5

        # factor pequeño por margen de victoria
        margin = abs(away_score - home_score)

        if margin > 0:
            margin_factor = np.log(margin + 1) * 1.5
        else:
            margin_factor = 1

        change = K * margin_factor * (
            actual_away - expected_away
        )

        ratings[away] += change
        ratings[home] -= change

    return ratings


# ============================================================
# MODELO DE PROBABILIDAD
# ============================================================

def calcular_probabilidades(away, home, ratings):

    away = normalize_team(away)
    home = normalize_team(home)

    ra = ratings.get(away, 1500)
    rh = ratings.get(home, 1500)

    # ventaja local
    home_advantage = 55

    adjusted_home = rh + home_advantage

    probability_away = 1 / (
        1 + 10 ** ((adjusted_home - ra) / 400)
    )

    probability_home = 1 - probability_away

    return probability_away, probability_home


# ============================================================
# FUENTE DE PARTIDOS
# ============================================================

@st.cache_data(ttl=300)
def obtener_partidos_espn(fecha_str):

    """
    Obtiene el marcador/calendario del día desde ESPN.
    No necesita API key.
    """

    url = (
        "https://site.api.espn.com/apis/site/v2/"
        "sports/football/nfl/scoreboard"
        f"?dates={fecha_str}"
    )

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json",
    }

    try:

        response = requests.get(
            url,
            headers=headers,
            timeout=15
        )

        response.raise_for_status()

        data = response.json()

        events = data.get("events", [])

        partidos = []

        for event in events:

            competitions = event.get(
                "competitions",
                []
            )

            if not competitions:
                continue

            comp = competitions[0]

            competitors = comp.get(
                "competitors",
                []
            )

            if len(competitors) < 2:
                continue

            away = None
            home = None

            for c in competitors:

                team = c.get("team", {})

                code = team.get("abbreviation")

                if c.get("homeAway") == "away":
                    away = code

                elif c.get("homeAway") == "home":
                    home = code

            if not away or not home:
                continue

            away = normalize_team(away)
            home = normalize_team(home)

            status = event.get(
                "status",
                {}
            )

            competitions_info = comp.get(
                "odds",
                []
            )

            partidos.append({
                "id": event.get("id"),
                "away": away,
                "home": home,
                "name": event.get(
                    "name",
                    f"{away} @ {home}"
                ),
                "date": event.get("date"),
                "status": status,
                "odds": competitions_info,
                "venue": comp.get(
                    "venue",
                    {}
                ).get("fullName"),
            })

        return partidos, None

    except Exception as e:

        return [], str(e)


# ============================================================
# FUENTE ALTERNATIVA: NFVERSE
# ============================================================

@st.cache_data(ttl=300)
def obtener_partidos_nfverse():

    try:

        df = pd.read_csv(
            HISTORICAL_URL
        )

        if df.empty:
            return []

        df["gameday"] = pd.to_datetime(
            df["gameday"],
            errors="coerce"
        )

        # próximos 14 días
        hoy = pd.Timestamp(
            datetime.now(
                ZoneInfo("America/Chicago")
            ).date()
        )

        limite = hoy + pd.Timedelta(days=14)

        upcoming = df[
            (df["gameday"] >= hoy)
            & (df["gameday"] <= limite)
            & (df["away_score"].isna())
            & (df["home_score"].isna())
        ].copy()

        partidos = []

        for _, row in upcoming.iterrows():

            away = normalize_team(
                str(row["away_team"])
            )

            home = normalize_team(
                str(row["home_team"])
            )

            partidos.append({
                "id": row.get(
                    "game_id",
                    f"{row['gameday']}_{away}_{home}"
                ),
                "away": away,
                "home": home,
                "name": (
                    f"{team_name(away)} @ "
                    f"{team_name(home)}"
                ),
                "date": row["gameday"],
                "gametime": row.get(
                    "gametime"
                ),
                "status": {},
                "odds": [],
                "venue": row.get(
                    "stadium"
                ),
            })

        return partidos

    except Exception:
        return []


# ============================================================
# COMBINAR FUENTES
# ============================================================

def obtener_partidos():

    ahora = datetime.now(
        ZoneInfo("America/Chicago")
    )

    fecha_str = ahora.strftime(
        "%Y%m%d"
    )

    partidos, error = obtener_partidos_espn(
        fecha_str
    )

    # Si ESPN tiene partidos, usamos esos.
    if partidos:
        return partidos, "ESPN"

    # Fallback
    partidos = obtener_partidos_nfverse()

    if partidos:
        return partidos, "nflverse"

    return [], None


# ============================================================
# EXTRAER CUOTAS
# ============================================================

def obtener_odds(partido):

    odds_list = partido.get(
        "odds",
        []
    )

    if not odds_list:
        return {
            "away_moneyline": None,
            "home_moneyline": None,
            "spread": None,
            "total": None,
        }

    try:

        odds = odds_list[0]

        details = odds.get(
            "details"
        )

        over_under = odds.get(
            "overUnder"
        )

        away_ml = None
        home_ml = None

        # ESPN suele colocar moneyline
        # dentro de open/close o details.
        if "moneyline" in odds:
            ml = odds["moneyline"]

            if isinstance(ml, dict):

                away_ml = ml.get(
                    "away"
                )

                home_ml = ml.get(
                    "home"
                )

        return {
            "away_moneyline": away_ml,
            "home_moneyline": home_ml,
            "spread": details,
            "total": over_under,
        }

    except Exception:

        return {
            "away_moneyline": None,
            "home_moneyline": None,
            "spread": None,
            "total": None,
        }


# ============================================================
# HORA
# ============================================================

def formatear_hora(fecha):

    try:

        dt = pd.to_datetime(
            fecha,
            utc=True
        )

        dt = dt.tz_convert(
            "America/Chicago"
        )

        return dt.strftime(
            "%I:%M %p"
        ).lstrip("0")

    except Exception:
        return "Hora no disponible"


# ============================================================
# CALIBRACIÓN HISTÓRICA
# ============================================================

def calcular_calibracion(df):

    if df.empty:
        return pd.DataFrame()

    data = df.copy()

    data = data[
        data["game_type"].isin(
            ["REG", "WC", "DIV", "CON", "SB"]
        )
    ]

    data = data[
        data["away_score"].notna()
        & data["home_score"].notna()
    ]

    if data.empty:
        return pd.DataFrame()

    ratings = {
        team: 1500.0
        for team in NFL_TEAMS
    }

    registros = []

    K = 20

    for _, game in data.sort_values(
        ["season", "gameday"]
    ).iterrows():

        away = normalize_team(
            str(game["away_team"])
        )

        home = normalize_team(
            str(game["home_team"])
        )

        if away not in ratings:
            ratings[away] = 1500

        if home not in ratings:
            ratings[home] = 1500

        ra = ratings[away]
        rh = ratings[home]

        expected_away = 1 / (
            1 + 10 ** ((rh + 55 - ra) / 400)
        )

        actual = (
            1
            if game["away_score"]
            > game["home_score"]
            else 0
        )

        registros.append({
            "season": game["season"],
            "probability": expected_away,
            "actual": actual,
        })

        if actual == 1:
            actual_away = 1
        else:
            actual_away = 0

        change = K * (
            actual_away - expected_away
        )

        ratings[away] += change
        ratings[home] -= change

    result = pd.DataFrame(registros)

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
        1.01,
    ]

    labels = [
        "50-55%",
        "55-60%",
        "60-65%",
        "65-70%",
        "70-75%",
        "75-80%",
        "80-85%",
        "85-90%",
        "90%+",
    ]

    result["grupo"] = pd.cut(
        result["probability"],
        bins=bins,
        labels=labels,
        include_lowest=True
    )

    calibration = (
        result
        .groupby(
            "grupo",
            observed=False
        )
        .agg(
            partidos=("actual", "count"),
            aciertos=("actual", "sum"),
            prob_modelo=("probability", "mean"),
            acierto_real=("actual", "mean"),
        )
        .reset_index()
    )

    calibration["prob_modelo"] *= 100
    calibration["acierto_real"] *= 100

    calibration["diferencia"] = (
        calibration["acierto_real"]
        - calibration["prob_modelo"]
    )

    return calibration


# ============================================================
# CABECERA
# ============================================================

st.title("🏈 Monitor NFL")

st.subheader(
    "Modelo propio — análisis NFL automático"
)

tab1, tab2, tab3 = st.tabs([
    "🏈 NFL DE HOY",
    "🧪 VALIDACIÓN DEL MODELO",
    "📊 INFORMACIÓN",
])


# ============================================================
# TAB 1
# ============================================================

with tab1:

    st.markdown(
        '<div class="section-title">'
        '🏈 NFL DE HOY'
        '</div>',
        unsafe_allow_html=True
    )

    if st.button(
        "🔄 ACTUALIZAR PARTIDOS",
        use_container_width=True
    ):

        st.cache_data.clear()
        st.rerun()

    partidos, fuente = obtener_partidos()

    if fuente:

        st.markdown(
            f"""
            <div class="info-box">
            Fuente de calendario: <b>{fuente}</b><br>
            Hora utilizada: Dallas, Texas
            </div>
            """,
            unsafe_allow_html=True
        )

    historico = cargar_historico()

    ratings = construir_elo(
        historico
    )

    if not partidos:

        st.markdown(
            """
            <div class="yellow-box">
            ⚠️ No se encontraron partidos en la
            fuente automática para esta fecha.
            </div>
            """,
            unsafe_allow_html=True
        )

        st.info(
            "El calendario se consulta automáticamente. "
            "Si la fuente tarda en actualizarse, vuelve a "
            "pulsar ACTUALIZAR PARTIDOS."
        )

    else:

        st.success(
            f"Se encontraron {len(partidos)} partido(s)."
        )

        for partido in partidos:

            away = partido["away"]
            home = partido["home"]

            p_away, p_home = calcular_probabilidades(
                away,
                home,
                ratings
            )

            fair_away = prob_to_american(
                p_away
            )

            fair_home = prob_to_american(
                p_home
            )

            hora = formatear_hora(
                partido.get("date")
            )

            venue = partido.get(
                "venue"
            )

            odds = obtener_odds(
                partido
            )

            st.markdown(
                '<div class="game-card">',
                unsafe_allow_html=True
            )

            st.markdown(
                f"""
                <h2>
                🏈 {team_name(away)}
                @
                {team_name(home)}
                </h2>
                """,
                unsafe_allow_html=True
            )

            st.markdown(
                f"""
                <div class="info-box">
                🕐 Hora Dallas: {hora}
                </div>
                """,
                unsafe_allow_html=True
            )

            if venue:

                st.caption(
                    f"🏟️ {venue}"
                )

            col1, col2 = st.columns(2)

            with col1:

                st.markdown(
                    f"""
                    <div class="team-name">
                    ✈️ {team_name(away)}
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                st.markdown(
                    '<div class="small-gray">'
                    'Probabilidad modelo'
                    '</div>',
                    unsafe_allow_html=True
                )

                st.markdown(
                    f'<div class="prob">'
                    f'{p_away * 100:.1f}%'
                    f'</div>',
                    unsafe_allow_html=True
                )

                st.write(
                    f"🎯 Cuota justa: "
                    f"{fair_away}"
                )

            with col2:

                st.markdown(
                    f"""
                    <div class="team-name">
                    🏠 {team_name(home)}
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                st.markdown(
                    '<div class="small-gray">'
                    'Probabilidad modelo'
                    '</div>',
                    unsafe_allow_html=True
                )

                st.markdown(
                    f'<div class="prob">'
                    f'{p_home * 100:.1f}%'
                    f'</div>',
                    unsafe_allow_html=True
                )

                st.write(
                    f"🎯 Cuota justa: "
                    f"{fair_home}"
                )

            # ------------------------------------------------
            # COMPARACIÓN CON CASA
            # ------------------------------------------------

            st.markdown(
                """
                <div class="yellow-box">
                🏦 <b>COMPARACIÓN CON LA CASA</b>
                </div>
                """,
                unsafe_allow_html=True
            )

            away_market = odds.get(
                "away_moneyline"
            )

            home_market = odds.get(
                "home_moneyline"
            )

            if (
                away_market is not None
                or home_market is not None
            ):

                c1, c2 = st.columns(2)

                with c1:

                    if away_market is not None:

                        implied = american_to_implied(
                            away_market
                        )

                        st.write(
                            f"✈️ {team_name(away)}"
                        )

                        st.write(
                            f"Casa: {away_market}"
                        )

                        if implied:
                            st.write(
                                f"Prob. implícita: "
                                f"{implied * 100:.1f}%"
                            )

                            st.write(
                                f"Diferencia modelo: "
                                f"{(p_away - implied) * 100:+.1f}%"
                            )

                with c2:

                    if home_market is not None:

                        implied = american_to_implied(
                            home_market
                        )

                        st.write(
                            f"🏠 {team_name(home)}"
                        )

                        st.write(
                            f"Casa: {home_market}"
                        )

                        if implied:
                            st.write(
                                f"Prob. implícita: "
                                f"{implied * 100:.1f}%"
                            )

                            st.write(
                                f"Diferencia modelo: "
                                f"{(p_home - implied) * 100:+.1f}%"
                            )

            else:

                st.info(
                    "Todavía no se encontraron cuotas "
                    "de apuestas en la fuente automática."
                )

            st.markdown(
                "</div>",
                unsafe_allow_html=True
            )


# ============================================================
# TAB 2 — VALIDACIÓN
# ============================================================

with tab2:

    st.markdown(
        '<div class="section-title">'
        '🧪 Validación del modelo'
        '</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        """
        <div class="yellow-box">

        🎯 <b>Lo que queremos comprobar</b>

        <br><br>

        Si nuestro modelo dice 70%, queremos comprobar
        históricamente qué porcentaje de esos partidos
        realmente terminó ganándose.

        <br><br>

        No buscamos simplemente tener muchos aciertos.

        <br><br>

        Buscamos que una probabilidad del modelo
        tenga significado estadístico.

        </div>
        """,
        unsafe_allow_html=True
    )

    historico = cargar_historico()

    if historico.empty:

        st.error(
            "No se pudo cargar el histórico NFL."
        )

    else:

        calibration = calcular_calibracion(
            historico
        )

        if calibration.empty:

            st.warning(
                "No hay suficientes datos para calcular "
                "la calibración."
            )

        else:

            st.markdown(
                "### 📈 Calibración histórica"
            )

            mostrar = calibration.copy()

            mostrar["prob_modelo"] = (
                mostrar["prob_modelo"]
                .round(1)
                .astype(str)
                + "%"
            )

            mostrar["acierto_real"] = (
                mostrar["acierto_real"]
                .round(1)
                .astype(str)
                + "%"
            )

            mostrar["diferencia"] = (
                mostrar["diferencia"]
                .round(1)
                .astype(str)
                + "%"
            )

            mostrar = mostrar.rename(
                columns={
                    "grupo":
                        "Probabilidad modelo",
                    "partidos":
                        "Partidos",
                    "aciertos":
                        "Aciertos",
                    "prob_modelo":
                        "Prob. promedio modelo",
                    "acierto_real":
                        "Acierto real",
                    "diferencia":
                        "Diferencia",
                }
            )

            st.dataframe(
                mostrar,
                use_container_width=True,
                hide_index=True
            )

            st.markdown(
                """
                <div class="info-box">
                La calibración real se calcula utilizando
                resultados históricos. No se muestran valores
                inventados.
                </div>
                """,
                unsafe_allow_html=True
            )

            # ------------------------------------------------
            # RESUMEN
            # ------------------------------------------------

            total_partidos = len(
                historico[
                    historico["away_score"].notna()
                    & historico["home_score"].notna()
                ]
            )

            st.metric(
                "Partidos históricos utilizados",
                f"{total_partidos:,}"
            )


# ============================================================
# TAB 3 — INFORMACIÓN
# ============================================================

with tab3:

    st.markdown(
        '<div class="section-title">'
        '📊 Información'
        '</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        """
        <div class="green-box">

        <h3>🧠 ¿Cómo funciona el modelo?</h3>

        <br>

        El sistema utiliza un rating tipo <b>Elo</b>
        calculado a partir de partidos históricos.

        <br><br>

        Cada resultado modifica la fuerza estimada
        de cada equipo.

        <br><br>

        Para un partido nuevo:

        <br><br>

        • Calculamos la fuerza de ambos equipos<br>
        • Añadimos ventaja de local<br>
        • Convertimos la diferencia en probabilidad<br>
        • Calculamos una cuota justa<br>
        • Comparamos posteriormente contra la casa

        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown(
        """
        <div class="yellow-box">

        🎯 <b>IMPORTANTE</b>

        <br><br>

        Una probabilidad de 70% NO significa que
        el siguiente partido necesariamente vaya a ganar.

        <br><br>

        Significa que, si el modelo está correctamente
        calibrado, situaciones similares deberían ganar
        aproximadamente 70 de cada 100 veces.

        <br><br>

        Por eso necesitamos validar el modelo con una
        muestra histórica grande antes de utilizarlo
        para tomar decisiones.

        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown(
        "### 📚 Fuente de datos"
    )

    st.write(
        "El calendario e histórico se obtienen "
        "automáticamente de fuentes públicas NFL."
    )

    st.write(
        "No es necesario subir ningún CSV "
        "para consultar los partidos actuales."
    )


# ============================================================
# FOOTER
# ============================================================

st.markdown(
    """
    <div class="footer">

    🏈 Monitor NFL — herramienta experimental
    de análisis estadístico.

    <br><br>

    Las probabilidades son estimaciones del modelo
    y no garantizan resultados futuros.

    </div>
    """,
    unsafe_allow_html=True
)
