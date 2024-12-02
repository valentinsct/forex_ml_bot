import talib as ta
from backbone.trader_bot import TraderBot
from backtesting import Strategy
from backtesting.lib import crossover
import numpy as np
import MetaTrader5 as mt5
import numpy as np

from backbone.utils.general_purpose import calculate_units_size, diff_pips

np.seterr(divide='ignore')

class BbandsCross(Strategy):
    pip_value = None
    minimum_units = None
    maximum_units = None
    contract_volume = None
    opt_params = None
    
    risk = 1
    bbands_timeperiod = 50
    bband_std = 1.5
    sma_period = 200

    atr_multiplier = 4
    pip_value = 0.1

    def init(self):
        
        self.sma = self.I(
            ta.SMA, self.data.Close, timeperiod=self.sma_period
        )

        self.atr = self.I(ta.ATR, self.data.High, self.data.Low, self.data.Close)


    def next(self):
        actual_date = self.data.index[-1]
        
        if self.opt_params and actual_date in self.opt_params.keys():
            for k, v in self.opt_params[actual_date].items():
                setattr(self, k, v)
        
        self.upper_band, self.middle_band, self.lower_band = ta.BBANDS(
            self.data.Close, 
            timeperiod=self.bbands_timeperiod, 
            nbdevup=self.bband_std, 
            nbdevdn=self.bband_std
        )
        
        actual_close = self.data.Close[-1]
        
        if self.position:
            if self.position.is_long:
                if crossover(self.data.Close, self.middle_band):
                    self.position.close()

            if self.position.is_short:
                if crossover(self.middle_band, self.data.Close):
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
                    pip_value=self.pip_value,
                    maximum_lot=self.maximum_units,
                    minimum_lot=self.minimum_units
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
                    pip_value=self.pip_value,
                    maximum_lot=self.maximum_units,
                    minimum_lot=self.minimum_units
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
                if crossover(self.data.Close, self.middle_band):
                    trader.close_order(open_positions[-1])

            if open_positions[-1].type == mt5.ORDER_TYPE_SELL:
                if crossover(self.middle_band, self.data.Close):
                    trader.close_order(open_positions[-1])

        else:

            if crossover(self.data.Close, self.lower_band) and actual_close > self.sma[-1]:
                info_tick = trader.get_info_tick()
                price = info_tick.ask
                
                sl_price = price - self.atr_multiplier * self.atr[-1]
                
                pip_distance = diff_pips(
                    price, 
                    sl_price, 
                    pip_value=self.pip_value
                )
                
                units = calculate_units_size(
                    account_size=trader.equity, 
                    risk_percentage=self.risk, 
                    stop_loss_pips=pip_distance, 
                    pip_value=self.pip_value,
                    maximum_lot=self.maximum_units,
                    minimum_lot=self.minimum_units
                )
                
                lots = units / self.contract_volume

                trader.open_order(
                    type_='buy',
                    price=price,
                    size=lots, 
                    sl=sl_price
                )  
                
            if crossover(self.upper_band, self.data.Close) and actual_close < self.sma[-1]:
                info_tick = trader.get_info_tick()
                price = info_tick.bid
                
                sl_price = price + self.atr_multiplier * self.atr[-1]
                
                pip_distance = diff_pips(
                    price, 
                    sl_price, 
                    pip_value=self.pip_value
                )
                
                units = calculate_units_size(
                    account_size=trader.equity, 
                    risk_percentage=self.risk, 
                    stop_loss_pips=pip_distance, 
                    pip_value=self.pip_value,
                    maximum_lot=self.maximum_units,
                    minimum_lot=self.minimum_units
                )
                
                lots = units / self.contract_volume
                
                trader.open_order(
                    type_='sell',
                    price=price,
                    sl=sl_price,
                    size=lots
                )