from importlib import import_module
import itertools

def load_function(dotpath: str):
    """Carga una función desde un módulo."""
    module_, func = dotpath.rsplit(".", maxsplit=1)
    m = import_module(module_)
    return getattr(m, func)



screener_columns = [
    'industry',
    'sector',
    'trailingPE',
    'forwardPE',
    'pegRatio',
    'trailingPegRatio'
    'beta',
    'totalDebt',
    'quickRatio',
    'currentRatio',
    'totalRevenue',
    'debtToEquity',
    'revenuePerShare',
    'returnOnAssets',
    'returnOnEquity',
    'freeCashflow',
    'operatingCashflow',
    'earningsGrowth',
    'revenueGrowth',
    'bid',
    'ask',
    'marketCap',
    'twoHundredDayAverage',
    'recommendationKey',
    'numberOfAnalystOpinions',
    'symbol',
]


def calculate_units_size(
    account_size, 
    risk_percentage, 
    stop_loss_pips, 
    pip_value, 
    maximum_units, 
    minimum_units,
    return_lots=False,
    contract_volume=None,
    actual_price=None,
    trade_tick_value_loss=None
    
    ):
    
    account_currency_risk = account_size * (risk_percentage / 100)
    lots = account_currency_risk / (trade_tick_value_loss * stop_loss_pips)
   
    if return_lots:
        lots = int(lots * 100) / 100
        return lots    

    units = lots * contract_volume
    units = minimum_units if units < minimum_units else units
    units = maximum_units if units > maximum_units else units

    units = max(units, minimum_units)
    units = min(units, maximum_units)

    return units

def diff_pips(price1, price2, pip_value, absolute=True):
    if absolute:
        difference = abs(price1 - price2)
    else:
        difference = price1 - price2
    pips = difference / pip_value
    
    return pips

def transformar_a_uno(numero):
    # Inicializar contador de decimales
    decimales = 0
    while numero != int(numero):
        numero *= 10
        decimales += 1

    return 1 / (10 ** decimales)
