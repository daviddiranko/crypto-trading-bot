import pandas as pd
from typing import List, Any
from dotenv import load_dotenv
import os
import json

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


def binance_to_bybit(klines: List[List[Any]], topics: List[str]) -> List[str]:
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

    return messages
