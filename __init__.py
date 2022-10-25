import pandas as pd
from binance.client import Client
from typing import List
# Get historical data from binance

# client: current client used in api
# ticker: e.g. "BTCUSDC"
# frequency: Integer, number of frequency_unit to aggregate within one datapoint
# frequency_unit: minutes, hours, days ('m','h','d')
# start_ts: start date as pandas Timestamp 
# end_ts: start date as pandas Timestamp 


def get_klines(
    client: Client,
    symbol: str, 
    interval_length: int =1, 
    interval_unit: str = 'm',
    time_shift: int = 1,
    limit: int =1, 
    drop_columns: List[int]=[11], 
    date_columns: List[int]=[0,6], 
    column_names: List[str] =['OpenTime','Open','High','Low','Close','Volume','CloseTime','QuoteVolume','NumberOfTrades','ActiveBuyVolume', 'ActiveBuyQuoteVolume'],
    finished_klines: bool = True):
    '''
    get recent candlestick data

    Parameters
    ----------
    client: binance.client
        client of websocket to pull data from
    symbol: string
        trading pair
    interval_length: integer
        length of interval of individual candlestick
    interval_unit: string
        unit of interval
        Options:
            m: minutes
            h: hours
            d: days
    time_shift: integer
        number of hours time_shift to UTC+1
    limit: integer
        how many candles to return
    drop_columns: list(integer)
        column indices to drop
    date_columns: list(integer)
        column indices of date columns
    column_names: list(string)
        names of non-dropped columns
    finished_klines: Boolean
        True: Consider only finished candles (max 1 minute delay)
        False: Also consider building candles (live data)


    Returns
    -------
    df: pandas.DataFrame
        candlestick data for provided symbol with shape (limit, column_names)
    '''


    # Request new data from binance
    # If unavailable pass empty dataframe

    try:
        df = pd.DataFrame(client.get_klines(symbol=symbol, 
                            interval=str(interval_length)+interval_unit,
                            limit=limit+finished_klines)
                            )[:limit].drop(columns=drop_columns)
    except:
        df = pd.DataFrame(columns=column_names)
        print('Server Timeout!')

    df.columns = column_names
    df.iloc[:,date_columns]=df.iloc[:,date_columns].apply(pd.to_datetime,unit='ms')+pd.Timedelta(hours=time_shift)
    non_date_columns = [x for x in column_names if column_names.index(x) not in date_columns]
    df.loc[:,non_date_columns]=df.loc[:,non_date_columns].apply(pd.to_numeric)
    df['Symbol']=symbol

    return df


def bnc_get_recent_historical_klines(
    client: Client,
    ticker: str,
    frequency: int,
    frequency_unit: str,
    limit: int):
    '''
    get historical candlestick data

    Parameters
    ----------
    client: binance.client
        client of websocket to pull data from
    ticker: string
        trading pair
    frequency: integer
        length of interval of individual candlestick
    frequency_unit: string
        unit of interval
        Options:
            m: minutes
            h: hours
            d: days
    limit: int
        number of candles to receive


    Returns
    -------
    df: pandas.DataFrame
        candlestick data for provided symbol with shape (limit, column_names)
    '''
    df = pd.DataFrame(client.get_historical_klines(ticker, interval=str(frequency)+frequency_unit, limit=limit))
    
    # if no data is available return empty dataframe
    if df.empty:
        return df
    df = df.drop(columns=11)
    df[0] = pd.to_datetime(df[0],unit='ms')
    df[6] = pd.to_datetime(df[6],unit='ms')
    df[[1,2,3,4,5,7,8,9,10]]=df[[1,2,3,4,5,7,8,9,10]].apply(pd.to_numeric, errors='coerce')
    df.columns = ['OpenTime','Open','High','Low','Close','Volume','CloseTime','QuoteVolume','NumberOfTrades','ActiveBuyVolume',
                  'ActiveBuyQuoteVolume']
    return df