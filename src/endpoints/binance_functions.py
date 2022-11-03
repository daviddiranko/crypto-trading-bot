import pandas as pd
import json
from typing import List, Any
from dotenv import load_dotenv
import os

load_dotenv()

HIST_COLUMNS = eval(os.getenv('HIST_COLUMNS'))


def format_historical_klines(msg: List[List[Any]]):
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
