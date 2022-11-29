import warnings

warnings.simplefilter(action='ignore', category=FutureWarning)
import pandas as pd
import numpy as np
from typing import Tuple, List


def slice_timestamps(
        start_str: str, end_str: str, freq: str,
        slice_length: int) -> List[Tuple[pd.Timestamp, pd.Timestamp]]:
    '''
    Slice a long time series into equally sliced shorter time series and return a list of tuples.
    Each tuple is the start and end timestamp of a particular shorter time series.
    
    Parameters
    ----------
    start_str: str
        start of time series in format yyyy-mm-dd hh-mm-ss
    end_str: str
        end of time series in format yyyy-mm-dd hh-mm-ss
    freq: str
        frequency of time series in format '<n>min'
    slice_length: int
        length of each partial time series
    
    Returns
    -------
    timestamps: List[Tuple[pandas.Timestamp, pandas.Timestamp]]
        list of start end and end timestamps of each partial time series
    '''

    time_series = pd.date_range(start=start_str, end=end_str, freq=freq)
    n_slices = np.ceil(len(time_series) / slice_length)
    partial_series = np.array_split(time_series, n_slices)
    timestamps = [(ts[0], ts[-1]) for ts in partial_series]

    return timestamps
