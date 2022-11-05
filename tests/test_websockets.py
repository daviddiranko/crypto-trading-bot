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

    async def test_connections(self):
        # start listening to the public and private websockets "in parallel"
        async with websockets.connect(self.public_url) as ws_public, \
                    websockets.connect(self.private_url) as ws_private:

            # initialize http connection for trading
            session = usdt_perpetual.HTTP(endpoint=BYBIT_TEST_ENDPOINT,
                                          api_key=BYBIT_TEST_KEY,
                                          api_secret=BYBIT_TEST_SECRET)

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

            # Wait for 10 seconds to receive success messages and data from all endpoints
            t_end = time.time() + 5
            while time.time() < t_end:
                source, msg = await channel.get()
                response = json.loads(msg)

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
        # self.assertEqual(sum(private_topics_data.values()), len(PRIVATE_TOPICS))

        # TODO Add mock trade and monitor account endpoint updates