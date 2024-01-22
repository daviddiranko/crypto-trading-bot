import warnings

warnings.simplefilter(action='ignore', category=FutureWarning)
import pandas as pd
import numpy as np
import unittest
from src.helper_functions import helper_functions


class TestHelperFunctions(unittest.TestCase):

    def test_slice_timestamps(self):
        timestamps_correct = [(pd.Timestamp('2020-01-01 00:00:00'),
                               pd.Timestamp('2020-03-07 04:00:00')),
                              (pd.Timestamp('2020-03-07 04:01:00'),
                               pd.Timestamp('2020-05-12 08:00:00')),
                              (pd.Timestamp('2020-05-12 08:01:00'),
                               pd.Timestamp('2020-07-17 12:00:00')),
                              (pd.Timestamp('2020-07-17 12:01:00'),
                               pd.Timestamp('2020-09-21 16:00:00')),
                              (pd.Timestamp('2020-09-21 16:01:00'),
                               pd.Timestamp('2020-11-26 20:00:00')),
                              (pd.Timestamp('2020-11-26 20:01:00'),
                               pd.Timestamp('2021-02-01 00:00:00'))]

        timestamps = helper_functions.slice_timestamps(start_str='2020-01-01',
                                                       end_str='2021-02-01',
                                                       freq='1min',
                                                       slice_length=100000)

        self.assertListEqual(timestamps_correct, timestamps)
