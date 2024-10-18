from datetime import datetime, timedelta
import pytz
import talib as ta
from backbone.trader_bot import TraderBot
from backtesting import Strategy, Backtest
from backtesting.lib import crossover
import numpy as np
import MetaTrader5 as mt5
import numpy as np

from backbone.utils.general_purpose import calculate_units_size, diff_pips

np.seterr(divide='ignore')

def  optim_func(series):
    return (series['Return [%]'] /  (1 + (-1*series['Max. Drawdown [%]']))) * np.log(1 + series['# Trades'])

class BbandsCross(Strategy):
    risk = 1
    bbands_timeperiod = 50
    bband_std = 1.5
    sma_period = 200

    atr_multiplier = 1.5
    pip_value = 0.1

    def init(self):
        
        self.sma = self.I(
            ta.SMA, self.data.Close, timeperiod=self.sma_period
        )

        self.upper_band, self.middle_band, self.lower_band = self.I(
            ta.BBANDS, self.data.Close, 
            timeperiod=self.bbands_timeperiod, 
            nbdevup=self.bband_std, 
            nbdevdn=self.bband_std
        )

        self.atr = self.I(ta.ATR, self.data.High, self.data.Low, self.data.Close)


    def next(self):
        actual_close = self.data.Close[-1]
        
        if self.position:
            if self.position.is_long:
                if crossover(self.data.Close, self.middle_band) or actual_close <= self.sma[-1]:
                    self.position.close()

            if self.position.is_short:
                if crossover(self.middle_band, self.data.Close) or actual_close >= self.sma[-1]:
                    self.position.close()

        else:

            if crossover(self.data.Close, self.lower_band) and actual_close > self.sma[-1]:
                sl_price = self.data.Close[-1] - self.atr_multiplier * self.atr[-1]
                
                pip_distance = diff_pips(
                    self.data.Close[-1], 
                    sl_price, 
                    pip_value=self.pip_value
                )
                
                units = calculate_units_size(
                    account_size=self.equity, 
                    risk_percentage=self.risk, 
                    stop_loss_pips=pip_distance, 
                    pip_value=self.pip_value
                )
                
                self.buy(
                    size=units,
                    sl=sl_price
                )
                
            if crossover(self.upper_band, self.data.Close) and actual_close < self.sma[-1]:
                sl_price = self.data.Close[-1] + self.atr_multiplier * self.atr[-1]
                
                pip_distance = diff_pips(
                    self.data.Close[-1], 
                    sl_price, 
                    pip_value=self.pip_value
                )
                
                units = calculate_units_size(
                    account_size=self.equity, 
                    risk_percentage=self.risk, 
                    stop_loss_pips=pip_distance, 
                    pip_value=self.pip_value
                )
                
                self.sell(
                    size=units,
                    sl=sl_price
                )
                            
    def next_live(self, trader:TraderBot):
        actual_close = self.data.Close[-1]
        
        open_positions = trader.get_open_positions()
        
        if open_positions:
            if open_positions[-1].type == mt5.ORDER_TYPE_BUY:
                if crossover(self.data.Close, self.middle_band) or actual_close <= self.sma[-1]:
                    trader.close_order(open_positions[-1])

            if open_positions[-1].type == mt5.ORDER_TYPE_SELL:
                if crossover(self.middle_band, self.data.Close) or actual_close >= self.sma[-1]:
                    trader.close_order(open_positions[-1])

        else:

            if crossover(self.data.Close, self.lower_band) and actual_close > self.sma[-1]:
                info_tick = trader.get_info_tick()
                price = info_tick.ask
                
                capital_to_risk = trader.equity * self.risk / 100
                units = capital_to_risk / price
                
                lots = round(units / trader.contract_volume, 2)
                
                trader.open_order(
                    type_='buy',
                    price=price,
                    size=lots
                )             
                   
            if crossover(self.upper_band, self.data.Close) and actual_close < self.sma[-1]:
                info_tick = trader.get_info_tick()
                price = info_tick.bid
                
                capital_to_risk = trader.equity * self.risk / 100
                units = capital_to_risk / price
                
                lots = round(units / trader.contract_volume, 2)
                
                trader.open_order(
                    type_='sell',
                    price=price,
                    size=lots
                )

class BbandsCrossTrader(TraderBot):
    
    def __init__(self, ticker, timeframe, contract_volume, creds, opt_params, wfo_params):
        name = f'BBandsCross_{ticker}_{timeframe}'
        
        self.trader = TraderBot(
            name=name,
            ticker=ticker, 
            timeframe=timeframe, 
            creds=creds,
            contract_volume=contract_volume
        )
        
        self.opt_params = opt_params
        self.wfo_params = wfo_params
        self.opt_params['maximize'] = optim_func
        self.strategy = BbandsCross

    def run(self):
        warmup_bars = self.wfo_params['warmup_bars']
        look_back_bars = self.wfo_params['look_back_bars']

        timezone = pytz.timezone("Etc/UTC")
        now = datetime.now(tz=timezone)
        date_from = now - timedelta(hours=look_back_bars) - timedelta(hours=warmup_bars) 
        
        print(f'excecuting run {self.trader.name} at {now}')
        
        df = self.trader.get_data(
            date_from=date_from, 
            date_to=now,
        )

        df.index = df.index.tz_localize('UTC').tz_convert('UTC')

        bt_train = Backtest(
            df, 
            self.strategy,
            commission=7e-4,
            cash=100_000, 
            margin=1/30
        )
        
        stats_training = bt_train.optimize(
            **self.opt_params
        )
        
        bt = Backtest(
            df, 
            self.strategy,
            commission=7e-4,
            cash=100_000, 
            margin=1/30
        )
        
        opt_params = {param: getattr(stats_training._strategy, param) for param in self.opt_params.keys() if param != 'maximize'}

        stats = bt.run(
            **opt_params
        )

        bt_train._results._strategy.next_live(trader=self.trader)   
