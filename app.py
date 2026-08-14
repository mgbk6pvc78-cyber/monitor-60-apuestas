import streamlit as st
import pandas as pd
from pathlib import Path

# ============================================================
# 🏈 NFL_SIMPLE_V1
# DATA AUDIT
#
# PROYECTO COMPLETAMENTE INDEPENDIENTE
# NO UTILIZA:
# - Moneylines
# - Spreads
# - Over/Under
# - Odds
# - Probabilidades de sportsbooks
#
# TEMPORADAS:
# - 2024
# - 2025
# ============================================================

st.set_page_config(
    page_title="NFL_SIMPLE_V1",
    page_icon="🏈",
    layout="wide"
)

st.title("🏈 NFL_SIMPLE_V1")
st.subheader("Data Audit — 2024 y 2025")

# ============================================================
# CONFIGURACIÓN
# ============================================================

DATA_URL = (
    "https://raw.githubusercontent.com/"
    "nflverse/nfldata/master/data/games.csv"
)

SEASONS = [2024, 2025]

OUTPUT_DIR = Path("NFL_SIMPLE_V1")
OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# 1. DESCARGAR DATASET
# ============================================================

st.header("1. Descargando datos NFL")

try:

    df = pd.read_csv(
        DATA_URL
    )

    st.success(
        "✅ Dataset NFL descargado correctamente."
    )

except Exception as e:

    st.error(
        "❌ No se pudo descargar el dataset."
    )

    st.exception(e)

    st.stop()


# ============================================================
# 2. NORMALIZAR COLUMNAS
# ============================================================

df.columns = [
    str(c).strip().lower()
    for c in df.columns
]


# ============================================================
# 3. INFORMACIÓN GENERAL
# ============================================================

st.header("2. Dataset original")

col1, col2, col3 = st.columns(3)

with col1:

    st.metric(
        "Registros",
        f"{len(df):,}"
    )

with col2:

    st.metric(
        "Columnas",
        len(df.columns)
    )

with col3:

    st.metric(
        "Temporadas",
        df["season"].nunique()
    )


# ============================================================
# 4. COLUMNAS
# ============================================================

st.header("3. Columnas disponibles")

columns_table = pd.DataFrame({
    "Número": range(
        len(df.columns)
    ),
    "Columna": df.columns
})

st.dataframe(
    columns_table,
    use_container_width=True,
    hide_index=True
)


# ============================================================
# 5. TIPOS DE DATOS
# ============================================================

st.header("4. Tipos de datos")

dtype_table = pd.DataFrame({
    "Columna": df.columns,
    "Tipo": [
        str(df[c].dtype)
        for c in df.columns
    ]
})

st.dataframe(
    dtype_table,
    use_container_width=True,
    hide_index=True
)


# ============================================================
# 6. COLUMNAS ESENCIALES
# ============================================================

st.header("5. Validación de columnas esenciales")

required_columns = [
    "game_id",
    "season",
    "game_type",
    "week",
    "gameday",
    "away_team",
    "away_score",
    "home_team",
    "home_score",
    "location",
    "result",
    "total"
]

missing_columns = [
    c
    for c in required_columns
    if c not in df.columns
]

if len(missing_columns) == 0:

    st.success(
        "✅ Todas las columnas esenciales están presentes."
    )

else:

    st.error(
        "❌ Faltan columnas esenciales:"
    )

    st.write(
        missing_columns
    )

    st.stop()


# ============================================================
# 7. NORMALIZAR TEMPORADA
# ============================================================

df["season"] = pd.to_numeric(
    df["season"],
    errors="coerce"
)


# ============================================================
# 8. SELECCIONAR 2024 Y 2025
# ============================================================

nfl = df[
    df["season"].isin(
        SEASONS
    )
].copy()


# ============================================================
# 9. INFORMACIÓN DE 2024 Y 2025
# ============================================================

st.header("6. Temporadas seleccionadas")

col1, col2 = st.columns(2)

with col1:

    rows_2024 = len(
        nfl[
            nfl["season"] == 2024
        ]
    )

    games_2024 = nfl[
        nfl["season"] == 2024
    ]["game_id"].nunique()

    st.metric(
        "Registros 2024",
        f"{rows_2024:,}"
    )

    st.metric(
        "Partidos 2024",
        f"{games_2024:,}"
    )


with col2:

    rows_2025 = len(
        nfl[
            nfl["season"] == 2025
        ]
    )

    games_2025 = nfl[
        nfl["season"] == 2025
    ]["game_id"].nunique()

    st.metric(
        "Registros 2025",
        f"{rows_2025:,}"
    )

    st.metric(
        "Partidos 2025",
        f"{games_2025:,}"
    )


# ============================================================
# 10. GAME TYPES
# ============================================================

st.header("7. Tipos de partidos")

game_type_table = (
    nfl
    .groupby(
        [
            "season",
            "game_type"
        ]
    )["game_id"]
    .nunique()
    .reset_index()
)

game_type_table.columns = [
    "Temporada",
    "Tipo",
    "Partidos"
]

st.dataframe(
    game_type_table,
    use_container_width=True,
    hide_index=True
)


# ============================================================
# 11. REGULAR SEASON
# ============================================================

regular = nfl[
    nfl["game_type"]
    .astype(str)
    .str.upper()
    == "REG"
].copy()


# ============================================================
# 12. REGULAR SEASON POR TEMPORADA
# ============================================================

st.header(
    "8. Regular Season únicamente"
)

regular_games = (
    regular
    .groupby("season")["game_id"]
    .nunique()
    .reset_index()
)

regular_games.columns = [
    "Temporada",
    "Partidos Regular Season"
]

st.dataframe(
    regular_games,
    use_container_width=True,
    hide_index=True
)


# ============================================================
# 13. VALIDACIÓN DE REGULAR SEASON
# ============================================================

st.header(
    "9. Validación Regular Season"
)

for season in SEASONS:

    count = regular[
        regular["season"] == season
    ]["game_id"].nunique()

    if count == 272:

        st.success(
            f"✅ {season}: {count} partidos de Regular Season."
        )

    else:

        st.warning(
            f"⚠️ {season}: {count} partidos de Regular Season."
        )


# ============================================================
# 14. EQUIPOS
# ============================================================

st.header("10. Equipos")

home_teams = set(
    regular["home_team"]
    .dropna()
    .unique()
)

away_teams = set(
    regular["away_team"]
    .dropna()
    .unique()
)

all_teams = sorted(
    home_teams | away_teams
)

st.metric(
    "Equipos encontrados",
    len(all_teams)
)

teams_table = pd.DataFrame({
    "Equipo": all_teams
})

st.dataframe(
    teams_table,
    use_container_width=True,
    hide_index=True
)


# ============================================================
# 15. DUPLICADOS
# ============================================================

st.header("11. Validación de duplicados")

duplicate_mask = regular.duplicated(
    subset=["game_id"],
    keep=False
)

duplicate_rows = int(
    duplicate_mask.sum()
)

duplicate_games = regular[
    duplicate_mask
]["game_id"].nunique()

col1, col2 = st.columns(2)

with col1:

    st.metric(
        "Registros duplicados",
        duplicate_rows
    )

with col2:

    st.metric(
        "GAME_ID duplicados",
        duplicate_games
    )

if duplicate_games == 0:

    st.success(
        "✅ No existen GAME_ID duplicados."
    )

else:

    st.warning(
        "⚠️ Existen GAME_ID duplicados."
    )


# ============================================================
# 16. EQUIPOS HOME/AWAY
# ============================================================

st.header(
    "12. Validación Home / Away"
)

missing_home = int(
    regular["home_team"]
    .isna()
    .sum()
)

missing_away = int(
    regular["away_team"]
    .isna()
    .sum()
)

col1, col2 = st.columns(2)

with col1:

    st.metric(
        "Home Team faltante",
        missing_home
    )

with col2:

    st.metric(
        "Away Team faltante",
        missing_away
    )

if (
    missing_home == 0
    and missing_away == 0
):

    st.success(
        "✅ Todos los partidos tienen Home y Away."
    )

else:

    st.warning(
        "⚠️ Hay equipos faltantes."
    )


# ============================================================
# 17. SCORES
# ============================================================

st.header("13. Validación de resultados")

regular["home_score"] = pd.to_numeric(
    regular["home_score"],
    errors="coerce"
)

regular["away_score"] = pd.to_numeric(
    regular["away_score"],
    errors="coerce"
)

missing_home_score = int(
    regular["home_score"]
    .isna()
    .sum()
)

missing_away_score = int(
    regular["away_score"]
    .isna()
    .sum()
)

col1, col2 = st.columns(2)

with col1:

    st.metric(
        "Home Score faltante",
        missing_home_score
    )

with col2:

    st.metric(
        "Away Score faltante",
        missing_away_score
    )


# ============================================================
# 18. RESULTADO
# ============================================================

regular["home_win"] = (
    regular["home_score"]
    >
    regular["away_score"]
)

regular["away_win"] = (
    regular["away_score"]
    >
    regular["home_score"]
)

regular["tie"] = (
    regular["home_score"]
    ==
    regular["away_score"]
)

result_table = pd.DataFrame({

    "Resultado": [
        "Victoria Home",
        "Victoria Away",
        "Empate"
    ],

    "Partidos": [
        int(
            regular["home_win"].sum()
        ),

        int(
            regular["away_win"].sum()
        ),

        int(
            regular["tie"].sum()
        )
    ]
})

st.dataframe(
    result_table,
    use_container_width=True,
    hide_index=True
)


# ============================================================
# 19. FECHAS
# ============================================================

st.header("14. Fechas")

regular["gameday"] = pd.to_datetime(
    regular["gameday"],
    errors="coerce"
)

min_date = regular[
    "gameday"
].min()

max_date = regular[
    "gameday"
].max()

invalid_dates = int(
    regular["gameday"]
    .isna()
    .sum()
)

col1, col2, col3 = st.columns(3)

with col1:

    st.metric(
        "Fecha inicial",
        str(
            min_date.date()
        )
    )

with col2:

    st.metric(
        "Fecha final",
        str(
            max_date.date()
        )
    )

with col3:

    st.metric(
        "Fechas inválidas",
        invalid_dates
    )


# ============================================================
# 20. SEMANAS
# ============================================================

st.header("15. Semanas")

weeks_table = (
    regular
    .groupby("season")
    .agg(
        Primera_Semana=("week", "min"),
        Ultima_Semana=("week", "max"),
        Semanas=("week", "nunique")
    )
    .reset_index()
)

st.dataframe(
    weeks_table,
    use_container_width=True,
    hide_index=True
)


# ============================================================
# 21. VALORES FALTANTES
# ============================================================

st.header("16. Valores faltantes")

missing_table = (
    regular
    .isna()
    .sum()
    .reset_index()
)

missing_table.columns = [
    "Columna",
    "Valores faltantes"
]

missing_table = missing_table[
    missing_table["Valores faltantes"] > 0
].sort_values(
    "Valores faltantes",
    ascending=False
)

if len(missing_table) == 0:

    st.success(
        "✅ No existen valores faltantes."
    )

else:

    st.dataframe(
        missing_table,
        use_container_width=True,
        hide_index=True
    )


# ============================================================
# 22. VISTA DE PARTIDOS
# ============================================================

st.header("17. Vista de partidos")

preview_columns = [
    "game_id",
    "season",
    "week",
    "gameday",
    "away_team",
    "away_score",
    "home_team",
    "home_score",
    "location",
    "result",
    "total"
]

preview_columns = [
    c
    for c in preview_columns
    if c in regular.columns
]

st.dataframe(
    regular[
        preview_columns
    ]
    .sort_values(
        [
            "season",
            "gameday"
        ]
    )
    .head(30),
    use_container_width=True,
    hide_index=True
)


# ============================================================
# 23. DATASET FINAL
# ============================================================

st.header(
    "18. Construyendo NFL_SIMPLE_V1_DATA"
)

# Orden cronológico
regular = (
    regular
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
# GUARDAR DATASET
# ============================================================

data_path = (
    OUTPUT_DIR
    / "NFL_SIMPLE_V1_DATA.csv"
)

regular.to_csv(
    data_path,
    index=False
)


# ============================================================
# 24. AUDITORÍA FINAL
# ============================================================

audit = pd.DataFrame({

    "Metric": [

        "Temporadas",

        "Registros",

        "Partidos únicos",

        "Regular Season 2024",

        "Regular Season 2025",

        "Equipos",

        "GAME_ID duplicados",

        "Home faltantes",

        "Away faltantes",

        "Home Score faltantes",

        "Away Score faltantes",

        "Fechas inválidas"
    ],

    "Value": [

        "2024, 2025",

        len(regular),

        regular["game_id"].nunique(),

        regular[
            regular["season"] == 2024
        ]["game_id"].nunique(),

        regular[
            regular["season"] == 2025
        ]["game_id"].nunique(),

        len(all_teams),

        duplicate_games,

        missing_home,

        missing_away,

        missing_home_score,

        missing_away_score,

        invalid_dates
    ]
})


# ============================================================
# GUARDAR AUDITORÍA
# ============================================================

audit_path = (
    OUTPUT_DIR
    / "NFL_SIMPLE_V1_AUDIT.csv"
)

audit.to_csv(
    audit_path,
    index=False
)


# ============================================================
# RESULTADO FINAL
# ============================================================

st.header(
    "🏁 NFL_SIMPLE_V1 - AUDITORÍA FINAL"
)

st.dataframe(
    audit,
    use_container_width=True,
    hide_index=True
)

st.success(
    "✅ NFL_SIMPLE_V1 DATASET CREADO"
)

st.write(
    "Archivo principal:"
)

st.code(
    str(data_path)
)

st.write(
    "Archivo de auditoría:"
)

st.code(
    str(audit_path)
)

st.info(
    """
    SIGUIENTE ETAPA:

    NFL_SIMPLE_V1_PREGAME

    Vamos a calcular las estadísticas de cada equipo
    ANTES de cada partido.

    NO se utilizarán:
    - Moneylines
    - Spreads
    - Odds
    - Sportsbooks

    El resultado del propio partido NO podrá contaminar
    las estadísticas utilizadas para predecirlo.
    """
)
