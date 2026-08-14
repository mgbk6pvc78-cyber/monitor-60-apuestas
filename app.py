import streamlit as st
import requests
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import json
import re

# ============================================================
# CONFIG
# ============================================================

st.set_page_config(
    page_title="Monitor NFL",
    page_icon="🏈",
    layout="wide"
)

TZ = ZoneInfo("America/Chicago")


# ============================================================
# ESTILO
# ============================================================

st.markdown("""
<style>

.stApp {
    background:#0e0f14;
}

.block-container {
    padding-top:2rem;
    padding-bottom:3rem;
    max-width:1100px;
}

h1,h2,h3 {
    color:#f5f5f5;
}

.game-card {
    background:#171922;
    border:1px solid #343741;
    border-radius:20px;
    padding:25px;
    margin:20px 0;
}

.time-box {
    background:#1c3049;
    color:#63a9ff;
    padding:14px;
    border-radius:12px;
    margin:12px 0;
}

.team {
    font-size:1.5rem;
    font-weight:700;
    margin-top:10px;
}

.prob {
    font-size:2.2rem;
    font-weight:700;
}

.success-box {
    background:#183324;
    border:1px solid #397050;
    border-radius:15px;
    padding:20px;
}

.warning-box {
    background:#3b351d;
    border:1px solid #75651b;
    border-radius:15px;
    padding:20px;
}

.error-box {
    background:#3b2025;
    border-radius:15px;
    padding:20px;
    color:#ff8585;
}

.info-box {
    background:#1c3049;
    border-radius:15px;
    padding:20px;
    color:#63a9ff;
}

</style>
""", unsafe_allow_html=True)


# ============================================================
# ELO BASE
# ============================================================

ELO = {

    "Arizona Cardinals":1500,
    "Atlanta Falcons":1500,
    "Baltimore Ravens":1555,
    "Buffalo Bills":1560,
    "Carolina Panthers":1450,
    "Chicago Bears":1490,
    "Cincinnati Bengals":1535,
    "Cleveland Browns":1450,
    "Dallas Cowboys":1515,
    "Denver Broncos":1530,
    "Detroit Lions":1540,
    "Green Bay Packers":1545,
    "Houston Texans":1515,
    "Indianapolis Colts":1490,
    "Jacksonville Jaguars":1490,
    "Kansas City Chiefs":1570,
    "Las Vegas Raiders":1450,
    "Los Angeles Chargers":1530,
    "Los Angeles Rams":1540,
    "Miami Dolphins":1500,
    "Minnesota Vikings":1515,
    "New England Patriots":1510,
    "New Orleans Saints":1460,
    "New York Giants":1450,
    "New York Jets":1470,
    "Philadelphia Eagles":1570,
    "Pittsburgh Steelers":1525,
    "San Francisco 49ers":1570,
    "Seattle Seahawks":1515,
    "Tampa Bay Buccaneers":1500,
    "Tennessee Titans":1470,
    "Washington Commanders":1500
}


# ============================================================
# TEAM ALIASES
# ============================================================

ALIASES = {

    "Arizona":"Arizona Cardinals",
    "Atlanta":"Atlanta Falcons",
    "Baltimore":"Baltimore Ravens",
    "Buffalo":"Buffalo Bills",
    "Carolina":"Carolina Panthers",
    "Chicago":"Chicago Bears",
    "Cincinnati":"Cincinnati Bengals",
    "Cleveland":"Cleveland Browns",
    "Dallas":"Dallas Cowboys",
    "Denver":"Denver Broncos",
    "Detroit":"Detroit Lions",
    "Green Bay":"Green Bay Packers",
    "Houston":"Houston Texans",
    "Indianapolis":"Indianapolis Colts",
    "Jacksonville":"Jacksonville Jaguars",
    "Kansas City":"Kansas City Chiefs",
    "Las Vegas":"Las Vegas Raiders",
    "LA Chargers":"Los Angeles Chargers",
    "Los Angeles Chargers":"Los Angeles Chargers",
    "LA Rams":"Los Angeles Rams",
    "Los Angeles Rams":"Los Angeles Rams",
    "Miami":"Miami Dolphins",
    "Minnesota":"Minnesota Vikings",
    "New England":"New England Patriots",
    "New Orleans":"New Orleans Saints",
    "NY Giants":"New York Giants",
    "NY Jets":"New York Jets",
    "Philadelphia":"Philadelphia Eagles",
    "Pittsburgh":"Pittsburgh Steelers",
    "San Francisco":"San Francisco 49ers",
    "Seattle":"Seattle Seahawks",
    "Tampa Bay":"Tampa Bay Buccaneers",
    "Tennessee":"Tennessee Titans",
    "Washington":"Washington Commanders"
}


def normalize_team(name):

    if name in ELO:
        return name

    if name in ALIASES:
        return ALIASES[name]

    for key,value in ALIASES.items():

        if key.lower() in name.lower():
            return value

    return name


# ============================================================
# HTTP SESSION
# ============================================================

def make_session():

    session = requests.Session()

    session.headers.update({
        "User-Agent":
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",

        "Accept":
            "application/json,text/plain,*/*",

        "Accept-Language":
            "en-US,en;q=0.9",

        "Connection":
            "keep-alive"
    })

    return session


# ============================================================
# SOURCE 1 — ESPN SITE API
# ============================================================

def source_espn(date):

    date_string = date.strftime("%Y%m%d")

    urls = [

        f"https://site.api.espn.com/apis/site/v2/"
        f"sports/football/nfl/scoreboard"
        f"?dates={date_string}",

        f"https://site.api.espn.com/apis/site/v2/"
        f"sports/football/nfl/scoreboard"
        f"?dates={date_string}&limit=100"

    ]

    session = make_session()

    for url in urls:

        try:

            r = session.get(
                url,
                timeout=12
            )

            if r.status_code == 200:

                data = r.json()

                events = data.get(
                    "events",
                    []
                )

                if events:
                    return events, "ESPN"

        except Exception:
            pass

    return [], None


# ============================================================
# SOURCE 2 — ESPN CDN
# ============================================================

def source_espn_cdn(date):

    urls = [

        "https://cdn.espn.com/core/nfl/scoreboard"
        "?xhr=1",

        "https://cdn.espn.com/core/nfl/scoreboard"
        "?xhr=1&limit=100"
    ]

    session = make_session()

    for url in urls:

        try:

            r = session.get(
                url,
                timeout=12
            )

            if r.status_code != 200:
                continue

            text = r.text

            # ESPN CDN sometimes wraps JSON
            # inside a JS variable.

            match = re.search(
                r'\{.*\}',
                text,
                re.S
            )

            if not match:
                continue

            data = json.loads(
                match.group(0)
            )

            events = data.get(
                "events",
                []
            )

            if events:

                # Filter date when possible

                result = []

                wanted = date.strftime(
                    "%Y-%m-%d"
                )

                for event in events:

                    event_date = event.get(
                        "date",
                        ""
                    )

                    if event_date.startswith(
                        wanted
                    ):
                        result.append(event)

                if result:
                    return result, "ESPN CDN"

        except Exception:
            pass

    return [], None


# ============================================================
# SOURCE 3 — ESPN WEEK
# ============================================================

def source_espn_week():

    # 2026 preseason = season type 1
    # ESPN's scoreboard can return the week's events.

    urls = [

        "https://site.api.espn.com/apis/site/v2/"
        "sports/football/nfl/scoreboard"
        "?seasontype=1",

        "https://site.api.espn.com/apis/site/v2/"
        "sports/football/nfl/scoreboard"
        "?seasontype=2"
    ]

    session = make_session()

    for url in urls:

        try:

            r = session.get(
                url,
                timeout=12
            )

            if r.status_code != 200:
                continue

            data = r.json()

            events = data.get(
                "events",
                []
            )

            if events:
                return events, "ESPN WEEK"

        except Exception:
            pass

    return [], None


# ============================================================
# MASTER CALENDAR
# ============================================================

def get_games():

    today = datetime.now(
        TZ
    ).date()

    all_events = []
    used_sources = []
    errors = []

    # --------------------------------------------------------
    # FIRST: exact dates
    # --------------------------------------------------------

    for i in range(8):

        date = today + timedelta(days=i)

        events, source = source_espn(
            date
        )

        if events:

            used_sources.append(source)

            all_events.extend(events)

            continue

        # Try CDN

        events, source = source_espn_cdn(
            date
        )

        if events:

            used_sources.append(source)

            all_events.extend(events)

    # --------------------------------------------------------
    # IF NOTHING WORKED → WEEK SOURCE
    # --------------------------------------------------------

    if not all_events:

        events, source = source_espn_week()

        if events:

            used_sources.append(source)

            all_events.extend(events)

    # --------------------------------------------------------
    # REMOVE DUPLICATES
    # --------------------------------------------------------

    unique = {}

    for event in all_events:

        event_id = event.get(
            "id"
        )

        if event_id:

            unique[event_id] = event

    return (
        list(unique.values()),
        list(set(used_sources)),
        errors
    )


# ============================================================
# MODEL
# ============================================================

def probability(home, away):

    home_elo = ELO.get(
        home,
        1500
    )

    away_elo = ELO.get(
        away,
        1500
    )

    difference = (
        home_elo + 45
    ) - away_elo

    p_home = 1 / (
        1 +
        10 ** (
            -difference / 400
        )
    )

    p_away = 1 - p_home

    return p_home,p_away


# ============================================================
# FAIR ODDS
# ============================================================

def fair_odds(p):

    if p <= 0 or p >= 1:
        return None

    if p >= .5:

        return round(
            -100*p/(1-p)
        )

    return round(
        100*(1-p)/p
    )


# ============================================================
# PROCESS EVENT
# ============================================================

def process_event(event):

    competitions = event.get(
        "competitions",
        []
    )

    if not competitions:
        return None

    competition = competitions[0]

    competitors = competition.get(
        "competitors",
        []
    )

    if len(competitors) < 2:
        return None

    home = None
    away = None

    for c in competitors:

        if c.get("homeAway") == "home":
            home = c

        elif c.get("homeAway") == "away":
            away = c

    if not home or not away:
        return None

    home_raw = home.get(
        "team",
        {}
    ).get(
        "displayName",
        "Home"
    )

    away_raw = away.get(
        "team",
        {}
    ).get(
        "displayName",
        "Away"
    )

    home_name = normalize_team(
        home_raw
    )

    away_name = normalize_team(
        away_raw
    )

    p_home,p_away = probability(
        home_name,
        away_name
    )

    # --------------------------------------------------------
    # PRESEASON SHRINK
    # --------------------------------------------------------

    season = event.get(
        "season",
        {}
    )

    season_type = str(
        season.get(
            "slug",
            ""
        )
    ).lower()

    if "pre" in season_type:

        p_home = .5 + (
            p_home-.5
        )*.55

        p_away = 1-p_home

    # --------------------------------------------------------
    # TIME
    # --------------------------------------------------------

    event_date = event.get(
        "date"
    )

    local_time = None

    if event_date:

        try:

            dt = datetime.fromisoformat(
                event_date.replace(
                    "Z",
                    "+00:00"
                )
            )

            local_time = dt.astimezone(
                TZ
            )

        except Exception:
            pass

    # --------------------------------------------------------
    # STATUS
    # --------------------------------------------------------

    status = event.get(
        "status",
        {}
    )

    status_type = status.get(
        "type",
        {}
    )

    return {

        "id":
            event.get("id"),

        "home":
            home_name,

        "away":
            away_name,

        "home_raw":
            home_raw,

        "away_raw":
            away_raw,

        "home_elo":
            ELO.get(
                home_name,
                1500
            ),

        "away_elo":
            ELO.get(
                away_name,
                1500
            ),

        "p_home":
            p_home,

        "p_away":
            p_away,

        "time":
            local_time,

        "status":
            status_type.get(
                "description",
                ""
            ),

        "season":
            season.get(
                "displayName",
                ""
            )
    }


# ============================================================
# DISPLAY GAME
# ============================================================

def display_game(game):

    st.markdown(
        '<div class="game-card">',
        unsafe_allow_html=True
    )

    if game["time"]:

        st.markdown(
            f"""
            <div class="time-box">
            🕐 Hora Dallas:
            <b>
            {game["time"].strftime(
                "%A %d/%m — %I:%M %p"
            )}
            </b>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.markdown(
        f"""
        <h2>
        🏈 {game["away"]} @ {game["home"]}
        </h2>
        """,
        unsafe_allow_html=True
    )

    col1,col2 = st.columns(2)

    with col1:

        st.markdown(
            f"""
            <div class="team">
            ✈️ {game["away"]}
            </div>

            Probabilidad modelo

            <div class="prob">
            {game["p_away"]*100:.1f}%
            </div>

            🎯 Cuota justa:
            <b>
            {fair_odds(game["p_away"])}
            </b>
            """,
            unsafe_allow_html=True
        )

    with col2:

        st.markdown(
            f"""
            <div class="team">
            🏠 {game["home"]}
            </div>

            Probabilidad modelo

            <div class="prob">
            {game["p_home"]*100:.1f}%
            </div>

            🎯 Cuota justa:
            <b>
            {fair_odds(game["p_home"])}
            </b>
            """,
            unsafe_allow_html=True
        )

    with st.expander(
        "📊 Ver datos del modelo"
    ):

        st.write(
            f'{game["away"]}: '
            f'Elo {game["away_elo"]}'
        )

        st.write(
            f'{game["home"]}: '
            f'Elo {game["home_elo"]}'
        )

        st.write(
            f'Estado: {game["status"]}'
        )

        st.write(
            f'Temporada: {game["season"]}'
        )

    st.markdown(
        "</div>",
        unsafe_allow_html=True
    )


# ============================================================
# HEADER
# ============================================================

st.title(
    "🏈 Monitor NFL"
)

st.subheader(
    "Modelo propio — análisis NFL automático"
)


tab1,tab2,tab3 = st.tabs([
    "🏈 NFL DE HOY",
    "🧪 VALIDACIÓN DEL MODELO",
    "📊 INFORMACIÓN"
])


# ============================================================
# TAB 1
# ============================================================

with tab1:

    st.header(
        "🏈 NFL DE HOY"
    )

    if st.button(
        "🔄 ACTUALIZAR PARTIDOS",
        use_container_width=True
    ):

        st.cache_data.clear()

    games_raw,sources,errors = get_games()

    games = []

    for event in games_raw:

        try:

            game = process_event(
                event
            )

            if game:
                games.append(game)

        except Exception:
            pass

    today = datetime.now(
        TZ
    ).date()

    today_games = []

    upcoming = []

    for game in games:

        if not game["time"]:
            continue

        game_date = game["time"].date()

        if game_date == today:

            today_games.append(game)

        elif (
            today <
            game_date <=
            today+timedelta(days=7)
        ):

            upcoming.append(game)

    # ========================================================
    # SOURCE STATUS
    # ========================================================

    if sources:

        st.markdown(
            f"""
            <div class="success-box">
            ✅ Calendario conectado correctamente.
            <br><br>
            Fuente:
            <b>{", ".join(sources)}</b>
            <br>
            Partidos encontrados:
            <b>{len(games)}</b>
            </div>
            """,
            unsafe_allow_html=True
        )

    # ========================================================
    # TODAY
    # ========================================================

    if today_games:

        st.success(
            f"🏈 {len(today_games)} "
            f"partidos encontrados para hoy."
        )

        for game in sorted(
            today_games,
            key=lambda x:x["time"]
        ):

            display_game(game)

    else:

        st.markdown(
            """
            <div class="warning-box">

            ⚠️ No hay partidos encontrados
            para hoy en la respuesta del calendario.

            </div>
            """,
            unsafe_allow_html=True
        )

    # ========================================================
    # UPCOMING
    # ========================================================

    st.divider()

    st.header(
        "📅 PRÓXIMOS 7 DÍAS"
    )

    if upcoming:

        for game in sorted(
            upcoming,
            key=lambda x:x["time"]
        ):

            display_game(game)

    else:

        st.info(
            "No se encontraron partidos adicionales."
        )

    # ========================================================
    # DEBUG
    # ========================================================

    with st.expander(
        "🔧 Información técnica"
    ):

        st.write(
            "Fecha Dallas:",
            today
        )

        st.write(
            "Fuentes utilizadas:",
            sources
        )

        st.write(
            "Eventos recibidos:",
            len(games_raw)
        )

        if errors:

            st.write(
                errors
            )


# ============================================================
# TAB 2
# ============================================================

with tab2:

    st.header(
        "🧪 Validación del modelo"
    )

    st.markdown(
        """
        <div class="warning-box">

        🎯 <b>Objetivo</b>

        <br><br>

        Si el modelo asigna 70% de probabilidad
        a determinados resultados, queremos comprobar
        que históricamente aproximadamente 70 de cada
        100 terminan ocurriendo.

        <br><br>

        No queremos simplemente acertar mucho.

        Queremos que las probabilidades estén
        <b>bien calibradas</b>.

        </div>
        """,
        unsafe_allow_html=True
    )

    st.subheader(
        "📈 Ejemplo"
    )

    st.table({

        "Probabilidad modelo":[
            "55%",
            "60%",
            "65%",
            "70%",
            "75%",
            "80%",
            "85%",
            "90%"
        ],

        "Resultado esperado":[
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

    st.info(
        """
        La validación real se conectará
        cuando construyamos el histórico
        completo de partidos.
        """
    )


# ============================================================
# TAB 3
# ============================================================

with tab3:

    st.header(
        "📊 Información"
    )

    st.markdown(
        """
        ### 🧠 Modelo actual

        El modelo utiliza:

        • Ratings Elo  
        • Ventaja de local  
        • Probabilidad matemática  
        • Ajuste conservador de pretemporada  
        • Cuota justa americana  

        ### 🔜 Próximos pasos

        1. Calendario automático
        2. Histórico NFL
        3. Ratings calculados por resultados
        4. Lesiones
        5. Forma reciente
        6. Probabilidad calibrada
        7. Cuotas reales
        8. Probabilidad implícita
        9. Edge
        10. Selección de picks

        ### ⚠️ Importante

        Este sistema es experimental.
        Las probabilidades no garantizan resultados futuros.
        """
    )


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    "Monitor NFL — herramienta experimental "
    "de análisis estadístico."
)
