from datetime import datetime, timedelta
import pytz
import talib as ta
from backbone.trader_bot import TraderBot
from backtesting import Strategy, Backtest
from backtesting.lib import crossover
import numpy as np
import MetaTrader5 as mt5
import numpy as np

np.seterr(divide='ignore')

def  optim_func(series):
    return (series['Return [%]'] /  (1 + (-1*series['Max. Drawdown [%]']))) * np.log(1 + series['# Trades'])

class BbandsCross(Strategy):
    risk=10
    bbands_timeperiod = 50
    bband_std = 1.5
    sma_period = 200

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
                self.buy(size=self.risk / 100)
                
            if crossover(self.upper_band, self.data.Close) and actual_close < self.sma[-1]:
                self.sell(size=self.risk / 100)
                            
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
                
                trader.open_order(
                    type_='buy',
                    price=price
                )             
                   
            if crossover(self.upper_band, self.data.Close) and actual_close < self.sma[-1]:
                info_tick = trader.get_info_tick()
                price = info_tick.bid
                
                trader.open_order(
                    type_='sell',
                    price=price
                )


class BbandsCrossTrader(TraderBot):
    
    def __init__(self, ticker, lot, timeframe, creds, opt_params, wfo_params):
        name = f'BBandsCross_{ticker}_{timeframe}'
        
        self.trader = TraderBot(
            name=name,
            ticker=ticker, 
            lot=lot,
            timeframe=timeframe, 
            creds=creds
        )
        
        self.opt_params = opt_params
        self.wfo_params = wfo_params
        self.opt_params['maximize'] = optim_func

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
            BbandsCross,
            commission=7e-4,
            cash=100_000, 
            margin=1/30
        )
        
        stats_training = bt_train.optimize(
            **self.opt_params
        )
        
        bt = Backtest(
            df, 
            BbandsCross,
            commission=7e-4,
            cash=100_000, 
            margin=1/30
        )
        
        opt_params = {param: getattr(stats_training._strategy, param) for param in self.opt_params.keys() if param != 'maximize'}

        stats = bt.run(
            **opt_params
        )

        bt_train._results._strategy.next_live(trader=self.trader)   
