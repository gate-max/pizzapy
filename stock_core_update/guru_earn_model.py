
# STANDARD LIBRARIES
import sys; sys.path.append('..')
import json
from multiprocessing.managers import DictProxy
from typing import Any, Dict, List, Optional, Tuple


# THIRD PARTY LIBRARIES

from bs4 import BeautifulSoup
from bs4.element import ResultSet

from pandas.core.frame import DataFrame

import requests


# CUSTOM LIBRARIES
from batterypy.string.read import readf

# PROGRAM MODULES
from price_cap_model import get_html_soup, proxy_price_cap




def get_guru_earn_per_share(symbol: str, d: DictProxy={}) -> Optional[float]:
    '''
    REQUIRES: beautifulsoup4
    
    https://www.gurufocus.com/term/eps_nri/NVDA/EPS-without-NRI/
    
    '''
    earn_url: str = f'https://www.gurufocus.com/term/eps_nri/{symbol}/EPS-without-NRI/'
    earn_soup: BeautifulSoup = get_html_soup(earn_url)
    earn_soup_items: ResultSet = earn_soup.find_all('meta', attrs={'name': 'description'})
    content: str = '' if not earn_soup_items else earn_soup_items[0].get('content')
    earn_strlist: List[str] = content.split()
    earn_strlist2: List[str] = list(filter(lambda x: '$' in x, earn_strlist))
    earn_per_share: Optional[float] = readf(earn_strlist2[0][:-1]) if earn_strlist2 else None
    return earn_per_share



def tryget_guru_earn_per_share(symbol: str) -> Optional[float]:
    """ DEPENDS: get_guru_earn_per_share"""
    try:
        earn_per_share: Optional[float] =  get_guru_earn_per_share(symbol)
        return earn_per_share
    except requests.exceptions.RequestException as requests_error:
        print('tryget_guru_earn_per_share RequestException: ', requests_error)
        return None
    except Exception as error:
        print('tryget_guru_earn_per_share general Exception: ', error)
        return None



def proxy_guru_earn(symbol: str, proxy: DictProxy={}) -> DictProxy:
    '''DEPENDS: tryget_guru_earn_per_share > get_guru_earn_per_share'''
    earn_per_share: Optional[float]  = tryget_guru_earn_per_share(symbol)
    if earn_per_share is not None:
        proxy['earn_per_share'] = earn_per_share
    
    earnpc: Optional[float] = None if ('price' not in proxy or earn_per_share is None) \
        else round((earn_per_share / proxy['price'] * 100.0), 2)
    if earnpc is not None:
        proxy['earnpc'] = earnpc
    return proxy




if __name__ == '__main__':
    
    stock = input('which stock do you want to check? ')
    proxy = proxy_price_cap(stock)
    x = proxy_guru_earn(stock, proxy=proxy)
    print(x)
    