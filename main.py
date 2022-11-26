import sys

sys.path.append('../')

import hmac
import json
import time
import websockets
from pybit import usdt_perpetual
import pandas as pd
from typing import List
from binance.client import Client
from src.endpoints.binance_functions import format_historical_klines
from datetime import datetime
import threading
import asyncio
from dotenv import load_dotenv
import os
from src.MarketData import MarketData
from src.AccountData import AccountData
from src.TradingModel import TradingModel
from src.models.mock_model import mock_model
from src.endpoints.bybit_functions import format_klines, place_order, place_conditional_order

# load environment variables
load_dotenv()

BYBIT_TEST_KEY = os.getenv('BYBIT_TEST_KEY')
BYBIT_TEST_SECRET = os.getenv('BYBIT_TEST_SECRET')

BINANCE_KEY = os.getenv('BINANCE_KEY')
BINANCE_SECRET = os.getenv('BINANCE_SECRET')

BYBIT_TEST_ENDPOINT = os.getenv('BYBIT_TEST_ENDPOINT')

WS_PUBLIC_TEST_URL = os.getenv('WS_PUBLIC_TEST_URL')
WS_PRIVATE_TEST_URL = os.getenv('WS_PRIVATE_TEST_URL')

PUBLIC_TOPICS = eval(os.getenv('PUBLIC_TOPICS'))
PRIVATE_TOPICS = eval(os.getenv('PRIVATE_TOPICS'))
PUBLIC_TOPICS_COLUMNS = eval(os.getenv('PUBLIC_TOPICS_COLUMNS'))

BACKTEST_SYMBOLS = eval(os.getenv('BACKTEST_SYMBOLS'))

HIST_TICKERS = eval(os.getenv('HIST_TICKERS'))


async def main():
    # Generate expires.
    expires = int((time.time() + 7200) * 1000)

    # Generate signature.
    signature = str(
        hmac.new(bytes(BYBIT_TEST_SECRET, "utf-8"),
                 bytes(f"GET/realtime{expires}", "utf-8"),
                 digestmod="sha256").hexdigest())

    param = "api_key={api_key}&expires={expires}&signature={signature}".format(
        api_key=BYBIT_TEST_KEY, expires=expires, signature=signature)

    # generate websocket urls
    public_url = WS_PUBLIC_TEST_URL + "?" + param
    private_url = WS_PRIVATE_TEST_URL + "?" + param

    # generate parameters for historical data
    start = 10
    start_unit = 'm'

    symbol_list = [symbol[:3] for symbol in HIST_TICKERS]
    symbol_list.extend([symbol[3:] for symbol in HIST_TICKERS])

    # initialize http connection for trading
    session = usdt_perpetual.HTTP(endpoint=BYBIT_TEST_ENDPOINT,
                                  api_key=BYBIT_TEST_KEY,
                                  api_secret=BYBIT_TEST_SECRET)

    # initialize binance client to pull historical data and add to market data history
    binance_client = Client(BINANCE_KEY, BINANCE_SECRET)

    # initialize MarketData, AccountData and TradingModel objects
    market_data = MarketData(client=binance_client, topics=PUBLIC_TOPICS)
    account_data = AccountData(http_session=session, symbols=symbol_list)
    model = TradingModel(market_data=market_data,
                         account=account_data,
                         model=mock_model,
                         model_args={'open': True},
                         model_storage={
                             'open': False,
                             'close': False
                         })

    # construct start string
    start_str = str(pd.Timestamp.now() - pd.Timedelta(start, start_unit))
    end_str = str(pd.Timestamp.now())

    model.market_data.build_history(symbols=BACKTEST_SYMBOLS,
                                    start_str=start_str,
                                    end_str=end_str)

    # if connection is lost, immediately set up new connection
    while True:
        # start listening to the public and private websockets "in parallel"
        async with websockets.connect(private_url) as ws_private, \
                    websockets.connect(public_url) as ws_public:

            # subscribe to public and private topics
            await ws_public.send(
                json.dumps({
                    "op": "subscribe",
                    "args": PUBLIC_TOPICS
                }))
            await ws_private.send(
                json.dumps({
                    "op": "auth",
                    "args": [BYBIT_TEST_KEY, expires, signature]
                }))
            await ws_private.send(
                json.dumps({
                    "op": "subscribe",
                    "args": PRIVATE_TOPICS
                }))

            # create a task queue of websocket messages
            channel = asyncio.Queue()

            async def transmit(w, source):
                while True:
                    msg = await w.recv()
                    message = json.loads(msg)
                    # only include full candlesticks to avoid spamming
                    try:
                        if message['data'][0]['confirm'] == True:
                            await channel.put((source, msg))
                    except:
                        await channel.put((source, msg))
                    await channel.put((source, msg))

            # create tasks for reception of public and private messages
            asyncio.create_task(transmit(ws_public, 'public_source'))
            asyncio.create_task(transmit(ws_private, 'private_source'))

            while True:
                source, msg = await channel.get()
                model.on_message(msg)


if __name__ == "__main__":
    main()
