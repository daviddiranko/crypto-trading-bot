from typing import List, Any
from src.endpoints.binance_functions import format_historical_klines
from src.helper_functions.helper_functions import *
import json
import pandas as pd
import unittest


class TestHelper_functions(unittest.TestCase):

    def test_binance_to_bybit(self):

        self.binance_msg = pd.DataFrame({
            'start': {
                pd.Timestamp('2022-11-22 00:01:00'):
                    pd.Timestamp('2022-11-22 00:00:00'),
                pd.Timestamp('2022-11-22 00:02:00'):
                    pd.Timestamp('2022-11-22 00:01:00')
            },
            'open': {
                pd.Timestamp('2022-11-22 00:01:00'): 15781.29,
                pd.Timestamp('2022-11-22 00:02:00'): 15773.47
            },
            'high': {
                pd.Timestamp('2022-11-22 00:01:00'): 15792.2,
                pd.Timestamp('2022-11-22 00:02:00'): 15778.84
            },
            'low': {
                pd.Timestamp('2022-11-22 00:01:00'): 15771.85,
                pd.Timestamp('2022-11-22 00:02:00'): 15754.17
            },
            'close': {
                pd.Timestamp('2022-11-22 00:01:00'): 15773.47,
                pd.Timestamp('2022-11-22 00:02:00'): 15764.87
            },
            'volume': {
                pd.Timestamp('2022-11-22 00:01:00'): 177.50515,
                pd.Timestamp('2022-11-22 00:02:00'): 239.191
            },
            'end': {
                pd.Timestamp('2022-11-22 00:01:00'):
                    pd.Timestamp('2022-11-22 00:01:00'),
                pd.Timestamp('2022-11-22 00:02:00'):
                    pd.Timestamp('2022-11-22 00:02:00')
            },
            'turnover': {
                pd.Timestamp('2022-11-22 00:01:00'): 2801323.8563535,
                pd.Timestamp('2022-11-22 00:02:00'): 3770939.1076589
            }
        })

        self.bybit_response = [
            '{"topic": "candle.1.BTCUSDT", "data": [{"start": 1669075200.0, "end": 1669075260.0, "period": "1", "open": 15781.29, "close": 15773.47, "high": 15792.2, "low": 15771.85, "volume": 177.50515, "turnover": 2801323.8563535, "confirm": true, "cross_seq": 0, "timestamp": 1669075260000000000}], "timestamp_e6": 1669075260000000000}',
            '{"topic": "candle.1.BTCUSDT", "data": [{"start": 1669075260.0, "end": 1669075320.0, "period": "1", "open": 15773.47, "close": 15764.87, "high": 15778.84, "low": 15754.17, "volume": 239.191, "turnover": 3770939.1076589, "confirm": true, "cross_seq": 0, "timestamp": 1669075320000000000}], "timestamp_e6": 1669075320000000000}'
        ]

        self.binance_to_bybit = binance_to_bybit(klines=self.binance_msg,
                                                 topic="candle.1.BTCUSDT")
        self.assertListEqual(self.bybit_response, self.binance_to_bybit)
