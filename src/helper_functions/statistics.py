import warnings

warnings.simplefilter(action='ignore', category=FutureWarning)
import pandas as pd
from typing import Tuple


def sma(data: pd.Series, window: int, new_col: str = 'sma') -> pd.Series:
    '''
    Calculate simple moving average for a pandas Series.
    
    Parameters
    ----------
    data: pandas.Series
        series to compute sma of.
    window: int
        rolling window for the sma.
    
    new_col: str
        name of the new series. Default = 'sma'
    
    Returns
    -------
    sma: pd.Series
        sma of data with rolling window 
    '''
    sma = data.rolling(window).mean()
    sma.name = '{}_{}'.format(new_col, window)
    return sma


def get_highs(candles: pd.Series, min_int: int) -> pd.Series:
    '''
    Return highs of candles.
    Highs are defined of points with lower min_int successors and predecessors.

    Parameters
    -----------
    candles: pandas.Series
        price series to identify highs and lows in.
    min_int: int
        minimum number of preceeding and successing prices to be lower than a price to be a high

    Returns
    ----------
    highs: pandas.Series
        identified highs
    '''
    highs = candles.loc[candles == candles.rolling(window=2 * min_int + 1,
                                                   center=True).max()]

    # recent_high = candles.iloc[-(min_int - 1):-1].max()
    # recent_high_idx = candles.iloc[-(min_int - 1):-1].idxmax()

    # if maximum of last min_int-1 candles is higher than last high append to highs for a lack of recent history
    # if not highs.empty:
    #     if recent_high > highs.iloc[-1]:
    #         highs.loc[recent_high_idx] = recent_high
    return highs


def get_alternate_highs_lows(candles: pd.Series,
                             min_int: int) -> Tuple[pd.Series, pd.Series]:
    '''
    Get alternating highs and lows.
    Highs are defined of points with lower min_int successors and predecessors.
    Lows are defined of points with highr min_int successors and predecessors.
    If there is no high between two lows, add maximum of candles_open and candles_close between lows as high.
    Follow same procedure for two consecutive highs.

    Parameters
    -----------
    candles: pandas.Series
        price series to identify highs and lows in.
    min_int: int
        minimum number of preceeding and successing prices to be lower than a price to be a high (analogous for lows)

    Returns
    ----------
    highs: pandas.Series
        identified highs
    lows: pandas.Series
        identified lows
    '''

    # calculate highs and lows
    highs = get_highs(candles=candles, min_int=min_int)
    lows = -get_highs(candles=-candles, min_int=min_int)

    # rename indices of highs and lows to ensure equal names
    highs.index.name = 'ts'
    lows.index.name = 'ts'

    # reformat highs and lows as dataframes with index = 'high' or 'low' and timestamp as extra column
    new_lows = lows.reset_index()
    new_lows.index = ['low'] * len(lows)
    new_lows.index.name = 'high_low'
    new_highs = highs.reset_index()
    new_highs.index = ['high'] * len(highs)
    new_highs.index.name = 'high_low'

    # concatenate highs and lows, sort by timestamp and add index as new column
    highs_lows = pd.concat([new_lows,
                            new_highs]).sort_values('ts').reset_index()

    # identify highs and lows that follow the same type (high or low)
    consecutives = highs_lows.loc[highs_lows['high_low'].shift(1) ==
                                  highs_lows['high_low']]

    # iterate through those highs and lows
    # note that each row in consecutives is by definition preceeded by the same type (high or low)
    for row in consecutives.index:

        # price range between consecutive highs or lows
        high_low_range = candles.loc[highs_lows.loc[row - 1]['ts']:highs_lows.
                                     loc[row]['ts']]

        # if it is a low (i.e. two lows in a row) -> add high in between
        if consecutives.loc[row]['high_low'] == 'low':

            # high is largest price between consecutive lows
            new_high = high_low_range.max()
            new_high_idx = high_low_range.idxmax()
            highs.loc[new_high_idx] = new_high

        # if it is a high (i.e. two highs in a row) -> add low in between
        else:
            # low is smallest price between consecutive highs
            new_low = high_low_range.min()
            new_low_idx = high_low_range.idxmin()
            lows.loc[new_low_idx] = new_low

    lows = lows.sort_index()
    highs = highs.sort_index()

    return highs, lows
