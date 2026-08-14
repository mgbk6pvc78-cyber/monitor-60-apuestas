import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="NFL_SIMPLE_V1 TEST",
    layout="wide"
)

st.title("🏈 NFL_SIMPLE_V1 - PRUEBA REAL NFL")

URL = "https://raw.githubusercontent.com/nflverse/nfldata/master/data/games.csv"

try:

    st.write("Descargando dataset NFL...")

    df = pd.read_csv(URL)

    st.success("Dataset NFL descargado correctamente.")

    # --------------------------------------------------------
    # INFORMACIÓN GENERAL
    # --------------------------------------------------------

    st.header("1. Dataset original")

    st.write("Filas:", len(df))
    st.write("Columnas:", len(df.columns))

    # --------------------------------------------------------
    # COLUMNAS
    # --------------------------------------------------------

    st.header("2. Columnas")

    st.write(list(df.columns))

    # --------------------------------------------------------
    # TEMPORADAS
    # --------------------------------------------------------

    st.header("3. Temporadas disponibles")

    st.write(
        sorted(
            df["season"]
            .dropna()
            .unique()
            .tolist()
        )[-10:]
    )

    # --------------------------------------------------------
    # 2024
    # --------------------------------------------------------

    nfl_2024 = df[
        df["season"] == 2024
    ].copy()

    # --------------------------------------------------------
    # 2025
    # --------------------------------------------------------

    nfl_2025 = df[
        df["season"] == 2025
    ].copy()

    # --------------------------------------------------------
    # PARTIDOS
    # --------------------------------------------------------

    st.header("4. Comprobación NFL")

    c1, c2 = st.columns(2)

    with c1:
        st.metric(
            "Partidos 2024",
            nfl_2024["game_id"].nunique()
        )

    with c2:
        st.metric(
            "Partidos 2025",
            nfl_2025["game_id"].nunique()
        )

    # --------------------------------------------------------
    # GAME TYPE
    # --------------------------------------------------------

    st.header("5. Tipo de partidos")

    if "game_type" in df.columns:

        st.dataframe(
            df[
                df["season"].isin([2024, 2025])
            ]
            .groupby(
                ["season", "game_type"]
            )["game_id"]
            .nunique()
            .reset_index(),
            use_container_width=True
        )

    # --------------------------------------------------------
    # PREVIEW
    # --------------------------------------------------------

    st.header("6. Primeros partidos")

    st.dataframe(
        df[
            df["season"].isin([2024, 2025])
        ][
            [
                "game_id",
                "season",
                "week",
                "game_type",
                "home_team",
                "away_team"
            ]
        ]
        .head(20),
        use_container_width=True
    )

except Exception as e:

    st.error("ERROR")

    st.exception(e)
