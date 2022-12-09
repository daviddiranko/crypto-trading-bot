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
