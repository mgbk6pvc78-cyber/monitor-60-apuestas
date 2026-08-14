# ============================================================
# NBA_V1_DATA_AUDIT
# Proyecto independiente del NFL
# ============================================================

import pandas as pd
import numpy as np
import requests
from io import BytesIO
from pathlib import Path

# ------------------------------------------------------------
# CONFIGURACIÓN
# ------------------------------------------------------------

BASE_URL = "https://raw.githubusercontent.com/llimllib/nba_data/main/data/"

SEASONS = {
    2025: "2024-25",
    2026: "2025-26"
}

OUTPUT_DIR = Path("NBA_V1")
OUTPUT_DIR.mkdir(exist_ok=True)

# ------------------------------------------------------------
# DESCARGAR PARQUET
# ------------------------------------------------------------

def download_parquet(season_end_year):
    url = f"{BASE_URL}gamelog_{season_end_year}.parquet"

    print(f"\nDescargando temporada {SEASONS[season_end_year]}...")
    print(url)

    response = requests.get(url, timeout=60)
    response.raise_for_status()

    df = pd.read_parquet(BytesIO(response.content))

    print(f"OK: {len(df):,} registros de equipo")

    return df


# ------------------------------------------------------------
# CARGAR TEMPORADAS
# ------------------------------------------------------------

dfs = []

for season_year in SEASONS:
    df = download_parquet(season_year)

    df["SEASON"] = SEASONS[season_year]
    df["SEASON_END_YEAR"] = season_year

    dfs.append(df)

raw = pd.concat(dfs, ignore_index=True)

print("\n========================================")
print("NBA_V1 RAW CARGADO")
print("========================================")
print(f"Registros totales: {len(raw):,}")
print(f"Columnas: {len(raw.columns)}")


# ------------------------------------------------------------
# MOSTRAR COLUMNAS
# ------------------------------------------------------------

print("\n========================================")
print("COLUMNAS DISPONIBLES")
print("========================================")

for i, col in enumerate(raw.columns, 1):
    print(f"{i:02d}. {col}")


# ------------------------------------------------------------
# TIPOS DE DATOS
# ------------------------------------------------------------

print("\n========================================")
print("TIPOS DE DATOS")
print("========================================")

print(raw.dtypes)


# ------------------------------------------------------------
# GAME ID
# ------------------------------------------------------------

raw["GAME_ID"] = raw["GAME_ID"].astype(str)

raw["GAME_TYPE"] = raw["GAME_ID"].str[:3]

print("\n========================================")
print("TIPOS DE PARTIDO")
print("========================================")

print(raw["GAME_TYPE"].value_counts())


# ------------------------------------------------------------
# SOLO REGULAR SEASON
# ------------------------------------------------------------

regular = raw[raw["GAME_TYPE"] == "002"].copy()

print("\n========================================")
print("REGULAR SEASON")
print("========================================")

print(f"Registros de equipo: {len(regular):,}")
print(f"Partidos únicos: {regular['GAME_ID'].nunique():,}")


# ------------------------------------------------------------
# PARTIDOS POR TEMPORADA
# ------------------------------------------------------------

print("\n========================================")
print("PARTIDOS POR TEMPORADA")
print("========================================")

games_by_season = (
    regular.groupby("SEASON")["GAME_ID"]
    .nunique()
    .sort_index()
)

print(games_by_season)


# ------------------------------------------------------------
# EQUIPOS
# ------------------------------------------------------------

print("\n========================================")
print("EQUIPOS")
print("========================================")

print(
    regular.groupby("SEASON")["TEAM_NAME"]
    .nunique()
)


# ------------------------------------------------------------
# DUPLICADOS
# ------------------------------------------------------------

print("\n========================================")
print("DUPLICADOS")
print("========================================")

duplicate_rows = regular.duplicated(
    subset=["GAME_ID", "TEAM_ID"],
    keep=False
)

print(
    f"Registros duplicados GAME_ID + TEAM_ID: "
    f"{duplicate_rows.sum():,}"
)


# ------------------------------------------------------------
# CADA PARTIDO DEBE TENER 2 EQUIPOS
# ------------------------------------------------------------

teams_per_game = (
    regular.groupby("GAME_ID")["TEAM_ID"]
    .nunique()
)

bad_games = teams_per_game[teams_per_game != 2]

print("\n========================================")
print("VALIDACIÓN DE PARTIDOS")
print("========================================")

print(
    f"Partidos con exactamente 2 equipos: "
    f"{(teams_per_game == 2).sum():,}"
)

print(
    f"Partidos problemáticos: "
    f"{len(bad_games):,}"
)

if len(bad_games) > 0:
    print(bad_games.head(20))


# ------------------------------------------------------------
# VALORES FALTANTES
# ------------------------------------------------------------

print("\n========================================")
print("VALORES FALTANTES")
print("========================================")

missing = (
    regular.isna()
    .sum()
    .sort_values(ascending=False)
)

print(missing[missing > 0])


# ------------------------------------------------------------
# FECHAS
# ------------------------------------------------------------

regular["GAME_DATE"] = pd.to_datetime(
    regular["GAME_DATE"],
    errors="coerce"
)

print("\n========================================")
print("RANGO DE FECHAS")
print("========================================")

print("Inicio:", regular["GAME_DATE"].min())
print("Fin:", regular["GAME_DATE"].max())


# ------------------------------------------------------------
# IDENTIFICAR LOCAL / VISITANTE
# ------------------------------------------------------------

# En MATCHUP normalmente:
# "TEAM vs. OPPONENT" = local
# "TEAM @ OPPONENT"  = visitante

regular["IS_HOME"] = regular["MATCHUP"].str.contains(
    " vs. ",
    regex=False,
    na=False
)

regular["IS_AWAY"] = regular["MATCHUP"].str.contains(
    " @ ",
    regex=False,
    na=False
)

print("\n========================================")
print("LOCAL / VISITANTE")
print("========================================")

print("Local:", regular["IS_HOME"].sum())
print("Visitante:", regular["IS_AWAY"].sum())

unknown_location = regular[
    ~(regular["IS_HOME"] | regular["IS_AWAY"])
]

print(
    "Sin identificar:",
    len(unknown_location)
)

if len(unknown_location) > 0:
    print(
        unknown_location[
            ["GAME_ID", "TEAM_NAME", "MATCHUP"]
        ].head(20)
    )


# ------------------------------------------------------------
# VALIDAR RESULTADO
# ------------------------------------------------------------

print("\n========================================")
print("RESULTADOS")
print("========================================")

print(regular["WL"].value_counts(dropna=False))


# ------------------------------------------------------------
# ESTADÍSTICAS BÁSICAS
# ------------------------------------------------------------

numeric_candidates = [
    "PTS",
    "FG_PCT",
    "FG3_PCT",
    "FT_PCT",
    "OREB",
    "DREB",
    "REB",
    "AST",
    "STL",
    "BLK",
    "TOV",
    "PF",
    "PLUS_MINUS"
]

available_numeric = [
    c for c in numeric_candidates
    if c in regular.columns
]

print("\n========================================")
print("ESTADÍSTICAS DISPONIBLES")
print("========================================")

print(available_numeric)

print("\nResumen:")
print(
    regular[available_numeric]
    .describe()
    .T
)


# ------------------------------------------------------------
# CREAR DATASET DE PARTIDOS
# UNA FILA POR EQUIPO TODAVÍA
# ------------------------------------------------------------

team_game_data = regular[
    [
        "SEASON",
        "SEASON_END_YEAR",
        "GAME_ID",
        "GAME_DATE",
        "TEAM_ID",
        "TEAM_NAME",
        "MATCHUP",
        "WL",
        "IS_HOME"
    ] + available_numeric
].copy()

team_game_data = team_game_data.sort_values(
    ["GAME_DATE", "GAME_ID", "TEAM_ID"]
).reset_index(drop=True)


# ------------------------------------------------------------
# GUARDAR DATASET LIMPIO
# ------------------------------------------------------------

output_file = OUTPUT_DIR / "NBA_V1_DATA.csv"

team_game_data.to_csv(
    output_file,
    index=False
)

print("\n========================================")
print("NBA_V1_DATA CREADO")
print("========================================")

print(output_file)
print(f"Registros: {len(team_game_data):,}")


# ------------------------------------------------------------
# RESUMEN FINAL
# ------------------------------------------------------------

print("\n========================================")
print("NBA_V1_DATA_AUDIT FINAL")
print("========================================")

print(f"Temporadas: {team_game_data['SEASON'].unique()}")
print(f"Partidos: {team_game_data['GAME_ID'].nunique():,}")
print(f"Equipos: {team_game_data['TEAM_NAME'].nunique():,}")
print(f"Fecha inicial: {team_game_data['GAME_DATE'].min()}")
print(f"Fecha final: {team_game_data['GAME_DATE'].max()}")

print("\nArchivo generado:")
print(output_file)

print("\nAUDITORÍA TERMINADA.")
