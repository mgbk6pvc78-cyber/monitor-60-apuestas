import streamlit as st
import pandas as pd
import numpy as np

from pathlib import Path

from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression

from sklearn.metrics import (
    accuracy_score,
    log_loss,
    brier_score_loss,
    roc_auc_score
)


# ============================================================
# 🏈 NFL_SIMPLE_V2_MODEL
#
# Primera versión del modelo de probabilidad NFL.
#
# 2024 = TRAIN
# 2025 = TEST OUT-OF-SAMPLE
#
# NO UTILIZA:
# - Moneyline
# - Spread
# - Odds
# - Sportsbooks
# ============================================================

st.set_page_config(
    page_title="NFL_SIMPLE_V2_MODEL",
    page_icon="🏈",
    layout="wide"
)

st.title("🏈 NFL_SIMPLE_V2_MODEL")

st.markdown(
    """
    ### Primera probabilidad propia NFL

    El modelo utiliza únicamente información disponible
    antes del partido.

    **2024 → entrenamiento**

    **2025 → evaluación fuera de muestra**

    Las casas de apuestas NO participan en esta etapa.
    """
)


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
# CARGAR PREGAME
# ============================================================

st.header("1. Cargando NFL_SIMPLE_V1_PREGAME")

if not PREGAME_FILE.exists():

    st.error(
        f"""
        No se encontró:

        {PREGAME_FILE}

        Primero debes ejecutar NFL_SIMPLE_V1_PREGAME
        en el mismo proyecto.
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
# INFORMACIÓN GENERAL
# ============================================================

st.header("2. Dataset del modelo")

c1, c2, c3 = st.columns(3)

with c1:

    st.metric(
        "Partidos",
        len(pregame)
    )

with c2:

    st.metric(
        "Temporadas",
        pregame["season"].nunique()
    )

with c3:

    st.metric(
        "Variables",
        len(pregame.columns)
    )


# ============================================================
# VALIDACIÓN DE TEMPORADAS
# ============================================================

required_seasons = {2024, 2025}

available_seasons = set(
    pregame["season"]
    .dropna()
    .astype(int)
    .unique()
)

missing_seasons = (
    required_seasons
    -
    available_seasons
)

if missing_seasons:

    st.error(
        f"Faltan temporadas: {missing_seasons}"
    )

    st.stop()


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
# DEFINIR TARGET
# ============================================================

TARGET = "home_win"


# ============================================================
# VARIABLES PROHIBIDAS
#
# Estas columnas NO pueden entrar al modelo.
# ============================================================

FORBIDDEN = [

    # Identificación
    "season",
    "week",
    "game_id",
    "gameday",
    "home_team",
    "away_team",

    # Target
    "home_win",

    # Resultado futuro
    "home_score",
    "away_score"
]


# ============================================================
# VARIABLES PREDICTORAS
# ============================================================

FEATURES = [

    column
    for column in pregame.columns
    if column not in FORBIDDEN
]


# ============================================================
# AUDITORÍA DE VARIABLES
# ============================================================

st.header("3. Auditoría de variables")

audit_rows = []

for column in FEATURES:

    audit_rows.append({

        "Variable": column,

        "Tipo":
            str(
                pregame[column].dtype
            ),

        "Faltantes":
            int(
                pregame[column].isna().sum()
            ),

        "Valores únicos":
            int(
                pregame[column].nunique(
                    dropna=True
                )
            )
    })


audit = pd.DataFrame(
    audit_rows
)

st.dataframe(
    audit,
    use_container_width=True,
    hide_index=True
)


# ============================================================
# COMPROBAR LEAKAGE
# ============================================================

leakage_columns = [

    column
    for column in FEATURES
    if column in FORBIDDEN
]

if leakage_columns:

    st.error(
        f"❌ LEAKAGE DETECTADO: {leakage_columns}"
    )

    st.stop()

else:

    st.success(
        "✅ No hay variables prohibidas dentro del modelo."
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


# ============================================================
# VALIDAR TARGET
# ============================================================

train = train[
    train[TARGET].notna()
].copy()

test = test[
    test[TARGET].notna()
].copy()


y_train = (
    train[TARGET]
    .astype(int)
)

y_test = (
    test[TARGET]
    .astype(int)
)


X_train = train[
    FEATURES
].copy()

X_test = test[
    FEATURES
].copy()


# ============================================================
# INFORMACIÓN TRAIN / TEST
# ============================================================

st.header("4. Separación temporal")

split_table = pd.DataFrame({

    "Grupo": [
        "TRAIN",
        "TEST"
    ],

    "Temporada": [
        "2024",
        "2025"
    ],

    "Partidos": [
        len(train),
        len(test)
    ]
})

st.dataframe(
    split_table,
    use_container_width=True,
    hide_index=True
)

st.info(
    """
    🔒 El modelo aprende exclusivamente con 2024.

    🔒 Ningún resultado de 2025 se utiliza durante el entrenamiento.

    🔒 2025 funciona como evaluación completamente fuera de muestra.
    """
)


# ============================================================
# MODELO
# ============================================================
#
# Pipeline:
#
# 1. Imputar valores faltantes
# 2. Estandarizar variables
# 3. Logistic Regression
#
# Logistic Regression es deliberadamente simple.
# Primero queremos una referencia limpia antes de
# intentar modelos más complejos.
# ============================================================

model = Pipeline(
    steps=[

        (
            "imputer",
            SimpleImputer(
                strategy="median"
            )
        ),

        (
            "scaler",
            StandardScaler()
        ),

        (
            "model",
            LogisticRegression(
                max_iter=5000,
                C=1.0,
                solver="lbfgs"
            )
        )
    ]
)


# ============================================================
# ENTRENAMIENTO
# ============================================================

st.header("5. Entrenamiento")

with st.spinner(
    "Entrenando modelo con 2024..."
):

    model.fit(
        X_train,
        y_train
    )


st.success(
    "✅ Modelo entrenado utilizando solamente 2024."
)


# ============================================================
# PREDICCIONES
# ============================================================

st.header(
    "6. Probabilidades 2025"
)

probabilities = model.predict_proba(
    X_test
)


# ------------------------------------------------------------
# Probabilidad de HOME
# ------------------------------------------------------------

home_probability = (
    probabilities[:, 1]
)


away_probability = (
    1
    -
    home_probability
)


predicted_home = (
    home_probability >= 0.50
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
] = home_probability

results[
    "away_probability"
] = away_probability

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
# PORCENTAJES
# ============================================================

results[
    "home_probability"
] = (
    results[
        "home_probability"
    ]
    * 100
)

results[
    "away_probability"
] = (
    results[
        "away_probability"
    ]
    * 100
)


# ============================================================
# MÉTRICAS
# ============================================================

accuracy = accuracy_score(
    y_test,
    predicted_home
)

logloss = log_loss(
    y_test,
    home_probability
)

brier = brier_score_loss(
    y_test,
    home_probability
)

auc = roc_auc_score(
    y_test,
    home_probability
)


# ============================================================
# RESULTADOS GENERALES
# ============================================================

st.header(
    "7. Evaluación 2025"
)

m1, m2, m3, m4 = st.columns(4)

with m1:

    st.metric(
        "Accuracy",
        f"{accuracy * 100:.2f}%"
    )

with m2:

    st.metric(
        "Log Loss",
        f"{logloss:.4f}"
    )

with m3:

    st.metric(
        "Brier Score",
        f"{brier:.4f}"
    )

with m4:

    st.metric(
        "ROC AUC",
        f"{auc:.4f}"
    )


# ============================================================
# BASELINE
# ============================================================

st.header(
    "8. Comparación contra baseline"
)

home_rate = (
    y_train.mean()
)

baseline_predictions = np.full(
    len(y_test),
    home_rate
)

baseline_brier = brier_score_loss(
    y_test,
    baseline_predictions
)

baseline_logloss = log_loss(
    y_test,
    baseline_predictions
)


baseline_table = pd.DataFrame({

    "Métrica": [
        "Home win rate TRAIN",
        "Model Brier",
        "Baseline Brier",
        "Model Log Loss",
        "Baseline Log Loss"
    ],

    "Valor": [
        f"{home_rate * 100:.2f}%",
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
# CALIBRACIÓN SIMPLE
# ============================================================

st.header(
    "9. Calibración"
)

calibration_bins = [

    (0.50, 0.55),
    (0.55, 0.60),
    (0.60, 0.65),
    (0.65, 0.70),
    (0.70, 0.75),
    (0.75, 0.80),
    (0.80, 0.85),
    (0.85, 0.90),
    (0.90, 1.01)
]


calibration_rows = []


for lower, upper in calibration_bins:

    mask = (
        (home_probability >= lower)
        &
        (home_probability < upper)
    )

    n = int(mask.sum())

    if n == 0:
        continue

    avg_probability = (
        home_probability[mask].mean()
    )

    actual_rate = (
        y_test.iloc[
            np.where(mask)[0]
        ].mean()
    )

    calibration_rows.append({

        "Rango":
            f"{lower * 100:.0f}% - {min(upper, 1.0) * 100:.0f}%",

        "Partidos":
            n,

        "Probabilidad promedio":
            avg_probability * 100,

        "Resultado real":
            actual_rate * 100,

        "Diferencia":
            (
                avg_probability
                -
                actual_rate
            )
            * 100
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
# MAYORES PROBABILIDADES
# ============================================================

st.header(
    "10. Predicciones de mayor confianza"
)

top_results = (
    results
    .sort_values(
        "home_probability",
        ascending=False
    )
    .head(20)
)

st.dataframe(
    top_results,
    use_container_width=True,
    hide_index=True
)


# ============================================================
# MENORES PROBABILIDADES HOME
# ============================================================

st.header(
    "11. Mayor confianza visitante"
)

away_confidence = (
    results
    .sort_values(
        "home_probability",
        ascending=True
    )
    .head(20)
)

st.dataframe(
    away_confidence,
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

        "Train season",
        "Test season",
        "Train games",
        "Test games",
        "Features",
        "Accuracy",
        "Log Loss",
        "Brier Score",
        "ROC AUC",
        "Baseline Brier",
        "Baseline Log Loss"
    ],

    "Valor": [

        2024,
        2025,
        len(train),
        len(test),
        len(FEATURES),
        accuracy,
        logloss,
        brier,
        auc,
        baseline_brier,
        baseline_logloss
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


st.info(
    """
    SIGUIENTE PASO:

    No vamos a cambiar parámetros todavía.

    Primero analizaremos objetivamente cómo se comportó
    esta primera probabilidad en 2025.

    Después podremos construir V3 y comparar modelos
    sin contaminar la evaluación.
    """
)
