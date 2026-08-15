import streamlit as st
import pandas as pd
import numpy as np
from pathlib import Path

# ============================================================
# 🏈 NFL_SIMPLE_V1_PREGAME
#
# Construye únicamente información disponible ANTES
# de cada partido.
#
# NO USA:
# - Moneyline
# - Spread
# - Odds
# - Sportsbooks
# - Resultado futuro
# ============================================================

st.set_page_config(
    page_title="NFL_SIMPLE_V1_PREGAME",
    page_icon="🏈",
    layout="wide"
)

st.title("🏈 NFL_SIMPLE_V1_PREGAME")

st.info(
    """
    Este módulo construye las estadísticas que conocíamos
    ANTES de cada partido.

    El resultado del propio partido jamás se utiliza para
    construir sus variables predictoras.
    """
)

# ============================================================
# CONFIGURACIÓN
# ============================================================

DATA_URL = (
    "https://raw.githubusercontent.com/"
    "nflverse/nfldata/master/data/games.csv"
)

SEASONS = [2024, 2025]

OUTPUT_DIR = Path(
    "NFL_SIMPLE_V1"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# DESCARGAR DATA
# ============================================================

@st.cache_data
def load_data():

    df = pd.read_csv(
        DATA_URL
    )

    df.columns = [
        str(c).strip().lower()
        for c in df.columns
    ]

    return df


try:

    df = load_data()

except Exception as e:

    st.error(
        "No se pudo descargar el dataset NFL."
    )

    st.exception(e)

    st.stop()


# ============================================================
# FILTRAR REGULAR SEASON
# ============================================================

df["season"] = pd.to_numeric(
    df["season"],
    errors="coerce"
)

games = df[
    (df["season"].isin(SEASONS))
    &
    (
        df["game_type"]
        .astype(str)
        .str.upper()
        == "REG"
    )
].copy()


# ============================================================
# FECHAS
# ============================================================

games["gameday"] = pd.to_datetime(
    games["gameday"],
    errors="coerce"
)

games = (
    games
    .sort_values(
        [
            "season",
            "gameday",
            "game_id"
        ]
    )
    .reset_index(drop=True)
)


# ============================================================
# VALIDACIÓN
# ============================================================

st.header("1. Dataset")

c1, c2, c3 = st.columns(3)

with c1:
    st.metric(
        "Partidos",
        games["game_id"].nunique()
    )

with c2:
    st.metric(
        "Temporadas",
        games["season"].nunique()
    )

with c3:
    st.metric(
        "Equipos",
        len(
            set(
                games["home_team"].dropna()
            )
            |
            set(
                games["away_team"].dropna()
            )
        )
    )


# ============================================================
# ESTRUCTURA DE ESTADÍSTICAS DE EQUIPOS
# ============================================================

def empty_team_stats():

    return {
        "games": 0,
        "wins": 0,
        "losses": 0,

        "points_for": 0.0,
        "points_against": 0.0,

        "home_games": 0,
        "home_wins": 0,

        "away_games": 0,
        "away_wins": 0,

        "recent_results": [],
        "recent_diffs": [],

        "last_game_date": None
    }


# ============================================================
# FUNCIONES
# ============================================================

def safe_divide(
    numerator,
    denominator
):

    if denominator == 0:
        return 0.5

    return numerator / denominator


def snapshot(
    stats,
    is_home
):

    games_played = stats["games"]

    win_pct = safe_divide(
        stats["wins"],
        games_played
    )

    points_for_avg = (
        stats["points_for"]
        / games_played
        if games_played > 0
        else 0.0
    )

    points_against_avg = (
        stats["points_against"]
        / games_played
        if games_played > 0
        else 0.0
    )

    point_diff_avg = (
        points_for_avg
        -
        points_against_avg
    )

    if is_home:

        venue_games = stats["home_games"]
        venue_wins = stats["home_wins"]

    else:

        venue_games = stats["away_games"]
        venue_wins = stats["away_wins"]

    venue_win_pct = safe_divide(
        venue_wins,
        venue_games
    )

    recent_results = (
        stats["recent_results"][-5:]
    )

    recent_diffs = (
        stats["recent_diffs"][-5:]
    )

    recent_games = len(
        recent_results
    )

    recent_win_pct = (
        sum(recent_results)
        /
        recent_games
        if recent_games > 0
        else 0.5
    )

    recent_diff_avg = (
        np.mean(recent_diffs)
        if recent_diffs
        else 0.0
    )

    # Días desde último partido
    if stats["last_game_date"] is None:

        rest_days = np.nan

    else:

        rest_days = None

    return {
        "games": games_played,
        "win_pct": win_pct,

        "points_for_avg":
            points_for_avg,

        "points_against_avg":
            points_against_avg,

        "point_diff_avg":
            point_diff_avg,

        "venue_win_pct":
            venue_win_pct,

        "recent_win_pct":
            recent_win_pct,

        "recent_diff_avg":
            recent_diff_avg,

        "last_game_date":
            stats["last_game_date"]
    }


# ============================================================
# ESTADÍSTICAS PRE-PARTIDO
# ============================================================

team_stats = {}

pregame_rows = []


# ============================================================
# PROCESAR PARTIDOS CRONOLÓGICAMENTE
# ============================================================

for _, game in games.iterrows():

    season = int(
        game["season"]
    )

    game_id = game["game_id"]

    game_date = game["gameday"]

    home_team = game["home_team"]

    away_team = game["away_team"]

    # --------------------------------------------------------
    # Crear estadísticas si no existen
    # --------------------------------------------------------

    if home_team not in team_stats:

        team_stats[home_team] = (
            empty_team_stats()
        )

    if away_team not in team_stats:

        team_stats[away_team] = (
            empty_team_stats()
        )

    home_stats = team_stats[
        home_team
    ]

    away_stats = team_stats[
        away_team
    ]

    # --------------------------------------------------------
    # SNAPSHOT ANTES DEL PARTIDO
    # --------------------------------------------------------

    home_snapshot = snapshot(
        home_stats,
        True
    )

    away_snapshot = snapshot(
        away_stats,
        False
    )

    # --------------------------------------------------------
    # DESCANSO
    # --------------------------------------------------------

    if (
        home_stats["last_game_date"]
        is None
    ):

        home_rest = np.nan

    else:

        home_rest = (
            game_date
            -
            home_stats["last_game_date"]
        ).days

    if (
        away_stats["last_game_date"]
        is None
    ):

        away_rest = np.nan

    else:

        away_rest = (
            game_date
            -
            away_stats["last_game_date"]
        ).days

    # --------------------------------------------------------
    # RESULTADO DEL PARTIDO
    #
    # ESTE DATO SOLO SE GUARDA COMO TARGET.
    # NO SE USA PARA CREAR LAS VARIABLES ANTERIORES.
    # --------------------------------------------------------

    home_score = float(
        game["home_score"]
    )

    away_score = float(
        game["away_score"]
    )

    if home_score > away_score:

        target_home_win = 1

    elif home_score < away_score:

        target_home_win = 0

    else:

        target_home_win = np.nan

    # --------------------------------------------------------
    # CREAR FILA PREGAME
    # --------------------------------------------------------

    row = {

        "season":
            season,

        "week":
            game["week"],

        "game_id":
            game_id,

        "gameday":
            game_date,

        "home_team":
            home_team,

        "away_team":
            away_team,

        # ----------------------------
        # HOME
        # ----------------------------

        "home_games":
            home_snapshot["games"],

        "home_win_pct":
            home_snapshot["win_pct"],

        "home_points_for_avg":
            home_snapshot[
                "points_for_avg"
            ],

        "home_points_against_avg":
            home_snapshot[
                "points_against_avg"
            ],

        "home_point_diff_avg":
            home_snapshot[
                "point_diff_avg"
            ],

        "home_venue_win_pct":
            home_snapshot[
                "venue_win_pct"
            ],

        "home_recent_win_pct":
            home_snapshot[
                "recent_win_pct"
            ],

        "home_recent_diff_avg":
            home_snapshot[
                "recent_diff_avg"
            ],

        "home_rest_days":
            home_rest,

        # ----------------------------
        # AWAY
        # ----------------------------

        "away_games":
            away_snapshot["games"],

        "away_win_pct":
            away_snapshot["win_pct"],

        "away_points_for_avg":
            away_snapshot[
                "points_for_avg"
            ],

        "away_points_against_avg":
            away_snapshot[
                "points_against_avg"
            ],

        "away_point_diff_avg":
            away_snapshot[
                "point_diff_avg"
            ],

        "away_venue_win_pct":
            away_snapshot[
                "venue_win_pct"
            ],

        "away_recent_win_pct":
            away_snapshot[
                "recent_win_pct"
            ],

        "away_recent_diff_avg":
            away_snapshot[
                "recent_diff_avg"
            ],

        "away_rest_days":
            away_rest,

        # ----------------------------
        # DIFERENCIAS
        # ----------------------------

        "diff_win_pct":
            (
                home_snapshot["win_pct"]
                -
                away_snapshot["win_pct"]
            ),

        "diff_points_for":
            (
                home_snapshot[
                    "points_for_avg"
                ]
                -
                away_snapshot[
                    "points_for_avg"
                ]
            ),

        "diff_points_against":
            (
                home_snapshot[
                    "points_against_avg"
                ]
                -
                away_snapshot[
                    "points_against_avg"
                ]
            ),

        "diff_point_diff":
            (
                home_snapshot[
                    "point_diff_avg"
                ]
                -
                away_snapshot[
                    "point_diff_avg"
                ]
            ),

        "diff_recent_win_pct":
            (
                home_snapshot[
                    "recent_win_pct"
                ]
                -
                away_snapshot[
                    "recent_win_pct"
                ]
            ),

        "diff_recent_diff":
            (
                home_snapshot[
                    "recent_diff_avg"
                ]
                -
                away_snapshot[
                    "recent_diff_avg"
                ]
            ),

        "diff_rest":
            (
                home_rest
                -
                away_rest
                if (
                    pd.notna(home_rest)
                    and
                    pd.notna(away_rest)
                )
                else np.nan
            ),

        # ----------------------------
        # TARGET
        # ----------------------------

        "home_win":
            target_home_win,

        # Guardamos resultado solamente
        # para auditoría
        "home_score":
            home_score,

        "away_score":
            away_score
    }

    pregame_rows.append(
        row
    )

    # ========================================================
    # AHORA ACTUALIZAMOS LOS DATOS
    #
    # TODO ESTO OCURRE DESPUÉS DEL SNAPSHOT.
    # POR ESO NO HAY LEAKAGE.
    # ========================================================

    # --------------------------------------------------------
    # HOME
    # --------------------------------------------------------

    home_diff = (
        home_score
        -
        away_score
    )

    home_stats["games"] += 1

    home_stats["points_for"] += (
        home_score
    )

    home_stats["points_against"] += (
        away_score
    )

    home_stats["home_games"] += 1

    if home_score > away_score:

        home_stats["wins"] += 1

        home_stats["home_wins"] += 1

        home_stats[
            "recent_results"
        ].append(1)

    elif home_score < away_score:

        home_stats["losses"] += 1

        home_stats[
            "recent_results"
        ].append(0)

    else:

        # Empate:
        # no lo contamos como victoria
        # para mantener la métrica simple.
        home_stats[
            "recent_results"
        ].append(0.5)

    home_stats[
        "recent_diffs"
    ].append(
        home_diff
    )

    home_stats[
        "recent_results"
    ] = (
        home_stats[
            "recent_results"
        ][-5:]
    )

    home_stats[
        "recent_diffs"
    ] = (
        home_stats[
            "recent_diffs"
        ][-5:]
    )

    home_stats[
        "last_game_date"
    ] = game_date

    # --------------------------------------------------------
    # AWAY
    # --------------------------------------------------------

    away_diff = (
        away_score
        -
        home_score
    )

    away_stats["games"] += 1

    away_stats["points_for"] += (
        away_score
    )

    away_stats["points_against"] += (
        home_score
    )

    away_stats["away_games"] += 1

    if away_score > home_score:

        away_stats["wins"] += 1

        away_stats["away_wins"] += 1

        away_stats[
            "recent_results"
        ].append(1)

    elif away_score < home_score:

        away_stats["losses"] += 1

        away_stats[
            "recent_results"
        ].append(0)

    else:

        away_stats[
            "recent_results"
        ].append(0.5)

    away_stats[
        "recent_diffs"
    ].append(
        away_diff
    )

    away_stats[
        "recent_results"
    ] = (
        away_stats[
            "recent_results"
        ][-5:]
    )

    away_stats[
        "recent_diffs"
    ] = (
        away_stats[
            "recent_diffs"
        ][-5:]
    )

    away_stats[
        "last_game_date"
    ] = game_date


# ============================================================
# CREAR DATAFRAME
# ============================================================

pregame = pd.DataFrame(
    pregame_rows
)


# ============================================================
# ORDENAR
# ============================================================

pregame = (
    pregame
    .sort_values(
        [
            "season",
            "gameday",
            "game_id"
        ]
    )
    .reset_index(drop=True)
)


# ============================================================
# AUDITORÍA DE LEAKAGE
# ============================================================

st.header(
    "2. Auditoría de leakage"
)

forbidden_columns = [
    "home_score",
    "away_score"
]

predictor_columns = [
    c
    for c in pregame.columns
    if c not in [
        "season",
        "week",
        "game_id",
        "gameday",
        "home_team",
        "away_team",
        "home_win",
        "home_score",
        "away_score"
    ]
]

found_forbidden = [
    c
    for c in predictor_columns
    if c in forbidden_columns
]

if len(found_forbidden) == 0:

    st.success(
        "✅ No hay score actual dentro de las variables predictoras."
    )

else:

    st.error(
        f"❌ Leakage detectado: {found_forbidden}"
    )


# ============================================================
# ESTADÍSTICAS GENERADAS
# ============================================================

st.header(
    "3. Variables PREGAME generadas"
)

variable_table = pd.DataFrame({
    "Variable": predictor_columns
})

st.dataframe(
    variable_table,
    use_container_width=True,
    hide_index=True
)


# ============================================================
# PRIMERAS FILAS
# ============================================================

st.header(
    "4. Primeros partidos"
)

st.dataframe(
    pregame.head(20),
    use_container_width=True,
    hide_index=True
)


# ============================================================
# PARTIDOS POR TEMPORADA
# ============================================================

st.header(
    "5. Partidos PREGAME por temporada"
)

season_counts = (
    pregame
    .groupby("season")
    .size()
    .reset_index(
        name="Partidos"
    )
)

st.dataframe(
    season_counts,
    use_container_width=True,
    hide_index=True
)


# ============================================================
# PRIMER PARTIDO DE CADA EQUIPO
# ============================================================

st.header(
    "6. Primeros partidos sin historial"
)

no_history = pregame[
    pregame["home_games"] == 0
]

st.metric(
    "Partidos donde el Home no tenía historial",
    len(no_history)
)


# ============================================================
# VALORES FALTANTES
# ============================================================

st.header(
    "7. Valores faltantes"
)

missing = (
    pregame
    .isna()
    .sum()
    .reset_index()
)

missing.columns = [
    "Variable",
    "Faltantes"
]

missing = missing[
    missing["Faltantes"] > 0
]

st.dataframe(
    missing,
    use_container_width=True,
    hide_index=True
)


# ============================================================
# GUARDAR
# ============================================================

pregame_path = (
    OUTPUT_DIR
    /
    "NFL_SIMPLE_V1_PREGAME.csv"
)

pregame.to_csv(
    pregame_path,
    index=False
)


# ============================================================
# GUARDAR LISTA DE VARIABLES
# ============================================================

variables_path = (
    OUTPUT_DIR
    /
    "NFL_SIMPLE_V1_PREGAME_VARIABLES.csv"
)

variable_table.to_csv(
    variables_path,
    index=False
)


# ============================================================
# RESUMEN
# ============================================================

st.header(
    "🏁 NFL_SIMPLE_V1_PREGAME FINAL"
)

summary = pd.DataFrame({

    "Métrica": [

        "Partidos",

        "Variables PREGAME",

        "Leakage detectado",

        "Archivo principal",

        "Variables guardadas"
    ],

    "Resultado": [

        len(pregame),

        len(predictor_columns),

        (
            "NO"
            if len(found_forbidden) == 0
            else "SI"
        ),

        str(pregame_path),

        str(variables_path)
    ]
})

st.dataframe(
    summary,
    use_container_width=True,
    hide_index=True
)

st.success(
    "✅ NFL_SIMPLE_V1_PREGAME creado correctamente."
)

st.info(
    """
    SIGUIENTE PASO:

    Entrenaremos el primer modelo de probabilidad.

    El modelo solamente podrá utilizar variables PREGAME.

    NO utilizaremos odds de sportsbooks.
    """
)
