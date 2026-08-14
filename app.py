import math
from datetime import date, datetime

import numpy as np
import pandas as pd
import requests
import streamlit as st


# ============================================================
# NFL EDGE
# MODELO INDEPENDIENTE DE PROBABILIDAD
#
# HISTORICO:
#   2025 + 2026 disponible
#
# IMPORTANTE:
#   Las cuotas de las casas NO se utilizan para calcular
#   la probabilidad del modelo.
#
# EL MODELO CONSIDERA:
#   - rendimiento reciente
#   - ofensiva
#   - defensa
#   - margen de puntos
#   - victorias recientes
#   - localía
#   - descanso
#   - clima cuando está disponible
#   - lesiones actuales cuando están disponibles
# ============================================================


# ============================================================
# CONFIGURACIÓN
# ============================================================

st.set_page_config(
    page_title="NFL EDGE",
    page_icon="🏈",
    layout="wide"
)

GAMES_URL = (
    "https://raw.githubusercontent.com/"
    "leesharpe/nfldata/master/data/games.csv"
)

ESPN_SCOREBOARD = (
    "https://site.api.espn.com/"
    "apis/site/v2/sports/football/nfl/scoreboard"
)

ESPN_INJURIES = (
    "https://site.api.espn.com/"
    "apis/site/v2/sports/football/nfl/injuries"
)

HISTORICAL_SEASONS = [2025, 2026]

ROLLING_GAMES = 5


# ============================================================
# NORMALIZACIÓN DE EQUIPOS
# ============================================================

TEAM_MAP = {
    "JAC": "JAX",
    "STL": "LA",
    "SL": "LA",
    "LAR": "LA",
    "LA": "LA",
    "ARZ": "ARI",
    "BLT": "BAL",
    "CLV": "CLE",
    "HST": "HOU",
    "SD": "LAC",
    "OAK": "LV",
}


def normalize_team(team):

    if pd.isna(team):
        return team

    team = str(
        team
    ).upper().strip()

    return TEAM_MAP.get(
        team,
        team
    )


# ============================================================
# CARGAR DATOS NFL
# ============================================================

@st.cache_data(
    ttl=1800,
    show_spinner=False
)
def load_games():

    df = pd.read_csv(
        GAMES_URL
    )

    df.columns = [
        str(c).strip()
        for c in df.columns
    ]

    for col in [
        "away_team",
        "home_team"
    ]:

        if col in df.columns:

            df[col] = (
                df[col]
                .map(normalize_team)
            )

    df["season"] = pd.to_numeric(
        df["season"],
        errors="coerce"
    )

    df["gameday"] = pd.to_datetime(
        df["gameday"],
        errors="coerce"
    )

    df["away_score"] = pd.to_numeric(
        df["away_score"],
        errors="coerce"
    )

    df["home_score"] = pd.to_numeric(
        df["home_score"],
        errors="coerce"
    )

    # --------------------------------
    # SOLO 2025 + 2026
    # --------------------------------

    df = df[
        df["season"].isin(
            HISTORICAL_SEASONS
        )
    ].copy()

    # --------------------------------
    # SOLO TEMPORADA REGULAR
    # --------------------------------

    if "game_type" in df.columns:

        df = df[
            df["game_type"]
            .astype(str)
            .str.upper()
            .eq("REG")
        ].copy()

    return (
        df
        .sort_values(
            [
                "gameday",
                "season",
                "week"
            ]
        )
        .reset_index(drop=True)
    )


# ============================================================
# ESPN — PARTIDOS DE HOY
# ============================================================

@st.cache_data(
    ttl=900,
    show_spinner=False
)
def get_espn_today():

    try:

        today = datetime.now().strftime(
            "%Y%m%d"
        )

        response = requests.get(
            ESPN_SCOREBOARD,
            params={
                "dates": today
            },
            timeout=12,
            headers={
                "User-Agent":
                    "Mozilla/5.0"
            }
        )

        response.raise_for_status()

        return response.json()

    except Exception:

        return {}


def extract_espn_games(
    payload
):

    rows = []

    for event in payload.get(
        "events",
        []
    ):

        competitions = (
            event.get(
                "competitions",
                []
            )
        )

        if not competitions:
            continue

        competition = (
            competitions[0]
        )

        competitors = (
            competition.get(
                "competitors",
                []
            )
        )

        if len(competitors) < 2:
            continue

        home = next(
            (
                x
                for x in competitors
                if x.get("homeAway")
                == "home"
            ),
            None
        )

        away = next(
            (
                x
                for x in competitors
                if x.get("homeAway")
                == "away"
            ),
            None
        )

        if not home or not away:
            continue

        rows.append({

            "event_id":
                event.get("id"),

            "home_team":
                normalize_team(
                    home
                    .get("team", {})
                    .get("abbreviation")
                ),

            "away_team":
                normalize_team(
                    away
                    .get("team", {})
                    .get("abbreviation")
                ),

            "date":
                pd.to_datetime(
                    event.get("date"),
                    errors="coerce"
                ),

            "status":
                event
                .get("status", {})
                .get("type", {})
                .get("description"),

            "weather":
                competition.get(
                    "weather",
                    {}
                ),

            "venue":
                competition
                .get("venue", {})
                .get("fullName")
        })

    return rows


# ============================================================
# LESIONES ACTUALES
# ============================================================

POSITION_WEIGHT = {

    "QB": 1.00,

    "OL": 0.55,

    "WR": 0.45,

    "TE": 0.35,

    "RB": 0.30,

    "DL": 0.45,

    "DE": 0.45,

    "DT": 0.40,

    "LB": 0.40,

    "CB": 0.40,

    "S": 0.35,

    "DB": 0.35,

    "K": 0.12,

    "P": 0.08,

    "LS": 0.03,
}


@st.cache_data(
    ttl=900,
    show_spinner=False
)
def get_injuries():

    try:

        response = requests.get(
            ESPN_INJURIES,
            timeout=12,
            headers={
                "User-Agent":
                    "Mozilla/5.0"
            }
        )

        response.raise_for_status()

        data = response.json()

    except Exception:

        return {}

    injuries = (
        data.get(
            "injuries",
            []
        )
    )

    if isinstance(
        injuries,
        dict
    ):

        injuries = (
            injuries.get(
                "items",
                []
            )
            or injuries.get(
                "injuries",
                []
            )
        )

    result = {}

    for item in (
        injuries
        if isinstance(
            injuries,
            list
        )
        else []
    ):

        athlete = (
            item.get(
                "athlete",
                {}
            )
            or {}
        )

        team_obj = (
            item.get(
                "team",
                {}
            )
            or {}
        )

        team = normalize_team(
            team_obj.get(
                "abbreviation"
            )
            or team_obj.get(
                "shortDisplayName"
            )
            or team_obj.get(
                "displayName"
            )
        )

        if not team:
            continue

        position_obj = (
            athlete.get(
                "position"
            )
            or {}
        )

        if isinstance(
            position_obj,
            dict
        ):

            position = (
                position_obj.get(
                    "abbreviation"
                )
                or position_obj.get(
                    "name"
                )
                or ""
            )

        else:

            position = ""

        position = str(
            position
        ).upper()

        status = str(
            item.get(
                "status"
            )
            or item
            .get("type", {})
            .get("description")
            or item
            .get("details", {})
            .get("status")
            or ""
        ).lower()

        name = (
            athlete.get(
                "displayName"
            )
            or athlete.get(
                "fullName"
            )
            or "Jugador"
        )

        # --------------------------------
        # IMPORTANCIA DE LA LESIÓN
        # --------------------------------

        if (
            "out" in status
            or "doubtful" in status
        ):

            severity = 1.0

        elif "questionable" in status:

            severity = 0.45

        elif "day-to-day" in status:

            severity = 0.25

        else:

            severity = 0.0

        if severity <= 0:
            continue

        weight = POSITION_WEIGHT.get(
            position,
            0.22
        )

        impact = (
            severity
            * weight
        )

        result.setdefault(
            team,
            []
        ).append({

            "name":
                name,

            "position":
                position
                or "?",

            "status":
                status,

            "impact":
                impact
        })

    return result


# ============================================================
# CREAR HISTORIAL POR EQUIPO
# ============================================================

def team_game_history(
    games
):

    home = games[
        [
            "season",
            "week",
            "gameday",
            "home_team",
            "away_team",
            "home_score",
            "away_score"
        ]
    ].copy()

    home["team"] = (
        home["home_team"]
    )

    home["opponent"] = (
        home["away_team"]
    )

    home["points_for"] = (
        home["home_score"]
    )

    home["points_against"] = (
        home["away_score"]
    )

    home["is_home"] = 1

    away = games[
        [
            "season",
            "week",
            "gameday",
            "home_team",
            "away_team",
            "home_score",
            "away_score"
        ]
    ].copy()

    away["team"] = (
        away["away_team"]
    )

    away["opponent"] = (
        away["home_team"]
    )

    away["points_for"] = (
        away["away_score"]
    )

    away["points_against"] = (
        away["home_score"]
    )

    away["is_home"] = 0

    home["win"] = (
        home["points_for"]
        >
        home["points_against"]
    ).astype(float)

    away["win"] = (
        away["points_for"]
        >
        away["points_against"]
    ).astype(float)

    cols = [

        "season",
        "week",
        "gameday",
        "team",
        "opponent",
        "points_for",
        "points_against",
        "is_home",
        "win"

    ]

    result = pd.concat(
        [
            home[cols],
            away[cols]
        ],
        ignore_index=True
    )

    return (
        result
        .sort_values(
            [
                "team",
                "gameday",
                "week"
            ]
        )
        .reset_index(drop=True)
    )


# ============================================================
# FEATURES ANTES DEL PARTIDO
# ============================================================

def add_pregame_features(
    games
):

    games = (
        games
        .copy()
        .sort_values(
            [
                "gameday",
                "week"
            ]
        )
        .reset_index(drop=True)
    )

    team_rows = team_game_history(
        games
    )

    feature_rows = []

    for team, group in (
        team_rows
        .groupby(
            "team",
            sort=False
        )
    ):

        group = (
            group
            .sort_values(
                [
                    "gameday",
                    "week"
                ]
            )
            .copy()
        )

        group["pf_roll"] = (
            group["points_for"]
            .shift(1)
            .rolling(
                ROLLING_GAMES,
                min_periods=1
            )
            .mean()
        )

        group["pa_roll"] = (
            group["points_against"]
            .shift(1)
            .rolling(
                ROLLING_GAMES,
                min_periods=1
            )
            .mean()
        )

        group["win_roll"] = (
            group["win"]
            .shift(1)
            .rolling(
                ROLLING_GAMES,
                min_periods=1
            )
            .mean()
        )

        group["diff_roll"] = (
            (
                group["points_for"]
                -
                group["points_against"]
            )
            .shift(1)
            .rolling(
                ROLLING_GAMES,
                min_periods=1
            )
            .mean()
        )

        group["diff_ewm"] = (
            (
                group["points_for"]
                -
                group["points_against"]
            )
            .shift(1)
            .ewm(
                span=ROLLING_GAMES,
                adjust=False,
                min_periods=1
            )
            .mean()
        )

        group["last_game_date"] = (
            group["gameday"]
            .shift(1)
        )

        group["rest_days"] = (
            group["gameday"]
            -
            group["last_game_date"]
        ).dt.days

        group["rest_days"] = (
            group["rest_days"]
            .fillna(7)
            .clip(
                lower=3,
                upper=21
            )
        )

        group["pf_roll"] = (
            group["pf_roll"]
            .fillna(22.0)
        )

        group["pa_roll"] = (
            group["pa_roll"]
            .fillna(22.0)
        )

        group["win_roll"] = (
            group["win_roll"]
            .fillna(0.50)
        )

        group["diff_roll"] = (
            group["diff_roll"]
            .fillna(0.0)
        )

        group["diff_ewm"] = (
            group["diff_ewm"]
            .fillna(0.0)
        )

        feature_rows.append(
            group
        )

    team_features = pd.concat(
        feature_rows,
        ignore_index=True
    )

    key = [
        "season",
        "week",
        "gameday",
        "team"
    ]

    team_features = (
        team_features[
            key
            + [
                "pf_roll",
                "pa_roll",
                "win_roll",
                "diff_roll",
                "diff_ewm",
                "rest_days"
            ]
        ]
    )

    home = (
        team_features
        .rename(
            columns={

                "team":
                    "home_team",

                "pf_roll":
                    "h_pf",

                "pa_roll":
                    "h_pa",

                "win_roll":
                    "h_win",

                "diff_roll":
                    "h_diff",

                "diff_ewm":
                    "h_ewm",

                "rest_days":
                    "h_rest"
            }
        )
    )

    away = (
        team_features
        .rename(
            columns={

                "team":
                    "away_team",

                "pf_roll":
                    "a_pf",

                "pa_roll":
                    "a_pa",

                "win_roll":
                    "a_win",

                "diff_roll":
                    "a_diff",

                "diff_ewm":
                    "a_ewm",

                "rest_days":
                    "a_rest"
            }
        )
    )

    merged = (
        games
        .merge(
            home[
                [
                    "season",
                    "week",
                    "gameday",
                    "home_team",
                    "h_pf",
                    "h_pa",
                    "h_win",
                    "h_diff",
                    "h_ewm",
                    "h_rest"
                ]
            ],
            on=[
                "season",
                "week",
                "gameday",
                "home_team"
            ],
            how="left"
        )
        .merge(
            away[
                [
                    "season",
                    "week",
                    "gameday",
                    "away_team",
                    "a_pf",
                    "a_pa",
                    "a_win",
                    "a_diff",
                    "a_ewm",
                    "a_rest"
                ]
            ],
            on=[
                "season",
                "week",
                "gameday",
                "away_team"
            ],
            how="left"
        )
    )

    # --------------------------------
    # VALORES INICIALES
    # --------------------------------

    for col in [
        "h_pf",
        "a_pf",
        "h_pa",
        "a_pa"
    ]:

        merged[col] = (
            merged[col]
            .fillna(22.0)
        )

    for col in [
        "h_win",
        "a_win"
    ]:

        merged[col] = (
            merged[col]
            .fillna(0.50)
        )

    for col in [
        "h_diff",
        "a_diff",
        "h_ewm",
        "a_ewm"
    ]:

        merged[col] = (
            merged[col]
            .fillna(0.0)
        )

    for col in [
        "h_rest",
        "a_rest"
    ]:

        merged[col] = (
            merged[col]
            .fillna(7.0)
        )

    # --------------------------------
    # DIFERENCIAS
    # --------------------------------

    merged["off_diff"] = (
        merged["h_pf"]
        -
        merged["a_pf"]
    )

    merged["def_diff"] = (
        merged["a_pa"]
        -
        merged["h_pa"]
    )

    merged["win_diff"] = (
        merged["h_win"]
        -
        merged["a_win"]
    )

    merged["form_diff"] = (
        merged["h_ewm"]
        -
        merged["a_ewm"]
    )

    merged["margin_diff"] = (
        merged["h_diff"]
        -
        merged["a_diff"]
    )

    merged["rest_diff"] = (
        merged["h_rest"]
        -
        merged["a_rest"]
    )

    # --------------------------------
    # CLIMA
    # --------------------------------

    if "temp" in merged.columns:

        merged["temp"] = pd.to_numeric(
            merged["temp"],
            errors="coerce"
        ).fillna(65)

    else:

        merged["temp"] = 65

    if "wind" in merged.columns:

        merged["wind"] = pd.to_numeric(
            merged["wind"],
            errors="coerce"
        ).fillna(0)

    else:

        merged["wind"] = 0

    merged["high_wind"] = np.maximum(
        merged["wind"] - 15,
        0
    )

    merged["cold"] = np.maximum(
        45 - merged["temp"],
        0
    )

    return merged


# ============================================================
# VARIABLES DEL MODELO
# ============================================================

FEATURES = [

    "off_diff",

    "def_diff",

    "win_diff",

    "form_diff",

    "margin_diff",

    "rest_diff",

    "high_wind",

    "cold",

]


# ============================================================
# NORMALIZACIÓN
# ============================================================

def standardize_fit(X):

    mean = np.nanmean(
        X,
        axis=0
    )

    std = np.nanstd(
        X,
        axis=0
    )

    std[
        std < 1e-8
    ] = 1

    return mean, std


def standardize_apply(
    X,
    mean,
    std
):

    return (
        X - mean
    ) / std


# ============================================================
# SIGMOIDE
# ============================================================

def sigmoid(z):

    z = np.clip(
        z,
        -35,
        35
    )

    return (
        1
        /
        (
            1
            +
            np.exp(-z)
        )
    )


# ============================================================
# REGRESIÓN LOGÍSTICA PROPIA
# ============================================================

def fit_logistic(
    X,
    y,
    learning_rate=0.035,
    epochs=3500,
    regularization=0.15
):

    X = np.asarray(
        X,
        dtype=float
    )

    y = np.asarray(
        y,
        dtype=float
    )

    X_design = np.column_stack(
        [
            np.ones(
                len(X)
            ),
            X
        ]
    )

    weights = np.zeros(
        X_design.shape[1]
    )

    for _ in range(
        epochs
    ):

        probability = sigmoid(
            X_design
            @
            weights
        )

        error = (
            probability
            -
            y
        )

        gradient = (
            X_design.T
            @
            error
            /
            len(y)
        )

        gradient[1:] += (
            regularization
            * weights[1:]
        )

        weights -= (
            learning_rate
            * gradient
        )

    return weights


def predict_logistic(
    X,
    weights
):

    X = np.asarray(
        X,
        dtype=float
    )

    X_design = np.column_stack(
        [
            np.ones(
                len(X)
            ),
            X
        ]
    )

    return sigmoid(
        X_design
        @
        weights
    )


# ============================================================
# CREAR MODELO
# ============================================================

@st.cache_data(
    ttl=1800,
    show_spinner=False
)
def build_model():

    games = load_games()

    # --------------------------------
    # 2025 PARA ENTRENAMIENTO
    # --------------------------------

    train_games = games[
        (
            games["season"]
            == 2025
        )
        &
        games["home_score"].notna()
        &
        games["away_score"].notna()
    ].copy()

    dataset = (
        add_pregame_features(
            train_games
        )
    )

    dataset = dataset.dropna(
        subset=FEATURES
    )

    # --------------------------------
    # RESULTADO
    # --------------------------------

    dataset["target"] = (
        dataset["home_score"]
        >
        dataset["away_score"]
    ).astype(int)

    # Empates fuera
    dataset = dataset[
        dataset["home_score"]
        !=
        dataset["away_score"]
    ].copy()

    X = dataset[
        FEATURES
    ].to_numpy(
        dtype=float
    )

    y = dataset[
        "target"
    ].to_numpy(
        dtype=float
    )

    mean, std = (
        standardize_fit(
            X
        )
    )

    X_scaled = (
        standardize_apply(
            X,
            mean,
            std
        )
    )

    weights = fit_logistic(
        X_scaled,
        y
    )

    # --------------------------------
    # VALIDACIÓN CRONOLÓGICA
    # --------------------------------

    split = max(
        1,
        int(
            len(dataset)
            * 0.75
        )
    )

    validation = (
        dataset
        .iloc[split:]
        .copy()
    )

    X_validation = (
        standardize_apply(
            validation[
                FEATURES
            ].to_numpy(
                dtype=float
            ),
            mean,
            std
        )
    )

    validation_probability = (
        predict_logistic(
            X_validation,
            weights
        )
    )

    validation_accuracy = (
        np.mean(
            (
                validation_probability
                >= 0.50
            )
            ==
            validation[
                "target"
            ].to_numpy(
                dtype=int
            )
        )
    )

    return {

        "games":
            games,

        "mean":
            mean,

        "std":
            std,

        "weights":
            weights,

        "validation_accuracy":
            validation_accuracy
    }


# ============================================================
# ESTADO ACTUAL DE LOS EQUIPOS
# ============================================================

def current_features_for_game(
    games,
    home_team,
    away_team,
    game_date
):

    completed = games[
        games["home_score"].notna()
        &
        games["away_score"].notna()
        &
        (
            games["gameday"]
            <
            pd.Timestamp(
                game_date
            )
        )
    ].copy()

    if completed.empty:

        return {

            "off_diff": 0,

            "def_diff": 0,

            "win_diff": 0,

            "form_diff": 0,

            "margin_diff": 0,

            "rest_diff": 0,

            "high_wind": 0,

            "cold": 0
        }

    history = team_game_history(
        completed
    )

    states = {}

    for team, group in (
        history
        .groupby(
            "team"
        )
    ):

        group = (
            group
            .sort_values(
                [
                    "gameday",
                    "week"
                ]
            )
        )

        recent = (
            group
            .tail(
                ROLLING_GAMES
            )
        )

        margin = (
            group["points_for"]
            -
            group["points_against"]
        )

        states[team] = {

            "pf":
                float(
                    recent[
                        "points_for"
                    ].mean()
                ),

            "pa":
                float(
                    recent[
                        "points_against"
                    ].mean()
                ),

            "win":
                float(
                    recent[
                        "win"
                    ].mean()
                ),

            "diff":
                float(
                    (
                        recent[
                            "points_for"
                        ]
                        -
                        recent[
                            "points_against"
                        ]
                    ).mean()
                ),

            "ewm":
                float(
                    margin
                    .ewm(
                        span=ROLLING_GAMES,
                        adjust=False
                    )
                    .mean()
                    .iloc[-1]
                ),

            "last_date":
                group[
                    "gameday"
                ].max()
        }

    def state(team):

        return states.get(
            team,
            {

                "pf": 22,

                "pa": 22,

                "win": 0.50,

                "diff": 0,

                "ewm": 0,

                "last_date":
                    pd.NaT
            }
        )

    home = state(
        home_team
    )

    away = state(
        away_team
    )

    def rest_days(
        team_state
    ):

        if pd.isna(
            team_state[
                "last_date"
            ]
        ):

            return 7

        days = (
            pd.Timestamp(
                game_date
            )
            -
            team_state[
                "last_date"
            ]
        ).days

        return float(
            max(
                3,
                min(
                    21,
                    days
                )
            )
        )

    home_rest = (
        rest_days(
            home
        )
    )

    away_rest = (
        rest_days(
            away
        )
    )

    return {

        "off_diff":
            home["pf"]
            -
            away["pf"],

        "def_diff":
            away["pa"]
            -
            home["pa"],

        "win_diff":
            home["win"]
            -
            away["win"],

        "form_diff":
            home["ewm"]
            -
            away["ewm"],

        "margin_diff":
            home["diff"]
            -
            away["diff"],

        "rest_diff":
            home_rest
            -
            away_rest,

        "high_wind":
            0,

        "cold":
            0
    }


# ============================================================
# IMPACTO DE LESIONES
# ============================================================

def injury_adjustment(
    injuries,
    home_team,
    away_team
):

    home_impact = sum(
        player["impact"]
        for player
        in injuries.get(
            home_team,
            []
        )
    )

    away_impact = sum(
        player["impact"]
        for player
        in injuries.get(
            away_team,
            []
        )
    )

    difference = np.clip(
        away_impact
        -
        home_impact,
        -1.8,
        1.8
    )

    probability_adjustment = (
        difference
        *
        0.018
    )

    return (

        float(
            probability_adjustment
        ),

        home_impact,

        away_impact
    )


# ============================================================
# PROBABILIDAD FINAL
# ============================================================

def calculate_probability(
    model,
    games,
    home,
    away,
    game_date,
    weather=None,
    injuries=None
):

    features = (
        current_features_for_game(
            games,
            home,
            away,
            game_date
        )
    )

    # --------------------------------
    # CLIMA
    # --------------------------------

    if weather:

        try:

            temperature = weather.get(
                "temperature"
            )

            wind = weather.get(
                "windSpeed"
            )

            if temperature is not None:

                features["cold"] = max(
                    45
                    -
                    float(
                        temperature
                    ),
                    0
                )

            if wind is not None:

                features["high_wind"] = max(
                    float(
                        wind
                    )
                    -
                    15,
                    0
                )

        except Exception:

            pass

    X = np.array(
        [
            [
                features[col]
                for col
                in FEATURES
            ]
        ],
        dtype=float
    )

    X_scaled = (
        standardize_apply(
            X,
            model["mean"],
            model["std"]
        )
    )

    home_probability = float(
        predict_logistic(
            X_scaled,
            model["weights"]
        )[0]
    )

    # --------------------------------
    # LESIONES
    # --------------------------------

    injury_delta = 0

    home_injury = 0

    away_injury = 0

    if injuries is not None:

        (
            injury_delta,
            home_injury,
            away_injury
        ) = injury_adjustment(
            injuries,
            home,
            away
        )

    home_probability += (
        injury_delta
    )

    home_probability = float(
        np.clip(
            home_probability,
            0.05,
            0.95
        )
    )

    return (

        home_probability,

        features,

        home_injury,

        away_injury
    )


# ============================================================
# CLIMA DE ESPN
# ============================================================

def get_game_weather(
    espn_games,
    home,
    away
):

    for game in espn_games:

        if (
            game["home_team"]
            == home
            and
            game["away_team"]
            == away
        ):

            weather = (
                game.get(
                    "weather"
                )
                or {}
            )

            if not isinstance(
                weather,
                dict
            ):

                return None

            return {

                "temperature":
                    weather.get(
                        "temperature"
                    ),

                "windSpeed":
                    weather.get(
                        "windSpeed"
                    )
                    or weather.get(
                        "wind"
                    ),

                "condition":
                    weather.get(
                        "displayValue"
                    )
                    or weather.get(
                        "condition"
                    )
            }

    return None


# ============================================================
# DISEÑO
# ============================================================

st.markdown(
    """
    <style>

    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 3rem;
        max-width: 900px;
    }

    .game-card {

        border:
            1px solid #30333d;

        border-radius:
            18px;

        padding:
            22px;

        margin-bottom:
            18px;

        background:
            #15161d;
    }

    .probability {

        font-size:
            48px;

        font-weight:
            800;

        margin-top:
            4px;
    }

    .pick {

        font-size:
            22px;

        font-weight:
            700;
    }

    .muted {

        color:
            #9ca3af;

        font-size:
            13px;
    }

    </style>
    """,
    unsafe_allow_html=True
)


# ============================================================
# ENCABEZADO
# ============================================================

st.title(
    "🏈 NFL EDGE"
)

st.caption(
    "Probabilidad independiente del modelo"
)

st.caption(
    "Sin utilizar cuotas de sportsbook"
)


# ============================================================
# CARGAR MODELO
# ============================================================

try:

    model = build_model()

    games = model[
        "games"
    ]

except Exception as error:

    st.error(
        "No se pudieron cargar los datos NFL."
    )

    st.code(
        str(error)
    )

    st.stop()


# ============================================================
# INFORMACIÓN ACTUAL
# ============================================================

espn_payload = (
    get_espn_today()
)

espn_games = (
    extract_espn_games(
        espn_payload
    )
)

injuries = (
    get_injuries()
)


# ============================================================
# PARTIDOS DE HOY
# ============================================================

today = date.today()

today_games = games[
    games["gameday"]
    .dt.date
    ==
    today
].copy()

today_games = today_games[
    today_games[
        "home_score"
    ].isna()
    |
    today_games[
        "away_score"
    ].isna()
].copy()


st.header(
    "🏈 PARTIDOS DE HOY"
)


if today_games.empty:

    # Si nflverse todavía no tiene el partido,
    # intentamos mostrar los eventos actuales de ESPN.

    if espn_games:

        st.info(
            "Partidos encontrados mediante ESPN."
        )

        for game in espn_games:

            home = game[
                "home_team"
            ]

            away = game[
                "away_team"
            ]

            weather = (
                get_game_weather(
                    espn_games,
                    home,
                    away
                )
            )

            probability, _, _, _ = (
                calculate_probability(
                    model,
                    games,
                    home,
                    away,
                    today,
                    weather,
                    injuries
                )
            )

            if probability >= 0.50:

                pick = home

                pick_probability = (
                    probability
                )

            else:

                pick = away

                pick_probability = (
                    1
                    -
                    probability
                )

            st.markdown(
                f"""
                <div class="game-card">

                <div>
                <b>{away} @ {home}</b>
                </div>

                <div class="muted">
                Probabilidad del modelo
                </div>

                <div class="probability">
                {pick_probability * 100:.1f}%
                </div>

                <div class="pick">
                🧠 {pick}
                </div>

                </div>
                """,
                unsafe_allow_html=True
            )

    else:

        st.info(
            "No hay partidos NFL de temporada regular hoy."
        )

else:

    for _, game in (
        today_games
        .sort_values(
            "gameday"
        )
        .iterrows()
    ):

        home = normalize_team(
            game[
                "home_team"
            ]
        )

        away = normalize_team(
            game[
                "away_team"
            ]
        )

        weather = (
            get_game_weather(
                espn_games,
                home,
                away
            )
        )

        (
            probability,
            features,
            home_injury,
            away_injury
        ) = calculate_probability(
            model,
            games,
            home,
            away,
            game[
                "gameday"
            ],
            weather,
            injuries
        )

        if probability >= 0.50:

            pick = home

            pick_probability = (
                probability
            )

        else:

            pick = away

            pick_probability = (
                1
                -
                probability
            )

        st.markdown(
            f"""
            <div class="game-card">

            <div style="font-size:20px;font-weight:700;">
            {away} @ {home}
            </div>

            <div class="muted">
            Probabilidad del modelo
            </div>

            <div class="probability">
            {pick_probability * 100:.1f}%
            </div>

            <div class="pick">
            🧠 {pick}
            </div>

            </div>
            """,
            unsafe_allow_html=True
        )

        # --------------------------------
        # INFORMACIÓN OPCIONAL
        # --------------------------------

        with st.expander(
            "Ver información utilizada"
        ):

            st.write(
                """
                El modelo considera rendimiento reciente,
                ofensiva, defensa, margen de puntos,
                victorias recientes, localía, descanso,
                clima disponible y lesiones actuales.
                """
            )

            if weather:

                st.write(
                    f"🌦️ Clima: "
                    f"{weather.get('condition', 'N/D')} | "
                    f"Temperatura: "
                    f"{weather.get('temperature', 'N/D')} | "
                    f"Viento: "
                    f"{weather.get('windSpeed', 'N/D')}"
                )

            st.write(
                f"🩹 Impacto lesiones "
                f"{home}: {home_injury:.2f}"
            )

            st.write(
                f"🩹 Impacto lesiones "
                f"{away}: {away_injury:.2f}"
            )


# ============================================================
# VALIDACIÓN MINIMALISTA
# ============================================================

with st.expander(
    "📊 Validación del modelo"
):

    accuracy = model[
        "validation_accuracy"
    ]

    if not math.isnan(
        accuracy
    ):

        st.write(
            "Validación cronológica interna usando 2025."
        )

        st.metric(
            "Accuracy",
            f"{accuracy * 100:.1f}%"
        )

    st.caption(
        "Esta cifra sirve únicamente para evaluar "
        "el modelo. No representa una garantía de "
        "aciertos futuros."
    )


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    "Histórico: 2025 + resultados disponibles de 2026. "
    "Las cuotas de las casas NO se utilizan para generar "
    "las probabilidades."
)
