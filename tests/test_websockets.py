# !/usr/bin/env python
# coding: utf-8

import hmac
import json
import time
import websockets
from pybit import usdt_perpetual
from binance.client import Client
import asyncio
from dotenv import load_dotenv
import os
import unittest
from src.endpoints.bybit_functions import place_order, place_conditional_order
from src.TradingModel import TradingModel
from src.MarketData import MarketData
from src.AccountData import AccountData
from src.models.mock_model import mock_model
from src.endpoints.binance_functions import format_historical_klines

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
PRIVATE_TOPICS_COLUMNS = eval(os.getenv('PRIVATE_TOPICS_COLUMNS'))

HIST_TICKERS = eval(os.getenv('HIST_TICKERS'))
HIST_COLUMNS = eval(os.getenv('HIST_COLUMNS'))


class TestWebsocksets(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        # Generate expires.
        self.expires = int((time.time() + 7200) * 1000)

        # Generate signature.
        self.signature = str(
            hmac.new(bytes(BYBIT_TEST_SECRET, "utf-8"),
                     bytes(f"GET/realtime{self.expires}", "utf-8"),
                     digestmod="sha256").hexdigest())

        self.param = "api_key={api_key}&expires={expires}&signature={signature}".format(
            api_key=BYBIT_TEST_KEY,
            expires=self.expires,
            signature=self.signature)

        self.public_url = WS_PUBLIC_TEST_URL + "?" + self.param
        self.private_url = WS_PRIVATE_TEST_URL + "?" + self.param
        self.frequency = 1
        self.frequency_unit = 'm'
        self.start = 10
        self.start_unit = 'm'
        self.ticker = 'BTCUSDT'
        # initialize http connection for trading
        self.session = usdt_perpetual.HTTP(endpoint=BYBIT_TEST_ENDPOINT,
                                           api_key=BYBIT_TEST_KEY,
                                           api_secret=BYBIT_TEST_SECRET)

        # set leverage to 1
        try:
            self.session.set_leverage(symbol=self.ticker,
                                      sell_leverage=1,
                                      buy_leverage=1)
        except:
            pass

        # close all possible open positions
        try:
            place_order(session=self.session,
                        symbol=self.ticker,
                        order_type='Market',
                        side='Sell',
                        qty=10,
                        reduce_only=True)
        except:
            pass
        try:
            place_conditional_order(session=self.session,
                                    symbol=self.ticker,
                                    order_type='Market',
                                    side='Sell',
                                    qty=10,
                                    reduce_only=True)
        except:
            pass

    def tearDown(self):
        try:
            place_order(session=self.session,
                        symbol=self.ticker,
                        order_type='Market',
                        side='Sell',
                        qty=10,
                        reduce_only=True)
        except:
            pass
        try:
            place_conditional_order(session=self.session,
                                    symbol=self.ticker,
                                    order_type='Market',
                                    side='Sell',
                                    qty=10,
                                    reduce_only=True)
        except:
            pass

    async def test_connections(self):
        # start listening to the public and private websockets "in parallel"
        async with websockets.connect(self.public_url) as ws_public, \
                    websockets.connect(self.private_url) as ws_private:

            # pull historical data from binance and add to market data history
            binance_client = Client(BINANCE_KEY, BINANCE_SECRET)

            # construct start string
            start_str = str(self.start) + ' ' + self.start_unit + ' ago'

            for ticker in HIST_TICKERS:
                # load history as list of lists from binance
                msg = binance_client.get_historical_klines(
                    ticker,
                    interval=str(self.frequency) + self.frequency_unit,
                    start_str=start_str)

                self.assertGreater(len(msg), 0)
                self.assertEqual(len(msg[0]), len(HIST_COLUMNS))

            # initialize dictionaries to check if websocket connection is successful and data is received
            public_topics_success = {topic: None for topic in PUBLIC_TOPICS}
            private_topics_success = {topic: None for topic in PRIVATE_TOPICS}
            public_topics_data = {topic: False for topic in PUBLIC_TOPICS}
            private_topics_data = {topic: False for topic in PRIVATE_TOPICS}

            # subscribe to public and private topics
            await ws_public.send(
                json.dumps({
                    "op": "subscribe",
                    "args": PUBLIC_TOPICS
                }))
            await ws_private.send(
                json.dumps({
                    "op": "auth",
                    "args": [BYBIT_TEST_KEY, self.expires, self.signature]
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
                    await channel.put((source, msg))

            # create tasks for reception of public and private messages
            asyncio.create_task(transmit(ws_public, 'public_source'))
            asyncio.create_task(transmit(ws_private, 'private_source'))

            # Wait for 5 seconds to receive success messages and data from all endpoints
            # Then place a market buy order and wait another 5 seconds for fulfillment
            t_trade = time.time() + 5
            t_end = t_trade + 10

            # initialize traded flag to ensure that only one order is placed
            traded = False

            while time.time() < t_end:

                # load new message
                source, msg = await channel.get()
                response = json.loads(msg)

                # try to collect a success message, otherwise extract data from public topic
                # messages are tracked in a dictionary to count topics from which messages were received
                # if message contains data and 5+ seconds have passed, place a market order
                if source == 'public_source':
                    try:
                        topics = response['request']['args']
                        for topic in set(topics).intersection(
                                set(PUBLIC_TOPICS)):
                            public_topics_success[topic] = response['success']

                    except:
                        try:
                            topic = response['topic']
                            if set(response['data'][0].keys()) == set(
                                    PUBLIC_TOPICS_COLUMNS):
                                public_topics_data[topic] = True

                            if time.time() > t_trade and not traded:
                                order = place_order(session=self.session,
                                                    symbol=self.ticker,
                                                    order_type='Market',
                                                    side='Buy',
                                                    qty=0.001)

                                conditional_order = place_conditional_order(
                                    session=self.session,
                                    symbol=self.ticker,
                                    order_type='Market',
                                    side='Buy',
                                    qty=0.001,
                                    base_price=10,
                                    stop_px=10)
                                traded = True
                        except:
                            pass

                if source == 'private_source':
                    try:
                        topics = response['request']['args']
                        for topic in set(topics).intersection(
                                set(PRIVATE_TOPICS)):
                            private_topics_success[topic] = response['success']

                    except:
                        try:
                            topic = response['topic']
                            if set(response['data'][0].keys()) == set(
                                    PRIVATE_TOPICS_COLUMNS[topic]):
                                private_topics_data[topic] = True
                        except:
                            pass

        self.assertEqual(sum(public_topics_success.values()),
                         len(PUBLIC_TOPICS))
        self.assertEqual(sum(private_topics_success.values()),
                         len(PRIVATE_TOPICS))
        self.assertEqual(sum(public_topics_data.values()), len(PUBLIC_TOPICS))
        self.assertEqual(sum(private_topics_data.values()), len(PRIVATE_TOPICS))

    async def test_system(self):

        # initialize MarketData, AccountData and TradingModel objects
        market_data = MarketData(topics=PUBLIC_TOPICS)
        account_data = AccountData(http_session=self.session,
                                   symbols=[self.ticker[:3], self.ticker[3:]])
        model = TradingModel(market_data=market_data,
                             account=account_data,
                             model=mock_model,
                             model_args={'open': True},
                             model_storage={
                                 'open': False,
                                 'close': False
                             })

        # pull historical data from binance and add to market data history
        binance_client = Client(BINANCE_KEY, BINANCE_SECRET)

        # construct start string
        start_str = str(self.start) + ' ' + self.start_unit + ' ago'

        # load history as list of lists from binance
        msg = binance_client.get_historical_klines(
            self.ticker,
            interval=str(self.frequency) + self.frequency_unit,
            start_str=start_str)

        # format payload to dataframe
        klines = format_historical_klines(msg)

        model.market_data.add_history(topic=PUBLIC_TOPICS[0], data=klines)

        wallet_start = model.account.wallet['USDT']

        # start listening to the public and private websockets "in parallel"
        async with websockets.connect(self.private_url) as ws_private, \
                    websockets.connect(self.public_url) as ws_public:

            # subscribe to public and private topics
            await ws_public.send(
                json.dumps({
                    "op": "subscribe",
                    "args": PUBLIC_TOPICS
                }))
            await ws_private.send(
                json.dumps({
                    "op": "auth",
                    "args": [BYBIT_TEST_KEY, self.expires, self.signature]
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
                    await channel.put((source, msg))

            # create tasks for reception of public and private messages
            asyncio.create_task(transmit(ws_public, 'public_source'))
            asyncio.create_task(transmit(ws_private, 'private_source'))

            start_time = time.time()
            while time.time() < start_time + 5:
                source, msg = await channel.get()
                model.on_message(msg)
                if not model.model_storage['open'] or not model.model_storage[
                        'close']:
                    start_time = time.time()

        order_keys = list(model.account.orders['BTCUSDT'].keys())
        execution_keys = list(model.account.executions['BTCUSDT'].keys())
        order_fee = model.account.orders['BTCUSDT'][
            order_keys[1]]['cum_exec_fee'] + model.account.orders['BTCUSDT'][
                order_keys[0]]['cum_exec_fee']
        exec_fee = model.account.executions['BTCUSDT'][
            order_keys[1]]['exec_fee'] + model.account.executions['BTCUSDT'][
                order_keys[0]]['exec_fee']
        order_profit = model.account.orders['BTCUSDT'][
            order_keys[1]]['cum_exec_value'] - model.account.orders['BTCUSDT'][
                order_keys[0]]['cum_exec_value']
        exec_profit = model.account.executions['BTCUSDT'][order_keys[1]][
            'price'] * model.account.executions['BTCUSDT'][order_keys[1]][
                'exec_qty'] - model.account.executions['BTCUSDT'][order_keys[
                    0]]['price'] * model.account.executions['BTCUSDT'][
                        order_keys[0]]['exec_qty']
        wallet_balance = model.account.wallet['USDT'][
            'available_balance'] - wallet_start['available_balance']
        available_balance = model.account.wallet['USDT'][
            'available_balance'] - wallet_start['available_balance']
        self.assertListEqual(order_keys, execution_keys)
        self.assertEqual(order_fee, exec_fee)
        self.assertEqual(order_profit, exec_profit)
        self.assertEqual(wallet_balance, available_balance)
        self.assertAlmostEqual(wallet_balance,
                               order_profit - order_fee,
                               places=2)