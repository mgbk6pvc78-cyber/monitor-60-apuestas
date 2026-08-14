# ============================================================
# FUENTES NFL
# ============================================================

import requests
import pandas as pd
import numpy as np
import streamlit as st
from datetime import datetime
from zoneinfo import ZoneInfo


NFLDATA_GAMES = "https://api.nfldata.org/v1/games"


# ============================================================
# OBTENER JUEGOS NFL DESDE NFLDATA
# ============================================================

@st.cache_data(ttl=900)
def obtener_juegos_nfldata(
    season=2026
):

    try:

        response = requests.get(
            NFLDATA_GAMES,
            params={
                "season": season
            },
            timeout=20
        )

        if response.status_code != 200:

            return pd.DataFrame(), (
                f"HTTP {response.status_code}"
            )

        data = response.json()

        # Algunas APIs devuelven:
        # {"data": [...]}

        if isinstance(data, dict):

            juegos = data.get(
                "data",
                data.get(
                    "games",
                    []
                )
            )

        elif isinstance(data, list):

            juegos = data

        else:

            juegos = []

        if not juegos:

            return pd.DataFrame(), None

        df = pd.DataFrame(juegos)

        return df, None

    except Exception as e:

        return pd.DataFrame(), str(e)


# ============================================================
# NORMALIZAR FECHAS
# ============================================================

def normalizar_fecha(valor):

    if pd.isna(valor):

        return None

    try:

        fecha = pd.to_datetime(
            valor,
            utc=True
        )

        return fecha.astimezone(
            ZoneInfo(
                "America/Chicago"
            )
        )

    except:

        return None


# ============================================================
# PARTIDOS PARA MOSTRAR
# ============================================================

def obtener_partidos_nfl():

    año = datetime.now(
        ZoneInfo(
            "America/Chicago"
        )
    ).year

    df, error = obtener_juegos_nfldata(
        season=año
    )

    if error:

        return [], error

    if df.empty:

        return [], None

    # --------------------------------------------------------
    # BUSCAR COLUMNA DE FECHA
    # --------------------------------------------------------

    columnas_fecha = [
        "game_date",
        "gameday",
        "date",
        "gameDate"
    ]

    columna_fecha = None

    for columna in columnas_fecha:

        if columna in df.columns:

            columna_fecha = columna
            break

    if columna_fecha is None:

        return [], (
            "La fuente no contiene "
            "una columna de fecha."
        )

    df["_fecha"] = df[
        columna_fecha
    ].apply(
        normalizar_fecha
    )

    df = df[
        df["_fecha"].notna()
    ].copy()

    # --------------------------------------------------------
    # FECHA ACTUAL DALLAS
    # --------------------------------------------------------

    ahora = datetime.now(
        ZoneInfo(
            "America/Chicago"
        )
    )

    hoy = ahora.date()

    # --------------------------------------------------------
    # PARTIDOS DEL DÍA
    # --------------------------------------------------------

    partidos_hoy = df[
        df["_fecha"].dt.date == hoy
    ].copy()

    # --------------------------------------------------------
    # SI NO HAY HOY
    # BUSCAR PRÓXIMOS 7 DÍAS
    # --------------------------------------------------------

    if partidos_hoy.empty:

        limite = hoy + pd.Timedelta(
            days=7
        )

        partidos_hoy = df[
            (
                df["_fecha"].dt.date >= hoy
            )
            &
            (
                df["_fecha"].dt.date <= limite
            )
        ].copy()

    # --------------------------------------------------------
    # ORDEN
    # --------------------------------------------------------

    partidos_hoy = partidos_hoy.sort_values(
        "_fecha"
    )

    return (
        partidos_hoy.to_dict(
            "records"
        ),
        None
    )


# ============================================================
# OBTENER NOMBRE EQUIPO
# ============================================================

def buscar_campo(
    juego,
    posibles
):

    for campo in posibles:

        if campo in juego:

            valor = juego[campo]

            if (
                valor is not None
                and not pd.isna(valor)
            ):

                return valor

    return None


# ============================================================
# PREPARAR PARTIDO
# ============================================================

def preparar_partido(
    juego
):

    away = buscar_campo(
        juego,
        [
            "away_team",
            "awayTeam",
            "visitor_team",
            "visitorTeam"
        ]
    )

    home = buscar_campo(
        juego,
        [
            "home_team",
            "homeTeam"
        ]
    )

    fecha = juego.get(
        "_fecha"
    )

    if fecha is not None:

        hora = fecha.strftime(
            "%I:%M %p"
        )

        fecha_texto = fecha.strftime(
            "%m/%d/%Y"
        )

    else:

        hora = "N/D"
        fecha_texto = "N/D"

    return {
        "away": away,
        "home": home,
        "fecha": fecha_texto,
        "hora": hora,
        "raw": juego
    }
