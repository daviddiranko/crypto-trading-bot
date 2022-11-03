import pandas as pd
from typing import Dict, Any


def format_klines(msg: Dict[str, Any]):
    '''
    Format candlestick data received by bybit websocket

    Parameters
    ----------
    msg: Dict[str, Any]
        extracted json payload

    Returns
    -------
    df: Dict[str, Any]
        formatted json payload
    '''

    # extract candlestick data
    data = msg['data'][0]
    data['start'] = pd.to_datetime(data['start'], unit='s')
    data['end'] = pd.to_datetime(data['end'], unit='s')
    data['open'] = float(data['open'])
    data['close'] = float(data['close'])
    data['high'] = float(data['high'])
    data['low'] = float(data['low'])
    data['volume'] = float(data['volume'])
    data['turnover'] = float(data['turnover'])

    return data
