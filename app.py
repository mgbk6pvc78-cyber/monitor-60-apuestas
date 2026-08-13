# ============================================================
# BACKTEST ROI REALISTA
# ============================================================

NFLVERSE_SCHEDULES = (
    "https://raw.githubusercontent.com/nflverse/nfldata/"
    "master/data/games.csv"
)


@st.cache_data(ttl=3600)
def load_historical_odds():
    """
    Carga automáticamente los partidos históricos NFL
    incluyendo moneylines.

    Fuente: nflverse / Lee Sharpe.
    """

    df = pd.read_csv(NFLVERSE_SCHEDULES)

    df.columns = [
        c.lower().strip()
        for c in df.columns
    ]

    # Normalizar nombres
    rename_map = {
        "gameday": "date",
        "away_team": "away",
        "home_team": "home",
        "away_score": "away_score",
        "home_score": "home_score",
        "away_moneyline": "away_moneyline",
        "home_moneyline": "home_moneyline",
    }

    df = df.rename(
        columns={
            k: v
            for k, v in rename_map.items()
            if k in df.columns
        }
    )

    required = [
        "season",
        "game_type",
        "date",
        "away",
        "home",
        "away_score",
        "home_score",
        "away_moneyline",
        "home_moneyline",
    ]

    missing = [
        c for c in required
        if c not in df.columns
    ]

    if missing:
        raise ValueError(
            "Faltan columnas en los datos históricos: "
            + ", ".join(missing)
        )

    # Solo temporada regular 2025
    df = df[
        (df["season"] == 2025)
        &
        (
            df["game_type"]
            .astype(str)
            .str.upper()
            == "REG"
        )
    ].copy()

    # Convertir fecha
    df["date"] = pd.to_datetime(
        df["date"],
        errors="coerce"
    )

    # Convertir scores
    df["away_score"] = pd.to_numeric(
        df["away_score"],
        errors="coerce"
    )

    df["home_score"] = pd.to_numeric(
        df["home_score"],
        errors="coerce"
    )

    df["away_moneyline"] = pd.to_numeric(
        df["away_moneyline"],
        errors="coerce"
    )

    df["home_moneyline"] = pd.to_numeric(
        df["home_moneyline"],
        errors="coerce"
    )

    df = df.dropna(
        subset=[
            "date",
            "away_score",
            "home_score",
        ]
    )

    return df.sort_values("date").reset_index(
        drop=True
    )


def american_odds_profit(
    odds,
    stake
):
    """
    Calcula cuánto gana una apuesta de $stake
    según la moneyline americana.
    """

    if pd.isna(odds):
        return None

    odds = float(odds)

    if odds > 0:

        return stake * (
            odds / 100
        )

    elif odds < 0:

        return stake * (
            100 / abs(odds)
        )

    return 0


def run_realistic_backtest(
    games,
    minimum_probability=0.70,
    stake=10.0
):
    """
    Backtest SIN utilizar información futura.

    Para cada partido:

    1. Usa únicamente partidos anteriores.
    2. Construye las estadísticas hasta ese momento.
    3. Calcula nuestra probabilidad.
    4. Si >= minimum_probability:
       realiza apuesta virtual.
    5. Usa la moneyline histórica SOLO para
       calcular el retorno.
    """

    # --------------------------------------------------------
    # Orden cronológico
    # --------------------------------------------------------

    games = games.sort_values(
        "date"
    ).reset_index(drop=True)

    historical_games = []

    bets = []

    for _, game in games.iterrows():

        home = normalize_team(
            str(game["home"])
        )

        away = normalize_team(
            str(game["away"])
        )

        # ----------------------------------------------------
        # NO apostamos si no tenemos historial suficiente
        # ----------------------------------------------------

        if len(historical_games) < 10:
            historical_games.append(
                game.to_dict()
            )
            continue

        # ----------------------------------------------------
        # Construir estadísticas SOLO con pasado
        # ----------------------------------------------------

        past_df = pd.DataFrame(
            historical_games
        )

        if past_df.empty:
            continue

        # Adaptar nombres
        past_for_stats = past_df[
            [
                "home",
                "away",
                "home_score",
                "away_score",
            ]
        ].copy()

        # Normalizar equipos
        past_for_stats["home"] = (
            past_for_stats["home"]
            .astype(str)
            .map(normalize_team)
        )

        past_for_stats["away"] = (
            past_for_stats["away"]
            .astype(str)
            .map(normalize_team)
        )

        past_for_stats = past_for_stats.dropna(
            subset=[
                "home",
                "away",
                "home_score",
                "away_score",
            ]
        )

        # ----------------------------------------------------
        # Crear estadísticas
        # ----------------------------------------------------

        stats = build_team_stats(
            past_for_stats
        )

        # ----------------------------------------------------
        # Calcular probabilidad
        # ----------------------------------------------------

        prediction = calculate_probability(
            home,
            away,
            stats
        )

        # Guardar partido como información disponible
        # para el futuro
        historical_games.append(
            game.to_dict()
        )

        if prediction is None:
            continue

        hp = prediction[
            "home_probability"
        ]

        ap = prediction[
            "away_probability"
        ]

        # ----------------------------------------------------
        # Elegir favorito del modelo
        # ----------------------------------------------------

        if hp >= ap:

            favorite = home

            probability = hp

            odds = game[
                "home_moneyline"
            ]

            actual_winner = (
                home
                if game["home_score"]
                >
                game["away_score"]
                else
                away
            )

        else:

            favorite = away

            probability = ap

            odds = game[
                "away_moneyline"
            ]

            actual_winner = (
                away
                if game["away_score"]
                >
                game["home_score"]
                else
                home
            )

        # ----------------------------------------------------
        # Filtro 70%
        # ----------------------------------------------------

        if probability < minimum_probability:
            continue

        # Sin cuota histórica no podemos calcular ROI
        if pd.isna(odds):
            continue

        # ----------------------------------------------------
        # Resultado
        # ----------------------------------------------------

        won = (
            favorite
            ==
            actual_winner
        )

        if won:

            profit = american_odds_profit(
                odds,
                stake
            )

            if profit is None:
                continue

        else:

            profit = -stake

        bets.append({

            "date":
                game["date"],

            "away":
                away,

            "home":
                home,

            "pick":
                favorite,

            "probability":
                probability,

            "moneyline":
                odds,

            "won":
                won,

            "stake":
                stake,

            "profit":
                profit,

        )

    # --------------------------------------------------------
    # DataFrame final
    # --------------------------------------------------------

    result = pd.DataFrame(
        bets
    )

    return result


# ============================================================
# INTERFAZ BACKTEST
# ============================================================

st.divider()

st.header(
    "📈 Backtest ROI"
)

st.write(
    "Probamos el modelo partido por partido "
    "utilizando únicamente información disponible "
    "ANTES de cada partido."
)

st.info(
    "Las cuotas históricas NO se utilizan para "
    "decidir qué apostar. Solamente se utilizan "
    "para calcular cuánto habría ganado o perdido "
    "cada apuesta."
)

# ------------------------------------------------------------
# CONTROLES
# ------------------------------------------------------------

minimum_probability = st.number_input(
    "Probabilidad mínima",
    min_value=0.50,
    max_value=0.95,
    value=0.70,
    step=0.01,
    format="%.2f"
)

stake = st.number_input(
    "Apuesta por partido ($)",
    min_value=1.0,
    max_value=10000.0,
    value=10.0,
    step=1.0
)

# ------------------------------------------------------------
# EJECUTAR
# ------------------------------------------------------------

if st.button(
    "🚀 EJECUTAR BACKTEST",
    use_container_width=True
):

    with st.spinner(
        "Calculando backtest histórico..."
    ):

        try:

            odds_games = (
                load_historical_odds()
            )

            bets = run_realistic_backtest(
                odds_games,
                minimum_probability,
                stake
            )

            if bets.empty:

                st.warning(
                    "No se encontraron apuestas "
                    "con los criterios seleccionados."
                )

            else:

                total_bets = len(
                    bets
                )

                wins = int(
                    bets["won"].sum()
                )

                losses = (
                    total_bets
                    -
                    wins
                )

                total_staked = (
                    bets["stake"].sum()
                )

                net_profit = (
                    bets["profit"].sum()
                )

                total_return = (
                    total_staked
                    +
                    net_profit
                )

                roi = (
                    net_profit
                    /
                    total_staked
                    *
                    100
                )

                win_rate = (
                    wins
                    /
                    total_bets
                    *
                    100
                )

                # ------------------------------------------------
                # Métricas
                # ------------------------------------------------

                st.subheader(
                    "🏆 RESULTADO DEL BACKTEST"
                )

                c1, c2 = st.columns(2)

                with c1:

                    st.metric(
                        "🎯 Apuestas",
                        total_bets
                    )

                with c2:

                    st.metric(
                        "✅ Aciertos",
                        wins
                    )

                c3, c4 = st.columns(2)

                with c3:

                    st.metric(
                        "📈 Win Rate",
                        f"{win_rate:.1f}%"
                    )

                with c4:

                    st.metric(
                        "💰 ROI",
                        f"{roi:+.2f}%"
                    )

                c5, c6 = st.columns(2)

                with c5:

                    st.metric(
                        "💵 Apostado",
                        f"${total_staked:,.2f}"
                    )

                with c6:

                    st.metric(
                        "💰 Ganancia/Pérdida",
                        f"${net_profit:+,.2f}"
                    )

                st.metric(
                    "🏦 Retorno total",
                    f"${total_return:,.2f}"
                )

                # ------------------------------------------------
                # RESUMEN
                # ------------------------------------------------

                if net_profit > 0:

                    st.success(
                        f"🟢 El modelo habría terminado "
                        f"con GANANCIA de "
                        f"${net_profit:,.2f}"
                    )

                elif net_profit < 0:

                    st.error(
                        f"🔴 El modelo habría terminado "
                        f"con PÉRDIDA de "
                        f"${abs(net_profit):,.2f}"
                    )

                else:

                    st.info(
                        "⚪ El modelo habría quedado "
                        "exactamente en break-even."
                    )

                # ------------------------------------------------
                # TABLA DE APUESTAS
                # ------------------------------------------------

                st.subheader(
                    "📊 Apuestas realizadas"
                )

                display_bets = bets.copy()

                display_bets[
                    "probability"
                ] = (
                    display_bets[
                        "probability"
                    ]
                    *
                    100
                ).round(1)

                display_bets[
                    "moneyline"
                ] = display_bets[
                    "moneyline"
                ].round(0)

                display_bets[
                    "profit"
                ] = display_bets[
                    "profit"
                ].round(2)

                display_bets[
                    "result"
                ] = np.where(
                    display_bets[
                        "won"
                    ],
                    "✅ GANÓ",
                    "❌ PERDIÓ"
                )

                st.dataframe(
                    display_bets[
                        [
                            "date",
                            "pick",
                            "probability",
                            "moneyline",
                            "result",
                            "profit",
                        ]
                    ],
                    use_container_width=True
                )

                # ------------------------------------------------
                # DESCARGAR RESULTADOS
                # ------------------------------------------------

                csv = bets.to_csv(
                    index=False
                )

                st.download_button(
                    "📥 DESCARGAR RESULTADOS CSV",
                    csv,
                    "backtest_nfl_2025.csv",
                    "text/csv",
                    use_container_width=True
                )

        except Exception as e:

            st.error(
                "❌ Error ejecutando el backtest."
            )

            st.code(
                str(e)
            )
