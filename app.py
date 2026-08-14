import streamlit as st
import requests
import math
from datetime import datetime, timezone, timedelta

# ============================================================
# NFL EDGE
# ============================================================
#
# OBJETIVO:
# Mostrar solamente los partidos del día y la probabilidad
# estimada por un modelo independiente.
#
# NO UTILIZA CUOTAS DE SPORTSBOOK PARA GENERAR PROBABILIDADES.
#
# HISTORICO MAXIMO:
#   2025
#   + resultados disponibles de 2026
#
# FACTORES:
#   - Rendimiento histórico
#   - Forma reciente
#   - Diferencial de puntos
#   - ELO
#   - Localía
#   - Lesiones disponibles
#
# ============================================================


# ------------------------------------------------------------
# CONFIGURACION
# ------------------------------------------------------------

st.set_page_config(
    page_title="NFL EDGE",
    page_icon="🏈",
    layout="wide"
)

ESPN_SCOREBOARD = (
    "https://site.api.espn.com/apis/site/v2/sports/"
    "football/nfl/scoreboard"
)

ESPN_TEAM_SCHEDULE = (
    "https://site.api.espn.com/apis/site/v2/sports/"
    "football/nfl/teams/{team}/schedule"
)

ESPN_INJURIES = (
    "https://site.api.espn.com/apis/site/v2/sports/"
    "football/nfl/injuries"
)

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

# Dallas está en UTC-5 durante agosto
DALLAS_TZ = timezone(timedelta(hours=-5))

HISTORICAL_SEASONS = [2025, 2026]


# ------------------------------------------------------------
# EQUIPOS
# ------------------------------------------------------------

TEAMS = {

    "ARI": "arizona-cardinals",
    "ATL": "atlanta-falcons",
    "BAL": "baltimore-ravens",
    "BUF": "buffalo-bills",
    "CAR": "carolina-panthers",
    "CHI": "chicago-bears",
    "CIN": "cincinnati-bengals",
    "CLE": "cleveland-browns",
    "DAL": "dallas-cowboys",
    "DEN": "denver-broncos",
    "DET": "detroit-lions",
    "GB": "green-bay-packers",
    "HOU": "houston-texans",
    "IND": "indianapolis-colts",
    "JAX": "jacksonville-jaguars",
    "KC": "kansas-city-chiefs",
    "LAC": "los-angeles-chargers",
    "LAR": "los-angeles-rams",
    "LV": "las-vegas-raiders",
    "MIA": "miami-dolphins",
    "MIN": "minnesota-vikings",
    "NE": "new-england-patriots",
    "NO": "new-orleans-saints",
    "NYG": "new-york-giants",
    "NYJ": "new-york-jets",
    "PHI": "philadelphia-eagles",
    "PIT": "pittsburgh-steelers",
    "SEA": "seattle-seahawks",
    "SF": "san-francisco-49ers",
    "TB": "tampa-bay-buccaneers",
    "TEN": "tennessee-titans",
    "WSH": "washington-commanders",
}


# ------------------------------------------------------------
# REQUEST
# ------------------------------------------------------------

def get_json(url, params=None, timeout=20):

    try:

        response = requests.get(
            url,
            params=params,
            headers=HEADERS,
            timeout=timeout
        )

        if response.status_code != 200:
            return None

        return response.json()

    except Exception:
        return None


# ------------------------------------------------------------
# FECHA LOCAL
# ------------------------------------------------------------

def today_dallas():

    now = datetime.now(DALLAS_TZ)

    return now.strftime("%Y%m%d")


# ------------------------------------------------------------
# SIGMOID
# ------------------------------------------------------------

def sigmoid(x):

    try:
        return 1 / (1 + math.exp(-x))

    except OverflowError:

        return 0.0 if x < 0 else 1.0


# ============================================================
# PARTIDOS DE HOY
# ============================================================

@st.cache_data(ttl=300)
def get_today_games():

    date_string = today_dallas()

    games = []
    seen = set()

    # ESPN separa:
    #
    # 1 = Pretemporada
    # 2 = Temporada regular
    # 3 = Playoffs

    for season_type in [1, 2, 3]:

        data = get_json(
            ESPN_SCOREBOARD,
            params={
                "dates": date_string,
                "seasontype": season_type,
                "limit": 100,
                "region": "us",
                "lang": "en"
            }
        )

        if not data:
            continue

        for event in data.get("events", []):

            try:

                event_id = event.get("id")

                if not event_id:
                    continue

                if event_id in seen:
                    continue

                competition = event[
                    "competitions"
                ][0]

                competitors = competition.get(
                    "competitors",
                    []
                )

                if len(competitors) != 2:
                    continue

                home = None
                away = None

                for competitor in competitors:

                    team = competitor.get(
                        "team",
                        {}
                    )

                    abbreviation = team.get(
                        "abbreviation"
                    )

                    display_name = team.get(
                        "displayName",
                        abbreviation
                    )

                    if competitor.get(
                        "homeAway"
                    ) == "home":

                        home = {
                            "abbr": abbreviation,
                            "name": display_name
                        }

                    elif competitor.get(
                        "homeAway"
                    ) == "away":

                        away = {
                            "abbr": abbreviation,
                            "name": display_name
                        }

                if not home or not away:
                    continue

                seen.add(event_id)

                if season_type == 1:
                    phase = "PRETEMPORADA"

                elif season_type == 2:
                    phase = "TEMPORADA REGULAR"

                else:
                    phase = "PLAYOFFS"

                games.append({

                    "id": event_id,

                    "date": event.get(
                        "date",
                        ""
                    ),

                    "away": away["abbr"],
                    "away_name": away["name"],

                    "home": home["abbr"],
                    "home_name": home["name"],

                    "phase": phase,

                    "status": event.get(
                        "status",
                        {}
                    )

                )

            except Exception:
                continue

    games.sort(
        key=lambda x: x.get(
            "date",
            ""
        )
    )

    return games


# ============================================================
# HISTORICO DE EQUIPO
# ============================================================

@st.cache_data(ttl=3600)
def get_team_history(
    team_abbr,
    season,
    season_type
):

    if team_abbr not in TEAMS:
        return []

    url = ESPN_TEAM_SCHEDULE.format(
        team=TEAMS[team_abbr]
    )

    data = get_json(
        url,
        params={
            "season": season,
            "seasontype": season_type,
            "limit": 100
        }
    )

    if not data:
        return []

    results = []

    for event in data.get(
        "events",
        []
    ):

        try:

            competition = event[
                "competitions"
            ][0]

            status = competition.get(
                "status",
                {}
            ).get(
                "type",
                {}
            )

            # Solo partidos terminados
            if not status.get(
                "completed",
                False
            ):
                continue

            competitors = competition.get(
                "competitors",
                []
            )

            our_team = None
            opponent = None

            for competitor in competitors:

                abbr = (
                    competitor
                    .get("team", {})
                    .get("abbreviation")
                )

                if abbr == team_abbr:
                    our_team = competitor
                else:
                    opponent = competitor

            if not our_team or not opponent:
                continue

            our_score = float(
                our_team.get(
                    "score",
                    0
                )
            )

            opp_score = float(
                opponent.get(
                    "score",
                    0
                )
            )

            margin = (
                our_score -
                opp_score
            )

            if margin > 0:
                result = "W"

            elif margin < 0:
                result = "L"

            else:
                result = "T"

            results.append({

                "date": event.get(
                    "date",
                    ""
                ),

                "team": team_abbr,

                "opponent": (
                    opponent
                    .get("team", {})
                    .get("abbreviation")
                ),

                "team_score": our_score,

                "opp_score": opp_score,

                "margin": margin,

                "result": result,

                "home": (
                    our_team
                    .get("homeAway")
                    == "home"
                ),

                "season": season,

                "season_type": season_type

            })

        except Exception:
            continue

    return results


# ============================================================
# CONSTRUIR HISTORICO
# ============================================================

@st.cache_data(ttl=3600)
def build_history():

    all_games = []

    for season in HISTORICAL_SEASONS:

        # 1 = pretemporada
        # 2 = temporada regular

        for season_type in [1, 2]:

            for team in TEAMS:

                games = get_team_history(
                    team,
                    season,
                    season_type
                )

                all_games.extend(
                    games
                )

    return all_games


# ============================================================
# ESTADISTICAS
# ============================================================

def get_team_stats(
    team,
    history
):

    games = [
        g for g in history
        if g["team"] == team
    ]

    if not games:

        return {

            "games": 0,
            "wins": 0,
            "losses": 0,
            "ties": 0,

            "win_pct": 0.50,

            "avg_margin": 0.0,

            "recent_margin": 0.0,

            "recent_win_pct": 0.50

        }

    wins = sum(
        1 for g in games
        if g["result"] == "W"
    )

    losses = sum(
        1 for g in games
        if g["result"] == "L"
    )

    ties = sum(
        1 for g in games
        if g["result"] == "T"
    )

    win_pct = (
        wins + ties * 0.5
    ) / len(games)

    avg_margin = (
        sum(
            g["margin"]
            for g in games
        )
        / len(games)
    )

    games_sorted = sorted(
        games,
        key=lambda x: x.get(
            "date",
            ""
        )
    )

    recent = games_sorted[-8:]

    if recent:

        recent_margin = (
            sum(
                g["margin"]
                for g in recent
            )
            / len(recent)
        )

        recent_win_pct = (
            sum(
                1
                for g in recent
                if g["result"] == "W"
            )
            +
            0.5 * sum(
                1
                for g in recent
                if g["result"] == "T"
            )
        ) / len(recent)

    else:

        recent_margin = 0.0
        recent_win_pct = 0.50

    return {

        "games": len(games),

        "wins": wins,

        "losses": losses,

        "ties": ties,

        "win_pct": win_pct,

        "avg_margin": avg_margin,

        "recent_margin": recent_margin,

        "recent_win_pct": recent_win_pct

    }


# ============================================================
# ELO
# ============================================================

def build_elo(history):

    elo = {
        team: 1500.0
        for team in TEAMS
    }

    # Evita utilizar resultados futuros
    games = sorted(
        history,
        key=lambda x: x.get(
            "date",
            ""
        )
    )

    processed = set()

    for game in games:

        team = game["team"]
        opponent = game["opponent"]

        if not opponent:
            continue

        if opponent not in elo:
            continue

        # Cada partido aparece dos veces:
        # una desde cada equipo.
        #
        # Identificamos por fecha + equipos.
        key = tuple(
            sorted([
                team,
                opponent
            ])
        ) + (
            game.get(
                "date",
                ""
            ),
        )

        if key in processed:
            continue

        processed.add(key)

        team_elo = elo[team]
        opponent_elo = elo[opponent]

        # Localía
        home_bonus = (
            55
            if game["home"]
            else -55
        )

        expected = sigmoid(
            (
                team_elo
                + home_bonus
                - opponent_elo
            )
            / 400
        )

        if game["result"] == "W":
            actual = 1.0

        elif game["result"] == "L":
            actual = 0.0

        else:
            actual = 0.5

        margin = abs(
            game["margin"]
        )

        if margin >= 14:
            k = 24

        elif margin >= 7:
            k = 22

        else:
            k = 20

        change = k * (
            actual - expected
        )

        elo[team] += change
        elo[opponent] -= change

    return elo


# ============================================================
# LESIONES
# ============================================================

@st.cache_data(ttl=900)
def get_injuries():

    data = get_json(
        ESPN_INJURIES,
        params={
            "limit": 500
        }
    )

    if not data:
        return {}

    injuries = {}

    # ESPN puede cambiar la estructura.
    # Intentamos manejar las estructuras habituales.

    teams_data = data.get(
        "teams",
        []
    )

    for team_data in teams_data:

        try:

            team_abbr = (
                team_data
                .get("team", {})
                .get("abbreviation")
            )

            if not team_abbr:
                continue

            team_injuries = (
                team_data
                .get("injuries", [])
            )

            for injury in team_injuries:

                athlete = injury.get(
                    "athlete",
                    {}
                )

                name = athlete.get(
                    "displayName",
                    "Jugador"
                )

                status = str(
                    injury.get(
                        "status",
                        ""
                    )
                ).lower()

                position = (
                    athlete
                    .get("position", {})
                    .get("abbreviation", "")
                )

                severity = 0

                if "out" in status:
                    severity = 3

                elif "doubtful" in status:
                    severity = 2

                elif "questionable" in status:
                    severity = 1

                if severity <= 0:
                    continue

                # QB pesa más porque su ausencia
                # suele tener mayor impacto.
                if position == "QB":
                    severity *= 2

                injuries.setdefault(
                    team_abbr,
                    []
                ).append({

                    "name": name,

                    "status": status,

                    "position": position,

                    "severity": severity

                })

        except Exception:
            continue

    return injuries


def injury_score(
    team,
    injuries
):

    items = injuries.get(
        team,
        []
    )

    if not items:
        return 0.0

    total = sum(
        x["severity"]
        for x in items
    )

    return min(
        total,
        10.0
    )


# ============================================================
# MODELO
# ============================================================

def predict_game(
    away,
    home,
    history,
    elo,
    injuries,
    phase
):

    away_stats = get_team_stats(
        away,
        history
    )

    home_stats = get_team_stats(
        home,
        history
    )

    away_elo = elo.get(
        away,
        1500
    )

    home_elo = elo.get(
        home,
        1500
    )

    # --------------------------------------------------------
    # 1. ELO
    # --------------------------------------------------------

    elo_difference = (
        home_elo -
        away_elo
    )

    # --------------------------------------------------------
    # 2. DIFERENCIAL DE PUNTOS
    # --------------------------------------------------------

    margin_difference = (
        home_stats["avg_margin"]
        -
        away_stats["avg_margin"]
    )

    # --------------------------------------------------------
    # 3. FORMA RECIENTE
    # --------------------------------------------------------

    recent_difference = (
        home_stats["recent_margin"]
        -
        away_stats["recent_margin"]
    )

    # --------------------------------------------------------
    # 4. WIN %
    # --------------------------------------------------------

    win_difference = (
        home_stats["win_pct"]
        -
        away_stats["win_pct"]
    )

    # --------------------------------------------------------
    # 5. LESIONES
    # --------------------------------------------------------

    home_injury = injury_score(
        home,
        injuries
    )

    away_injury = injury_score(
        away,
        injuries
    )

    injury_difference = (
        away_injury -
        home_injury
    )

    # --------------------------------------------------------
    # PRETEMPORADA
    # --------------------------------------------------------
    #
    # En pretemporada NO queremos darle demasiado peso
    # a resultados porque los titulares pueden jugar poco.
    #
    # Por eso reducimos el peso estadístico.
    # --------------------------------------------------------

    if phase == "PRETEMPORADA":

        elo_weight = 0.35
        margin_weight = 3.0
        recent_weight = 2.0
        win_weight = 0.30
        home_bonus = 35
        injury_weight = 7.0

    else:

        elo_weight = 0.60
        margin_weight = 7.0
        recent_weight = 5.0
        win_weight = 0.80
        home_bonus = 55
        injury_weight = 8.0

    # --------------------------------------------------------
    # SCORE
    # --------------------------------------------------------

    score = (

        elo_difference
        * elo_weight

        +

        margin_difference
        * margin_weight

        +

        recent_difference
        * recent_weight

        +

        win_difference
        * 100
        * win_weight

        +

        home_bonus

        +

        injury_difference
        * injury_weight

    )

    # --------------------------------------------------------
    # PROBABILIDAD HOME
    # --------------------------------------------------------

    home_probability = sigmoid(
        score / 400
    )

    # Limites para evitar resultados absurdos
    home_probability = max(
        0.05,
        min(
            0.95,
            home_probability
        )
    )

    away_probability = (
        1 -
        home_probability
    )

    if home_probability >= 0.50:

        pick = home
        probability = home_probability

    else:

        pick = away
        probability = away_probability

    return {

        "pick": pick,

        "probability": probability,

        "home_probability":
            home_probability,

        "away_probability":
            away_probability,

        "away_stats":
            away_stats,

        "home_stats":
            home_stats,

        "away_elo":
            away_elo,

        "home_elo":
            home_elo,

        "away_injury":
            away_injury,

        "home_injury":
            home_injury

    }


# ============================================================
# INTERFAZ
# ============================================================

st.title("🏈 NFL EDGE")

st.subheader(
    "Modelo independiente del mercado"
)

st.write(
    "Probabilidad estimada con datos deportivos, "
    "sin utilizar cuotas de sportsbooks."
)

st.warning(
    "🚫 Las cuotas de sportsbooks NO se utilizan "
    "para generar las probabilidades."
)

st.caption(
    "Histórico máximo: 2025 + resultados disponibles de 2026."
)

st.divider()


# ============================================================
# CARGAR DATOS
# ============================================================

with st.spinner(
    "Analizando datos NFL..."
):

    games = get_today_games()

    history = build_history()

    elo = build_elo(
        history
    )

    injuries = get_injuries()


# ============================================================
# PARTIDOS DE HOY
# ============================================================

st.header(
    "🏈 PARTIDOS DE HOY"
)


if not games:

    st.info(
        "No se encontraron partidos NFL para hoy."
    )

    st.caption(
        "La aplicación consulta pretemporada, "
        "temporada regular y playoffs."
    )

else:

    st.success(
        f"{len(games)} partido(s) encontrado(s)."
    )

    for game in games:

        away = game["away"]
        home = game["home"]
        phase = game["phase"]

        prediction = predict_game(
            away,
            home,
            history,
            elo,
            injuries,
            phase
        )

        pick = prediction["pick"]

        probability = (
            prediction["probability"]
            * 100
        )

        st.divider()

        # ----------------------------------------------------
        # PARTIDO
        # ----------------------------------------------------

        st.subheader(
            f"🏈 {away} @ {home}"
        )

        st.caption(
            f"{game['away_name']} @ "
            f"{game['home_name']} · "
            f"{phase}"
        )

        # ----------------------------------------------------
        # RESULTADO PRINCIPAL
        # ----------------------------------------------------

        col1, col2, col3 = st.columns(3)

        with col1:

            st.metric(
                "PICK",
                pick
            )

        with col2:

            st.metric(
                "PROBABILIDAD",
                f"{probability:.1f}%"
            )

        with col3:

            if probability >= 70:

                signal = "🔥 MUY FUERTE"

            elif probability >= 65:

                signal = "🟢 FUERTE"

            elif probability >= 60:

                signal = "🟢 INTERESANTE"

            elif probability >= 55:

                signal = "🟡 MODERADA"

            else:

                signal = "⚪ CERRADO"

            st.metric(
                "SEÑAL",
                signal
            )

        # ----------------------------------------------------
        # FRASE PRINCIPAL
        # ----------------------------------------------------

        st.write(
            f"### El modelo estima **{probability:.1f}%** "
            f"para que **{pick}** gane."
        )

        st.caption(
            "Después tú comparas este porcentaje con "
            "la cuota que te ofrece tu sportsbook."
        )

        # ----------------------------------------------------
        # FACTORES
        # ----------------------------------------------------

        with st.expander(
            "📊 Ver factores utilizados"
        ):

            c1, c2 = st.columns(2)

            with c1:

                st.markdown(
                    f"### {away}"
                )

                stats = prediction[
                    "away_stats"
                ]

                st.write(
                    f"Partidos analizados: "
                    f"**{stats['games']}**"
                )

                st.write(
                    f"Récord: "
                    f"**{stats['wins']}-"
                    f"{stats['losses']}-"
                    f"{stats['ties']}**"
                )

                st.write(
                    f"Win %: "
                    f"**{stats['win_pct']*100:.1f}%**"
                )

                st.write(
                    f"Diferencial promedio: "
                    f"**{stats['avg_margin']:+.1f}**"
                )

                st.write(
                    f"Forma reciente: "
                    f"**{stats['recent_margin']:+.1f}**"
                )

                st.write(
                    f"ELO: "
                    f"**{prediction['away_elo']:.0f}**"
                )

                st.write(
                    f"Impacto lesiones: "
                    f"**{prediction['away_injury']:.1f}**"
                )

            with c2:

                st.markdown(
                    f"### {home}"
                )

                stats = prediction[
                    "home_stats"
                ]

                st.write(
                    f"Partidos analizados: "
                    f"**{stats['games']}**"
                )

                st.write(
                    f"Récord: "
                    f"**{stats['wins']}-"
                    f"{stats['losses']}-"
                    f"{stats['ties']}**"
                )

                st.write(
                    f"Win %: "
                    f"**{stats['win_pct']*100:.1f}%**"
                )

                st.write(
                    f"Diferencial promedio: "
                    f"**{stats['avg_margin']:+.1f}**"
                )

                st.write(
                    f"Forma reciente: "
                    f"**{stats['recent_margin']:+.1f}**"
                )

                st.write(
                    f"ELO: "
                    f"**{prediction['home_elo']:.0f}**"
                )

                st.write(
                    f"Impacto lesiones: "
                    f"**{prediction['home_injury']:.1f}**"
                )

        # ----------------------------------------------------
        # LESIONES
        # ----------------------------------------------------

        relevant_injuries = []

        for team in [away, home]:

            for injury in injuries.get(
                team,
                []
            ):

                relevant_injuries.append(
                    (
                        team,
                        injury
                    )
                )

        if relevant_injuries:

            with st.expander(
                "🏥 Lesiones relevantes"
            ):

                for team, injury in (
                    relevant_injuries
                ):

                    st.write(
                        f"**{team}** — "
                        f"{injury['name']} "
                        f"({injury['position']}) — "
                        f"{injury['status']}"
                    )

        # ----------------------------------------------------
        # EXPLICACION
        # ----------------------------------------------------

        if probability >= 65:

            st.success(
                "🔥 El modelo encuentra una señal "
                "relativamente fuerte."
            )

        elif probability >= 58:

            st.info(
                "🟢 El modelo ve una ligera "
                "ventaja."
            )

        else:

            st.warning(
                "⚪ El modelo considera que es "
                "un partido bastante cerrado."
            )


# ============================================================
# EXPLICACION
# ============================================================

st.divider()

st.header(
    "🧠 ¿Qué significa el porcentaje?"
)

st.write(
    """
El porcentaje es una **estimación del modelo**, no una garantía.

Por ejemplo:

**Modelo: 70%**

Significa que, según los datos utilizados por el modelo,
el equipo tiene aproximadamente 70% de probabilidad de ganar.

La aplicación NO mira primero la cuota para decidir ese número.

La idea es:

**Datos deportivos → Modelo → Probabilidad**

y después:

**Probabilidad del modelo → tú comparas con la casa**
"""
)

st.info(
    "🎯 El objetivo de NFL EDGE es darte una segunda "
    "opinión independiente del mercado."
)

st.caption(
    "NFL EDGE — Modelo experimental independiente. "
    "No garantiza resultados."
)
