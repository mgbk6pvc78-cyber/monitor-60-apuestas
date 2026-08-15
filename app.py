import streamlit as st
import pandas as pd
import numpy as np
from pathlib import Path


# ============================================================
# 🏈 NFL_SIMPLE_V2_MODEL
#
# PRIMER MODELO PROPIO DE PROBABILIDAD
#
# 2024 = ENTRENAMIENTO
# 2025 = TEST OUT-OF-SAMPLE
#
# NO UTILIZA:
# - Moneyline
# - Odds
# - Spread
# - Sportsbooks
#
# Solo utiliza información PREGAME.
# ============================================================

st.set_page_config(
    page_title="NFL_SIMPLE_V2_MODEL",
    page_icon="🏈",
    layout="wide"
)

st.title("🏈 NFL_SIMPLE_V2_MODEL")

st.markdown("""
### Primera probabilidad propia NFL

El modelo aprende con **2024** y se prueba
completamente fuera de muestra con **2025**.

No se utilizan probabilidades de casas de apuestas.
""")


# ============================================================
# CONFIGURACIÓN
# ============================================================

BASE_DIR = Path("NFL_SIMPLE_V1")

PREGAME_FILE = (
    BASE_DIR /
    "NFL_SIMPLE_V1_PREGAME.csv"
)

OUTPUT_DIR = Path(
    "NFL_SIMPLE_V2"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# CARGAR DATASET
# ============================================================

st.header("1. Cargando PREGAME")

if not PREGAME_FILE.exists():

    st.error(
        f"""
No se encontró el archivo:

{PREGAME_FILE}

Primero ejecuta NFL_SIMPLE_V1_PREGAME.
"""
    )

    st.stop()


pregame = pd.read_csv(
    PREGAME_FILE
)

pregame["gameday"] = pd.to_datetime(
    pregame["gameday"],
    errors="coerce"
)

st.success(
    "✅ NFL_SIMPLE_V1_PREGAME cargado correctamente."
)


# ============================================================
# ORDEN CRONOLÓGICO
# ============================================================

pregame = (
    pregame
    .sort_values(
        [
            "gameday",
            "game_id"
        ]
    )
    .reset_index(drop=True)
)


# ============================================================
# VARIABLES PROHIBIDAS
# ============================================================

FORBIDDEN = [

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


# ============================================================
# TARGET
# ============================================================

TARGET = "home_win"


# ============================================================
# FEATURES
# ============================================================

FEATURES = [

    c
    for c in pregame.columns
    if c not in FORBIDDEN
]


# ============================================================
# AUDITORÍA
# ============================================================

st.header("2. Auditoría del modelo")

audit = pd.DataFrame({

    "Variable": FEATURES,

    "Tipo": [
        str(pregame[c].dtype)
        for c in FEATURES
    ],

    "Faltantes": [
        int(pregame[c].isna().sum())
        for c in FEATURES
    ],

    "Únicos": [
        int(pregame[c].nunique())
        for c in FEATURES
    ]
})

st.dataframe(
    audit,
    use_container_width=True,
    hide_index=True
)


# ============================================================
# LEAKAGE
# ============================================================

leakage = [
    c
    for c in FEATURES
    if c in FORBIDDEN
]

if leakage:

    st.error(
        f"❌ Leakage detectado: {leakage}"
    )

    st.stop()

else:

    st.success(
        "✅ Auditoría de leakage aprobada."
    )


# ============================================================
# TRAIN / TEST
# ============================================================

train = pregame[
    pregame["season"] == 2024
].copy()

test = pregame[
    pregame["season"] == 2025
].copy()


train = train[
    train[TARGET].notna()
].copy()

test = test[
    test[TARGET].notna()
].copy()


# ============================================================
# CONVERTIR FEATURES A NUMÉRICAS
# ============================================================

X_train_raw = train[
    FEATURES
].copy()

X_test_raw = test[
    FEATURES
].copy()


for c in FEATURES:

    X_train_raw[c] = pd.to_numeric(
        X_train_raw[c],
        errors="coerce"
    )

    X_test_raw[c] = pd.to_numeric(
        X_test_raw[c],
        errors="coerce"
    )


# ============================================================
# ELIMINAR COLUMNAS QUE NO SON NUMÉRICAS
#
# En V2 solo queremos variables estadísticas.
# ============================================================

numeric_features = []

for c in FEATURES:

    if (
        pd.api.types
        .is_numeric_dtype(
            X_train_raw[c]
        )
    ):

        numeric_features.append(c)


FEATURES = numeric_features


X_train_raw = X_train_raw[
    FEATURES
]

X_test_raw = X_test_raw[
    FEATURES
]


# ============================================================
# TARGET
# ============================================================

y_train = (
    train[TARGET]
    .astype(float)
    .values
)

y_test = (
    test[TARGET]
    .astype(float)
    .values
)


# ============================================================
# IMPUTACIÓN
#
# MUY IMPORTANTE:
#
# Las medianas se calculan SOLO usando 2024.
# ============================================================

medians = (
    X_train_raw
    .median()
)


X_train = (
    X_train_raw
    .fillna(medians)
)

X_test = (
    X_test_raw
    .fillna(medians)
)


# ============================================================
# ESTANDARIZACIÓN
#
# También se calcula SOLO usando 2024.
# ============================================================

means = (
    X_train
    .mean()
)

stds = (
    X_train
    .std()
)

stds = stds.replace(
    0,
    1
)

X_train = (
    X_train
    - means
) / stds

X_test = (
    X_test
    - means
) / stds


# ============================================================
# CONVERTIR A NUMPY
# ============================================================

X_train = X_train.values.astype(float)

X_test = X_test.values.astype(float)


# ============================================================
# FUNCIÓN SIGMOIDE
# ============================================================

def sigmoid(z):

    z = np.clip(
        z,
        -30,
        30
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
# MODELO LOGÍSTICO SIMPLE
#
# IMPLEMENTADO CON NUMPY.
#
# NO DEPENDE DE SKLEARN.
# ============================================================

def train_logistic_regression(
    X,
    y,
    learning_rate=0.03,
    epochs=5000,
    l2=0.01
):

    n_rows, n_features = X.shape

    weights = np.zeros(
        n_features
    )

    bias = 0.0

    for epoch in range(epochs):

        z = (
            X @ weights
            +
            bias
        )

        p = sigmoid(z)

        error = (
            p - y
        )

        grad_w = (
            X.T @ error
            /
            n_rows
        )

        grad_b = (
            error.mean()
        )

        # Regularización L2
        grad_w += (
            l2
            *
            weights
        )

        weights -= (
            learning_rate
            *
            grad_w
        )

        bias -= (
            learning_rate
            *
            grad_b
        )

    return (
        weights,
        bias
    )


# ============================================================
# ENTRENAMIENTO
# ============================================================

st.header(
    "3. Entrenamiento"
)

st.info("""
🔒 TRAIN = 2024

🔒 TEST = 2025

🔒 Las medianas y escalas también se calcularon
solamente con 2024.
""")


with st.spinner(
    "Entrenando modelo con 2024..."
):

    weights, bias = (
        train_logistic_regression(
            X_train,
            y_train
        )
    )


st.success(
    "✅ Modelo entrenado correctamente."
)


# ============================================================
# PREDICCIÓN
# ============================================================

home_probability = sigmoid(
    X_test @ weights
    +
    bias
)

away_probability = (
    1
    -
    home_probability
)


predicted_home = (
    home_probability
    >=
    0.50
).astype(int)


# ============================================================
# RESULTADOS
# ============================================================

results = test[
    [
        "season",
        "week",
        "game_id",
        "gameday",
        "home_team",
        "away_team"
    ]
].copy()


results[
    "home_probability"
] = (
    home_probability
    *
    100
)

results[
    "away_probability"
] = (
    away_probability
    *
    100
)


results[
    "predicted_winner"
] = np.where(
    home_probability >= 0.50,
    results["home_team"],
    results["away_team"]
)


results[
    "actual_winner"
] = np.where(
    y_test == 1,
    results["home_team"],
    results["away_team"]
)


results[
    "correct"
] = (
    predicted_home
    ==
    y_test
)


# ============================================================
# MÉTRICAS
# ============================================================

def calculate_accuracy(
    y,
    p
):

    predictions = (
        p >= 0.50
    ).astype(int)

    return (
        predictions == y
    ).mean()


def calculate_brier(
    y,
    p
):

    return np.mean(
        (
            p - y
        ) ** 2
    )


def calculate_log_loss(
    y,
    p
):

    p = np.clip(
        p,
        1e-15,
        1 - 1e-15
    )

    return -np.mean(
        (
            y * np.log(p)
        )
        +
        (
            1 - y
        )
        *
        np.log(1 - p)
    )


def calculate_auc(
    y,
    p
):

    order = np.argsort(p)

    ranks = np.empty_like(
        order
    )

    ranks[order] = np.arange(
        len(p)
    )

    positive = (
        y == 1
    )

    negative = (
        y == 0
    )

    n_positive = positive.sum()

    n_negative = negative.sum()

    if (
        n_positive == 0
        or
        n_negative == 0
    ):

        return np.nan

    rank_sum = (
        ranks[positive].sum()
    )

    auc = (
        rank_sum
        -
        n_positive
        *
        (n_positive - 1)
        /
        2
    ) / (
        n_positive
        *
        n_negative
    )

    return auc


accuracy = calculate_accuracy(
    y_test,
    home_probability
)

brier = calculate_brier(
    y_test,
    home_probability
)

logloss = calculate_log_loss(
    y_test,
    home_probability
)

auc = calculate_auc(
    y_test,
    home_probability
)


# ============================================================
# MÉTRICAS
# ============================================================

st.header(
    "4. Evaluación 2025"
)

c1, c2, c3, c4 = st.columns(4)

with c1:

    st.metric(
        "Accuracy",
        f"{accuracy * 100:.2f}%"
    )

with c2:

    st.metric(
        "Brier Score",
        f"{brier:.4f}"
    )

with c3:

    st.metric(
        "Log Loss",
        f"{logloss:.4f}"
    )

with c4:

    st.metric(
        "ROC AUC",
        f"{auc:.4f}"
        if pd.notna(auc)
        else "N/A"
    )


# ============================================================
# BASELINE
# ============================================================

st.header(
    "5. Comparación contra baseline"
)

home_rate_train = (
    y_train.mean()
)


baseline_probability = np.full(
    len(y_test),
    home_rate_train
)


baseline_brier = (
    calculate_brier(
        y_test,
        baseline_probability
    )
)


baseline_logloss = (
    calculate_log_loss(
        y_test,
        baseline_probability
    )
)


baseline_accuracy = (
    calculate_accuracy(
        y_test,
        baseline_probability
    )
)


baseline_table = pd.DataFrame({

    "Métrica": [

        "Home win rate 2024",

        "Accuracy modelo",

        "Accuracy baseline",

        "Brier modelo",

        "Brier baseline",

        "Log Loss modelo",

        "Log Loss baseline"
    ],

    "Valor": [

        f"{home_rate_train * 100:.2f}%",

        f"{accuracy * 100:.2f}%",

        f"{baseline_accuracy * 100:.2f}%",

        f"{brier:.4f}",

        f"{baseline_brier:.4f}",

        f"{logloss:.4f}",

        f"{baseline_logloss:.4f}"
    ]
})


st.dataframe(
    baseline_table,
    use_container_width=True,
    hide_index=True
)


# ============================================================
# CALIBRACIÓN
# ============================================================

st.header(
    "6. Calibración"
)

bins = [

    (0.50, 0.55),
    (0.55, 0.60),
    (0.60, 0.65),
    (0.65, 0.70),
    (0.70, 0.75),
    (0.75, 0.80),
    (0.80, 0.85),
    (0.85, 0.90),
    (0.90, 1.00)
]


calibration_rows = []


for lower, upper in bins:

    mask = (
        (home_probability >= lower)
        &
        (
            home_probability
            <
            upper
        )
    )

    count = int(
        mask.sum()
    )

    if count == 0:
        continue

    actual = (
        y_test[mask].mean()
    )

    predicted = (
        home_probability[mask].mean()
    )

    calibration_rows.append({

        "Rango":
            f"{lower * 100:.0f}% - {upper * 100:.0f}%",

        "Partidos":
            count,

        "Probabilidad modelo":
            f"{predicted * 100:.2f}%",

        "Resultado real":
            f"{actual * 100:.2f}%",

        "Error":
            f"{(predicted - actual) * 100:+.2f}%"
    })


calibration = pd.DataFrame(
    calibration_rows
)


if len(calibration) > 0:

    st.dataframe(
        calibration,
        use_container_width=True,
        hide_index=True
    )


# ============================================================
# PREDICCIONES DE MAYOR CONFIANZA
# ============================================================

st.header(
    "7. Predicciones de mayor confianza"
)

top = (
    results
    .assign(
        confidence=lambda x:
        np.maximum(
            x["home_probability"],
            x["away_probability"]
        )
    )
    .sort_values(
        "confidence",
        ascending=False
    )
    .head(20)
)


st.dataframe(
    top,
    use_container_width=True,
    hide_index=True
)


# ============================================================
# EXPORTAR RESULTADOS
# ============================================================

results_file = (
    OUTPUT_DIR /
    "NFL_SIMPLE_V2_MODEL_2025.csv"
)

results.to_csv(
    results_file,
    index=False
)


# ============================================================
# EXPORTAR MÉTRICAS
# ============================================================

metrics = pd.DataFrame({

    "Métrica": [

        "Train",
        "Test",
        "Variables",
        "Odds",
        "Sportsbooks",
        "Leakage",
        "Accuracy",
        "Brier",
        "Log Loss",
        "ROC AUC"
    ],

    "Valor": [

        "2024",
        "2025",
        len(FEATURES),
        "NO",
        "NO",
        "NO",
        accuracy,
        brier,
        logloss,
        auc
    ]
})


metrics_file = (
    OUTPUT_DIR /
    "NFL_SIMPLE_V2_MODEL_METRICS.csv"
)

metrics.to_csv(
    metrics_file,
    index=False
)


# ============================================================
# EXPORTAR VARIABLES
# ============================================================

features_file = (
    OUTPUT_DIR /
    "NFL_SIMPLE_V2_MODEL_FEATURES.csv"
)

pd.DataFrame({
    "Variable": FEATURES
}).to_csv(
    features_file,
    index=False
)


# ============================================================
# AUDITORÍA FINAL
# ============================================================

st.header(
    "🏁 NFL_SIMPLE_V2_MODEL FINAL"
)


final_audit = pd.DataFrame({

    "Métrica": [

        "TRAIN",

        "TEST",

        "Partidos TRAIN",

        "Partidos TEST",

        "Variables utilizadas",

        "Odds utilizadas",

        "Sportsbooks utilizados",

        "Leakage",

        "Accuracy 2025",

        "Brier Score 2025",

        "Log Loss 2025",

        "ROC AUC 2025"
    ],

    "Resultado": [

        "2024",

        "2025",

        len(train),

        len(test),

        len(FEATURES),

        "NO",

        "NO",

        "NO",

        f"{accuracy * 100:.2f}%",

        f"{brier:.4f}",

        f"{logloss:.4f}",

        f"{auc:.4f}"
    ]
})


st.dataframe(
    final_audit,
    use_container_width=True,
    hide_index=True
)


st.success(
    "✅ NFL_SIMPLE_V2_MODEL creado correctamente."
)


st.info("""
### SIGUIENTE PASO

No vamos a modificar parámetros todavía.

Primero vamos a analizar objetivamente V2.

Después construiremos la siguiente versión solamente
si existe una razón estadística para hacerlo.

La meta sigue siendo:

**PROBABILIDAD PROPIA → comparar posteriormente
contra la línea de la casa.**

Sin meter la casa dentro del modelo.
""")


# ============================================================
# DESCARGAS
# ============================================================

st.header("8. Archivos generados")

st.write(
    f"📄 {results_file}"
)

st.write(
    f"📄 {metrics_file}"
)

st.write(
    f"📄 {features_file}"
)
