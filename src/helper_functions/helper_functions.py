from typing import List, Any
from src.endpoints.binance_functions import format_historical_klines
import json


def binance_to_bybit(klines: List[List[Any]], topic: str) -> List[str]:
    '''
    transform binance kline response to bybit websocket message for backtesting simulation.
    Parameters
    ----------
    klines: List[List[Any]]
        historical binance candlesticks
    topic: str
        respective bybit topic to simulate websocket responses
    
    Returns
    -------
    messages: List[str]
        list of json response bodys (formatted as string), analog to bybit websocket messages
    '''
    # initialize empty list of messages
    messages = []

    # format klines
    formatted_klines = format_historical_klines(klines)

    # iterate through all lines and format candles
    for idx in formatted_klines.index:
        kline = formatted_klines.loc[idx]

        # format candle to dict
        bybit_msg = {
            "topic": topic,
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
