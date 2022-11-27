import warnings

warnings.simplefilter(action='ignore', category=FutureWarning)
import pandas as pd
import numpy as np
import unittest
from src.helper_functions import statistics


class TestStatistics(unittest.TestCase):

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
