# !/usr/bin/env python
# coding: utf-8
import warnings

warnings.simplefilter(action='ignore', category=FutureWarning)
import pandas as pd
import json
from dotenv import load_dotenv
import os
from typing import List, Dict, Any
from src.endpoints.bybit_functions import format_klines
from src.backtest.BacktestMarketData import BacktestMarketData
from src.backtest.BacktestAccountData import BacktestAccountData

from binance.client import Client
from src.endpoints import binance_functions, bybit_functions

import unittest

load_dotenv()

BINANCE_KEY = os.getenv('BINANCE_KEY')
BINANCE_SECRET = os.getenv('BINANCE_SECRET')
PUBLIC_TOPICS = ["candle.1.BTCUSDT", "candle.5.BTCUSDT"]
BINANCE_BYBIT_MAPPING = {
    'candle.1.BTCUSDT': 'BTCUSDT',
    'candle.5.BTCUSDT': 'BTCUSDT'
}


class TestBacktestMarketData(unittest.TestCase):
    '''
    Class to provide historical market data for backtesting
    '''

    # create new backtesting marketdata object through inheritance from MarketData
    def setUp(self):
        self.client = Client(BINANCE_KEY, BINANCE_SECRET)
        self.account = BacktestAccountData(binance_client=self.client,
                                           symbols=['BTC', 'USDT'],
                                           budget={
                                               'BTC': 0,
                                               'USDT': 1000
                                           })
        self.market_data = BacktestMarketData(
            account=self.account,
            client=self.client,
            topics=PUBLIC_TOPICS,
            toppic_mapping=BINANCE_BYBIT_MAPPING)

        self.order_time = pd.Timestamp('2022-10-01 09:33:00')

        # order time + 1 minute
        self.order_time_1 = pd.Timestamp(self.order_time.value / 1000000000 +
                                         60,
                                         unit='s')
        # order time_1 + 1 minute
        self.order_time_2 = pd.Timestamp(self.order_time_1.value / 1000000000 +
                                         60,
                                         unit='s')
        # order time_2 + 1 minute
        self.order_time_3 = pd.Timestamp(self.order_time_2.value / 1000000000 +
                                         60,
                                         unit='s')

    def test_on_message(self):

        market_data_1 = json.dumps({
            "topic": PUBLIC_TOPICS[0],
            "data": [{
                'start': self.order_time.value / 1000000000,
                'end': self.order_time_1.value / 1000000000,
                'period': "1",
                'open': 19000,
                'close': 19500,
                'high': 19800,
                'low': 18500,
                'volume': 10,
                'turnover': 192000,
                "confirm": True,
                "cross_seq": 19909786084,
                "timestamp": 1667461837466318
            }],
            "timestamp_e6": 1667461837466318
        })

        market_data_2 = json.dumps({
            "topic": PUBLIC_TOPICS[0],
            "data": [{
                'start': self.order_time_1.value / 1000000000,
                'end': self.order_time_2.value / 1000000000,
                'period': "1",
                'open': 19500,
                'close': 19000,
                'high': 20100,
                'low': 18900,
                'volume': 10,
                'turnover': 192000,
                "confirm": True,
                "cross_seq": 19909786084,
                "timestamp": 1667461837466318
            }],
            "timestamp_e6": 1667461837466318
        })

        market_data_3 = json.dumps({
            "topic": PUBLIC_TOPICS[0],
            "data": [{
                'start': self.order_time_2.value / 1000000000,
                'end': self.order_time_3.value / 1000000000,
                'period': "1",
                'open': 19000,
                'close': 18500,
                'high': 19300,
                'low': 18200,
                'volume': 10,
                'turnover': 192000,
                "confirm": True,
                "cross_seq": 19909786084,
                "timestamp": 1667461837466318
            }],
            "timestamp_e6": 1667461837466318
        })

        response_1 = {
            'start': self.order_time,
            'end': self.order_time_1,
            'period': "1",
            'open': 19000.0,
            'close': 19500.0,
            'high': 19800.0,
            'low': 18500.0,
            'volume': 10.0,
            'turnover': 192000.0,
            "confirm": True,
            "cross_seq": 19909786084,
            "timestamp": 1667461837466318
        }

        msg_1 = self.market_data.on_message(message=market_data_1)

        response_2 = {
            'start': self.order_time_1,
            'end': self.order_time_2,
            'period': "1",
            'open': 19500.0,
            'close': 19000.0,
            'high': 20100.0,
            'low': 18900.0,
            'volume': 10.0,
            'turnover': 192000.0,
            "confirm": True,
            "cross_seq": 19909786084,
            "timestamp": 1667461837466318
        }
        msg_2 = self.market_data.on_message(message=market_data_2)

        response_3 = {
            'start': self.order_time_2,
            'end': self.order_time_3,
            'period': "1",
            'open': 19000.0,
            'close': 18500.0,
            'high': 19300.0,
            'low': 18200.0,
            'volume': 10.0,
            'turnover': 192000.0,
            "confirm": True,
            "cross_seq": 19909786084,
            "timestamp": 1667461837466318
        }
        msg_3 = self.market_data.on_message(message=market_data_3)

        history = pd.DataFrame([response_1, response_2,
                                response_3]).set_index('end', drop=False)
        history.index.name = None

        self.assertDictEqual(msg_1, response_1)
        self.assertDictEqual(msg_2, response_2)
        self.assertDictEqual(msg_3, response_3)

        pd.testing.assert_frame_equal(
            self.market_data.history[PUBLIC_TOPICS[0]], history)
