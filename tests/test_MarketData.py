# !/usr/bin/env python
# coding: utf-8

import pandas as pd
import json
import os
from typing import List
import unittest
from src.MarketData import MarketData

PUBLIC_TOPICS = ["candle.1.BTCUSDT"]


class TestMarketData(unittest.TestCase):

    def setUp(self):

        self.market_data = MarketData(topics=PUBLIC_TOPICS)
        self.success_message = '{"topic":"candle.1.BTCUSDT","data":[{"start":1667461800,"end":1667461860,"period":"1","open":20282,"close":20280.5,"high":20282.5,"low":20280,"volume":"20.753","turnover":"420912.939","confirm":false,"cross_seq":19909786084,"timestamp":1667461837466318}],"timestamp_e6":1667461837466318}'
        self.success_message_3 = '{"topic":"candle.1.BTCUSDT","data":[{"start":1667461860,"end":1667461920,"period":"1","open":20280.5,"close":20281,7,"high":20283.2,"low":20279.8,"volume":"21.853","turnover":"421912.939","confirm":false,"cross_seq":19909786084,"timestamp":1667461837466318}],"timestamp_e6":1667461837466318}'
        self.failure_message_1 = '{"success":true,"ret_msg":"","conn_id":"0645af2a-2a34-476e-bcc6-40baa771c0bf","request":{"op":"subscribe","args":["candle.1.BTCUSDT"]}}'
        self.failure_message_2 = '{"topic":"candle.1.EURUSD","data":[{"start":1667461800,"end":1667461860,"period":"1","open":20282,"close":20280.5,"high":20282.5,"low":20280,"volume":"20.753","turnover":"420912.939","confirm":false,"cross_seq":19909786084,"timestamp":1667461837466318}],"timestamp_e6":1667461837466318}'
        self.success = {
            "topic": "candle.1.BTCUSDT",
            "data": [{
                "start": pd.Timestamp('2022-11-03 07:50:00'),
                "end": pd.Timestamp('2022-11-03 07:51:00'),
                "period": "1",
                "open": 20282,
                "close": 20280.5,
                "high": 20282.5,
                "low": 20280,
                "volume": 20.753,
                "turnover": 420912.939,
                "confirm": False,
                "cross_seq": 19909786084,
                "timestamp": 1667461837466318
            }],
            "timestamp_e6": 1667461837466318
        }

        self.success_2 = {
            "topic": "candle.1.BTCUSDT",
            "data": [{
                "start": pd.Timestamp('2022-11-03 07:51:00'),
                "end": pd.Timestamp('2022-11-03 07:52:00'),
                "period": "1",
                "open": 20282,
                "close": 20280.5,
                "high": 20282.5,
                "low": 20280,
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

        history_1 = pd.DataFrame(self.success['data'][0]).set_index('end',
                                                                    drop=False)

        self.assertEqual(self.market_data.history["candle.1.BTCUSDT"],
                         history_1)

        data_2 = self.market_data.on_message(self.success_message)

        self.assertEqual(self.market_data.history["candle.1.BTCUSDT"],
                         history_1)

        data_3 = self.market_data.on_message(self.success_message_3)
        history_3 = history_1.copy()
        history_3.loc[data_3['end']] = data_3

        self.assertEqual(data, self.success)
        self.assertFalse(failure_1)
        self.assertFalse(failure_2)
        self.assertEqual(self.market_data.history["candle.1.BTCUSDT"],
                         history_3)

    def test_add_history(self):

        history = pd.DataFrame({
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
        })

        history = pd.concat(
            [history, self.market_data.history["candle.1.BTCUSDT"]])
        self.market_data.add_history(topic="candle.1.BTCUSDT")

        self.assertEqual(history,
                         self.market_data.history['"candle.1.BTCUSDT"'])
        self.assertListEqual(list(history.index), [
            pd.Timestamp('2022-11-03 07:50:00'),
            pd.Timestamp('2022-11-03 07:51:00'),
            pd.Timestamp('2022-11-03 07:52:00')
        ])
