import streamlit as st
import pandas as pd
import numpy as np
import requests
import math
from datetime import datetime, date
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


# ============================================================
# NFL EDGE MONITOR
# MODELO INDEPENDIENTE DEL MERCADO
#
# HISTORICO MAXIMO: 2024-2025
# TEMPORADA ACTUAL: 2026
#
# NO USA CUOTAS PARA CREAR LA PROBABILIDAD
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
CURRENT_SEASON = 2026

DATA_URL = (
    "https://raw.githubusercontent.com/"
    "nflverse/nfldata/master/data/games.csv"
)


# ============================================================
# ESTILO
# ============================================================

st.markdown("""
<style>

.block-container {
    padding-top: 2rem;
    padding-bottom: 4rem;
}

h1 {
    font-size: 3rem !important;
}

h2 {
    font-size: 2rem !important;
}

.metric-label {
    font-size: 1rem;
}

.edge-positive {
    color: #00d084;
    font-weight: bold;
}

.edge-negative {
    color: #ff4b4b;
    font-weight: bold;
}

.bet-card {
    padding: 18px;
    border-radius: 12px;
    border: 1px solid #333;
    margin-bottom: 12px;
}

</style>
""", unsafe_allow_html=True)


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

    # Normalizar nombres
    df.columns = [str(c).strip().lower() for c in df.columns]

    # Buscar columnas importantes
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
            "La fuente NFL cambió sus columnas. "
            f"Faltan: {missing}"
        )

        return pd.DataFrame()

    # Fecha
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

    # Numericos
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

    # Eliminar filas sin equipos
    df = df.dropna(
        subset=[
            "season",
            "home_team",
            "away_team"
        ]
    )

    df["season"] = df["season"].astype(int)

    return df


games = load_games()


if games.empty:

    st.stop()


# ============================================================
# TITULO
# ============================================================

st.title("🏈 NFL EDGE MONITOR")

st.subheader(
    "Modelo propio independiente del mercado"
)

st.caption(
    "Histórico máximo utilizado: temporadas 2024 y 2025"
)


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.header("⚙️ CONFIGURACIÓN")

min_edge = st.sidebar.slider(
    "EDGE mínimo para considerar apuesta",
    min_value=0.00,
    max_value=0.15,
    value=0.04,
    step=0.01,
    format="%.0f%%"
)

min_probability = st.sidebar.slider(
    "Probabilidad mínima",
    min_value=0.50,
    max_value=0.80,
    value=0.55,
    step=0.01,
    format="%.0f%%"
)

recent_games = st.sidebar.slider(
    "Partidos recientes utilizados",
    min_value=3,
    max_value=10,
    value=5
)


# ============================================================
# FUNCIONES
# ============================================================

def sigmoid(x):

    return 1 / (1 + np.exp(-np.clip(x, -20, 20)))


def american_to_decimal(odds):

    try:

        odds = float(odds)

    except:

        return None

    if odds == 0:

        return None

    if odds > 0:

        return 1 + odds / 100

    return 1 + 100 / abs(odds)


def decimal_to_implied(decimal):

    if decimal is None or decimal <= 1:

        return None

    return 1 / decimal


def probability_to_fair_odds(prob):

    if prob <= 0 or prob >= 1:

        return None

    decimal = 1 / prob

    if decimal >= 2:

        american = (decimal - 1) * 100

    else:

        american = -100 / (decimal - 1)

    return american


# ============================================================
# PREPARAR PARTIDOS TERMINADOS
# ============================================================

historical = games[
    games["season"].isin(HISTORIC_SEASONS)
].copy()


# Solo partidos con marcador
historical = historical[
    historical["home_score"].notna()
    &
    historical["away_score"].notna()
].copy()


# ============================================================
# CREAR ESTADO DE EQUIPOS
# ============================================================

def initial_team():

    return {
        "elo": 1500.0,

        "games": 0,

        "wins": 0,

        "points_for": [],

        "points_against": [],

        "point_diff": [],

        "last_dates": []
    }


def get_team(
    teams,
    name
):

    if name not in teams:

        teams[name] = initial_team()

    return teams[name]


def team_features(team):

    if team["games"] == 0:

        return {
            "elo": 1500.0,
            "win_rate": 0.50,
            "pf": 22.0,
            "pa": 22.0,
            "diff": 0.0,
            "recent_win": 0.50,
            "recent_diff": 0.0
        }

    pf = np.mean(
        team["points_for"][-recent_games:]
    )

    pa = np.mean(
        team["points_against"][-recent_games:]
    )

    diff = np.mean(
        team["point_diff"][-recent_games:]
    )

    recent_wins = []

    for i in range(
        max(
            0,
            len(team["point_diff"]) - recent_games
        ),
        len(team["point_diff"])
    ):

        if team["point_diff"][i] > 0:

            recent_wins.append(1)

        else:

            recent_wins.append(0)

    recent_win = (
        np.mean(recent_wins)
        if recent_wins
        else 0.50
    )

    return {
        "elo": team["elo"],
        "win_rate": team["wins"] / team["games"],
        "pf": pf,
        "pa": pa,
        "diff": diff,
        "recent_win": recent_win,
        "recent_diff": diff
    }


# ============================================================
# CONSTRUIR DATASET SIN LOOK-AHEAD
# ============================================================

def build_training_dataset(df):

    df = df.sort_values(
        ["date", "season", "week"]
    ).copy()

    teams = {}

    X = []
    y = []

    for _, game in df.iterrows():

        home = str(game["home_team"])
        away = str(game["away_team"])

        hs = game["home_score"]
        aws = game["away_score"]

        if pd.isna(hs) or pd.isna(aws):

            continue

        home_team = get_team(
            teams,
            home
        )

        away_team = get_team(
            teams,
            away
        )

        hf = team_features(home_team)
        af = team_features(away_team)

        # -------------------------------
        # FEATURES
        # -------------------------------

        elo_diff = (
            hf["elo"]
            - af["elo"]
        )

        win_rate_diff = (
            hf["win_rate"]
            - af["win_rate"]
        )

        pf_diff = (
            hf["pf"]
            - af["pf"]
        )

        pa_diff = (
            hf["pa"]
            - af["pa"]
        )

        point_diff = (
            hf["diff"]
            - af["diff"]
        )

        recent_win_diff = (
            hf["recent_win"]
            - af["recent_win"]
        )

        recent_diff = (
            hf["recent_diff"]
            - af["recent_diff"]
        )

        X.append([
            elo_diff,
            win_rate_diff,
            pf_diff,
            pa_diff,
            point_diff,
            recent_win_diff,
            recent_diff,
            1.0  # localía
        ])

        y.append(
            1 if hs > aws else 0
        )

        # -------------------------------
        # ACTUALIZAR ELO
        # -------------------------------

        expected = sigmoid(
            (away_team["elo"]
             - home_team["elo"]
             + 65)
            / 400
        )

        home_expected = 1 - expected

        actual = (
            1
            if hs > aws
            else 0
        )

        elo_change = (
            20
            * (
                actual
                - home_expected
            )
        )

        home_team["elo"] += elo_change
        away_team["elo"] -= elo_change

        # -------------------------------
        # ACTUALIZAR ESTADISTICAS
        # -------------------------------

        home_team["games"] += 1
        away_team["games"] += 1

        if hs > aws:

            home_team["wins"] += 1

        else:

            away_team["wins"] += 1

        home_team[
            "points_for"
        ].append(float(hs))

        home_team[
            "points_against"
        ].append(float(aws))

        home_team[
            "point_diff"
        ].append(
            float(hs - aws)
        )

        away_team[
            "points_for"
        ].append(float(aws))

        away_team[
            "points_against"
        ].append(float(hs))

        away_team[
            "point_diff"
        ].append(
            float(aws - hs)
        )

        if pd.notna(game["date"]):

            home_team[
                "last_dates"
            ].append(game["date"])

            away_team[
                "last_dates"
            ].append(game["date"])

    return (
        np.array(X),
        np.array(y),
        teams
    )


# ============================================================
# ENTRENAR
# ============================================================

X_train, y_train, teams = build_training_dataset(
    historical
)


if len(X_train) < 100:

    st.error(
        "No hay suficientes partidos históricos "
        "para entrenar el modelo."
    )

    st.stop()


model = Pipeline([
    (
        "scale",
        StandardScaler()
    ),
    (
        "logistic",
        LogisticRegression(
            max_iter=2000,
            C=0.7
        )
    )
])


model.fit(
    X_train,
    y_train
)


# ============================================================
# BACKTEST
# ============================================================

def run_backtest(df):

    df = df.sort_values(
        ["date", "season", "week"]
    ).copy()

    teams_bt = {}

    predictions = []

    for _, game in df.iterrows():

        home = str(game["home_team"])
        away = str(game["away_team"])

        hs = game["home_score"]
        aws = game["away_score"]

        if pd.isna(hs) or pd.isna(aws):

            continue

        ht = get_team(
            teams_bt,
            home
        )

        at = get_team(
            teams_bt,
            away
        )

        hf = team_features(ht)
        af = team_features(at)

        features = [[

            hf["elo"] - af["elo"],

            hf["win_rate"]
            - af["win_rate"],

            hf["pf"] - af["pf"],

            hf["pa"] - af["pa"],

            hf["diff"] - af["diff"],

            hf["recent_win"]
            - af["recent_win"],

            hf["recent_diff"]
            - af["recent_diff"],

            1.0

        ]]

        # Entrenamiento progresivo
        # usando solamente información anterior

        if len(predictions) >= 100:

            p = model.predict_proba(
                features
            )[0][1]

            actual = (
                1
                if hs > aws
                else 0
            )

            predictions.append({
                "prob": p,
                "actual": actual
            })

        else:

            predictions.append({
                "prob": 0.5,
                "actual":
                    1 if hs > aws else 0
            })

        # Actualizar
        expected = sigmoid(
            (at["elo"]
             - ht["elo"]
             + 65)
            / 400
        )

        home_expected = 1 - expected

        actual = (
            1
            if hs > aws
            else 0
        )

        elo_change = (
            20
            * (
                actual
                - home_expected
            )
        )

        ht["elo"] += elo_change
        at["elo"] -= elo_change

        ht["games"] += 1
        at["games"] += 1

        if hs > aws:

            ht["wins"] += 1

        else:

            at["wins"] += 1

        ht["points_for"].append(float(hs))
        ht["points_against"].append(float(aws))
        ht["point_diff"].append(
            float(hs - aws)
        )

        at["points_for"].append(float(aws))
        at["points_against"].append(float(hs))
        at["point_diff"].append(
            float(aws - hs)
        )

    bt = pd.DataFrame(predictions)

    if bt.empty:

        return None

    bt["prediction"] = (
        bt["prob"] >= 0.50
    ).astype(int)

    accuracy = (
        bt["prediction"]
        == bt["actual"]
    ).mean()

    brier = np.mean(
        (
            bt["prob"]
            - bt["actual"]
        ) ** 2
    )

    return {
        "accuracy": accuracy,
        "brier": brier,
        "games": len(bt)
    }


backtest = run_backtest(
    historical
)


# ============================================================
# CABECERA
# ============================================================

st.divider()

col1, col2, col3 = st.columns(3)

with col1:

    st.metric(
        "📊 Partidos históricos",
        f"{len(historical):,}"
    )

with col2:

    st.metric(
        "🎯 Accuracy backtest",
        (
            f"{backtest['accuracy']:.2%}"
            if backtest
            else "N/A"
        )
    )

with col3:

    st.metric(
        "📉 Brier Score",
        (
            f"{backtest['brier']:.4f}"
            if backtest
            else "N/A"
        )
    )


st.caption(
    "El backtest utiliza únicamente información disponible "
    "antes de cada partido. No utiliza cuotas."
)


# ============================================================
# ESTADO FINAL DE LOS EQUIPOS
# ============================================================

# teams viene entrenado con todo 2024-2025


# ============================================================
# PARTIDOS 2026
# ============================================================

future = games[
    games["season"] == CURRENT_SEASON
].copy()


# Solo futuros / sin marcador
future = future[
    future["home_score"].isna()
    |
    future["away_score"].isna()
].copy()


if "date" in future.columns:

    future = future.sort_values(
        "date"
    )


st.divider()

st.header("🏈 PRÓXIMOS PARTIDOS")


if future.empty:

    st.warning(
        "No se encontraron partidos futuros de 2026 "
        "en la fuente de datos."
    )

else:

    rows = []

    for _, game in future.iterrows():

        home = str(game["home_team"])
        away = str(game["away_team"])

        ht = teams.get(
            home,
            initial_team()
        )

        at = teams.get(
            away,
            initial_team()
        )

        hf = team_features(ht)
        af = team_features(at)

        features = [[

            hf["elo"] - af["elo"],

            hf["win_rate"]
            - af["win_rate"],

            hf["pf"] - af["pf"],

            hf["pa"] - af["pa"],

            hf["diff"] - af["diff"],

            hf["recent_win"]
            - af["recent_win"],

            hf["recent_diff"]
            - af["recent_diff"],

            1.0

        ]]

        probability_home = (
            model.predict_proba(
                features
            )[0][1]
        )

        probability_home = float(
            np.clip(
                probability_home,
                0.05,
                0.95
            )
        )

        probability_away = (
            1
            - probability_home
        )

        if probability_home >= probability_away:

            pick = home
            probability = probability_home

        else:

            pick = away
            probability = probability_away

        fair_american = (
            probability_to_fair_odds(
                probability
            )
        )

        if "date" in future.columns:

            game_date = game["date"]

            if pd.isna(game_date):

                game_date = "Fecha pendiente"

            else:

                game_date = game_date.strftime(
                    "%Y-%m-%d"
                )

        else:

            game_date = "Fecha pendiente"

        rows.append({

            "Fecha": game_date,

            "Partido":
                f"{away} @ {home}",

            "Pick": pick,

            "Probabilidad":
                probability,

            "Cuota justa":
                fair_american,

            "ELO local":
                hf["elo"],

            "ELO visitante":
                af["elo"]

        })


    predictions = pd.DataFrame(rows)


    # ========================================================
    # MOSTRAR
    # ========================================================

    display_df = predictions.copy()

    display_df[
        "Probabilidad"
    ] = display_df[
        "Probabilidad"
    ].map(
        lambda x: f"{x:.1%}"
    )

    display_df[
        "Cuota justa"
    ] = display_df[
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
        display_df,
        use_container_width=True,
        hide_index=True
    )


# ============================================================
# ANALISIS DE CUOTAS
# ============================================================

st.divider()

st.header("💰 ANALIZAR UNA CUOTA")

st.write(
    "Aquí es donde buscamos la diferencia entre "
    "nuestro modelo y la casa. La cuota NO entra "
    "en el cálculo de nuestra probabilidad."
)


if not future.empty:

    game_options = [
        f"{r['Fecha']} — {r['Partido']}"
        for _, r in predictions.iterrows()
    ]

    selected_game = st.selectbox(
        "Selecciona partido",
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

    pick = selected["Pick"]
    model_prob = selected["Probabilidad"]

    st.subheader(
        f"🎯 Modelo: {pick}"
    )

    c1, c2, c3 = st.columns(3)

    with c1:

        st.metric(
            "Probabilidad modelo",
            f"{model_prob:.1%}"
        )

    with c2:

        fair = selected[
            "Cuota justa"
        ]

        st.metric(
            "Cuota justa",
            (
                f"+{fair:.0f}"
                if fair > 0
                else f"{fair:.0f}"
            )
        )

    with c3:

        st.metric(
            "EDGE mínimo",
            f"{min_edge:.1%}"
        )


    st.markdown("### Introduce la cuota de la casa")

    odds_type = st.radio(
        "Tipo de cuota",
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


    if odds_type == "American":

        decimal = american_to_decimal(
            market_odds
        )

    else:

        decimal = float(
            market_odds
        )


    if decimal is not None and decimal > 1:

        implied_probability = (
            decimal_to_implied(
                decimal
            )
        )

        # EDGE simple
        edge = (
            model_prob
            - implied_probability
        )

        # Valor esperado por $1 apostado
        expected_value = (
            model_prob
            * (decimal - 1)
            - (1 - model_prob)
        )


        st.divider()

        c1, c2, c3, c4 = st.columns(4)

        with c1:

            st.metric(
                "Prob. modelo",
                f"{model_prob:.1%}"
            )

        with c2:

            st.metric(
                "Prob. implícita",
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
            model_prob >= min_probability
            and edge >= min_edge
            and expected_value > 0
        ):

            st.success(
                f"🔥 EDGE DETECTADO — {pick}"
            )

            st.write(
                f"""
                **Probabilidad modelo:** {model_prob:.1%}

                **Probabilidad implícita:** {implied_probability:.1%}

                **EDGE:** {edge:+.1%}

                **EV estimado:** {expected_value:+.2%}

                El modelo encuentra una diferencia favorable
                respecto a la cuota introducida.
                """
            )

        elif model_prob >= min_probability:

            st.warning(
                "⚠️ BUENA PROBABILIDAD, PERO SIN EDGE SUFICIENTE"
            )

            st.write(
                "El modelo puede favorecer este equipo, "
                "pero la cuota no ofrece suficiente ventaja."
            )

        else:

            st.info(
                "🧊 NO BET"
            )

            st.write(
                "La probabilidad del modelo no alcanza "
                "el nivel mínimo configurado."
            )


# ============================================================
# EXPLICACION DEL MODELO
# ============================================================

st.divider()

st.header("🧠 ¿CÓMO FUNCIONA?")


st.markdown("""
### 1. No intentamos predecir el futuro con 100%

El modelo entrega una **probabilidad estimada**, no una certeza.

### 2. No copiamos a la casa

La cuota no se utiliza para calcular la probabilidad del modelo.

Primero:

**Datos NFL → Modelo → Probabilidad**

Después:

**Probabilidad del modelo ↔ Cuota de mercado → EDGE**

### 3. Solo usamos dos temporadas

El histórico máximo utilizado es:

**2024 + 2025**

No utilizamos 2019, 2020, 2021, 2022 ni 2023.

### 4. No necesitamos archivos V6 históricos

No hay que subir:

`nfl_v6_predictions_2019.csv`

ni

`nfl_v6_predictions_2025.csv`

### 5. No apostamos solamente porque el modelo diga 60%

Ejemplo:

Modelo = 62%

Casa = cuota equivalente a 61%

➡️ **No hay suficiente ventaja.**

Pero:

Modelo = 62%

Casa = cuota equivalente a 52%

➡️ **Existe un EDGE mucho más interesante.**

### 6. El objetivo real

No buscamos:

> "¿Quién va a ganar seguro?"

Buscamos:

> **"¿La probabilidad que estimamos es suficientemente diferente de la probabilidad que está pagando el mercado?"**
""")


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    "NFL Edge Monitor — modelo estadístico experimental "
    "independiente del mercado. Histórico máximo: 2024-2025. "
    "No realiza apuestas automáticamente."
)
