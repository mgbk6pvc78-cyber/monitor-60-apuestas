def get_json(url, params=None):

    try:

        response = requests.get(
            url,
            params=params,
            timeout=15
        )

        response.raise_for_status()

        return response.json()

    except Exception as e:

        st.error(
            f"Error consultando la fuente NFL: {e}"
        )

        return None


def obtener_partidos_hoy():

    # ========================================================
    # FECHA ACTUAL
    # ========================================================

    fecha_hoy = datetime.now(
        timezone.utc
    ).strftime("%Y%m%d")

    # ========================================================
    # CONSULTAR NFL
    # ========================================================

    data = get_json(
        SCOREBOARD_URL,
        {
            "dates": fecha_hoy,
            "limit": 100,
            "seasontype": 1
        }
    )

    # ========================================================
    # SI NO HAY RESULTADOS, INTENTAR TEMPORADA REGULAR
    # ========================================================

    if not data or not data.get("events"):

        data = get_json(
            SCOREBOARD_URL,
            {
                "dates": fecha_hoy,
                "limit": 100,
                "seasontype": 2
            }
        )

    if not data:

        return []

    partidos = []

    # ========================================================
    # PROCESAR PARTIDOS
    # ========================================================

    for event in data.get("events", []):

        try:

            competition = event["competitions"][0]

            equipos = competition["competitors"]

            if len(equipos) < 2:
                continue

            home = None
            away = None

            for equipo in equipos:

                if equipo.get("homeAway") == "home":

                    home = equipo

                elif equipo.get("homeAway") == "away":

                    away = equipo

            if not home or not away:
                continue

            partidos.append({

                "id": event.get("id"),

                "nombre": event.get(
                    "name",
                    f'{away["team"]["displayName"]} @ {home["team"]["displayName"]}'
                ),

                "fecha": event.get("date"),

                "estado": event.get(
                    "status",
                    {}
                ),

                "visitante": away["team"]["displayName"],

                "local": home["team"]["displayName"],

                "visitante_abrev": away["team"].get(
                    "abbreviation",
                    ""
                ),

                "local_abrev": home["team"].get(
                    "abbreviation",
                    ""
                )
            })

        except Exception:

            continue

    return partidos
