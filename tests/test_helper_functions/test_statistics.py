import warnings

warnings.simplefilter(action='ignore', category=FutureWarning)
import pandas as pd
import numpy as np
import unittest
from src.helper_functions import statistics


class TestStatistics(unittest.TestCase):

    def setUp(self):
        self.candles = pd.Series({
            (pd.Timestamp('2020-01-01 00:01:00')): 7195.24,
            (pd.Timestamp('2020-01-01 00:02:00')): 7187.67,
            (pd.Timestamp('2020-01-01 00:03:00')): 7184.41,
            (pd.Timestamp('2020-01-01 00:04:00')): 7183.83,
            (pd.Timestamp('2020-01-01 00:05:00')): 7185.54,
            (pd.Timestamp('2020-01-01 00:06:00')): 7179.76,
            (pd.Timestamp('2020-01-01 00:07:00')): 7180.0,
            (pd.Timestamp('2020-01-01 00:08:00')): 7179.9,
            (pd.Timestamp('2020-01-01 00:09:00')): 7179.8,
            (pd.Timestamp('2020-01-01 00:10:00')): 7182.68,
            (pd.Timestamp('2020-01-01 00:11:00')): 7183.00,
        })

    def test_sma(self):
        sma_data = pd.Series([
            0.86538941, 0.11460237, 0.65071004, 0.43218357, 0.02094688,
            0.97276623, 0.88298653, 0.96177265, 0.38298908, 0.26762353
        ])
        sma_result = pd.Series([
            np.nan, np.nan, 0.5435672713839343, 0.3991653233218317,
            0.3679468276251557, 0.4752988927966759, 0.6255665481662437,
            0.939175136740387, 0.7425827526841023, 0.5374617512584611
        ])
        sma_result.name = 'sma_3'

        sma = statistics.sma(data=sma_data, window=3)

        pd.testing.assert_series_equal(sma_result, sma)

    def test_true_range(self):
        tr_data = pd.DataFrame({
            'start': {
                pd.Timestamp('2022-01-01 00:15:00'):
                    pd.Timestamp('2022-01-01 00:00:00'),
                pd.Timestamp('2022-01-01 00:30:00'):
                    pd.Timestamp('2022-01-01 00:15:00'),
                pd.Timestamp('2022-01-01 00:45:00'):
                    pd.Timestamp('2022-01-01 00:30:00')
            },
            'open': {
                pd.Timestamp('2022-01-01 00:15:00'): 46216.93,
                pd.Timestamp('2022-01-01 00:30:00'): 46332.52,
                pd.Timestamp('2022-01-01 00:45:00'): 46375.42
            },
            'high': {
                pd.Timestamp('2022-01-01 00:15:00'): 46527.26,
                pd.Timestamp('2022-01-01 00:30:00'): 46421.27,
                pd.Timestamp('2022-01-01 00:45:00'): 46689.42
            },
            'low': {
                pd.Timestamp('2022-01-01 00:15:00'): 46208.37,
                pd.Timestamp('2022-01-01 00:30:00'): 46236.27,
                pd.Timestamp('2022-01-01 00:45:00'): 46360.19
            },
            'close': {
                pd.Timestamp('2022-01-01 00:15:00'): 46332.51,
                pd.Timestamp('2022-01-01 00:30:00'): 46375.42,
                pd.Timestamp('2022-01-01 00:45:00'): 46610.81
            },
            'volume': {
                pd.Timestamp('2022-01-01 00:15:00'): 386.65709,
                pd.Timestamp('2022-01-01 00:30:00'): 319.99973,
                pd.Timestamp('2022-01-01 00:45:00'): 386.08077
            },
            'end': {
                pd.Timestamp('2022-01-01 00:15:00'):
                    pd.Timestamp('2022-01-01 00:15:00'),
                pd.Timestamp('2022-01-01 00:30:00'):
                    pd.Timestamp('2022-01-01 00:30:00'),
                pd.Timestamp('2022-01-01 00:45:00'):
                    pd.Timestamp('2022-01-01 00:45:00')
            },
            'turnover': {
                pd.Timestamp('2022-01-01 00:15:00'): 17922004.4758951,
                pd.Timestamp('2022-01-01 00:30:00'): 14829190.1550472,
                pd.Timestamp('2022-01-01 00:45:00'): 17967322.8022338
            }
        })

        tr_result = pd.Series({
            pd.Timestamp('2022-01-01 00:15:00'): 318.8899999999994,
            pd.Timestamp('2022-01-01 00:30:00'): 185.0,
            pd.Timestamp('2022-01-01 00:45:00'): 329.2299999999959
        })
        tr_result.name = 'true_range'

        tr = statistics.true_range(data=tr_data)

        pd.testing.assert_series_equal(tr_result, tr)

    def test_avg_true_range(self):
        avg_tr_data = pd.Series({
            pd.Timestamp('2022-01-01 00:15:00'): 318.8899999999994,
            pd.Timestamp('2022-01-01 00:30:00'): 185.0,
            pd.Timestamp('2022-01-01 00:45:00'): 329.2299999999959,
            pd.Timestamp('2022-01-01 01:00:00'): 155.62999999999738,
            pd.Timestamp('2022-01-01 01:15:00'): 193.1800000000003
        })

        avg_tr_result = pd.Series({
            pd.Timestamp('2022-01-01 00:15:00'): np.nan,
            pd.Timestamp('2022-01-01 00:30:00'): np.nan,
            pd.Timestamp('2022-01-01 00:45:00'): 277.7066666666651,
            pd.Timestamp('2022-01-01 01:00:00'): 223.28666666666444,
            pd.Timestamp('2022-01-01 01:15:00'): 226.0133333333312
        })
        avg_tr_result.name = 'avg_true_range_3'

        avg_tr = statistics.avg_true_range(tr=avg_tr_data, window=3)

        pd.testing.assert_series_equal(avg_tr_result, avg_tr)

    def test_get_highs(self):

        highs = pd.Series({
            (pd.Timestamp('2020-01-01 00:05:00')): 7185.54,
            # (pd.Timestamp('2020-01-01 00:10:00')): 7187.68
        })

        get_highs = statistics.get_highs(candles=self.candles, min_int=2)

        pd.testing.assert_series_equal(highs, get_highs)

    def test_get_alternate_highs_lows(self):

        get_highs, get_lows = statistics.get_alternate_highs_lows(
            candles=self.candles, min_int=2)

        highs = pd.Series({
            (pd.Timestamp('2020-01-01 00:05:00')): 7185.54,
            (pd.Timestamp('2020-01-01 00:07:00')): 7180.0
        })

        highs.index.name = 'ts'

        lows = pd.Series({
            (pd.Timestamp('2020-01-01 00:06:00')): 7179.76,
            (pd.Timestamp('2020-01-01 00:09:00')): 7179.8
        })

        lows.index.name = 'ts'

        pd.testing.assert_series_equal(highs, get_highs)
        pd.testing.assert_series_equal(lows, get_lows)
