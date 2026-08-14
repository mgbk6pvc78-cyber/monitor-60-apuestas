# ============================================================
# NBA_V1_DATA_AUDIT
# VERSION CORREGIDA
# Proyecto independiente del NFL
# ============================================================

import pandas as pd
import numpy as np
import requests
from io import BytesIO
from pathlib import Path

# ============================================================
# CONFIGURACION
# ============================================================

BASE_URL = "https://raw.githubusercontent.com/llimllib/nba_data/main/data/"

SEASONS = {
    2025: "2024-25",
    2026: "2025-26"
}

OUTPUT_DIR = Path("NBA_V1")
OUTPUT_DIR.mkdir(exist_ok=True)


# ============================================================
# FUNCION PARA NORMALIZAR COLUMNAS
# ============================================================

def normalize_columns(df):

    # Convertir nombres a texto
    df.columns = [str(c).strip() for c in df.columns]

    # Mapa flexible para diferentes nombres
    aliases = {
        "game_id": "GAME_ID",
        "gameid": "GAME_ID",
        "GAMEID": "GAME_ID",

        "game_date": "GAME_DATE",
        "gamedate": "GAME_DATE",

        "team_id": "TEAM_ID",
        "teamid": "TEAM_ID",

        "team_name": "TEAM_NAME",
        "teamname": "TEAM_NAME",

        "team_abbreviation": "TEAM_ABBREVIATION",
        "team_abbreviation ": "TEAM_ABBREVIATION",

        "matchup": "MATCHUP",

        "wl": "WL",

        "pts": "PTS",
        "fg_pct": "FG_PCT",
        "fg3_pct": "FG3_PCT",
        "ft_pct": "FT_PCT",

        "oreb": "OREB",
        "dreb": "DREB",
        "reb": "REB",

        "ast": "AST",
        "stl": "STL",
        "blk": "BLK",
        "tov": "TOV",
        "pf": "PF",

        "plus_minus": "PLUS_MINUS",
        "plusminus": "PLUS_MINUS"
    }

    # Primero intentamos coincidencia exacta
    rename_map = {}

    for col in df.columns:

        clean = col.strip()
        lower = clean.lower()

        if clean in aliases:
            rename_map[col] = aliases[clean]

        elif lower in aliases:
            rename_map[col] = aliases[lower]

    df = df.rename(columns=rename_map)

    return df


# ============================================================
# DESCARGAR PARQUET
# ============================================================

def download_parquet(season_year):

    url = f"{BASE_URL}gamelog_{season_year}.parquet"

    print("\n----------------------------------------")
    print(f"DESCARGANDO {SEASONS[season_year]}")
    print("----------------------------------------")
    print(url)

    response = requests.get(url, timeout=120)

    response.raise_for_status()

    df = pd.read_parquet(
        BytesIO(response.content)
    )

    print(f"Registros descargados: {len(df):,}")

    # Normalizar inmediatamente
    df = normalize_columns(df)

    print("\nColumnas detectadas:")

    for col in df.columns:
        print(" -", col)

    return df


# ============================================================
# CARGAR TEMPORADAS
# ============================================================

dfs = []

for season_year in SEASONS:

    df = download_parquet(season_year)

    df["SEASON"] = SEASONS[season_year]
    df["SEASON_END_YEAR"] = season_year

    dfs.append(df)


# ============================================================
# UNIR
# ============================================================

raw = pd.concat(
    dfs,
    ignore_index=True
)

print("\n========================================")
print("NBA_V1 RAW CARGADO")
print("========================================")

print("Registros:", f"{len(raw):,}")
print("Columnas:", len(raw.columns))


# ============================================================
# COMPROBAR GAME_ID
# ============================================================

print("\n========================================")
print("COMPROBACION GAME_ID")
print("========================================")

if "GAME_ID" not in raw.columns:

    print("ERROR: GAME_ID no fue encontrado.")

    print("\nColumnas disponibles:")

    for col in raw.columns:
        print(" -", col)

    raise ValueError(
        "No se encontró GAME_ID después de normalizar columnas."
    )

else:

    print("GAME_ID encontrado correctamente.")


# ============================================================
# CONVERTIR GAME_ID
# ============================================================

raw["GAME_ID"] = (
    raw["GAME_ID"]
    .astype(str)
    .str.strip()
)


# ============================================================
# TIPO DE PARTIDO
# ============================================================

raw["GAME_TYPE"] = (
    raw["GAME_ID"]
    .str[:3]
)

print("\n========================================")
print("TIPOS DE PARTIDO")
print("========================================")

print(
    raw["GAME_TYPE"]
    .value_counts()
)


# ============================================================
# REGULAR SEASON
# ============================================================

regular = raw[
    raw["GAME_TYPE"] == "002"
].copy()

print("\n========================================")
print("REGULAR SEASON")
print("========================================")

print(
    "Registros de equipo:",
    f"{len(regular):,}"
)

print(
    "Partidos únicos:",
    f"{regular['GAME_ID'].nunique():,}"
)


# ============================================================
# PARTIDOS POR TEMPORADA
# ============================================================

print("\n========================================")
print("PARTIDOS POR TEMPORADA")
print("========================================")

games_by_season = (
    regular
    .groupby("SEASON")["GAME_ID"]
    .nunique()
    .sort_index()
)

print(games_by_season)


# ============================================================
# EQUIPOS
# ============================================================

print("\n========================================")
print("EQUIPOS")
print("========================================")

teams_by_season = (
    regular
    .groupby("SEASON")["TEAM_NAME"]
    .nunique()
)

print(teams_by_season)


# ============================================================
# DUPLICADOS
# ============================================================

print("\n========================================")
print("DUPLICADOS")
print("========================================")

duplicate_mask = regular.duplicated(
    subset=["GAME_ID", "TEAM_ID"],
    keep=False
)

duplicate_count = duplicate_mask.sum()

print(
    "Duplicados GAME_ID + TEAM_ID:",
    f"{duplicate_count:,}"
)


# ============================================================
# DOS EQUIPOS POR PARTIDO
# ============================================================

print("\n========================================")
print("VALIDACION DE PARTIDOS")
print("========================================")

teams_per_game = (
    regular
    .groupby("GAME_ID")["TEAM_ID"]
    .nunique()
)

bad_games = teams_per_game[
    teams_per_game != 2
]

print(
    "Partidos con exactamente 2 equipos:",
    f"{(teams_per_game == 2).sum():,}"
)

print(
    "Partidos problemáticos:",
    f"{len(bad_games):,}"
)

if len(bad_games) > 0:

    print("\nPrimeros partidos problemáticos:")

    print(
        bad_games.head(20)
    )


# ============================================================
# VALORES FALTANTES
# ============================================================

print("\n========================================")
print("VALORES FALTANTES")
print("========================================")

missing = (
    regular
    .isna()
    .sum()
    .sort_values(ascending=False)
)

missing = missing[
    missing > 0
]

if len(missing) == 0:

    print("No hay valores faltantes.")

else:

    print(missing)


# ============================================================
# FECHAS
# ============================================================

print("\n========================================")
print("FECHAS")
print("========================================")

regular["GAME_DATE"] = pd.to_datetime(
    regular["GAME_DATE"],
    errors="coerce"
)

print(
    "Primera fecha:",
    regular["GAME_DATE"].min()
)

print(
    "Última fecha:",
    regular["GAME_DATE"].max()
)

print(
    "Fechas inválidas:",
    regular["GAME_DATE"].isna().sum()
)


# ============================================================
# LOCAL / VISITANTE
# ============================================================

print("\n========================================")
print("LOCAL / VISITANTE")
print("========================================")

regular["IS_HOME"] = (
    regular["MATCHUP"]
    .astype(str)
    .str.contains(
        " vs. ",
        regex=False,
        na=False
    )
)

regular["IS_AWAY"] = (
    regular["MATCHUP"]
    .astype(str)
    .str.contains(
        " @ ",
        regex=False,
        na=False
    )
)

print(
    "Registros identificados como LOCAL:",
    regular["IS_HOME"].sum()
)

print(
    "Registros identificados como VISITANTE:",
    regular["IS_AWAY"].sum()
)

unknown_location = regular[
    ~(regular["IS_HOME"] | regular["IS_AWAY"])
]

print(
    "Registros sin identificar:",
    len(unknown_location)
)

if len(unknown_location) > 0:

    print(
        unknown_location[
            [
                "GAME_ID",
                "TEAM_NAME",
                "MATCHUP"
            ]
        ].head(20)
    )


# ============================================================
# RESULTADOS
# ============================================================

print("\n========================================")
print("RESULTADOS")
print("========================================")

print(
    regular["WL"]
    .value_counts(dropna=False)
)


# ============================================================
# ESTADISTICAS DISPONIBLES
# ============================================================

candidate_columns = [

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
    c
    for c in candidate_columns
    if c in regular.columns
]

print("\n========================================")
print("ESTADISTICAS DISPONIBLES")
print("========================================")

for col in available_numeric:
    print(" -", col)


# ============================================================
# RESUMEN ESTADISTICO
# ============================================================

if len(available_numeric) > 0:

    print("\n========================================")
    print("RESUMEN ESTADISTICO")
    print("========================================")

    print(
        regular[
            available_numeric
        ].describe().T
    )


# ============================================================
# DATASET LIMPIO
# ============================================================

base_columns = [

    "SEASON",
    "SEASON_END_YEAR",
    "GAME_ID",
    "GAME_DATE",
    "TEAM_ID",
    "TEAM_NAME",
    "MATCHUP",
    "WL",
    "IS_HOME"
]

final_columns = [
    c
    for c in base_columns + available_numeric
    if c in regular.columns
]

team_game_data = regular[
    final_columns
].copy()


# ============================================================
# ORDEN CRONOLOGICO
# ============================================================

team_game_data = (
    team_game_data
    .sort_values(
        [
            "GAME_DATE",
            "GAME_ID",
            "TEAM_ID"
        ]
    )
    .reset_index(drop=True)
)


# ============================================================
# GUARDAR
# ============================================================

csv_file = (
    OUTPUT_DIR /
    "NBA_V1_DATA.csv"
)

team_game_data.to_csv(
    csv_file,
    index=False
)


# ============================================================
# GUARDAR AUDITORIA
# ============================================================

audit_file = (
    OUTPUT_DIR /
    "NBA_V1_DATA_AUDIT.txt"
)

with open(
    audit_file,
    "w",
    encoding="utf-8"
) as f:

    f.write(
        "NBA_V1 DATA AUDIT\n"
    )

    f.write(
        "=================\n\n"
    )

    f.write(
        f"Registros RAW: {len(raw):,}\n"
    )

    f.write(
        f"Registros regular season: "
        f"{len(regular):,}\n"
    )

    f.write(
        f"Partidos únicos: "
        f"{regular['GAME_ID'].nunique():,}\n"
    )

    f.write(
        f"Equipos: "
        f"{regular['TEAM_NAME'].nunique():,}\n"
    )

    f.write(
        f"Fecha inicial: "
        f"{regular['GAME_DATE'].min()}\n"
    )

    f.write(
        f"Fecha final: "
        f"{regular['GAME_DATE'].max()}\n"
    )

    f.write(
        f"Duplicados: "
        f"{duplicate_count:,}\n"
    )

    f.write(
        f"Partidos problemáticos: "
        f"{len(bad_games):,}\n"
    )

    f.write(
        f"Estadísticas disponibles: "
        f"{available_numeric}\n"
    )


# ============================================================
# RESUMEN FINAL
# ============================================================

print("\n")
print("========================================")
print("NBA_V1_DATA_AUDIT TERMINADA")
print("========================================")

print(
    "Temporadas:",
    list(team_game_data["SEASON"].unique())
)

print(
    "Partidos:",
    f"{team_game_data['GAME_ID'].nunique():,}"
)

print(
    "Equipos:",
    f"{team_game_data['TEAM_NAME'].nunique():,}"
)

print(
    "Fecha inicial:",
    team_game_data["GAME_DATE"].min()
)

print(
    "Fecha final:",
    team_game_data["GAME_DATE"].max()
)

print(
    "\nArchivo de datos:"
)

print(csv_file)

print(
    "\nArchivo de auditoría:"
)

print(audit_file)

print("\nTODO CORRECTO.")
