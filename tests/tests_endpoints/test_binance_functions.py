import pandas as pd
from typing import List, Dict, Any
import unittest
from src.endpoints.binance_functions import format_historical_klines, binance_to_bybit


class TestBinanceFunctions(unittest.TestCase):

    def setUp(self):

        self.success_message = [[
            1667485500000, '20263.06000000', '20299.79000000', '20259.39000000',
            '20292.91000000', '684.45596000', 1667485559999,
            '13882836.27737160', 13870, '376.94802000', '7645725.78138490', '0'
        ],
                                [
                                    1667485560000, '20289.73000000',
                                    '20300.00000000', '20272.32000000',
                                    '20274.15000000', '520.67525000',
                                    1667485619999, '10561574.03920040', 10654,
                                    '245.74934000', '4984926.95213320', '0'
                                ]]

        self.failure_message = [[]]
        self.success = pd.DataFrame([{
            'start': pd.Timestamp('2022-11-03 14:25:00'),
            'open': 20263.06,
            'high': 20299.79,
            'low': 20259.39,
            'close': 20292.91,
            'volume': 684.45596,
            'end': pd.Timestamp('2022-11-03 14:26:00'),
            'turnover': 13882836.2773716
        }, {
            'start': pd.Timestamp('2022-11-03 14:26:00'),
            'open': 20289.73,
            'high': 20300.0,
            'low': 20272.32,
            'close': 20274.15,
            'volume': 520.67525,
            'end': pd.Timestamp('2022-11-03 14:27:00'),
            'turnover': 10561574.0392004
        }]).set_index('end', drop=False)

        self.failure = pd.DataFrame(columns=[
            'start', 'open', 'high', 'low', 'close', 'volume', 'end', 'turnover'
        ])

    def test_format_historical_klines(self):

        extraction = format_historical_klines(self.success_message)
        failed_extraction = format_historical_klines(self.failure)

        pd.testing.assert_frame_equal(extraction, self.success)
        pd.testing.assert_frame_equal(failed_extraction, self.failure)

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
                                                 topics=["candle.1.BTCUSDT"] *
                                                 len(self.binance_msg))
        self.assertListEqual(self.bybit_response, self.binance_to_bybit)
