import numpy as np
import pandas as pd

def montecarlo_statistics_simulation(
    trade_history,
    equity_curve,
    n_simulations,
    initial_equity,
    threshold_ruin=0.85,
    return_raw_curves=False,
    percentiles=None,
):

    # Renombro las columnas

    trade_history = trade_history.rename(columns={"ExitTime": "Date"})
    trade_history = trade_history[["Date", "PnL"]]

    equity_curve = (
        equity_curve.reset_index()
        .rename(columns={"index": "Date"})[["Date", "Equity"]]
        .sort_values(by="Date")
    )

    trade_history["Date"] = pd.to_datetime(trade_history["Date"])
    equity_curve["Date"] = pd.to_datetime(equity_curve["Date"])

    # joineo los dfs por fechas

    full_df = pd.merge(equity_curve, trade_history, on="Date", how="left")

    full_df = full_df[~full_df["PnL"].isna()]

    # Porcentaje de ganancia

    full_df["pct"] = full_df["PnL"] / full_df["Equity"].shift(1)

    # Parámetros iniciales

    n_steps = len(trade_history)
    mean_return = full_df["pct"].mean()
    std_return = full_df["pct"].std()

    drawdowns_pct = []  # Lista para almacenar los drawdowns en porcentaje
    final_returns_pct = []  # Lista para almacenar los retornos finales en porcentaje
    ruin_count = 0  # Contador de simulaciones que alcanzan la ruina
    ruin_threshold = (
        initial_equity * threshold_ruin
    )  # Umbral de ruina en términos de equidad

    # Función para calcular el drawdown máximo en porcentaje

    def max_drawdown(equity_curve):
        running_max = np.maximum.accumulate(equity_curve)
        drawdown = (equity_curve - running_max) / running_max
        return np.min(drawdown) * 100  # Convertir el drawdown a porcentaje

    # Simulaciones de Montecarlo

    for _ in range(n_simulations):
        # Generar retornos aleatorios con media y desviación estándar de los históricos

        random_returns = mean_return + std_return * np.random.standard_t(15, size=n_steps)

        # Calcular la curva de equidad acumulada

        synthetic_equity_curve = initial_equity * np.cumprod(1 + random_returns)

        # Calcular drawdown y almacenarlo en porcentaje

        dd_pct = max_drawdown(synthetic_equity_curve)
        drawdowns_pct.append(dd_pct)

        # Calcular el retorno acumulado porcentual y almacenarlo

        final_return_pct = (
            synthetic_equity_curve[-1] / initial_equity - 1
        ) * 100  # Retorno final en porcentaje
        final_returns_pct.append(final_return_pct)

        # Verificar si la equidad cae por debajo del umbral de ruina en algún punto

        if np.any(synthetic_equity_curve <= ruin_threshold):
            ruin_count += 1
    # Crear un DataFrame separado para los drawdowns y los retornos acumulados en porcentaje

    df_drawdowns = pd.DataFrame({"Drawdown (%)": drawdowns_pct})
    df_final_returns_pct = pd.DataFrame({"Final Return (%)": final_returns_pct})

    # Calcular las estadísticas usando df.describe() para cada DataFrame

    if not percentiles:
        drawdown_stats = df_drawdowns.describe()
        return_stats = df_final_returns_pct.describe()
    else:
        drawdown_stats = df_drawdowns.describe(percentiles=percentiles)
        return_stats = df_final_returns_pct.describe(percentiles=percentiles)
    # Calcular el riesgo de ruina

    risk_of_ruin = ruin_count / n_simulations

    # Agregar el riesgo de ruina a las estadísticas de drawdown

    drawdown_stats.loc["Risk of Ruin"] = risk_of_ruin

    # Combinar las métricas de drawdowns y retornos porcentuales

    combined_stats = pd.concat([drawdown_stats, return_stats], axis=1)
    if return_raw_curves:
        return combined_stats, df_drawdowns, df_final_returns_pct
    
    return combined_stats