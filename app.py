import streamlit as st
import pandas as pd
import numpy as np


# ============================================================
# NFL EDGE MONITOR
# ============================================================
#
# OBJETIVO:
# Crear una probabilidad PROPIA e independiente del mercado.
#
# HISTORICO:
# Solo 2024 y 2025.
#
# BACKTEST:
# 2024 -> entrena
# 2025 -> prueba
#
# MODELO FINAL:
# 2024 + 2025 -> analiza 2026
#
# NO USA CUOTAS PARA CALCULAR LA PROBABILIDAD.
#
# Dependencias:
# streamlit
# pandas
# numpy
#
# ============================================================


st.set_page_config(
    page_title="NFL Edge Monitor",
    page_icon="🏈",
    layout="wide"
)


# ============================================================
# CONFIGURACION
# ============================================================

HISTORIC_SEASONS = [2024, 2025]
BACKTEST_TRAIN_SEASON = 2024
BACKTEST_TEST_SEASON = 2025
CURRENT_SEASON = 2026

DATA_URL = (
    "https://raw.githubusercontent.com/"
    "nflverse/nfldata/master/data/games.csv"
)

RECENT_GAMES = 5


# ============================================================
# ESTILO
# ============================================================

st.markdown(
    """
    <style>

    .block-container {
        padding-top: 2rem;
        padding-bottom: 4rem;
    }

    h1 {
        font-size: 3rem !important;
    }

    h2 {
        font-size: 2.2rem !important;
    }

    h3 {
        font-size: 1.5rem !important;
    }

    .positive {
        color: #00d084;
        font-weight: 700;
    }

    .negative {
        color: #ff4b4b;
        font-weight: 700;
    }

    .neutral {
        color: #f0b90b;
        font-weight: 700;
    }

    </style>
    """,
    unsafe_allow_html=True
)


# ============================================================
# CARGAR DATOS
# ============================================================

@st.cache_data(ttl=3600)
def load_games():

    try:

        df = pd.read_csv(DATA_URL)

    except Exception as e:

        st.error(
            "No se pudo descargar la base de datos NFL."
        )

        st.code(str(e))

        return pd.DataFrame()

    df.columns = [
        str(c).strip().lower()
        for c in df.columns
    ]

    required = [
        "season",
        "week",
        "home_team",
        "away_team",
        "home_score",
        "away_score"
    ]

    missing = [
        c for c in required
        if c not in df.columns
    ]

    if missing:

        st.error(
            "La fuente de datos no contiene "
            f"las columnas necesarias: {missing}"
        )

        return pd.DataFrame()

    # --------------------------------------------------------
    # FECHA
    # --------------------------------------------------------

    if "gameday" in df.columns:

        df["date"] = pd.to_datetime(
            df["gameday"],
            errors="coerce"
        )

    elif "game_date" in df.columns:

        df["date"] = pd.to_datetime(
            df["game_date"],
            errors="coerce"
        )

    else:

        df["date"] = pd.NaT

    # --------------------------------------------------------
    # NUMERICOS
    # --------------------------------------------------------

    for col in [
        "season",
        "week",
        "home_score",
        "away_score"
    ]:

        df[col] = pd.to_numeric(
            df[col],
            errors="coerce"
        )

    df = df.dropna(
        subset=[
            "season",
            "home_team",
            "away_team"
        ]
    )

    df["season"] = df["season"].astype(int)

    # --------------------------------------------------------
    # SOLO REGULAR SEASON
    # --------------------------------------------------------

    if "season_type" in df.columns:

        df["season_type"] = (
            df["season_type"]
            .astype(str)
            .str.upper()
        )

        df = df[
            df["season_type"] == "REG"
        ]

    return df


games = load_games()


if games.empty:

    st.stop()


# ============================================================
# FUNCIONES MATEMATICAS
# ============================================================

def sigmoid(x):

    x = np.clip(
        x,
        -30,
        30
    )

    return 1.0 / (
        1.0 + np.exp(-x)
    )


def american_to_decimal(odds):

    odds = float(odds)

    if odds == 0:

        return None

    if odds > 0:

        return 1 + odds / 100

    return 1 + 100 / abs(odds)


def decimal_to_implied(decimal):

    if decimal is None:
        return None

    if decimal <= 1:
        return None

    return 1 / decimal


def probability_to_american(prob):

    if prob <= 0 or prob >= 1:

        return None

    decimal = 1 / prob

    if decimal >= 2:

        return (decimal - 1) * 100

    return -100 / (decimal - 1)


# ============================================================
# MODELO LOGISTICO PROPIO
# ============================================================
#
# NO necesita sklearn.
#
# ============================================================

class SimpleLogisticModel:

    def __init__(
        self,
        learning_rate=0.01,
        epochs=2500
    ):

        self.learning_rate = learning_rate
        self.epochs = epochs

        self.mean = None
        self.std = None

        self.weights = None
        self.bias = 0.0


    def fit(
        self,
        X,
        y
    ):

        X = np.asarray(
            X,
            dtype=float
        )

        y = np.asarray(
            y,
            dtype=float
        )

        # ----------------------------------------------------
        # NORMALIZACION
        # ----------------------------------------------------

        self.mean = X.mean(
            axis=0
        )

        self.std = X.std(
            axis=0
        )

        self.std[
            self.std < 1e-8
        ] = 1.0

        Xs = (
            X - self.mean
        ) / self.std

        # ----------------------------------------------------
        # PARAMETROS
        # ----------------------------------------------------

        self.weights = np.zeros(
            Xs.shape[1]
        )

        self.bias = 0.0

        n = len(Xs)

        # ----------------------------------------------------
        # GRADIENT DESCENT
        # ----------------------------------------------------

        for _ in range(
            self.epochs
        ):

            z = (
                Xs @ self.weights
                + self.bias
            )

            p = sigmoid(z)

            error = p - y

            grad_w = (
                Xs.T @ error
                / n
            )

            grad_b = (
                np.mean(error)
            )

            self.weights -= (
                self.learning_rate
                * grad_w
            )

            self.bias -= (
                self.learning_rate
                * grad_b
            )

        return self


    def predict_proba(
        self,
        X
    ):

        X = np.asarray(
            X,
            dtype=float
        )

        Xs = (
            X - self.mean
        ) / self.std

        z = (
            Xs @ self.weights
            + self.bias
        )

        p = sigmoid(z)

        return np.column_stack(
            [
                1 - p,
                p
            ]
        )


# ============================================================
# ESTADO DE EQUIPOS
# ============================================================

def new_team():

    return {
        "elo": 1500.0,

        "games": 0,

        "wins": 0,

        "points_for": [],

        "points_against": [],

        "point_diff": []
    }


def get_team(
    teams,
    name
):

    if name not in teams:

        teams[name] = new_team()

    return teams[name]


# ============================================================
# FEATURES DE UN EQUIPO
# ============================================================

def team_features(team):

    if team["games"] == 0:

        return {
            "elo": 1500.0,
            "win_rate": 0.500,
            "pf": 22.0,
            "pa": 22.0,
            "diff": 0.0,
            "recent_win": 0.500,
            "recent_diff": 0.0
        }

    pf_list = (
        team["points_for"]
        [-RECENT_GAMES:]
    )

    pa_list = (
        team["points_against"]
        [-RECENT_GAMES:]
    )

    diff_list = (
        team["point_diff"]
        [-RECENT_GAMES:]
    )

    pf = np.mean(
        pf_list
    )

    pa = np.mean(
        pa_list
    )

    diff = np.mean(
        diff_list
    )

    recent_wins = sum(
        1
        for x in diff_list
        if x > 0
    )

    recent_win = (
        recent_wins
        / len(diff_list)
        if diff_list
        else 0.500
    )

    return {

        "elo":
            team["elo"],

        "win_rate":
            team["wins"]
            / team["games"],

        "pf":
            pf,

        "pa":
            pa,

        "diff":
            diff,

        "recent_win":
            recent_win,

        "recent_diff":
            diff
    }


# ============================================================
# CREAR FEATURES
# ============================================================

def create_features(
    home_team,
    away_team
):

    hf = team_features(
        home_team
    )

    af = team_features(
        away_team
    )

    return [

        hf["elo"]
        - af["elo"],

        hf["win_rate"]
        - af["win_rate"],

        hf["pf"]
        - af["pf"],

        hf["pa"]
        - af["pa"],

        hf["diff"]
        - af["diff"],

        hf["recent_win"]
        - af["recent_win"],

        hf["recent_diff"]
        - af["recent_diff"],

        # Ventaja de local
        1.0
    ]


# ============================================================
# ACTUALIZAR EQUIPOS
# ============================================================

def update_teams(
    teams,
    home,
    away,
    home_score,
    away_score
):

    ht = get_team(
        teams,
        home
    )

    at = get_team(
        teams,
        away
    )

    # --------------------------------------------------------
    # ELO
    # --------------------------------------------------------

    expected_home = sigmoid(
        (
            ht["elo"]
            + 65
            - at["elo"]
        )
        / 400
    )

    actual_home = (
        1.0
        if home_score > away_score
        else 0.0
    )

    elo_change = (
        20
        * (
            actual_home
            - expected_home
        )
    )

    ht["elo"] += elo_change

    at["elo"] -= elo_change

    # --------------------------------------------------------
    # PARTIDOS
    # --------------------------------------------------------

    ht["games"] += 1

    at["games"] += 1

    # --------------------------------------------------------
    # VICTORIAS
    # --------------------------------------------------------

    if home_score > away_score:

        ht["wins"] += 1

    elif away_score > home_score:

        at["wins"] += 1

    # --------------------------------------------------------
    # ESTADISTICAS
    # --------------------------------------------------------

    ht[
        "points_for"
    ].append(
        float(home_score)
    )

    ht[
        "points_against"
    ].append(
        float(away_score)
    )

    ht[
        "point_diff"
    ].append(
        float(
            home_score
            - away_score
        )
    )

    at[
        "points_for"
    ].append(
        float(away_score)
    )

    at[
        "points_against"
    ].append(
        float(home_score)
    )

    at[
        "point_diff"
    ].append(
        float(
            away_score
            - home_score
        )
    )


# ============================================================
# PREPARAR PARTIDOS
# ============================================================

def sort_games(df):

    df = df.copy()

    df = df.sort_values(
        [
            "date",
            "season",
            "week"
        ],
        na_position="last"
    )

    return df


# ============================================================
# ENTRENAR CON UNA TEMPORADA
# ============================================================

def build_training_data(
    df
):

    df = sort_games(
        df
    )

    teams = {}

    X = []
    y = []

    for _, game in df.iterrows():

        home = str(
            game["home_team"]
        )

        away = str(
            game["away_team"]
        )

        hs = game["home_score"]
        aws = game["away_score"]

        if pd.isna(hs) or pd.isna(aws):

            continue

        # Ignoramos empates
        if hs == aws:

            update_teams(
                teams,
                home,
                away,
                hs,
                aws
            )

            continue

        ht = get_team(
            teams,
            home
        )

        at = get_team(
            teams,
            away
        )

        features = create_features(
            ht,
            at
        )

        X.append(
            features
        )

        y.append(
            1
            if hs > aws
            else 0
        )

        update_teams(
            teams,
            home,
            away,
            hs,
            aws
        )

    return (
        np.array(X),
        np.array(y),
        teams
    )


# ============================================================
# BACKTEST LIMPIO
# ============================================================
#
# Entrenamos SOLO con 2024.
#
# Después recorremos 2025 partido por partido.
#
# El modelo NO ve el resultado del partido antes
# de realizar la predicción.
#
# ============================================================

def run_clean_backtest(
    train_df,
    test_df
):

    # --------------------------------------------------------
    # ENTRENAMIENTO 2024
    # --------------------------------------------------------

    X_train, y_train, teams = (
        build_training_data(
            train_df
        )
    )

    if len(X_train) < 100:

        return None

    model = SimpleLogisticModel(
        learning_rate=0.01,
        epochs=2500
    )

    model.fit(
        X_train,
        y_train
    )

    # --------------------------------------------------------
    # PRUEBA 2025
    # --------------------------------------------------------

    test_df = sort_games(
        test_df
    )

    results = []

    for _, game in test_df.iterrows():

        home = str(
            game["home_team"]
        )

        away = str(
            game["away_team"]
        )

        hs = game["home_score"]
        aws = game["away_score"]

        if pd.isna(hs) or pd.isna(aws):

            continue

        # Empates no cuentan para clasificación
        if hs == aws:

            update_teams(
                teams,
                home,
                away,
                hs,
                aws
            )

            continue

        ht = get_team(
            teams,
            home
        )

        at = get_team(
            teams,
            away
        )

        features = create_features(
            ht,
            at
        )

        prob_home = float(
            model.predict_proba(
                [features]
            )[0][1]
        )

        actual_home = (
            1
            if hs > aws
            else 0
        )

        prediction = (
            1
            if prob_home >= 0.50
            else 0
        )

        results.append({

            "date":
                game["date"],

            "home":
                home,

            "away":
                away,

            "prob_home":
                prob_home,

            "actual_home":
                actual_home,

            "prediction":
                prediction
        })

        # MUY IMPORTANTE:
        # Solo después de predecir actualizamos
        # el estado con el resultado real.

        update_teams(
            teams,
            home,
            away,
            hs,
            aws
        )

    results = pd.DataFrame(
        results
    )

    if results.empty:

        return None

    results["correct"] = (
        results["prediction"]
        ==
        results["actual_home"]
    )

    accuracy = (
        results["correct"]
        .mean()
    )

    brier = np.mean(
        (
            results["prob_home"]
            -
            results["actual_home"]
        ) ** 2
    )

    return {

        "model":
            model,

        "results":
            results,

        "accuracy":
            accuracy,

        "brier":
            brier,

        "games":
            len(results)
    }


# ============================================================
# TITULO
# ============================================================

st.title(
    "🏈 NFL EDGE MONITOR"
)

st.subheader(
    "Modelo propio independiente del mercado"
)

st.caption(
    "Histórico máximo: 2024 y 2025"
)


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.header(
    "⚙️ CONFIGURACIÓN"
)

min_probability = st.sidebar.slider(
    "Probabilidad mínima",
    min_value=0.50,
    max_value=0.80,
    value=0.55,
    step=0.01,
    format="%.0f%%"
)

min_edge = st.sidebar.slider(
    "EDGE mínimo",
    min_value=0.00,
    max_value=0.20,
    value=0.04,
    step=0.01,
    format="%.0f%%"
)


# ============================================================
# DATOS HISTORICOS
# ============================================================

historical = games[
    games["season"].isin(
        HISTORIC_SEASONS
    )
].copy()

historical = historical[
    historical["home_score"].notna()
    &
    historical["away_score"].notna()
].copy()


season_2024 = historical[
    historical["season"] == 2024
].copy()

season_2025 = historical[
    historical["season"] == 2025
].copy()


# ============================================================
# BACKTEST
# ============================================================

with st.spinner(
    "Ejecutando backtest limpio 2024 → 2025..."
):

    backtest = run_clean_backtest(
        season_2024,
        season_2025
    )


# ============================================================
# RESULTADOS DEL BACKTEST
# ============================================================

st.divider()

st.header(
    "🧪 BACKTEST REAL"
)

st.write(
    """
    El modelo aprende con **2024** y luego intenta
    predecir **2025** partido por partido.

    El resultado de cada partido se incorpora al modelo
    solamente después de realizar la predicción.
    """
)


if backtest is None:

    st.error(
        "No fue posible ejecutar el backtest."
    )

    st.stop()


c1, c2, c3 = st.columns(3)

with c1:

    st.metric(
        "Partidos 2025",
        f"{backtest['games']:,}"
    )

with c2:

    st.metric(
        "Accuracy",
        f"{backtest['accuracy']:.2%}"
    )

with c3:

    st.metric(
        "Brier Score",
        f"{backtest['brier']:.4f}"
    )


# ============================================================
# EXPLICACION DEL BACKTEST
# ============================================================

st.info(
    "Este resultado es mucho más útil que el backtest "
    "anterior porque el modelo no está viendo los resultados "
    "de 2025 antes de intentar predecirlos."
)


# ============================================================
# MODELO FINAL
# ============================================================
#
# Ahora usamos 2024 + 2025 para crear el estado actual
# de los equipos.
#
# ============================================================

X_final, y_final, final_teams = (
    build_training_data(
        historical
    )
)


if len(X_final) < 100:

    st.error(
        "No hay suficientes datos para crear "
        "el modelo final."
    )

    st.stop()


final_model = SimpleLogisticModel(
    learning_rate=0.01,
    epochs=2500
)

final_model.fit(
    X_final,
    y_final
)


# ============================================================
# DATOS 2026
# ============================================================

future = games[
    games["season"] == CURRENT_SEASON
].copy()


# Solo partidos todavía no jugados
future = future[
    future["home_score"].isna()
    |
    future["away_score"].isna()
].copy()


future = sort_games(
    future
)


# ============================================================
# PROXIMOS PARTIDOS
# ============================================================

st.divider()

st.header(
    "🏈 PRÓXIMOS PARTIDOS 2026"
)


if future.empty:

    st.warning(
        "La fuente de datos todavía no muestra "
        "partidos futuros de 2026."
    )

else:

    predictions = []

    for _, game in future.iterrows():

        home = str(
            game["home_team"]
        )

        away = str(
            game["away_team"]
        )

        ht = final_teams.get(
            home,
            new_team()
        )

        at = final_teams.get(
            away,
            new_team()
        )

        features = create_features(
            ht,
            at
        )

        prob_home = float(
            final_model.predict_proba(
                [features]
            )[0][1]
        )

        # Evitamos probabilidades absurdas
        prob_home = float(
            np.clip(
                prob_home,
                0.05,
                0.95
            )
        )

        prob_away = (
            1
            - prob_home
        )

        if prob_home >= prob_away:

            pick = home
            probability = prob_home

        else:

            pick = away
            probability = prob_away

        fair_odds = (
            probability_to_american(
                probability
            )
        )

        if pd.isna(
            game["date"]
        ):

            game_date = "Fecha pendiente"

        else:

            game_date = (
                game["date"]
                .strftime(
                    "%Y-%m-%d"
                )
            )

        predictions.append({

            "Fecha":
                game_date,

            "Partido":
                f"{away} @ {home}",

            "Pick":
                pick,

            "Probabilidad":
                probability,

            "Cuota justa":
                fair_odds
        })


    predictions = pd.DataFrame(
        predictions
    )


    display = predictions.copy()

    display[
        "Probabilidad"
    ] = display[
        "Probabilidad"
    ].map(
        lambda x:
            f"{x:.1%}"
    )

    display[
        "Cuota justa"
    ] = display[
        "Cuota justa"
    ].map(
        lambda x:
            (
                f"+{x:.0f}"
                if x > 0
                else f"{x:.0f}"
            )
    )

    st.dataframe(
        display,
        use_container_width=True,
        hide_index=True
    )


# ============================================================
# ANALIZAR CUOTA
# ============================================================

st.divider()

st.header(
    "💰 BUSCAR EDGE"
)

st.write(
    """
    Aquí es donde realmente nos interesa el modelo.

    Primero el modelo calcula su probabilidad
    **sin conocer la cuota**.

    Después introducimos la cuota de la casa
    y comparamos ambas.
    """
)


if not future.empty:

    game_options = [
        (
            f"{row['Fecha']} — "
            f"{row['Partido']}"
        )
        for _, row
        in predictions.iterrows()
    ]

    selected_game = st.selectbox(
        "Selecciona el partido",
        game_options
    )

    selected_index = (
        game_options.index(
            selected_game
        )
    )

    selected = predictions.iloc[
        selected_index
    ]

    pick = selected[
        "Pick"
    ]

    model_probability = float(
        selected[
            "Probabilidad"
        ]
    )

    fair_odds = float(
        selected[
            "Cuota justa"
        ]
    )

    st.subheader(
        f"🎯 Pick del modelo: {pick}"
    )

    c1, c2 = st.columns(2)

    with c1:

        st.metric(
            "Probabilidad del modelo",
            f"{model_probability:.1%}"
        )

    with c2:

        st.metric(
            "Cuota justa",
            (
                f"+{fair_odds:.0f}"
                if fair_odds > 0
                else f"{fair_odds:.0f}"
            )
        )


    st.markdown(
        "### Introduce la cuota actual de la casa"
    )


    odds_type = st.radio(
        "Formato",
        [
            "American",
            "Decimal"
        ],
        horizontal=True
    )


    market_odds = st.number_input(
        "Cuota",
        value=100.0,
        step=5.0
    )


    # --------------------------------------------------------
    # CONVERTIR CUOTA
    # --------------------------------------------------------

    if odds_type == "American":

        decimal_odds = (
            american_to_decimal(
                market_odds
            )
        )

    else:

        decimal_odds = float(
            market_odds
        )


    if (
        decimal_odds is not None
        and decimal_odds > 1
    ):

        implied_probability = (
            decimal_to_implied(
                decimal_odds
            )
        )

        # ----------------------------------------------------
        # EDGE
        # ----------------------------------------------------

        edge = (
            model_probability
            -
            implied_probability
        )

        # ----------------------------------------------------
        # EV
        # ----------------------------------------------------

        expected_value = (
            model_probability
            * (
                decimal_odds
                - 1
            )
            -
            (
                1
                - model_probability
            )
        )


        st.divider()

        c1, c2, c3, c4 = st.columns(4)

        with c1:

            st.metric(
                "Modelo",
                f"{model_probability:.1%}"
            )

        with c2:

            st.metric(
                "Mercado",
                f"{implied_probability:.1%}"
            )

        with c3:

            st.metric(
                "EDGE",
                f"{edge:+.1%}"
            )

        with c4:

            st.metric(
                "EV",
                f"{expected_value:+.2%}"
            )


        # ====================================================
        # DECISION
        # ====================================================

        if (
            model_probability
            >= min_probability
            and
            edge
            >= min_edge
            and
            expected_value
            > 0
        ):

            st.success(
                f"🔥 POSIBLE EDGE — {pick}"
            )

            st.write(
                f"""
                El modelo estima **{model_probability:.1%}**.

                El mercado implica aproximadamente
                **{implied_probability:.1%}**.

                Diferencia:
                **{edge:+.1%}**

                EV matemático estimado:
                **{expected_value:+.2%}**
                """
            )

        elif (
            model_probability
            >= min_probability
        ):

            st.warning(
                "⚠️ EL MODELO FAVORECE EL PICK, "
                "PERO LA CUOTA NO OFRECE SUFICIENTE EDGE"
            )

        else:

            st.info(
                "🧊 NO BET"
            )

            st.write(
                "La probabilidad del modelo no "
                "supera el mínimo configurado."
            )


# ============================================================
# TABLA DE CALIBRACION DEL BACKTEST
# ============================================================

st.divider()

st.header(
    "🎯 CALIBRACIÓN DEL MODELO"
)

bt = backtest["results"].copy()


if not bt.empty:

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
        1.01
    ]

    labels = [
        "50-54%",
        "55-59%",
        "60-64%",
        "65-69%",
        "70-74%",
        "75-79%",
        "80-84%",
        "85-89%",
        "90%+"
    ]

    bt["bucket"] = pd.cut(
        bt["prob_home"],
        bins=bins,
        labels=labels,
        right=False
    )

    calibration = (
        bt
        .groupby(
            "bucket",
            observed=False
        )
        .agg(
            partidos=(
                "actual_home",
                "size"
            ),
            prob_modelo=(
                "prob_home",
                "mean"
            ),
            victorias=(
                "actual_home",
                "sum"
            )
        )
        .reset_index()
    )

    calibration[
        "victoria_real"
    ] = (
        calibration[
            "victorias"
        ]
        /
        calibration[
            "partidos"
        ]
    )

    calibration[
        "error"
    ] = (
        calibration[
            "victoria_real"
        ]
        -
        calibration[
            "prob_modelo"
        ]
    )

    calibration_display = (
        calibration.copy()
    )

    calibration_display[
        "prob_modelo"
    ] = calibration_display[
        "prob_modelo"
    ].map(
        lambda x:
            f"{x:.1%}"
    )

    calibration_display[
        "victoria_real"
    ] = calibration_display[
        "victoria_real"
    ].map(
        lambda x:
            f"{x:.1%}"
    )

    calibration_display[
        "error"
    ] = calibration_display[
        "error"
    ].map(
        lambda x:
            f"{x:+.1%}"
    )

    st.dataframe(
        calibration_display,
        use_container_width=True,
        hide_index=True
    )


# ============================================================
# QUE SIGNIFICA
# ============================================================

st.divider()

st.header(
    "🧠 ¿QUÉ ESTAMOS BUSCANDO?"
)

st.markdown(
    """
### No buscamos 100%.

Una probabilidad del 65% significa aproximadamente:

> El modelo cree que este resultado ocurre
> unas 65 veces de cada 100 situaciones similares.

No significa que el partido vaya a ganar.

---

### Tampoco queremos copiar a la casa.

El proceso es:

**Datos NFL → Modelo propio → Probabilidad**

y solamente después:

**Probabilidad propia ↔ Cuota del mercado → EDGE**

---

### Ejemplo

Si nuestro modelo dice:

**63%**

y la cuota de la casa equivale a:

**52%**

tenemos:

**EDGE ≈ +11%**

Eso es mucho más interesante que simplemente decir:

> "El equipo tiene 63% de probabilidad."

---

### Si el mercado ya está muy cerca

Modelo:

**63%**

Mercado:

**61%**

EDGE:

**+2%**

Entonces:

**NO BET**

Aunque el modelo crea que el equipo probablemente gana.

---

### Nuestro objetivo

No encontrar apuestas seguras.

Encontrar situaciones donde:

**nuestra estimación independiente**

sea suficientemente diferente de:

**la estimación implícita del mercado.**
"""
)


# ============================================================
# INFORMACION TECNICA
# ============================================================

st.divider()

st.header(
    "ℹ️ CONFIGURACIÓN DEL EXPERIMENTO"
)

info1, info2 = st.columns(2)

with info1:

    st.write(
        "**Histórico utilizado:**"
    )

    st.write(
        "2024 + 2025"
    )

    st.write(
        "**Backtest:**"
    )

    st.write(
        "Entrena 2024 → prueba 2025"
    )

    st.write(
        "**Temporada analizada:**"
    )

    st.write(
        "2026"
    )


with info2:

    st.write(
        "**Cuotas utilizadas para entrenar:**"
    )

    st.write(
        "NO"
    )

    st.write(
        "**Apuestas automáticas:**"
    )

    st.write(
        "NO"
    )

    st.write(
        "**Objetivo:**"
    )

    st.write(
        "Buscar EDGE independiente"
    )


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    "NFL Edge Monitor — modelo estadístico experimental "
    "independiente del mercado. "
    "Histórico máximo: 2024-2025. "
    "No realiza apuestas automáticamente."
)
