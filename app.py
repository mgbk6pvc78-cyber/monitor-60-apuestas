# ============================================================
# 🔬 ANÁLISIS AUTOMÁTICO DE NIVELES DE PROBABILIDAD
# ============================================================

st.divider()

st.subheader("🔬 ANÁLISIS DE RENTABILIDAD POR PROBABILIDAD")

st.write(
    "Probamos diferentes probabilidades mínimas para descubrir "
    "en qué nivel nuestro modelo tiene mejor rendimiento."
)

if "backtest_bets" in locals() and len(backtest_bets) > 0:

    # Convertimos a DataFrame
    analysis_df = pd.DataFrame(backtest_bets).copy()

    # --------------------------------------------------------
    # BUSCAR COLUMNAS IMPORTANTES
    # --------------------------------------------------------

    probability_col = None
    result_col = None
    odds_col = None

    possible_probability = [
        "probability",
        "model_probability",
        "predicted_probability",
        "prob",
        "favorite_probability"
    ]

    possible_result = [
        "won",
        "win",
        "result",
        "correct",
        "hit",
        "acierto"
    ]

    possible_odds = [
        "odds",
        "moneyline",
        "american_odds",
        "moneyline_odds"
    ]

    for c in possible_probability:
        if c in analysis_df.columns:
            probability_col = c
            break

    for c in possible_result:
        if c in analysis_df.columns:
            result_col = c
            break

    for c in possible_odds:
        if c in analysis_df.columns:
            odds_col = c
            break

    if probability_col is None:

        st.error(
            "No encontramos la columna de probabilidad "
            "en los resultados del backtest."
        )

        st.write(
            "Columnas encontradas:"
        )

        st.write(
            list(analysis_df.columns)
        )

    elif result_col is None:

        st.error(
            "No encontramos la columna que indica "
            "si la apuesta ganó o perdió."
        )

        st.write(
            "Columnas encontradas:"
        )

        st.write(
            list(analysis_df.columns)
        )

    elif odds_col is None:

        st.warning(
            "No encontramos las cuotas históricas. "
            "Podemos analizar aciertos, pero no ROI real."
        )

    else:

        # ----------------------------------------------------
        # NORMALIZAR DATOS
        # ----------------------------------------------------

        analysis_df[probability_col] = pd.to_numeric(
            analysis_df[probability_col],
            errors="coerce"
        )

        analysis_df[odds_col] = pd.to_numeric(
            analysis_df[odds_col],
            errors="coerce"
        )

        analysis_df = analysis_df.dropna(
            subset=[
                probability_col,
                odds_col
            ]
        ).copy()

        # ----------------------------------------------------
        # CONVERTIR RESULTADO A GANÓ / PERDIÓ
        # ----------------------------------------------------

        def normalize_result(x):

            if isinstance(x, bool):
                return 1 if x else 0

            value = str(x).strip().lower()

            if value in [
                "1",
                "true",
                "win",
                "won",
                "w",
                "yes",
                "correct",
                "acierto",
                "ganada",
                "ganó",
                "gano"
            ]:
                return 1

            return 0

        analysis_df["__won"] = (
            analysis_df[result_col]
            .apply(normalize_result)
        )

        # ----------------------------------------------------
        # CALCULAR GANANCIA SEGÚN MONEYLINE
        # ----------------------------------------------------

        STAKE = 10.0

        def profit_from_moneyline(odds, won):

            if won == 0:
                return -STAKE

            if odds > 0:
                return STAKE * (odds / 100)

            if odds < 0:
                return STAKE * (100 / abs(odds))

            return 0

        analysis_df["__profit"] = analysis_df.apply(
            lambda row: profit_from_moneyline(
                row[odds_col],
                row["__won"]
            ),
            axis=1
        )

        # ----------------------------------------------------
        # NIVELES A PROBAR
        # ----------------------------------------------------

        levels = [
            0.55,
            0.60,
            0.65,
            0.70,
            0.75,
            0.80,
            0.85,
            0.90
        ]

        rows = []

        for minimum in levels:

            subset = analysis_df[
                analysis_df[probability_col] >= minimum
            ].copy()

            if len(subset) == 0:
                continue

            bets = len(subset)

            wins = int(
                subset["__won"].sum()
            )

            losses = bets - wins

            win_rate = wins / bets

            total_staked = bets * STAKE

            profit = subset["__profit"].sum()

            roi = (
                profit / total_staked
                if total_staked > 0
                else 0
            )

            rows.append({
                "Probabilidad mínima":
                    f"{minimum * 100:.0f}%",

                "Apuestas":
                    bets,

                "Aciertos":
                    wins,

                "Pérdidas":
                    losses,

                "Win Rate":
                    win_rate,

                "Apostado":
                    total_staked,

                "Ganancia/Pérdida":
                    profit,

                "ROI":
                    roi
            })

        results_levels = pd.DataFrame(rows)

        # ----------------------------------------------------
        # MOSTRAR TABLA
        # ----------------------------------------------------

        if len(results_levels) > 0:

            display_df = results_levels.copy()

            display_df["Win Rate"] = (
                display_df["Win Rate"] * 100
            ).round(1).astype(str) + "%"

            display_df["ROI"] = (
                display_df["ROI"] * 100
            ).round(2).astype(str) + "%"

            display_df["Apostado"] = (
                "$" +
                display_df["Apostado"]
                .round(2)
                .map(lambda x: f"{x:,.2f}")
            )

            display_df["Ganancia/Pérdida"] = (
                display_df["Ganancia/Pérdida"]
                .round(2)
                .map(
                    lambda x:
                    ("+$" if x >= 0 else "-$")
                    + f"{abs(x):,.2f}"
                )
            )

            st.dataframe(
                display_df,
                use_container_width=True,
                hide_index=True
            )

            # ------------------------------------------------
            # BUSCAR MEJOR NIVEL
            # ------------------------------------------------

            best = results_levels.loc[
                results_levels["ROI"].idxmax()
            ]

            st.success(
                f"🏆 MEJOR NIVEL: "
                f"{best['Probabilidad mínima']} "
                f"→ ROI de "
                f"{best['ROI'] * 100:.2f}%"
            )

            st.write(
                f"Con este filtro tendríamos "
                f"**{int(best['Apuestas'])} apuestas**, "
                f"{int(best['Aciertos'])} aciertos y "
                f"una ganancia/pérdida de "
                f"**${best['Ganancia/Pérdida']:,.2f}** "
                f"apostando $10 por partido."
            )

            # ------------------------------------------------
            # ADVERTENCIA
            # ------------------------------------------------

            st.info(
                "⚠️ El mejor ROI no necesariamente significa "
                "que ese sea el mejor filtro. También debemos "
                "considerar cuántas apuestas quedan. "
                "Un ROI enorme con muy pocas apuestas puede "
                "ser simplemente ruido estadístico."
            )

else:

    st.info(
        "Ejecuta primero el backtest para poder analizar "
        "los diferentes niveles de probabilidad."
    )
