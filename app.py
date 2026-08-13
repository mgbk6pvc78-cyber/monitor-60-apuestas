@st.cache_data(ttl=300)
def obtener_partidos_hoy():

    # ========================================================
    # FECHA LOCAL DE DALLAS
    # ========================================================

    from zoneinfo import ZoneInfo

    ahora = datetime.now(
        ZoneInfo("America/Chicago")
    )

    fecha_hoy = ahora.strftime("%Y%m%d")

    # ========================================================
    # CONSULTAR NFL
    #
    # seasontype=1 = PRETEMPORADA
    # ========================================================

    data = get_json(
        SCOREBOARD_URL,
        {
            "dates": fecha_hoy,
            "seasontype": 1,
            "limit": 100
        }
    )

    # ========================================================
    # SI NO DEVUELVE NADA, INTENTAR TODA LA SEMANA
    # ========================================================

    if not data or not data.get("events"):

        data = get_json(
            SCOREBOARD_URL,
            {
                "dates": "20260813-20260816",
                "seasontype": 1,
                "limit": 100
            }
        )

    if not data:
        return []

    partidos = []

    # ========================================================
    # LEER PARTIDOS
    # ========================================================

    for event in data.get("events", []):

        try:

            competition = event["competitions"][0]

            competitors = competition["competitors"]

            if len(competitors) < 2:
                continue

            home = None
            away = None

            for team in competitors:

                if team.get("homeAway") == "home":
                    home = team

                elif team.get("homeAway") == "away":
                    away = team

            if home is None or away is None:
                continue

            partidos.append({

                "id": event.get("id"),

                "name": event.get("name"),

                "date": event.get("date"),

                "status": event.get(
                    "status",
                    {}
                ),

                "home": {
                    "id": home["team"]["id"],
                    "name": home["team"]["displayName"],
                    "abbrev": home["team"].get(
                        "abbreviation"
                    )
                },

                "away": {
                    "id": away["team"]["id"],
                    "name": away["team"]["displayName"],
                    "abbrev": away["team"].get(
                        "abbreviation"
                    )
                }
            })

        except Exception:
            continue

    return partidos
