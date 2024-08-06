from importlib import import_module
import itertools
from backbone.enums import OperationType
# from backbone.order import Order
from datetime import datetime
from collections import namedtuple
import os
import MetaTrader5 as mt5


def get_session(date: datetime):
    return True
    # hour = date.hour

    # if 7 <= hour <= 19:
    #     return True
    
    # return False


def load_function(dotpath: str):
    """Carga una función desde un módulo."""
    module_, func = dotpath.rsplit(".", maxsplit=1)
    m = import_module(module_)
    return getattr(m, func)

def get_parameter_combinations(
        models, 
        train_window, 
        train_period, 
        trading_strategies, 
        stop_loss_strategies, 
        take_profit_strategies, 
        periods_forward_target, 
        stop_loses_in_pips, 
        risk_reward_ratios,
        intervals,
        trades_to_increment_risks,
        leverages,
        risk_percentages
    ):

    parameter_combinations = []
    if None in models:
        parameter_combinations += list(itertools.product(
            [None], 
            [0], 
            [0], 
            trading_strategies, 
            stop_loss_strategies, 
            take_profit_strategies, 
            periods_forward_target,
            stop_loses_in_pips, 
            risk_reward_ratios ,
            intervals,
            trades_to_increment_risks,
            leverages,
            risk_percentages
        ))

        models.remove(None)
    
    parameter_combinations += list(itertools.product(
        models, 
        train_window, 
        train_period, 
        trading_strategies, 
        stop_loss_strategies, 
        take_profit_strategies, 
        periods_forward_target,
        stop_loses_in_pips, 
        risk_reward_ratios ,
        intervals,
        trades_to_increment_risks,
        leverages,
        risk_percentages
    ))

    return parameter_combinations

# def from_mt_order_to_order(mt_order) -> Order:
#     order = Order(
#         id=mt_order.ticket, 
#         order_type=OperationType.BUY if mt_order.type == 0 else OperationType.SELL, 
#         ticker=mt_order.symbol, 
#         open_time=datetime.fromtimestamp(mt_order.time),
#         open_price=mt_order.price_open,
#         units=mt_order.volume, #yo tengo unidades y son lotes
#         stop_loss=mt_order.sl, 
#         take_profit=mt_order.tp
#     )

#     return order

# def from_order_to_mt_order(order:Order) -> dict:
#     MtOrder = namedtuple('MtOrder', [
#         'ticket','type', 'symbol', 'time','price_open','volume', 'sl', 'tp' 
#     ])

#     mt_order = MtOrder(
#         order.id,
#         0 if order.operation_type == OperationType.BUY else 1, 
#         order.ticker, 
#         order.open_time,
#         order.open_price,
#         order.units, 
#         order.stop_loss, 
#         order.take_profit 
#     )

#     return mt_order

# def write_in_logs(path, time, comment, order):
#     with open(os.path.join(path), 'a') as file:
#         file.write(f'\n {time} \n')

#         file.write(f'{"="*32 + comment + "="*32} \n')
        
#         content = map_order_to_str(order)

#         file.write(f'{content}\n')
        
#         file.write('='*32)


# def map_order_to_str(order:dict):
#     message = '\n'
#     for key, value in order.items():
#         message += f'{key}: {value} \n'
    
#     return message

def diff_pips(price1, price2, pip_value, absolute=True):
    if absolute:
        difference = abs(price1 - price2)
    else:
        difference = price1 - price2
    pips = difference / pip_value
    return pips