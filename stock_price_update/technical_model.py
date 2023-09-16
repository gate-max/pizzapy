"""

The aim of this module is to get the result of get_technical_proxies(), all earlier functions are helper of get_technical_proxies().


"""

# STANDARD LIBS
import sys; sys.path.append('..')
from datetime import date, datetime, timezone
from functools import partial
from itertools import dropwhile, repeat
import io
from multiprocessing import Pool
from multiprocessing.managers import DictProxy, SyncManager
import os
from timeit import default_timer
from typing import Any, Dict, List, Tuple, Optional

import shutil
import urllib


# THIRD PARTY LIBS
import pandas
from pandas import DataFrame
import requests


# CUSTOM LIBS
from batterypy.functional.list import first, grab
from batterypy.time.cal import add_trading_days, date_range, tdate_range, tdate_length, date_length,  get_trading_day_utc, is_weekly_close
from batterypy.number.format import round0, round1, round2, round4

from dimsumpy.finance.technical import ema, quantile, deltas, convert_to_changes, calculate_rsi, steep
from dimsumpy.web.crawler import get_urllib_text, get_csv_dataframe

# PROGRAM MODULES

from database_update.postgres_connection_model import execute_pandas_read
from general_update.general_model import initialize_proxy

















def get_prices_rsi(pairs: List[Tuple[date, float]], td: date) -> Tuple[List[Tuple[date, float]], List[float], float, float]:
    """
    * INDEPENDENT *
    IMPORTS: is_weekly_close(), calculate_rsi()
    USED BY: get_technical_values()
    """

    # latest dates tuples are placed in the front in pairs
    td_pairs: List[Tuple[date, float]] = list(dropwhile(lambda x: x[0] > td, pairs))    # drop all dates exceeding target date   
    # td's closing price will the the first element, prices are placed from td to the past
    td_prices: List[float] = [adjclose for (_, adjclose) in td_pairs]   
    weekly_prices: List[float] = td_prices[:1] + [price for (day, price) in td_pairs[1:] if is_weekly_close(day)]
    rsi = calculate_rsi(14, td_prices)
    weekly_rsi = calculate_rsi(14, weekly_prices)
    return td_pairs, td_prices, rsi, weekly_rsi    



def get_specific_prices(prices: List[float]) -> Tuple[Optional[float], Optional[float], Optional[float], Optional[float], Optional[float]]:
    """
    * INDEPENDENT *
    IMPORTS: first(), grab()
    USED BY: get_technical_values()
    """
    price = first(prices)
    p20 = grab(prices, 20)
    p50 = grab(prices, 50)
    p125 = grab(prices, 125)
    p200 = grab(prices, 200)
    return price, p20, p50, p125, p200




def calculate_target_prices(p20: Optional[float], p50: Optional[float], prices: List[float]) -> Tuple[float, float, float, float, Optional[float], Optional[float], Optional[float], Optional[float]]:
    """
    * INDEPENDENT *
    IMPORTS: conver_to_changes(), quantile()
    USED BY: get_technical_values()
    """
    
    list_of_20_day_change = convert_to_changes(20, prices[:421])
    list_of_50_day_change = convert_to_changes(50, prices[:451])
    increase_20 = quantile(0.98, list_of_20_day_change)
    decrease_20 = quantile(0.02, list_of_20_day_change)
    increase_50 = quantile(0.98, list_of_50_day_change)
    decrease_50 = quantile(0.02, list_of_50_day_change)
    best_20 = p20 * (1.0 + increase_20) if p20 else None
    worst_20 = p20 * (1.0 + decrease_20) if p20 else None
    best_50 = p50 * (1.0 + increase_50) if p50 else None
    worst_50 = p50 * (1.0 + decrease_50) if p50 else None
    return increase_20, decrease_20, increase_50, decrease_50, best_20, worst_20, best_50, worst_50




def calculate_steep(prices: List[float]) -> Tuple[float, float]:
    """
    * INDEPENDENT *
    IMPORTS: ema(), steep()
    USED BY: get_technical_values()
    """

    steep_20 = steep(20, prices)
    steep_50 = steep(50, prices)
    return steep_20, steep_50


def check_top_bottom(pairs: List[Tuple[date, float]], td_price: Optional[float], td: date) -> Tuple[Optional[bool],Optional[bool]]:
    """
    * INDEPENDENT *
    IMPORTS: add_trading_days()
    USED BY: get_technical_values()

    the length is sometime 39.
    """
    plus_minus_20_prices = [price for (day, price) in pairs if add_trading_days(td, -21) < day < add_trading_days(td, 21) and day != td]

    length: int = len(plus_minus_20_prices)

    is_top: Optional[bool] = all(td_price > price for price in plus_minus_20_prices) if length > 38 and td_price else None
    
    is_bottom: Optional[bool] = all(td_price < price for price in plus_minus_20_prices) if length > 38 and td_price else None
    return is_top, is_bottom



def get_technical_values(pairs: List[Tuple[date, float]], td: date) -> Any:
    """
    DEPENDS ON: get_prices_rsi(), get_specific_prices(), calculate_target_prices(), calculate_steep(), check_top_bottom()
    IMPORTS: round1(), round2(), round4()
    USED BY: make_technical_proxy()

    pairs argument is generated by get_td_adjclose()
    
    I must place td at last because it is the iterable argument in pool.map()
    """
    td_pairs, td_prices, rsi, weekly_rsi = get_prices_rsi(pairs, td)
    
    td_price, p20, p50, p125, p200 = get_specific_prices(td_prices)

    increase_20, decrease_20, increase_50, decrease_50, best_20, worst_20, best_50, worst_50 = calculate_target_prices(p20, p50, td_prices)

    steep_20, steep_50 = calculate_steep(td_prices)
    is_top, is_bottom = check_top_bottom(pairs, td_price, td)
    
    technical_values = round2(td_price), round2(p20), round2(p50), round2(p125), round2(p200), round4(rsi), round4(weekly_rsi), round2(increase_20), round2(decrease_20), round2(increase_50), round2(decrease_50), round1(best_20), round1(worst_20), round1(best_50), round1(worst_50), round2(steep_20), round2(steep_50), is_top, is_bottom
    
    return technical_values




def make_technical_proxy(pairs: List[Tuple[date, float]], SYMBOL: str, td: date) -> Dict:
    """
    DEPENDS ON: get_technical_values()
    IMPORTS: datetime
    USED BY: get_technical_proxies()
    """
    
    price, p20, p50, p125, p200, rsi, weekly_rsi, increase_20, decrease_20, increase_50, decrease_50, best_20, worst_20, best_50, worst_50, steep_20, steep_50, is_top, is_bottom = get_technical_values(pairs, td)
    
    proxy: Dict = {}
    proxy['symbol'] = SYMBOL
    proxy['td'] = td
    proxy['t'] = datetime.now().replace(second=0, microsecond=0)
    
    proxy['price'] = price
    proxy['p20'] = p20
    proxy['p50'] = p50
    proxy['p125'] = p125
    proxy['p200'] = p200

    proxy['rsi'] = rsi
    proxy['weekly_rsi'] = weekly_rsi
    
    proxy['increase_20'] = increase_20
    proxy['decrease_20'] = decrease_20
    proxy['increase_50'] = increase_50
    proxy['decrease_50'] = decrease_50
    proxy['best_20'] = best_20
    proxy['worst_20'] = worst_20
    proxy['best_50'] = best_50
    proxy['worst_50'] = worst_50
    
    proxy['steep_20'] = steep_20
    proxy['steep_50'] = steep_50 
    proxy['is_top'] = is_top
    proxy['is_bottom'] = is_bottom
    
    return proxy



def get_td_adjclose(FROM: date, TO: date, symbol: str) -> Tuple[List[Tuple[date, float]], bool]:
    """
    IMPORTS: execute_pandas_read()
    USED BY: tech_upsert_1s()
    
    Get price data from my own database table.

    The resuling list will have latest dates placed at the front as it is DESC.
    """
    earlier_from = add_trading_days(FROM, -1000)
    later_to = add_trading_days(TO, 20)

    sql = f"SELECT td, adj_close FROM stock_price WHERE symbol = '{symbol}' AND td >= '{earlier_from.isoformat()}' AND td <= '{later_to.isoformat()}' ORDER BY td DESC"
    df: DataFrame = execute_pandas_read(sql) # no error for empty result
    td_adjclose_pairs: List[Any] = [tuple(x) for x in df.values] # List of 2-tuples
    
    pairs_length = len(td_adjclose_pairs)
    last_trading_day = get_trading_day_utc()
    theory_len = tdate_length(earlier_from, min(last_trading_day, later_to))
    valid_length = (theory_len - pairs_length) < 3

    return td_adjclose_pairs, valid_length




def get_technical_proxies(FROM: date, TO: date, SYMBOL: str) -> List[Any]:
    """
    DEPENDS ON: get_td_adjclose(), make_technical_proxy()
    IMPORTS: os, partial()
    do not use kwargs in partial()
    """
    td_adjclose_pairs, valid_length = get_td_adjclose(FROM, TO, SYMBOL)
    
    if valid_length:
        from_to_trading_dates: List[date] = [day for (day, _) in td_adjclose_pairs if FROM <= day <= TO]
        with Pool(os.cpu_count()) as pool:
            proxies: List[Any] = pool.map(partial(make_technical_proxy, td_adjclose_pairs, SYMBOL), from_to_trading_dates) 
        return proxies
    else:
        return []
        





def test():
    FROM = date(2023, 6, 7)
    TO = date(2023, 6, 10)
    #pairs = get_td_adjclose(FROM, TO, 'AMD')
    x = get_technical_proxies(FROM, TO, 'AMD')
    print(x)


if __name__ == '__main__':
    test()