import streamlit as st
import pandas as pd
import requests
from io import StringIO
from pathlib import Path

# ============================================================
# NFL_SIMPLE_V1 - DATA AUDIT
# PROYECTO INDEPENDIENTE DEL NFL V66/V75/V78
# ============================================================

st.set_page_config(
    page_title="NFL_SIMPLE_V1 DATA AUDIT",
    layout="wide"
)

st.title("🏈 NFL_SIMPLE_V1 - DATA AUDIT")

# ============================================================
# CONFIGURACIÓN
# ============================================================

URL = (
    "https://raw.githubusercontent.com/"
    "nflverse/nfldata/master/data/games.csv"
)

SEASONS = [2024, 2025]

OUTPUT_DIR = Path("NFL_SIMPLE_V1")
OUTPUT_DIR.mkdir(exist_ok=True)


# ============================================================
# DESCARGAR DATASET
# ============================================================

st.header("1. Descargando datos NFL")

try:

    response = requests.get(
        URL,
        timeout=120
    )

    response.raise_for_status()

    st.success(
        f"Dataset descargado correctamente."
    )

except Exception as e:

    st.error(
        "No se pudo descargar el dataset."
    )

    st.exception(e)

    st.stop()


# ============================================================
# LEER CSV
# ============================================================

try:

    games = pd.read_csv(
        StringIO(response.text)
    )

except Exception as e:

    st.error(
        "No se pudo leer el CSV."
    )

    st.exception(e)

    st.stop()


# ============================================================
# NORMALIZAR COLUMNAS
# ============================================================

games.columns = [
    str(c).strip().lower()
    for c in games.columns
]


# ============================================================
# INFORMACIÓN GENERAL
# ============================================================

st.header("2. Información general")

c1, c2, c3 = st.columns(3)

with c1:
    st.metric(
        "Registros totales",
        f"{len(games):,}"
    )

with c2:
    st.metric(
        "Columnas",
        len(games.columns)
    )

with c3:
    st.metric(
        "Temporadas",
        games["season"].nunique()
        if "season" in games.columns
        else "N/A"
    )


# ============================================================
# COLUMNAS
# ============================================================

st.header("3. Columnas disponibles")

columns_df = pd.DataFrame({
    "Columna": games.columns
})

st.dataframe(
    columns_df,
    use_container_width=True
)


# ============================================================
# TIPOS DE DATOS
# ============================================================

st.header("4. Tipos de datos")

dtype_df = pd.DataFrame({
    "Columna": games.columns,
    "Tipo": [
        str(games[c].dtype)
        for c in games.columns
    ]
})

st.dataframe(
    dtype_df,
    use_container_width=True
)


# ============================================================
# COMPROBAR COLUMNAS ESENCIALES
# ============================================================

required_columns = [
    "season",
    "game_id",
    "week",
    "home_team",
    "away_team"
]

missing_required = [
    c
    for c in required_columns
    if c not in games.columns
]

st.header("5. Columnas esenciales")

if len(missing_required) == 0:

    st.success(
        "Todas las columnas esenciales están presentes."
    )

else:

    st.error(
        f"Faltan columnas: {missing_required}"
    )

    st.stop()


# ============================================================
# FILTRAR 2024 Y 2025
# ============================================================

games["season"] = pd.to_numeric(
    games["season"],
    errors="coerce"
)

nfl = games[
    games["season"].isin(SEASONS)
].copy()


# ============================================================
# TIPO DE TEMPORADA
# ============================================================

st.header("6. Tipo de temporada")

if "game_type" in nfl.columns:

    game_types = (
        nfl["game_type"]
        .value_counts(dropna=False)
        .reset_index()
    )

    game_types.columns = [
        "game_type",
        "registros"
    ]

    st.dataframe(
        game_types,
        use_container_width=True
    )

else:

    st.warning(
        "No existe game_type en la fuente."
    )


# ============================================================
# REGULAR SEASON
# ============================================================

if "game_type" in nfl.columns:

    regular = nfl[
        nfl["game_type"].astype(str).str.lower()
        == "reg"
    ].copy()

else:

    regular = nfl.copy()


# ============================================================
# INFORMACIÓN DE REGULAR SEASON
# ============================================================

st.header("7. Regular Season")

c1, c2, c3 = st.columns(3)

with c1:
    st.metric(
        "Registros",
        f"{len(regular):,}"
    )

with c2:
    st.metric(
        "Partidos únicos",
        f"{regular['game_id'].nunique():,}"
    )

with c3:
    st.metric(
        "Equipos locales",
        regular["home_team"].nunique()
    )


# ============================================================
# PARTIDOS POR TEMPORADA
# ============================================================

st.header("8. Partidos por temporada")

games_by_season = (
    regular
    .groupby("season")["game_id"]
    .nunique()
    .reset_index()
)

games_by_season.columns = [
    "Temporada",
    "Partidos"
]

st.dataframe(
    games_by_season,
    use_container_width=True
)


# ============================================================
# SEMANAS
# ============================================================

st.header("9. Semanas disponibles")

weeks = (
    regular
    .groupby("season")["week"]
    .agg(
        Primera="min",
        Ultima="max",
        Semanas="nunique"
    )
    .reset_index()
)

st.dataframe(
    weeks,
    use_container_width=True
)


# ============================================================
# EQUIPOS
# ============================================================

st.header("10. Equipos")

teams_by_season = (
    pd.concat(
        [
            regular[
                ["season", "home_team"]
            ].rename(
                columns={
                    "home_team": "team"
                }
            ),

            regular[
                ["season", "away_team"]
            ].rename(
                columns={
                    "away_team": "team"
                }
            )
        ]
    )
    .drop_duplicates()
    .groupby("season")["team"]
    .nunique()
    .reset_index()
)

teams_by_season.columns = [
    "Temporada",
    "Equipos"
]

st.dataframe(
    teams_by_season,
    use_container_width=True
)


# ============================================================
# DUPLICADOS
# ============================================================

st.header("11. Duplicados")

duplicate_games = regular.duplicated(
    subset=["game_id"],
    keep=False
)

duplicate_count = int(
    duplicate_games.sum()
)

c1, c2 = st.columns(2)

with c1:
    st.metric(
        "Partidos únicos",
        regular["game_id"].nunique()
    )

with c2:
    st.metric(
        "Registros duplicados GAME_ID",
        duplicate_count
    )


# ============================================================
# LOCAL / VISITANTE
# ============================================================

st.header("12. Local / Visitante")

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

c1, c2 = st.columns(2)

with c1:
    st.metric(
        "Home Team faltante",
        missing_home
    )

with c2:
    st.metric(
        "Away Team faltante",
        missing_away
    )


# ============================================================
# RESULTADOS
# ============================================================

st.header("13. Resultados")

score_columns = [
    "home_score",
    "away_score"
]

available_scores = [
    c
    for c in score_columns
    if c in regular.columns
]

if len(available_scores) == 2:

    regular["home_score"] = pd.to_numeric(
        regular["home_score"],
        errors="coerce"
    )

    regular["away_score"] = pd.to_numeric(
        regular["away_score"],
        errors="coerce"
    )

    regular["home_win"] = (
        regular["home_score"]
        > regular["away_score"]
    )

    regular["away_win"] = (
        regular["away_score"]
        > regular["home_score"]
    )

    regular["tie"] = (
        regular["home_score"]
        == regular["away_score"]
    )

    results = pd.DataFrame({
        "Resultado": [
            "Victoria local",
            "Victoria visitante",
            "Empate"
        ],
        "Partidos": [
            int(regular["home_win"].sum()),
            int(regular["away_win"].sum()),
            int(regular["tie"].sum())
        ]
    })

    st.dataframe(
        results,
        use_container_width=True
    )

else:

    st.warning(
        "No encontramos home_score y away_score."
    )


# ============================================================
# FECHAS
# ============================================================

st.header("14. Fechas")

date_column = None

for candidate in [
    "gameday",
    "game_date",
    "date"
]:

    if candidate in regular.columns:
        date_column = candidate
        break

if date_column:

    regular[date_column] = pd.to_datetime(
        regular[date_column],
        errors="coerce"
    )

    c1, c2, c3 = st.columns(3)

    with c1:
        st.metric(
            "Fecha inicial",
            str(
                regular[date_column]
                .min()
                .date()
            )
        )

    with c2:
        st.metric(
            "Fecha final",
            str(
                regular[date_column]
                .max()
                .date()
            )
        )

    with c3:
        st.metric(
            "Fechas inválidas",
            int(
                regular[date_column]
                .isna()
                .sum()
            )
        )

else:

    st.warning(
        "No encontramos una columna de fecha."
    )


# ============================================================
# VALORES FALTANTES
# ============================================================

st.header("15. Valores faltantes")

missing = (
    regular
    .isna()
    .sum()
    .reset_index()
)

missing.columns = [
    "Columna",
    "Valores faltantes"
]

missing = missing[
    missing["Valores faltantes"] > 0
]

if len(missing) == 0:

    st.success(
        "No encontramos valores faltantes."
    )

else:

    st.dataframe(
        missing,
        use_container_width=True
    )


# ============================================================
# PREVIEW
# ============================================================

st.header("16. Vista de partidos")

preview_columns = [
    "season",
    "week",
    "game_id",
    "home_team",
    "away_team"
]

if "home_score" in regular.columns:
    preview_columns.append(
        "home_score"
    )

if "away_score" in regular.columns:
    preview_columns.append(
        "away_score"
    )

preview_columns = [
    c
    for c in preview_columns
    if c in regular.columns
]

st.dataframe(
    regular[
        preview_columns
    ].head(25),
    use_container_width=True
)


# ============================================================
# GUARDAR DATASET
# ============================================================

output_dir = Path(
    "NFL_SIMPLE_V1"
)

output_dir.mkdir(
    exist_ok=True
)

data_path = (
    output_dir /
    "NFL_SIMPLE_V1_SCHEDULE.csv"
)

audit_path = (
    output_dir /
    "NFL_SIMPLE_V1_DATA_AUDIT.csv"
)

regular.to_csv(
    data_path,
    index=False
)


# ============================================================
# AUDITORÍA RESUMIDA
# ============================================================

audit = pd.DataFrame({

    "Metric": [
        "Temporadas analizadas",
        "Registros",
        "Partidos únicos",
        "Equipos",
        "Partidos duplicados",
        "Home faltantes",
        "Away faltantes",
        "Regular season"
    ],

    "Value": [
        "2024, 2025",
        len(regular),
        regular["game_id"].nunique(),
        len(
            set(
                regular["home_team"]
            )
            |
            set(
                regular["away_team"]
            )
        ),
        duplicate_count,
        missing_home,
        missing_away,
        True
    ]
})

audit.to_csv(
    audit_path,
    index=False
)


# ============================================================
# RESULTADO FINAL
# ============================================================

st.header(
    "🏁 NFL_SIMPLE_V1 DATA AUDIT FINAL"
)

st.success(
    "AUDITORÍA TERMINADA"
)

st.dataframe(
    audit,
    use_container_width=True
)

st.write(
    "Dataset creado:"
)

st.code(
    str(data_path)
)

st.write(
    "Auditoría creada:"
)

st.code(
    str(audit_path)
)

st.info(
    "IMPORTANTE: todavía NO estamos utilizando "
    "moneylines, spreads, odds ni probabilidades de sportsbooks."
)

st.info(
    "El siguiente paso será construir las estadísticas "
    "PRE-PARTIDO sin leakage."
)
