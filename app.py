import streamlit as st
import pandas as pd
import requests
from io import BytesIO
from pathlib import Path

# ============================================================
# NBA_V1_DATA_AUDIT
# ============================================================

st.set_page_config(
    page_title="NBA_V1 DATA AUDIT",
    layout="wide"
)

st.title("🏀 NBA_V1 - DATA AUDIT")

BASE_URL = "https://raw.githubusercontent.com/llimllib/nba_data/main/data/"

SEASONS = {
    2025: "2024-25",
    2026: "2025-26"
}

# ============================================================
# DESCARGAR DATOS
# ============================================================

def download_season(season_year, season_name):

    url = f"{BASE_URL}gamelog_{season_year}.parquet"

    st.write(f"Descargando **{season_name}**...")

    response = requests.get(
        url,
        timeout=60
    )

    response.raise_for_status()

    df = pd.read_parquet(
        BytesIO(response.content)
    )

    df["season"] = season_name

    return df


# ============================================================
# CARGAR LAS DOS TEMPORADAS
# ============================================================

try:

    df_2025 = download_season(
        2025,
        "2024-25"
    )

    df_2026 = download_season(
        2026,
        "2025-26"
    )

    raw = pd.concat(
        [
            df_2025,
            df_2026
        ],
        ignore_index=True
    )

    st.success(
        "Las dos temporadas fueron descargadas correctamente."
    )

except Exception as e:

    st.error("Error descargando los datos.")
    st.exception(e)
    st.stop()


# ============================================================
# INFORMACION GENERAL
# ============================================================

st.header("1. Información general")

col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        "Registros totales",
        f"{len(raw):,}"
    )

with col2:
    st.metric(
        "Partidos únicos",
        f"{raw['game_id'].nunique():,}"
    )

with col3:
    st.metric(
        "Equipos",
        f"{raw['team_name'].nunique():,}"
    )


# ============================================================
# COLUMNAS
# ============================================================

st.header("2. Columnas disponibles")

columns_df = pd.DataFrame({
    "Columna": raw.columns
})

st.dataframe(
    columns_df,
    use_container_width=True
)


# ============================================================
# TIPOS DE DATOS
# ============================================================

st.header("3. Tipos de datos")

dtype_df = pd.DataFrame({
    "Columna": raw.columns,
    "Tipo": [
        str(raw[c].dtype)
        for c in raw.columns
    ]
})

st.dataframe(
    dtype_df,
    use_container_width=True
)


# ============================================================
# FECHAS
# ============================================================

raw["game_date"] = pd.to_datetime(
    raw["game_date"],
    errors="coerce"
)

st.header("4. Fechas")

c1, c2, c3 = st.columns(3)

with c1:
    st.metric(
        "Fecha inicial",
        str(raw["game_date"].min().date())
    )

with c2:
    st.metric(
        "Fecha final",
        str(raw["game_date"].max().date())
    )

with c3:
    st.metric(
        "Fechas inválidas",
        int(raw["game_date"].isna().sum())
    )


# ============================================================
# PARTIDOS POR TEMPORADA
# ============================================================

st.header("5. Partidos por temporada")

games_by_season = (
    raw.groupby("season")["game_id"]
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
# REGISTROS POR TEMPORADA
# ============================================================

records_by_season = (
    raw.groupby("season")
    .size()
    .reset_index(
        name="Registros"
    )
)

records_by_season.columns = [
    "Temporada",
    "Registros"
]

st.dataframe(
    records_by_season,
    use_container_width=True
)


# ============================================================
# EQUIPOS POR TEMPORADA
# ============================================================

st.header("6. Equipos por temporada")

teams_by_season = (
    raw.groupby("season")["team_name"]
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
# GAME_ID DUPLICADOS
# ============================================================

st.header("7. Validación de partidos")

teams_per_game = (
    raw.groupby("game_id")["team_id"]
    .nunique()
)

bad_games = teams_per_game[
    teams_per_game != 2
]

c1, c2 = st.columns(2)

with c1:
    st.metric(
        "Partidos con 2 equipos",
        int(
            (teams_per_game == 2).sum()
        )
    )

with c2:
    st.metric(
        "Partidos problemáticos",
        len(bad_games)
    )


# ============================================================
# DUPLICADOS GAME_ID + TEAM_ID
# ============================================================

duplicate_rows = raw.duplicated(
    subset=[
        "game_id",
        "team_id"
    ],
    keep=False
)

st.metric(
    "Registros duplicados GAME_ID + TEAM_ID",
    int(duplicate_rows.sum())
)


# ============================================================
# LOCAL / VISITANTE
# ============================================================

st.header("8. Local vs visitante")

raw["is_home"] = (
    raw["matchup"]
    .astype(str)
    .str.contains(
        " vs. ",
        regex=False,
        na=False
    )
)

raw["is_away"] = (
    raw["matchup"]
    .astype(str)
    .str.contains(
        " @ ",
        regex=False,
        na=False
    )
)

location_unknown = raw[
    ~(raw["is_home"] | raw["is_away"])
]

c1, c2, c3 = st.columns(3)

with c1:
    st.metric(
        "Local",
        int(raw["is_home"].sum())
    )

with c2:
    st.metric(
        "Visitante",
        int(raw["is_away"].sum())
    )

with c3:
    st.metric(
        "Sin identificar",
        len(location_unknown)
    )


# ============================================================
# RESULTADOS
# ============================================================

st.header("9. Resultados")

result_counts = (
    raw["wl"]
    .value_counts(dropna=False)
    .reset_index()
)

result_counts.columns = [
    "Resultado",
    "Registros"
]

st.dataframe(
    result_counts,
    use_container_width=True
)


# ============================================================
# VALORES FALTANTES
# ============================================================

st.header("10. Valores faltantes")

missing = (
    raw.isna()
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
# ESTADISTICAS IMPORTANTES
# ============================================================

st.header("11. Estadísticas disponibles")

important_columns = [
    "min",
    "fgm",
    "fga",
    "fg_pct",
    "fg3m",
    "fg3a",
    "fg3_pct",
    "ftm",
    "fta",
    "ft_pct",
    "oreb",
    "dreb",
    "reb",
    "ast",
    "tov",
    "stl",
    "blk",
    "pf",
    "pfd",
    "pts",
    "plus_minus"
]

available = [
    c
    for c in important_columns
    if c in raw.columns
]

stats_table = pd.DataFrame({
    "Variable": available
})

st.dataframe(
    stats_table,
    use_container_width=True
)


# ============================================================
# RESUMEN ESTADISTICO
# ============================================================

st.header("12. Resumen estadístico")

if len(available) > 0:

    summary = (
        raw[available]
        .describe()
        .T
        .reset_index()
    )

    summary = summary.rename(
        columns={
            "index": "Variable"
        }
    )

    st.dataframe(
        summary,
        use_container_width=True
    )


# ============================================================
# SEPARAR REGULAR SEASON
# ============================================================

st.header("13. Identificación de tipo de partido")

raw["game_id_str"] = (
    raw["game_id"]
    .astype(str)
)

raw["game_type"] = (
    raw["game_id_str"]
    .str[:3]
)

game_types = (
    raw["game_type"]
    .value_counts()
    .reset_index()
)

game_types.columns = [
    "GAME_TYPE",
    "Registros"
]

st.dataframe(
    game_types,
    use_container_width=True
)


# ============================================================
# REGULAR SEASON
# ============================================================

regular = raw[
    raw["game_type"] == "002"
].copy()

st.header("14. Regular Season")

c1, c2 = st.columns(2)

with c1:
    st.metric(
        "Registros",
        f"{len(regular):,}"
    )

with c2:
    st.metric(
        "Partidos",
        f"{regular['game_id'].nunique():,}"
    )


# ============================================================
# CREAR DATASET BASE
# ============================================================

base_columns = [
    "season",
    "season_year",
    "team_id",
    "team_abbreviation",
    "team_name",
    "game_id",
    "game_date",
    "matchup",
    "wl",
    "is_home"
]

base_columns += [
    c
    for c in available
    if c not in base_columns
]

base_columns = [
    c
    for c in base_columns
    if c in regular.columns
]

nba_v1_data = regular[
    base_columns
].copy()

nba_v1_data = (
    nba_v1_data
    .sort_values(
        [
            "game_date",
            "game_id",
            "team_id"
        ]
    )
    .reset_index(drop=True)
)


# ============================================================
# GUARDAR ARCHIVOS
# ============================================================

output_dir = Path("NBA_V1")

output_dir.mkdir(
    exist_ok=True
)

csv_path = (
    output_dir /
    "NBA_V1_DATA.csv"
)

audit_path = (
    output_dir /
    "NBA_V1_DATA_AUDIT.csv"
)

nba_v1_data.to_csv(
    csv_path,
    index=False
)


# ============================================================
# AUDITORIA RESUMIDA
# ============================================================

audit = pd.DataFrame({
    "Metric": [
        "Total records",
        "Unique games",
        "Unique teams",
        "Problem games",
        "Duplicate records",
        "Unknown location",
        "Missing game dates",
        "Regular season records",
        "Regular season games"
    ],

    "Value": [
        len(raw),
        raw["game_id"].nunique(),
        raw["team_name"].nunique(),
        len(bad_games),
        int(duplicate_rows.sum()),
        len(location_unknown),
        int(raw["game_date"].isna().sum()),
        len(regular),
        regular["game_id"].nunique()
    ]
})

audit.to_csv(
    audit_path,
    index=False
)


# ============================================================
# RESULTADO FINAL
# ============================================================

st.header("🏁 NBA_V1 DATA AUDIT FINAL")

st.success(
    "AUDITORÍA COMPLETADA"
)

st.dataframe(
    audit,
    use_container_width=True
)

st.write(
    "Archivo creado:",
    str(csv_path)
)

st.write(
    "Auditoría creada:",
    str(audit_path)
)

st.info(
    "IMPORTANTE: todavía NO hemos creado el modelo. "
    "Primero vamos a revisar estos resultados."
)
