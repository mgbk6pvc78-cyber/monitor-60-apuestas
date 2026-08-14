import streamlit as st
import requests
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import math

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

.small-muted {
    color: #9ca0aa;
    font-size: 0.95rem;
}

.game-card {
    background: #171922;
    border: 1px solid #30333d;
    border-radius: 18px;
    padding: 25px;
    margin-bottom: 25px;
}

.team-name {
    font-size: 1.45rem;
    font-weight: 700;
}

.probability {
    font-size: 2rem;
    font-weight: 700;
}

.time-box {
    background: #1d314d;
    padding: 14px;
    border-radius: 12px;
    color: #63a9ff;
    font-size: 1.1rem;
    margin: 12px 0;
}

.info-box {
    background: #1c3048;
    border-radius: 15px;
    padding: 20px;
    color: #62a7ff;
    margin: 15px 0;
}

.warning-box {
    background: #3b351d;
    border: 1px solid #75651b;
    border-radius: 15px;
    padding: 20px;
    color: #f4ed9a;
    margin: 15px 0;
}

.error-box {
    background: #3b2025;
    border-radius: 15px;
    padding: 20px;
    color: #ff8585;
    margin: 15px 0;
}

.value-box {
    background: #183324;
    border: 1px solid #376e4c;
    border-radius: 15px;
    padding: 20px;
    margin-top: 15px;
}

</style>
""", unsafe_allow_html=True)


# ============================================================
# ZONA HORARIA
# ============================================================

DALLAS_TZ = ZoneInfo("America/Chicago")


# ============================================================
# RATINGS INICIALES
# ============================================================
#
# Estos son ratings base para que el modelo pueda funcionar
# incluso antes de tener nuestro histórico propio.
#
# Posteriormente los sustituiremos por ratings calculados
# automáticamente con resultados históricos.
# ============================================================

ELO = {
    "Arizona Cardinals": 1500,
    "Atlanta Falcons": 1500,
    "Baltimore Ravens": 1555,
    "Buffalo Bills": 1560,
    "Carolina Panthers": 1450,
    "Chicago Bears": 1490,
    "Cincinnati Bengals": 1535,
    "Cleveland Browns": 1450,
    "Dallas Cowboys": 1515,
    "Denver Broncos": 1530,
    "Detroit Lions": 1540,
    "Green Bay Packers": 1545,
    "Houston Texans": 1515,
    "Indianapolis Colts": 1490,
    "Jacksonville Jaguars": 1490,
    "Kansas City Chiefs": 1570,
    "Las Vegas Raiders": 1450,
    "Los Angeles Chargers": 1530,
    "Los Angeles Rams": 1540,
    "Miami Dolphins": 1500,
    "Minnesota Vikings": 1515,
    "New England Patriots": 1510,
    "New Orleans Saints": 1460,
    "New York Giants": 1450,
    "New York Jets": 1470,
    "Philadelphia Eagles": 1570,
    "Pittsburgh Steelers": 1525,
    "San Francisco 49ers": 1570,
    "Seattle Seahawks": 1515,
    "Tampa Bay Buccaneers": 1500,
    "Tennessee Titans": 1470,
    "Washington Commanders": 1500
}


# ============================================================
# FUNCIÓN ELO
# ============================================================

def elo_probability(home_elo, away_elo, home_advantage=45):

    difference = (home_elo + home_advantage) - away_elo

    probability = 1 / (
        1 + 10 ** (-difference / 400)
    )

    return probability


# ============================================================
# NORMALIZAR NOMBRES
# ============================================================

TEAM_ALIASES = {
    "Arizona": "Arizona Cardinals",
    "Atlanta": "Atlanta Falcons",
    "Baltimore": "Baltimore Ravens",
    "Buffalo": "Buffalo Bills",
    "Carolina": "Carolina Panthers",
    "Chicago": "Chicago Bears",
    "Cincinnati": "Cincinnati Bengals",
    "Cleveland": "Cleveland Browns",
    "Dallas": "Dallas Cowboys",
    "Denver": "Denver Broncos",
    "Detroit": "Detroit Lions",
    "Green Bay": "Green Bay Packers",
    "Houston": "Houston Texans",
    "Indianapolis": "Indianapolis Colts",
    "Jacksonville": "Jacksonville Jaguars",
    "Kansas City": "Kansas City Chiefs",
    "Las Vegas": "Las Vegas Raiders",
    "LA Chargers": "Los Angeles Chargers",
    "Los Angeles Chargers": "Los Angeles Chargers",
    "LA Rams": "Los Angeles Rams",
    "Los Angeles Rams": "Los Angeles Rams",
    "Miami": "Miami Dolphins",
    "Minnesota": "Minnesota Vikings",
    "New England": "New England Patriots",
    "New Orleans": "New Orleans Saints",
    "NY Giants": "New York Giants",
    "NY Jets": "New York Jets",
    "Philadelphia": "Philadelphia Eagles",
    "Pittsburgh": "Pittsburgh Steelers",
    "San Francisco": "San Francisco 49ers",
    "Seattle": "Seattle Seahawks",
    "Tampa Bay": "Tampa Bay Buccaneers",
    "Tennessee": "Tennessee Titans",
    "Washington": "Washington Commanders"
}


def normalize_team(name):

    if name in ELO:
        return name

    if name in TEAM_ALIASES:
        return TEAM_ALIASES[name]

    # Buscar coincidencia parcial
    for key, value in TEAM_ALIASES.items():
        if key.lower() in name.lower():
            return value

    for team in ELO:
        if team.lower() in name.lower():
            return team

    return name


# ============================================================
# CONSULTAR ESPN
# ============================================================

def get_nfl_games_for_date(date_obj):

    date_string = date_obj.strftime("%Y%m%d")

    url = (
        "https://site.api.espn.com/apis/site/v2/"
        "sports/football/nfl/scoreboard"
    )

    params = {
        "dates": date_string,
        "limit": 100
    }

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) "
            "AppleWebKit/605.1.15 "
            "(KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1"
        ),
        "Accept": "application/json,text/plain,*/*",
        "Referer": "https://www.espn.com/"
    }

    response = requests.get(
        url,
        params=params,
        headers=headers,
        timeout=15
    )

    response.raise_for_status()

    data = response.json()

    return data.get("events", [])


# ============================================================
# BUSCAR PARTIDOS HOY + 7 DÍAS
# ============================================================

def get_upcoming_games():

    today = datetime.now(DALLAS_TZ).date()

    all_games = []
    errors = []

    for i in range(8):

        current_date = today + timedelta(days=i)

        try:

            events = get_nfl_games_for_date(current_date)

            for event in events:

                event_copy = dict(event)

                event_copy["_local_date"] = current_date

                all_games.append(event_copy)

        except Exception as e:

            errors.append(
                f"{current_date}: {str(e)}"
            )

    return all_games, errors


# ============================================================
# PROCESAR PARTIDO
# ============================================================

def process_game(event):

    competitions = event.get("competitions", [])

    if not competitions:
        return None

    competition = competitions[0]

    competitors = competition.get("competitors", [])

    if len(competitors) < 2:
        return None

    home = None
    away = None

    for team in competitors:

        if team.get("homeAway") == "home":
            home = team

        elif team.get("homeAway") == "away":
            away = team

    if not home or not away:
        return None

    home_name_raw = (
        home.get("team", {}).get("displayName")
        or home.get("team", {}).get("shortDisplayName")
        or "Local"
    )

    away_name_raw = (
        away.get("team", {}).get("displayName")
        or away.get("team", {}).get("shortDisplayName")
        or "Visitante"
    )

    home_name = normalize_team(home_name_raw)
    away_name = normalize_team(away_name_raw)

    home_elo = ELO.get(home_name, 1500)
    away_elo = ELO.get(away_name, 1500)

    probability_home = elo_probability(
        home_elo,
        away_elo
    )

    probability_away = 1 - probability_home

    # ========================================================
    # AJUSTE DE PRETEMPORADA
    # ========================================================
    #
    # En preseason las alineaciones cambian muchísimo.
    # Reducimos la confianza del modelo.
    # ========================================================

    season_type = (
        event.get("season", {})
        .get("slug", "")
        .lower()
    )

    if "pre" in season_type:

        probability_home = (
            0.50 +
            (probability_home - 0.50) * 0.55
        )

        probability_away = 1 - probability_home

    # ========================================================
    # HORA
    # ========================================================

    date_string = event.get("date")

    local_time = None

    if date_string:

        try:

            utc_time = datetime.fromisoformat(
                date_string.replace("Z", "+00:00")
            )

            local_time = utc_time.astimezone(
                DALLAS_TZ
            )

        except Exception:
            local_time = None

    # ========================================================
    # ODDS
    # ========================================================

    odds_info = []

    try:

        odds_list = competition.get("odds", [])

        for odds in odds_list:

            provider = odds.get("provider", {}).get(
                "name",
                "Casa"
            )

            details = odds.get("details")

            over_under = odds.get("overUnder")

            odds_info.append({
                "provider": provider,
                "details": details,
                "overUnder": over_under
            })

    except Exception:
        pass

    return {
        "id": event.get("id"),
        "home": home_name,
        "away": away_name,
        "home_raw": home_name_raw,
        "away_raw": away_name_raw,
        "home_probability": probability_home,
        "away_probability": probability_away,
        "home_elo": home_elo,
        "away_elo": away_elo,
        "time": local_time,
        "odds": odds_info,
        "status": event.get("status", {}),
        "season": event.get("season", {})
    }


# ============================================================
# FORMATO DE PROBABILIDAD
# ============================================================

def pct(value):

    return f"{value * 100:.1f}%"


# ============================================================
# CUOTA JUSTA AMERICANA
# ============================================================

def fair_american_odds(probability):

    if probability <= 0:
        return None

    if probability >= 1:
        return None

    if probability >= 0.50:

        odds = -100 * probability / (
            1 - probability
        )

    else:

        odds = 100 * (
            1 - probability
        ) / probability

    return int(round(odds))


# ============================================================
# MOSTRAR PARTIDO
# ============================================================

def show_game(game):

    st.markdown(
        '<div class="game-card">',
        unsafe_allow_html=True
    )

    # --------------------------------------------------------
    # FECHA / HORA
    # --------------------------------------------------------

    if game["time"]:

        game_time = game["time"]

        st.markdown(
            f"""
            <div class="time-box">
            🕐 Hora Dallas: <b>
            {game_time.strftime("%A %d de %B — %I:%M %p")}
            </b>
            </div>
            """,
            unsafe_allow_html=True
        )

    # --------------------------------------------------------
    # MATCHUP
    # --------------------------------------------------------

    st.markdown(
        f"""
        <h2>🏈 {game["away"]} @ {game["home"]}</h2>
        """,
        unsafe_allow_html=True
    )

    # --------------------------------------------------------
    # PROBABILIDADES
    # --------------------------------------------------------

    col1, col2 = st.columns(2)

    with col1:

        st.markdown(
            f"""
            <div class="team-name">
            ✈️ {game["away"]}
            </div>

            <div class="small-muted">
            Probabilidad modelo
            </div>

            <div class="probability">
            {pct(game["away_probability"])}
            </div>

            <div>
            🎯 Cuota justa:
            <b>{fair_american_odds(game["away_probability"])}</b>
            </div>
            """,
            unsafe_allow_html=True
        )

    with col2:

        st.markdown(
            f"""
            <div class="team-name">
            🏠 {game["home"]}
            </div>

            <div class="small-muted">
            Probabilidad modelo
            </div>

            <div class="probability">
            {pct(game["home_probability"])}
            </div>

            <div>
            🎯 Cuota justa:
            <b>{fair_american_odds(game["home_probability"])}</b>
            </div>
            """,
            unsafe_allow_html=True
        )

    # --------------------------------------------------------
    # ELO
    # --------------------------------------------------------

    with st.expander("📊 Detalles del modelo"):

        st.write(
            f"**{game['away']} Elo:** "
            f"{game['away_elo']}"
        )

        st.write(
            f"**{game['home']} Elo:** "
            f"{game['home_elo']}"
        )

        st.write(
            f"Probabilidad visitante: "
            f"{pct(game['away_probability'])}"
        )

        st.write(
            f"Probabilidad local: "
            f"{pct(game['home_probability'])}"
        )

        st.write(
            "Modelo: Elo + ventaja de local."
        )

        if game["season"]:

            season_name = game["season"].get(
                "displayName",
                ""
            )

            if season_name:

                st.write(
                    f"Temporada: {season_name}"
                )

    # --------------------------------------------------------
    # CUOTAS
    # --------------------------------------------------------

    if game["odds"]:

        st.markdown(
            """
            <div class="value-box">
            💰 <b>CUOTAS DISPONIBLES</b>
            </div>
            """,
            unsafe_allow_html=True
        )

        for odd in game["odds"]:

            provider = odd.get(
                "provider",
                "Casa"
            )

            details = odd.get(
                "details"
            )

            over_under = odd.get(
                "overUnder"
            )

            st.write(
                f"**{provider}** — "
                f"{details or 'Sin línea'}"
            )

            if over_under:

                st.write(
                    f"Total: {over_under}"
                )

    else:

        st.info(
            "ℹ️ ESPN no proporcionó cuotas "
            "para este partido."
        )

    st.markdown(
        "</div>",
        unsafe_allow_html=True
    )


# ============================================================
# HEADER
# ============================================================

st.title("🏈 Monitor NFL")

st.subheader(
    "Modelo propio — análisis NFL automático"
)


# ============================================================
# TABS
# ============================================================

tab1, tab2, tab3 = st.tabs([
    "🏈 NFL DE HOY",
    "🧪 VALIDACIÓN DEL MODELO",
    "📊 INFORMACIÓN"
])


# ============================================================
# TAB 1 — NFL
# ============================================================

with tab1:

    st.header("🏈 NFL DE HOY")

    refresh = st.button(
        "🔄 ACTUALIZAR PARTIDOS",
        use_container_width=True
    )

    # Siempre consulta al abrir.
    # Si se presiona actualizar, vuelve a consultar.

    games_raw, errors = get_upcoming_games()

    processed_games = []

    for event in games_raw:

        try:

            game = process_game(event)

            if game:
                processed_games.append(game)

        except Exception as e:

            errors.append(
                f"Error procesando partido: {e}"
            )

    # --------------------------------------------------------
    # FECHA DE HOY
    # --------------------------------------------------------

    today = datetime.now(
        DALLAS_TZ
    ).date()

    today_games = []

    upcoming_games = []

    for game in processed_games:

        if game["time"]:

            game_date = game["time"].date()

        else:

            game_date = today

        if game_date == today:

            today_games.append(game)

        elif today < game_date <= (
            today + timedelta(days=7)
        ):

            upcoming_games.append(game)

    # --------------------------------------------------------
    # MOSTRAR HOY
    # --------------------------------------------------------

    if today_games:

        st.success(
            f"Se encontraron "
            f"{len(today_games)} partidos NFL para hoy."
        )

        for game in sorted(
            today_games,
            key=lambda x: (
                x["time"] or datetime.now(DALLAS_TZ)
            )
        ):

            show_game(game)

    else:

        # IMPORTANTE:
        # No confundimos "error" con "no hay partidos".

        if errors:

            st.markdown(
                """
                <div class="error-box">
                ⚠️ La fuente automática presentó un
                problema al consultar el calendario.
                </div>
                """,
                unsafe_allow_html=True
            )

            with st.expander(
                "🔧 Ver detalles técnicos"
            ):

                for error in errors[:10]:

                    st.code(
                        str(error)
                    )

        else:

            st.markdown(
                """
                <div class="warning-box">
                ⚠️ No se encontraron partidos para hoy
                en la respuesta de la fuente.
                </div>
                """,
                unsafe_allow_html=True
            )

    # --------------------------------------------------------
    # PRÓXIMOS 7 DÍAS
    # --------------------------------------------------------

    st.divider()

    st.subheader(
        "📅 Próximos partidos"
    )

    if upcoming_games:

        for game in sorted(
            upcoming_games,
            key=lambda x: (
                x["time"] or datetime.max.replace(
                    tzinfo=DALLAS_TZ
                )
            )
        ):

            show_game(game)

    else:

        if not errors:

            st.info(
                "No hay partidos adicionales "
                "en los próximos 7 días."
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
        Aquí vamos a comprobar si las probabilidades
        generadas por nuestro modelo realmente corresponden
        con los resultados observados.
        """
    )

    st.markdown(
        """
        <div class="warning-box">

        🎯 <b>Lo que queremos comprobar</b>

        <br><br>

        Si nuestro modelo dice 70%, queremos comprobar
        históricamente si aproximadamente 70 de cada 100
        partidos terminan ganándose.

        <br><br>

        No buscamos simplemente una tasa de aciertos alta.

        <br><br>

        Buscamos <b>probabilidades bien calibradas</b>.

        </div>
        """,
        unsafe_allow_html=True
    )

    st.subheader(
        "📈 Ejemplo de calibración"
    )

    calibration_data = {
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
        "Objetivo histórico": [
            "≈55%",
            "≈60%",
            "≈65%",
            "≈70%",
            "≈75%",
            "≈80%",
            "≈85%",
            "≈90%"
        ]
    }

    st.table(
        calibration_data
    )

    st.info(
        """
        La validación histórica real se conectará
        cuando construyamos nuestro conjunto de datos
        históricos de partidos.
        """
    )


# ============================================================
# TAB 3 — INFORMACIÓN
# ============================================================

with tab3:

    st.header(
        "📊 Información del sistema"
    )

    st.markdown(
        """
        ### 🧠 Modelo actual

        El sistema utiliza:

        - Rating Elo
        - Ventaja de local
        - Probabilidad matemática
        - Ajuste conservador para pretemporada
        - Conversión a cuota justa americana

        ### 💰 Comparación con la casa

        El siguiente paso será comparar:

        **Probabilidad del modelo**

        contra

        **Probabilidad implícita de la casa**

        para identificar posibles diferencias.

        ### 🧪 Validación

        No vamos a considerar que el modelo es bueno
        solamente porque acierte algunos partidos.

        Primero necesitamos comprobarlo con una muestra
        histórica suficientemente grande.

        ### ⚠️ Importante

        Las probabilidades son estimaciones estadísticas.
        No garantizan resultados futuros.
        """
    )


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.markdown(
    """
    <div class="small-muted">
    Monitor NFL — herramienta experimental de análisis
    estadístico. Las probabilidades son estimaciones y no
    garantizan resultados futuros.
    </div>
    """,
    unsafe_allow_html=True
)
