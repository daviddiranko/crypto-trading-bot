import warnings

warnings.simplefilter(action='ignore', category=FutureWarning)
import pandas as pd
from typing import List, Any, Tuple, Dict
from dotenv import load_dotenv
import os
import json

def klines_to_bybit(klines: pd.DataFrame,
                     topics: List[str]) -> Tuple[List[str], pd.DataFrame]:
    '''
    transform klines in dataframe to bybit websocket message for backtesting simulation.
    Parameters
    ----------
    klines: pandas.DataFrame
        historical binance candlesticks
    topics: List[str]
        respective bybit topics to simulate websocket responses
    
    Returns
    -------
    messages: List[str]
        list of json response bodys (formatted as string), analog to bybit websocket messages
    formatted_klines: pandas.DataFrame
        formatted klines
    '''
    # initialize empty list of messages
    messages = []

    # add topics to klines
    # formatted_klines = format_historical_klines(klines)
    formatted_klines = klines.copy()
    formatted_klines['topic'] = topics

    formatted_klines = formatted_klines.reset_index(drop=True).set_index(
        ['end', 'topic'], drop=False)

    # sort klines by index
    formatted_klines = formatted_klines.sort_index()

    # iterate through all lines and format candles
    for idx in formatted_klines.index:
        kline = formatted_klines.loc[idx]

        # format candle to dict
        bybit_msg = {
            "topic": kline['topic'],
            "data": [{
                "start": kline['start'].value / 1000000000,
                "end": kline['end'].value / 1000000000,
                "period": "1",
                "open": kline['open'],
                "close": kline['close'],
                "high": kline['high'],
                "low": kline['low'],
                "volume": kline['volume'],
                "turnover": kline['volume']*(kline['close']+kline['open'])/2,
                "confirm": True,
                "cross_seq": 0,
                "timestamp": kline['end'].value
            }],
            "timestamp_e6": kline['end'].value
        }

        # jsonify message and append to messages
        messages.append(json.dumps(bybit_msg))

    return messages, formatted_klines


def create_simulation_data(symbols: Dict[str, str], start_str: str,
                           end_str: str) -> Tuple[List[List[Any]], List[str]]:
    '''
    Create simulation data.
    Pull all relevant candles from binance and add them to a single list.
    for each list index, add the bybit topic in another list

    Parameters
    ----------
    symbols: Dict[str, str]
        dictionary of relevant symbols for backtesting
        symbols for backtesting
        keys have format binance_ticker.binacne_interval and values are coresponding bybit ws topics.
    start_str: str
        start of simulation in format yyyy-mm-dd hh-mm-ss
    end_str: str
        end of simulation in format yyyy-mm-dd hh-mm-ss

    Returns
    --------
    klines: pandas.DataFrame
        dataframe of all candles
    
    topics: List[str]
        list of respective websocket topics
    '''

    # initialize empty dataframe and topics
    klines = pd.DataFrame(columns=['start', 'open', 'high', 'low', 'close', 'volume','end'])
    topics = []
    
    # for every relevant symbol import dataset from .txt file and add to list
    for symbol in symbols:
        ticker, interval = symbol.split('.')
        interval_length = int(interval[:-1])
        interval_unit = interval[-1]

        # extend data by one interval to close trades in the last timestamp
        actual_end_str = str(pd.Timestamp(end_str) + pd.Timedelta(interval))

        # import kline data and formatting to fit requirements of market data object
        quotes = pd.read_csv('src/backtest/data/{}_{}.txt'.format(ticker,interval), names=['start', 'open', 'high', 'low', 'close', 'volume'], parse_dates=[0])
        quotes['end']=quotes['start']+pd.Timedelta(interval_length,unit=interval_unit)
        quotes = quotes.set_index('end',drop=False)
        quotes = quotes.loc[quotes.index>=pd.Timestamp(start_str)]
        quotes = quotes.loc[quotes.index<=pd.Timestamp(actual_end_str)]

        klines = pd.concat([klines, quotes])
        topics.extend([symbols[symbol]] * len(quotes))

    return klines, topics
