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
from src.models.checklist_model import mock_model
from src.models.checklist_model import checklist_model
from src.endpoints.bybit_functions import format_klines, place_order, place_conditional_order
import argparse

# load environment variables
load_dotenv()

BYBIT_TEST_KEY = os.getenv('BYBIT_TEST_KEY')
BYBIT_TEST_SECRET = os.getenv('BYBIT_TEST_SECRET')

BINANCE_KEY = os.getenv('BINANCE_KEY')
BINANCE_SECRET = os.getenv('BINANCE_SECRET')

BYBIT_TEST_ENDPOINT = os.getenv('BYBIT_TEST_ENDPOINT')

WS_PUBLIC_TEST_URL = os.getenv('WS_PUBLIC_TEST_URL')
WS_PRIVATE_TEST_URL = os.getenv('WS_PRIVATE_TEST_URL')

PRIVATE_TOPICS = eval(os.getenv('PRIVATE_TOPICS'))


async def main():

    # parse arguments
    parser = argparse.ArgumentParser(
        description="Run Live Trading Model for bybit trading.")

    parser.add_argument('--ticker', type=str, default="BTCUSDT")
    parser.add_argument(
        '--freqs',
        type=str,
        default="1 5 15",
        help="List of candle frequencies in minutes required by the model")
    parser.add_argument('--model_args',
                        type=str,
                        default=str({'param': 1}),
                        help="optional arguments for trading model")
    args = parser.parse_args()
    args = vars(args)

    freqs = args['freqs'].split()
    model_args = eval(args['model_args'])
    model_args['ticker'] = args['ticker']

    ticker = args['ticker']

    BACKTEST_SYMBOLS = {
        '{}.{}m'.format(ticker, freq): 'candle.{}.{}'.format(freq, ticker)
        for freq in freqs
    }

    HIST_TICKERS = [ticker]
    PUBLIC_TOPICS = ["candle.{}.{}".format(freq, ticker) for freq in freqs]
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
    start = 2
    start_unit = 'd'

    symbol_list = [symbol[:-4] for symbol in HIST_TICKERS]
    symbol_list.extend([symbol[-4:] for symbol in HIST_TICKERS])

    print('Establish Bybit HTTP session...')
    # initialize http connection for trading
    session = usdt_perpetual.HTTP(endpoint=BYBIT_TEST_ENDPOINT,
                                  api_key=BYBIT_TEST_KEY,
                                  api_secret=BYBIT_TEST_SECRET)

    print('Done!')

    print('Establish Binance HTTP session...')
    # initialize binance client to pull historical data and add to market data history
    binance_client = Client(BINANCE_KEY, BINANCE_SECRET)

    print('Done!')

    # initialize TradingModel object
    model = TradingModel(client=binance_client,
                         http_session=session,
                         symbols=symbol_list,
                         topics=PUBLIC_TOPICS,
                         model=checklist_model,
                         model_args={
                             'open': None,
                             'reduce_only': True
                         },
                         model_storage={
                             'open': None,
                             'close': None,
                             'entry_bar_time': pd.Timestamp.now()
                         })

    # close potential open positions upfront
    for pos in model.account.positions.values():
        if (pos['size'] > 0) and (pos['symbol'] == ticker):
            if pos['side'] == 'Buy':
                side = 'Sell'
            else:
                side = 'Buy'
            model.account.place_order(symbol=pos['symbol'],
                                      side=side,
                                      order_type='Market',
                                      qty=pos['size'],
                                      reduce_only=True)

    # construct start string
    start_str = str(pd.Timestamp.now() - pd.Timedelta(start, start_unit))
    end_str = str(pd.Timestamp.now())

    print('Load trading history for trading model...')
    model.market_data.build_history(symbols=BACKTEST_SYMBOLS,
                                    start_str=start_str,
                                    end_str=end_str)

    print('Done!')

    # if connection is lost, immediately set up new connection
    while True:
        print('Connect to Bybit websockets...')

        try:
            # start listening to the public and private websockets "in parallel"
            async with websockets.connect(private_url) as ws_private, \
                        websockets.connect(public_url) as ws_public:

                # subscribe to public and private top‚ics
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

                print('Done!')

                print('Starting trading...')

                # create a task queue of websocket messages
                channel = asyncio.Queue()

                async def transmit(w, source):
                    while True:
                        msg = await w.recv()
                        message = json.loads(msg)

                        # only include full candlesticks to avoid spamming
                        if 'data' in message.keys():
                            if 'confirm' in message['data'][0].keys():
                                if message['data'][0]['confirm'] == True:
                                    await channel.put((source, msg))
                            else:
                                # print(message)
                                await channel.put((source, msg))
                        else:
                            await channel.put((source, msg))

                # create tasks for reception of public and private messages
                asyncio.create_task(transmit(ws_public, 'public_source'))
                asyncio.create_task(transmit(ws_private, 'private_source'))

                while True:
                    source, msg = await channel.get()
                    model.on_message(msg)
        except:
            print('Connection to Bybit websocket lost.')


if __name__ == "__main__":
    asyncio.run(main())
