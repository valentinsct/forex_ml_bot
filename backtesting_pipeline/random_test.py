import os
import re
import sys

current_dir = os.path.abspath(os.path.dirname(__file__))
root_dir = os.path.abspath(os.path.join(current_dir, ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)
    
import numpy as np
import pandas as pd
import yaml
from backbone.utils.general_purpose import load_function
from backbone.utils.wfo_utils import run_strategy

def find_matching_files(directory, ticker, interval):
    pattern = rf"^{ticker}_{interval}_.+_.+\.csv$"
    all_files = os.listdir(directory)
    matching_files = [file for file in all_files if re.match(pattern, file)]

    return matching_files

time_frames = {
    16385: 1,
    16386: 2,
    16387: 3,
    16388: 4,
}

if __name__ == '__main__':
    with open("./backtesting_pipeline/configs/backtest_params.yml", "r") as file_name:
        bt_params = yaml.safe_load(file_name)
    
    initial_cash = bt_params["initial_cash"]
    margin = bt_params["margin"]
    config_path = bt_params['config_path']
    
    with open(config_path, "r") as file_name:
        configs = yaml.safe_load(file_name)
            
    configs = configs["random_test"]

    date_from = configs["date_from"]
    date_to = configs["date_to"]
    strategy = configs["strategy_path"]
    in_path = configs["in_path"]
    data_path = configs["data_path"]
    out_path = configs["out_path"]
    strategy_path = configs["strategy_path"]
    plot_path = os.path.join(out_path, "plots")
    
    if not os.path.exists(out_path):
        os.makedirs(out_path)
        
    if not os.path.exists(plot_path):
        os.makedirs(plot_path)
        

    filter_performance = pd.read_csv(os.path.join(in_path, "filter_performance.csv"))

    commissions_path = os.path.join(data_path, "commissions/commissions.yml")
    with open(commissions_path, "r") as file_name:
        commissions = yaml.safe_load(file_name)
    
    strategy = load_function(strategy_path)


    performance = pd.DataFrame()
    all_opt_params = {}

    symbols = {}
    stats_per_symbol = {}

    for _, row in filter_performance.iterrows():
        try:
            ticker = row.ticker
            interval = row.interval
            
            path = os.path.join(data_path, "data")
            matching_file = find_matching_files(path, ticker, interval).pop()

            # busco el df del activo
            prices = pd.read_csv(os.path.join(path, matching_file))
            prices["Date"] = pd.to_datetime(prices["Date"])
            prices = prices.set_index("Date")
            
            # busco los trades para obtener sus probs
            trade_history = pd.read_csv(
                os.path.join(in_path, f'{ticker}_{interval}', 'trades.csv')
            )
            
            equity_curve = pd.read_csv(
                os.path.join(in_path, f'{ticker}_{interval}', 'equity.csv')
            )
            
            long_trades = trade_history[trade_history['Size'] > 0]
            short_trades = trade_history[trade_history['Size'] < 0]
            
            prob_trade = len(trade_history) / len(equity_curve)  # Probabilidad de realizar un trade
            prob_long = len(long_trades) / len(trade_history) if len(trade_history) > 0 else 0
            prob_short = len(short_trades) / len(trade_history) if len(trade_history) > 0 else 0

            timeframe_hours = time_frames[interval]
            trade_history["Duration"] = pd.to_timedelta(trade_history["Duration"])
            trade_history["Bars"] = (trade_history["Duration"] / pd.Timedelta(hours=timeframe_hours)).apply(lambda x: int(round(x)))

            avg_trade_duration = trade_history.Bars.mean()
            std_trade_duration = trade_history.Bars.std()

            params = {
                'prob_trade': prob_trade,
                'prob_long': prob_long,
                'prob_short': prob_short,
                'avg_trade_duration': avg_trade_duration,
                'std_trade_duration': std_trade_duration,
            }

            print(ticker, interval)
            commission = commissions[ticker]
            
            if ticker not in stats_per_symbol.keys():
                stats_per_symbol[ticker] = {}
                
            df_stats, wfo_stats = run_strategy(
                strategy=strategy,
                ticker=ticker,
                interval=interval,
                commission=commission,
                prices=prices,
                initial_cash=initial_cash,
                margin=margin,
                opt_params=params,
                plot=True,
                plot_path=plot_path,
            )

            stats_per_symbol[ticker][interval] = wfo_stats

            performance = pd.concat([performance, df_stats])
        
        except Exception as e:
            print(f"hubo un problema con {ticker} {interval}: {e}")
            
    performance["return/dd"] = performance["return"] / -performance["drawdown"]
    performance["drawdown"] = -performance["drawdown"]
    
    performance["custom_metric"] = (
        performance["return"] / (1 + performance.drawdown)
    ) * np.log(1 + performance.trades)

    performance.to_csv(os.path.join(out_path, "performance.csv"), index=False)
    
    for index, row in filter_performance.iterrows():
        ticker = row.ticker
        interval = row.interval

        path = os.path.join(out_path, f"{ticker}_{interval}")

        if not os.path.exists(path):
            os.makedirs(path)
            
        stats_per_symbol[ticker][interval]._trades.to_csv(
            os.path.join(path, "trades.csv"), index=False
        )

        stats_per_symbol[ticker][interval]._equity_curve.to_csv(
            os.path.join(path, "equity.csv")
        )
    
    