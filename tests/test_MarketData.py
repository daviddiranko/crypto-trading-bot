# !/usr/bin/env python
# coding: utf-8

import pandas as pd
import json
import os
from typing import List
import unittest
from src.MarketData import MarketData
from binance.client import Client
from dotenv import load_dotenv

PUBLIC_TOPICS = ["candle.1.BTCUSDT"]
PUBLIC_TOPICS_COLUMNS = [
    "start", "end", "period", "open", "close", "high", "low", "volume",
    "turnover", "confirm", "cross_seq", "timestamp"
]

load_dotenv()

BINANCE_KEY = os.getenv('BINANCE_KEY')
BINANCE_SECRET = os.getenv('BINANCE_SECRET')


class TestMarketData(unittest.TestCase):

    def setUp(self):
        self.client = Client(api_key=BINANCE_KEY, api_secret=BINANCE_SECRET)
        self.market_data = MarketData(client=self.client, topics=PUBLIC_TOPICS)
        self.success_message = '{"topic":"candle.1.BTCUSDT","data":[{"start":1667461800,"end":1667461860,"period":"1","open":20282,"close":20280.5,"high":20282.5,"low":20280,"volume":"20.753","turnover":"420912.939","confirm":false,"cross_seq":19909786084,"timestamp":1667461837466318}],"timestamp_e6":1667461837466318}'
        self.success_message_3 = '{"topic":"candle.1.BTCUSDT","data":[{"start":1667461860,"end":1667461920,"period":"1","open":20280.5,"close":20281.7,"high":20283.2,"low":20279.8,"volume":"21.853","turnover":"421912.939","confirm":false,"cross_seq":19909786084,"timestamp":1667461837466318}],"timestamp_e6":1667461837466318}'
        self.failure_message_1 = '{"success":true,"ret_msg":"","conn_id":"0645af2a-2a34-476e-bcc6-40baa771c0bf","request":{"op":"subscribe","args":["candle.1.BTCUSDT"]}}'
        self.failure_message_2 = '{"topic":"candle.1.EURUSD","data":[{"start":1667461800,"end":1667461860,"period":"1","open":20282,"close":20280.5,"high":20282.5,"low":20280,"volume":"20.753","turnover":"420912.939","confirm":false,"cross_seq":19909786084,"timestamp":1667461837466318}],"timestamp_e6":1667461837466318}'
        self.success = {
            "topic": PUBLIC_TOPICS[0],
            "data": [{
                "start": pd.Timestamp('2022-11-03 07:50:00'),
                "end": pd.Timestamp('2022-11-03 07:51:00'),
                "period": "1",
                "open": 20282.0,
                "close": 20280.5,
                "high": 20282.5,
                "low": 20280.0,
                "volume": 20.753,
                "turnover": 420912.939,
                "confirm": False,
                "cross_seq": 19909786084,
                "timestamp": 1667461837466318
            }],
            "timestamp_e6": 1667461837466318
        }

        self.success_2 = {
            "topic": PUBLIC_TOPICS[0],
            "data": [{
                "start": pd.Timestamp('2022-11-03 07:51:00'),
                "end": pd.Timestamp('2022-11-03 07:52:00'),
                "period": "1",
                "open": 20282.0,
                "close": 20280.5,
                "high": 20282.5,
                "low": 20280.0,
                "volume": 20.753,
                "turnover": 420912.939,
                "confirm": False,
                "cross_seq": 19909786084,
                "timestamp": 1667461837466318
            }],
            "timestamp_e6": 1667461837466318
        }

    def test_on_message(self):

        data = self.market_data.on_message(self.success_message)
        failure_1 = self.market_data.on_message(self.failure_message_1)
        failure_2 = self.market_data.on_message(self.failure_message_2)

        history_1 = pd.DataFrame(columns=PUBLIC_TOPICS_COLUMNS)
        history_1.loc[self.success['data'][0]['end']] = self.success['data'][0]

        pd.testing.assert_frame_equal(
            self.market_data.history[PUBLIC_TOPICS[0]], history_1)

        data_2 = self.market_data.on_message(self.success_message)

        pd.testing.assert_frame_equal(
            self.market_data.history[PUBLIC_TOPICS[0]], history_1)

        data_3 = self.market_data.on_message(self.success_message_3)
        history_3 = history_1.copy()
        history_3.loc[data_3['end']] = data_3

        self.assertDictEqual(data, self.success['data'][0])
        self.assertFalse(failure_1)
        self.assertFalse(failure_2)
        pd.testing.assert_frame_equal(
            self.market_data.history[PUBLIC_TOPICS[0]], history_3)

    def test_add_history(self):

        self.market_data.on_message(self.success_message)
        self.market_data.on_message(self.success_message_3)

        data = pd.DataFrame(columns=PUBLIC_TOPICS_COLUMNS)
        data.loc[pd.Timestamp('2022-11-03 07:50:00')] = {
            "start": pd.Timestamp('2022-11-03 07:49:00'),
            "end": pd.Timestamp('2022-11-03 07:50:00'),
            "period": "1",
            "open": 20280.3,
            "close": 20282,
            "high": 20282,
            "low": 20279.1,
            "volume": 19.753,
            "turnover": 410912.939,
            "confirm": False,
            "cross_seq": 19909786084,
            "timestamp": 1667461837466318
        }

        history = pd.concat([data, self.market_data.history[PUBLIC_TOPICS[0]]])

        self.market_data.add_history(topic=PUBLIC_TOPICS[0], data=data)

        pd.testing.assert_frame_equal(
            history, self.market_data.history[PUBLIC_TOPICS[0]])

        self.assertListEqual(list(history.index), [
            pd.Timestamp('2022-11-03 07:50:00'),
            pd.Timestamp('2022-11-03 07:51:00'),
            pd.Timestamp('2022-11-03 07:52:00')
        ])
