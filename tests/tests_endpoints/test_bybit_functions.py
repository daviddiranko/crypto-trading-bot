import pandas as pd
from typing import List, Dict, Any
import unittest
import json
from src.endpoints.bybit_functions import format_klines


class TestMarketData(unittest.TestCase):

    def setUp(self):

        self.success_message = json.loads(
            '{"topic":"candle.1.BTCUSDT","data":[{"start":1667461800,"end":1667461860,"period":"1","open":20282,"close":20280.5,"high":20282.5,"low":20280,"volume":"20.753","turnover":"420912.939","confirm":false,"cross_seq":19909786084,"timestamp":1667461837466318}],"timestamp_e6":1667461837466318}'
        )
        self.failure_message = '{"success":true,"ret_msg":"","conn_id":"0645af2a-2a34-476e-bcc6-40baa771c0bf","request":{"op":"subscribe","args":["candle.1.BTCUSDT"]}}'
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

    def test_format_klines(self):

        extraction = format_klines(self.success_message)

        self.assertEqual(extraction, self.success)
