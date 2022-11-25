import pandas as pd
from typing import List, Any, Tuple, Dict
from dotenv import load_dotenv
import os
import json
from binance.client import Client

load_dotenv()

HIST_COLUMNS = eval(os.getenv('HIST_COLUMNS'))


def format_historical_klines(msg: List[List[Any]]) -> pd.DataFrame:
    '''
    extract historical candlestick data

    Parameters
    ----------
    msg: List[List[Any]]
        payload from binance as list of list of historical candlestick data
    Returns
    -------
    df: pandas.DataFrame
        formated candlestick data
    '''

    # load payload into dataframe
    df = pd.DataFrame(msg, columns=HIST_COLUMNS)

    # drop obsolete columns
    df = df.drop(columns=[
        'NumberOfTrades', 'ActiveBuyVolume', 'ActiveBuyQuoteVolume', 'ignore'
    ])

    # if no data is available return empty dataframe
    if df.empty:
        return df

    # perform type conversions
    df['start'] = pd.to_datetime(df['start'], unit='ms')
    df['end'] = pd.to_datetime(df['end'], unit='ms')
    df[['open', 'high', 'low', 'close', 'volume', 'turnover'
       ]] = df[['open', 'high', 'low', 'close', 'volume',
                'turnover']].apply(pd.to_numeric, errors='coerce')

    # round imestamps to seconds
    df[['start', 'end']] = df[['start',
                               'end']].apply(lambda x: x.dt.round(freq='s'))

    # set end timestamp as index
    df = df.set_index('end', drop=False)

    return df


def binance_to_bybit(klines: List[List[Any]],
                     topics: List[str]) -> Tuple[List[str], pd.DataFrame]:
    '''
    transform binance kline response to bybit websocket message for backtesting simulation.
    Parameters
    ----------
    klines: List[List[Any]]
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

    # format klines and add topics
    formatted_klines = format_historical_klines(klines)
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
                "turnover": kline['turnover'],
                "confirm": True,
                "cross_seq": 0,
                "timestamp": kline['end'].value
            }],
            "timestamp_e6": kline['end'].value
        }

        # jsonify message and append to messages
        messages.append(json.dumps(bybit_msg))

    return messages, formatted_klines


def create_simulation_data(session: Client, symbols: Dict[str,
                                                          str], start_str: str,
                           end_str: str) -> Tuple[List[List[Any]], List[str]]:
    '''
    Create simulation data.
    Pull all relevant candles from binance and add them to a single list.
    for each list index, add the bybit topic in another list

    Parameters
    ----------
    session: binance.client.Client
        http session to pull historical data
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
    klines: List[List[Any]]
        list of raw klines
    
    topics: List[str]
        list of respective websocket topics
    '''
    klines = []
    topics = []
    for symbol in symbols:
        ticker, interval = symbol.split('.')
        bnc_data = session.get_historical_klines(ticker,
                                                 start_str=start_str,
                                                 end_str=end_str,
                                                 interval=interval)
        klines.extend(bnc_data)
        topics.extend([symbols[symbol]] * len(bnc_data))

    return klines, topics
