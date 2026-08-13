import streamlit as st
import requests
import math
from datetime import datetime, timezone
from zoneinfo import ZoneInfo


# ============================================================
# CONFIGURACIÓN
# ============================================================

st.set_page_config(
    page_title="Monitor 60% NFL",
    page_icon="🏈",
    layout="centered"
)

API_KEY = st.secrets.get("ODDS_API_KEY", "")

ODDS_URL = (
    "https://api.the-odds-api.com/v4/sports/"
    "americanfootball_nfl/odds"
)

ESPN_TEAMS_URL = (
    "https://site.api.espn.com/apis/site/v2/sports/"
    "football/nfl/teams"
)

DALLAS_TZ = ZoneInfo("America/Chicago")

# Temporada utilizada como base estatística.
# Cuando cambie la temporada, se puede actualizar aquí.
BASE_SEASON = 2025


# ============================================================
# ESTILO
# ============================================================

st.markdown(
    """
    <style>
    .main {
        background-color: #0e0f14;
    }

    .block-container {
        max-width: 900px;
        padding-top: 2rem;
    }

    .title {
        font-size: 42px;
        font-weight: 700;
        margin-bottom: 5px;
    }

    .subtitle {
        color: #9ca0aa;
        font-size: 18px;
        margin-bottom: 30px;
    }

    .pick {
        padding: 22px;
        border-radius: 18px;
        background: #142f23;
        margin-bottom: 20px;
    }

    .pick-title {
        font-size: 26px;
        font-weight: 700;
    }

    .prob {
        font-size: 48px;
        font-weight: 700;
        margin-top: 10px;
    }

    .edge {
        font-size: 24px;
        font-weight: 600;
    }

    .danger {
        background: #3a2024;
        padding: 20px;
        border-radius: 15px;
        margin-top: 20px;
    }

    .info {
        background: #172b43;
        padding: 18px;
        border-radius: 15px;
        margin-top: 20px;
    }

    .small {
        color: #9ca0aa;
        font-size: 14px;
    }
    </style>
    """,
    unsafe_allow_html=True
)


# ============================================================
# FUNCIONES GENERALES
# ============================================================

def american_to_decimal(american):
    """
    Convierte cuota americana a decimal.
    """
    if american is None:
        return None

    try:
        american = float(american)

        if american > 0:
            return 1 + american / 100

        return 1 + 100 / abs(american)

    except Exception:
        return None


def decimal_to_probability(decimal):
    """
    Probabilidad implícita bruta.
    SOLO se usa para comparar contra el mercado.
    NO se utiliza para crear nuestra probabilidad.
    """
    if not decimal or decimal <= 0:
        return None

    return 1 / decimal


def logistic(x):
    """
    Función logística para convertir una diferencia
    de fuerza en probabilidad.
    """
    try:
        return 1 / (1 + math.exp(-x))
    except OverflowError:
        return 0 if x < 0 else 1


# ============================================================
# OBTENER PARTIDOS DE HOY
# ============================================================

@st.cache_data(ttl=120)
def get_today_games():

    if not API_KEY:
        return None, "No se encontró ODDS_API_KEY."

    params = {
        "apiKey": API_KEY,
        "regions": "us",
        "markets": "h2h",
        "oddsFormat": "american"
    }

    try:
        response = requests.get(
            ODDS_URL,
            params=params,
            timeout=20
        )

        if response.status_code != 200:
            return None, (
                f"Error The Odds API: "
                f"{response.status_code} - {response.text[:300]}"
            )

        games = response.json()

        now_dallas = datetime.now(DALLAS_TZ)
        today = now_dallas.date()

        today_games = []

        for game in games:

            commence = game.get("commence_time")

            if not commence:
                continue

            dt = datetime.fromisoformat(
                commence.replace("Z", "+00:00")
            )

            local_dt = dt.astimezone(DALLAS_TZ)

            # SOLO HOY
            if local_dt.date() != today:
                continue

            # No mostrar partidos que ya comenzaron
            if local_dt <= now_dallas:
                continue

            game["local_datetime"] = local_dt

            today_games.append(game)

        today_games.sort(
            key=lambda x: x["local_datetime"]
        )

        return today_games, None

    except Exception as e:
        return None, f"Error obteniendo partidos: {e}"


# ============================================================
# OBTENER EQUIPOS ESPN
# ============================================================

@st.cache_data(ttl=86400)
def get_espn_teams():

    try:

        response = requests.get(
            ESPN_TEAMS_URL,
            timeout=20
        )

        if response.status_code != 200:
            return {}, f"ESPN teams error: {response.status_code}"

        data = response.json()

        teams = {}

        sports = data.get("sports", [])

        for sport in sports:

            leagues = sport.get("leagues", [])

            for league in leagues:

                for item in league.get("teams", []):

                    team = item.get("team", {})

                    abbreviation = team.get("abbreviation")
                    team_id = team.get("id")
                    display_name = team.get("displayName")

                    if abbreviation and team_id:
                        teams[abbreviation.upper()] = {
                            "id": team_id,
                            "name": display_name
                        }

        return teams, None

    except Exception as e:
        return {}, f"Error ESPN teams: {e}"


# ============================================================
# OBTENER HISTORIAL DE UN EQUIPO
# ============================================================

@st.cache_data(ttl=86400)
def get_team_history(team_id):

    url = (
        f"https://site.api.espn.com/apis/site/v2/"
        f"sports/football/nfl/teams/{team_id}/schedule"
    )

    params = {
        "season": BASE_SEASON,
        "seasontype": 2
    }

    try:

        response = requests.get(
            url,
            params=params,
            timeout=20
        )

        if response.status_code != 200:
            return None

        data = response.json()

        games = []

        for event in data.get("events", []):

            competitions = event.get("competitions", [])

            if not competitions:
                continue

            competition = competitions[0]

            competitors = competition.get(
                "competitors",
                []
            )

            if len(competitors) != 2:
                continue

            team_game = None
            opponent_game = None

            for competitor in competitors:

                if competitor.get("team", {}).get("id") == str(team_id):
                    team_game = competitor
                else:
                    opponent_game = competitor

            if not team_game or not opponent_game:
                continue

            try:

                team_score = float(
                    team_game.get("score", 0)
                )

                opponent_score = float(
                    opponent_game.get("score", 0)
                )

            except Exception:
                continue

            games.append({
                "team_score": team_score,
                "opponent_score": opponent_score,
                "home_away": team_game.get("homeAway"),
                "winner": team_game.get("winner", False)
            })

        return games

    except Exception:
        return None


# ============================================================
# CALCULAR FUERZA DEL EQUIPO
# ============================================================

def calculate_team_strength(games):

    if not games:
        return {
            "games": 0,
            "win_rate": 0.50,
            "point_diff": 0,
            "recent_form": 0.50,
            "offense": 0,
            "defense": 0
        }

    # Últimos 10 partidos disponibles
    games = games[-10:]

    wins = 0
    point_diffs = []
    offense = []
    defense = []

    for game in games:

        team_score = game["team_score"]
        opponent_score = game["opponent_score"]

        if team_score > opponent_score:
            wins += 1

        point_diffs.append(
            team_score - opponent_score
        )

        offense.append(team_score)
        defense.append(opponent_score)

    n = len(games)

    win_rate = wins / n

    avg_point_diff = sum(point_diffs) / n

    avg_offense = sum(offense) / n

    avg_defense = sum(defense) / n

    # Más peso a los últimos partidos
    recent = games[-5:]

    recent_wins = sum(
        1
        for g in recent
        if g["team_score"] > g["opponent_score"]
    )

    recent_form = recent_wins / len(recent)

    return {
        "games": n,
        "win_rate": win_rate,
        "point_diff": avg_point_diff,
        "recent_form": recent_form,
        "offense": avg_offense,
        "defense": avg_defense
    }


# ============================================================
# MODELO PROPIO
# ============================================================

def model_probability(home_stats, away_stats):

    """
    IMPORTANTE:

    Esta función NO utiliza cuotas.

    Utiliza únicamente:
    - Win rate
    - Diferencia de puntos
    - Forma reciente
    - Producción ofensiva
    - Defensa

    + ventaja de local.
    """

    # Diferencia de win rate
    win_component = (
        home_stats["win_rate"]
        - away_stats["win_rate"]
    )

    # Diferencia de puntos
    point_component = (
        home_stats["point_diff"]
        - away_stats["point_diff"]
    )

    # Forma reciente
    form_component = (
        home_stats["recent_form"]
        - away_stats["recent_form"]
    )

    # Ataque
    offense_component = (
        home_stats["offense"]
        - away_stats["offense"]
    )

    # Defensa.
    # Si el rival permite más puntos,
    # eso favorece al equipo.
    defense_component = (
        away_stats["defense"]
        - home_stats["defense"]
    )

    # Normalizamos los componentes.
    score = (
        win_component * 2.2
        + (point_component / 20) * 1.7
        + form_component * 1.4
        + (offense_component / 30) * 0.8
        + (defense_component / 30) * 0.8
    )

    # Ventaja de jugar en casa
    score += 0.12

    home_probability = logistic(score)

    # Limitamos para evitar porcentajes absurdamente extremos
    home_probability = max(
        0.52,
        min(0.88, home_probability)
    )

    away_probability = 1 - home_probability

    return home_probability, away_probability


# ============================================================
# OBTENER MEJOR CUOTA DE CADA EQUIPO
# ============================================================

def get_market_odds(game):

    results = {}

    bookmakers = game.get("bookmakers", [])

    for bookmaker in bookmakers:

        bookmaker_name = bookmaker.get(
            "title",
            bookmaker.get("key", "Casa")
        )

        for market in bookmaker.get("markets", []):

            if market.get("key") != "h2h":
                continue

            for outcome in market.get("outcomes", []):

                team = outcome.get("name")
                price = outcome.get("price")

                if team is None or price is None:
                    continue

                if (
                    team not in results
                    or price > results[team]["price"]
                ):
                    results[team] = {
                        "price": price,
                        "bookmaker": bookmaker_name
                    }

    return results


# ============================================================
# ANALIZAR PARTIDO
# ============================================================

def analyze_game(game, teams):

    home = game.get("home_team")
    away = game.get("away_team")

    # Buscar equipos ESPN por nombre
    home_info = None
    away_info = None

    for abbr, info in teams.items():

        if info["name"] == home:
            home_info = info

        if info["name"] == away:
            away_info = info

    # Si no encontramos ESPN, no inventamos estadísticas
    if not home_info or not away_info:
        return None

    home_games = get_team_history(
        home_info["id"]
    )

    away_games = get_team_history(
        away_info["id"]
    )

    home_stats = calculate_team_strength(
        home_games
    )

    away_stats = calculate_team_strength(
        away_games
    )

    # Si no tenemos datos suficientes, no hacemos pick
    if (
        home_stats["games"] < 5
        or away_stats["games"] < 5
    ):
        return None

    home_prob, away_prob = model_probability(
        home_stats,
        away_stats
    )

    market = get_market_odds(game)

    if not market:
        return None

    candidates = []

    for team_name, model_prob in [
        (home, home_prob),
        (away, away_prob)
    ]:

        if team_name not in market:
            continue

        american = market[team_name]["price"]

        decimal = american_to_decimal(
            american
        )

        market_prob = decimal_to_probability(
            decimal
        )

        if market_prob is None:
            continue

        edge = model_prob - market_prob

        candidates.append({
            "team": team_name,
            "opponent": away if team_name == home else home,
            "model_prob": model_prob,
            "market_prob": market_prob,
            "edge": edge,
            "american": american,
            "bookmaker": market[team_name]["bookmaker"],
            "home": team_name == home,
            "game": game
        })

    if not candidates:
        return None

    # La mejor opción del partido
    candidates.sort(
        key=lambda x: x["edge"],
        reverse=True
    )

    best = candidates[0]

    best["home_stats"] = home_stats
    best["away_stats"] = away_stats

    return best


# ============================================================
# INTERFAZ
# ============================================================

st.markdown(
    '<div class="title">🏈 Monitor 60% NFL</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtitle">'
    'Modelo independiente — solo partidos de HOY'
    '</div>',
    unsafe_allow_html=True
)


if not API_KEY:

    st.error(
        "No encontramos ODDS_API_KEY en Secrets."
    )

    st.stop()


# ============================================================
# BOTÓN
# ============================================================

if st.button(
    "🔎 ESCANEAR NFL DE HOY",
    use_container_width=True
):

    with st.spinner(
        "Analizando partidos y estadísticas..."
    ):

        games, error = get_today_games()

        if error:
            st.error(error)
            st.stop()

        if not games:

            st.info(
                "No hay partidos NFL disponibles "
                "para hoy."
            )

            st.stop()

        teams, team_error = get_espn_teams()

        if team_error:

            st.error(team_error)
            st.stop()

        analyzed = []

        for game in games:

            result = analyze_game(
                game,
                teams
            )

            if result:
                analyzed.append(result)

        # Ordenar por ventaja que encuentra el modelo
        analyzed.sort(
            key=lambda x: (
                x["edge"],
                x["model_prob"]
            ),
            reverse=True
        )

        # ====================================================
        # PARTIDOS DE HOY
        # ====================================================

        st.markdown("---")

        st.header(
            f"📅 Partidos de HOY — {len(games)}"
        )

        for game in games:

            local_dt = game["local_datetime"]

            st.write(
                f"🏈 **{game['away_team']} "
                f"vs {game['home_team']}**"
            )

            st.caption(
                f"🕐 {local_dt.strftime('%I:%M %p')}"
            )

        # ====================================================
        # RESULTADOS DEL MODELO
        # ====================================================

        st.markdown("---")

        st.header(
            "🏆 Mejores oportunidades"
        )

        if not analyzed:

            st.warning(
                "No pudimos obtener suficientes "
                "estadísticas independientes para "
                "generar una selección."
            )

            st.stop()

        # Máximo 3
        top3 = analyzed[:3]

        recommendations = []

        for index, pick in enumerate(top3, 1):

            model_pct = pick["model_prob"] * 100
            market_pct = pick["market_prob"] * 100
            edge_pct = pick["edge"] * 100

            game = pick["game"]

            local_dt = game["local_datetime"]

            # Clasificación
            if edge_pct >= 5:
                label = "🟢 APUESTA FUERTE"
            elif edge_pct >= 2:
                label = "🟡 APUESTA INTERESANTE"
            elif edge_pct >= 0:
                label = "🟠 VENTAJA PEQUEÑA"
            else:
                label = "🔴 SIN VENTAJA"

            if (
                model_pct >= 60
                and edge_pct >= 2
            ):
                recommendations.append(pick)

            st.markdown(
                f"""
                <div class="pick">

                <div class="pick-title">
                #{index} {pick['team']}
                </div>

                <p>
                🏈 {pick['opponent']} vs {pick['team']}
                </p>

                <h3>{label}</h3>

                <div>
                Probabilidad Monitor 60%
                </div>

                <div class="prob">
                {model_pct:.1f}%
                </div>

                <div>
                Probabilidad implícita del mercado
                </div>

                <div>
                {market_pct:.1f}%
                </div>

                <div style="margin-top:15px;">
                <b>Edge del modelo</b>
                </div>

                <div class="edge">
                {edge_pct:+.1f}%
                </div>

                <p>
                💰 Cuota: <b>{pick['american']:+}</b>
                </p>

                <p>
                🏦 Mejor cuota:
                <b>{pick['bookmaker']}</b>
                </p>

                <p>
                🕐 Partido:
                <b>{local_dt.strftime('%I:%M %p')}</b>
                </p>

                <p>
                💵 Apuesta de prueba:
                <b>$10</b>
                </p>

                </div>
                """,
                unsafe_allow_html=True
            )

        # ====================================================
        # RESUMEN
        # ====================================================

        st.markdown("---")

        if recommendations:

            st.success(
                f"🎯 {len(recommendations)} "
                f"selección(es) superan los criterios "
                f"del modelo."
            )

            st.write(
                "Estas son las selecciones que nuestro "
                "modelo considera con ventaja frente "
                "al mercado."
            )

        else:

            st.warning(
                "⚠️ Hoy el modelo no encontró una "
                "ventaja suficientemente grande."
            )

            st.write(
                "No significa que esos equipos vayan "
                "a perder. Significa que, con los datos "
                "disponibles, no encontramos suficiente "
                "diferencia entre nuestro modelo y el "
                "mercado."
            )


# ============================================================
# INFORMACIÓN
# ============================================================

st.markdown("---")

st.markdown(
    """
    <div class="info">

    <b>¿Cómo funciona esta versión?</b>

    <br><br>

    🏈 Los partidos y cuotas vienen de The Odds API.

    <br><br>

    📊 Las estadísticas utilizadas para la
    probabilidad vienen de datos históricos de ESPN.

    <br><br>

    🧠 La probabilidad de Monitor 60% se calcula
    <b>sin utilizar las cuotas</b>.

    <br><br>

    💰 Las cuotas solamente se utilizan después
    para calcular el <b>edge</b>.

    <br><br>

    ⚠️ Una probabilidad estimada no garantiza
    el resultado de una apuesta.

    </div>
    """,
    unsafe_allow_html=True
)

st.markdown(
    f"""
    <div class="small">

    Modelo inicial en prueba.
    Temporada estadística base: {BASE_SEASON}.
    Máximo 3 selecciones por día.
    Apuesta experimental de referencia: $10.

    </div>
    """,
    unsafe_allow_html=True
)
