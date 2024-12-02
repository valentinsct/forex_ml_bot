import pandas as pd
import MetaTrader5 as mt5
import telebot
from datetime import datetime, timedelta
from backtesting import Backtest
import pytz
from backbone.utils.wfo_utils import get_scaled_symbol_metadata, optimization_function

time_frames = {
    "M1": mt5.TIMEFRAME_M1,
    "M2": mt5.TIMEFRAME_M2,
    "M3": mt5.TIMEFRAME_M3,
    "M4": mt5.TIMEFRAME_M4,
    "M5": mt5.TIMEFRAME_M5,
    "M10": mt5.TIMEFRAME_M10,
    "M12": mt5.TIMEFRAME_M12,
    "M15": mt5.TIMEFRAME_M15,
    "M20": mt5.TIMEFRAME_M20,
    "M30": mt5.TIMEFRAME_M30,
    "H1": mt5.TIMEFRAME_H1,
    "H2": mt5.TIMEFRAME_H2,
    "H3": mt5.TIMEFRAME_H3,
    "H4": mt5.TIMEFRAME_H4,
    "H6": mt5.TIMEFRAME_H6,
    "H8": mt5.TIMEFRAME_H8,
    "H12": mt5.TIMEFRAME_H12,
    "D1": mt5.TIMEFRAME_D1,
    "W1": mt5.TIMEFRAME_W1,
    "MN1": mt5.TIMEFRAME_MN1,
}

order_tpyes = {
    "buy": mt5.ORDER_TYPE_BUY,
    "sell": mt5.ORDER_TYPE_SELL,
    "buy_limit": mt5.ORDER_TYPE_BUY_LIMIT,
    "sell_limit": mt5.ORDER_TYPE_SELL_LIMIT,
}

opposite_order_tpyes = {
    mt5.ORDER_TYPE_BUY: mt5.ORDER_TYPE_SELL,
    mt5.ORDER_TYPE_SELL: mt5.ORDER_TYPE_BUY,
}


class TraderBot:

    def __init__(
        self, name:str, ticker:str, timeframe:str, creds: dict, opt_params:dict, wfo_params:dict, strategy
    ):
        if not mt5.initialize():
            print("initialize() failed, error code =", mt5.last_error())
            quit()
            
        self.name = f"{name}_{ticker}_{timeframe}"
        
        bot_token = creds["telegram_bot_token"]
        chat_id = creds["telegram_chat_id"]
        server = creds["server"]
        account = creds["account"]
        pw = creds["pw"]

        self.mt5 = mt5
        self.bot = telebot.TeleBot(bot_token)
        self.chat_id = chat_id
        self.ticker = ticker
        self.timeframe = timeframe

        self.opt_params = opt_params
        self.wfo_params = wfo_params
        self.strategy = strategy

        authorized = self.mt5.login(server=server, login=account, password=pw)

        if authorized:
            account_info_dict = self.mt5.account_info()._asdict()
            for prop in account_info_dict:
                print("  {}={}".format(prop, account_info_dict[prop]))
        else:
            print(
                "failed to connect at account #{}, error code: {}".format(
                    account, mt5.last_error()
                )
            )
        self.equity = account_info_dict["equity"]

        (
            self.scaled_pip_value,
            self.scaled_minimum_lot,
            self.scaled_maximum_lot,
            self.scaled_contract_volume,
            self.minimum_fraction,
            self.trade_tick_value_loss,
        ) = get_scaled_symbol_metadata(ticker, metatrader=self.mt5)

        self.opt_params["minimum_lot"] = [self.scaled_minimum_lot]
        self.opt_params["maximum_lot"] = [self.scaled_maximum_lot]
        self.opt_params["pip_value"] = [self.scaled_pip_value]
        self.opt_params["contract_volume"] = [self.scaled_contract_volume]
        self.opt_params["trade_tick_value_loss"] = [self.trade_tick_value_loss]

        self.opt_params["maximize"] = optimization_function
        

    def get_data(self, date_from, date_to):
        rates = self.mt5.copy_rates_range(
            self.ticker, time_frames[self.timeframe], date_from, date_to
        )

        historical_prices = pd.DataFrame(rates)
        historical_prices["time"] = pd.to_datetime(historical_prices["time"], unit="s")

        historical_prices = historical_prices.rename(
            columns={
                "time": "Date",
                "open": "Open",
                "high": "High",
                "low": "Low",
                "close": "Close",
                "tick_volume": "Volume",
            }
        ).set_index("Date")

        return historical_prices

    def get_open_positions(self):
        positions = self.mt5.positions_get(symbol=self.ticker)
        positions = [
            position for position in positions if position.comment == self.name
        ]

        return positions

    def open_order(self, type_, price=None, sl=None, tp=None, size=None):
        symbol_info = self.mt5.symbol_info(self.ticker)
        if symbol_info is None:
            print(self.ticker, "not found, can not call order_check()")
        # if the symbol is unavailable in MarketWatch, add it

        if not symbol_info.visible:
            print(self.ticker, "is not visible, trying to switch on")
            if not self.mt5.symbol_select(self.ticker, True):
                print("symbol_select({}}) failed, exit", self.ticker)
        mt5_type = order_tpyes[type_]

        action = None
        action = (
            self.mt5.TRADE_ACTION_PENDING
            if mt5_type
            in [self.mt5.ORDER_TYPE_BUY_LIMIT, self.mt5.ORDER_TYPE_SELL_LIMIT]
            else self.mt5.TRADE_ACTION_DEAL
        )
        
        request = {
            "action": action,
            "symbol": self.ticker,
            "volume": size,
            "type": mt5_type,
            "price": price,
            "magic": 234000,
            "comment": f"{self.name}",
            "type_time": self.mt5.ORDER_TIME_GTC,
            "type_filling": self.mt5.ORDER_FILLING_FOK,
        }
        
        if sl:
            request['sl'] = sl
        
        if tp:
            request['tp'] = tp
       
        result_send = self.mt5.order_send(request)

        if not result_send or result_send.retcode != self.mt5.TRADE_RETCODE_DONE:
            message = f"fallo al abrir orden en {self.name}, retcode={result_send.retcode}, comment {result_send.comment}"
            print(message)
            self.bot.send_message(chat_id=self.chat_id, text=message)
        else:
            message = f"Se abrio una nueva orden: {self.name}, lot: {size}, price: {price}. Codigo: {result_send.retcode}"
            print(message)
            self.bot.send_message(chat_id=self.chat_id, text=message)

    def close_order(self, position):
        close_position_type = opposite_order_tpyes[position.type]

        if close_position_type == order_tpyes["buy"] or order_tpyes["buy_limit"]:
            price = self.mt5.symbol_info_tick(position.symbol).ask
        else:
            price = self.mt5.symbol_info_tick(position.symbol).bid
        request = {
            "action": self.mt5.TRADE_ACTION_DEAL,
            "symbol": position.symbol,
            "volume": position.volume,
            "type": close_position_type,
            "position": position.ticket,
            "price": price,
            "magic": 234000,
            "comment": f"{self.name} close",
            "type_time": self.mt5.ORDER_TIME_GTC,
            "type_filling": self.mt5.ORDER_FILLING_FOK,
        }

        result = self.mt5.order_send(request)

        if result.retcode != self.mt5.TRADE_RETCODE_DONE:
            message = f"fallo al cerrar orden en {self.name}, retcode: {result.retcode}"
            print(message)
            self.bot.send_message(chat_id=self.chat_id, text=message)
        else:
            message = f"Orden cerrada: {self.name} closed, {result}"
            print(message)
            self.bot.send_message(chat_id=self.chat_id, text=message)

    def get_info_tick(self):
        info_tick = self.mt5.symbol_info_tick(self.ticker)
        return info_tick

    def run(self):
        
        warmup_bars = self.wfo_params["warmup_bars"]
        look_back_bars = self.wfo_params["look_back_bars"]

        timezone = pytz.timezone("Etc/UTC")
        now = datetime.now(tz=timezone)
        date_from = now - timedelta(hours=look_back_bars) - timedelta(hours=warmup_bars)

        print(f"excecuting run {self.name} at {now}")

        df = self.get_data(
            date_from=date_from,
            date_to=now,
        )

        df.loc[:, ["Open", "High", "Low", "Close"]] = (
            df.loc[:, ["Open", "High", "Low", "Close"]] * self.minimum_fraction
        )

        df.index = df.index.tz_localize("UTC").tz_convert("UTC")

        symbol_info = self.mt5.symbol_info_tick(self.ticker)
        avg_price = (symbol_info.bid + symbol_info.ask) / 2
        spread = symbol_info.ask - symbol_info.bid
        commission = round(spread / avg_price, 5)
        
        bt_train = Backtest(
            df, self.strategy, commission=commission, cash=15_000, margin=1 / 30
        )

        stats_training = bt_train.optimize(**self.opt_params)

        opt_params = {
            param: getattr(stats_training._strategy, param)
            for param in self.opt_params.keys()
            if param != "maximize"
        }

        bt = Backtest(df, self.strategy, commission=commission, cash=15_000, margin=1 / 30)
        _ = bt.run(**opt_params)
            
        bt._results._strategy.next_live(trader=self)
        