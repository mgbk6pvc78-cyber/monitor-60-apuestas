import streamlit as st
import pandas as pd
import requests
from io import BytesIO

st.title("NBA_V1 - Prueba de datos")

url = "https://raw.githubusercontent.com/llimllib/nba_data/main/data/gamelog_2025.parquet"

st.write("1. Intentando descargar 2024-25...")

try:
    response = requests.get(url, timeout=60)

    st.write("HTTP:", response.status_code)
    st.write("Tamaño:", len(response.content))

    response.raise_for_status()

    st.write("2. Archivo descargado correctamente.")

    df = pd.read_parquet(BytesIO(response.content))

    st.write("3. Parquet leído correctamente.")

    st.write("Filas:", len(df))
    st.write("Columnas:", list(df.columns))

    st.dataframe(df.head(10))

except Exception as e:

    st.error("ERROR")
    st.exception(e)
