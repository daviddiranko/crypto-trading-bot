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
    data_sma = data.dropna()
    sma = data_sma.rolling(window).mean()
    sma = sma.dropna()
    sma.name = '{}_{}'.format(new_col, window)
    return sma


def true_range(data: pd.DataFrame,
               high: str = 'high',
               low: str = 'low',
               close: str = 'close') -> pd.Series:
    '''
    Calculate true range of a DataFrame of candles.
    Definition can be found at https://www.investopedia.com/terms/a/atr.asp

    Parameters
    ----------
    data: pandas.DataFrame
        candle stick data. Each row is one candlestick
    high: str
        column name of high price
    low: str
        column name of low price
    close: str
        column name of close price
    Returns
    -------
    tr: pandas.Series
        true range of each candle
    '''
    tr_parts = ((data[high] - data[low]).abs(),
                (data[high] - data[close].shift(1)).abs(),
                (data[low] - data[close].shift(1)).abs())
    tr = pd.DataFrame(tr_parts).transpose().max(axis=1)
    tr.name = 'true_range'
    return tr


def avg_true_range(tr: pd.Series, window: int) -> pd.Series:
    '''
    Calculate the average true range of a true range of candlestick data
    Definition can be found at https://www.investopedia.com/terms/a/atr.asp

    Parameters
    ----------
    tr: pandas.Series
        true range of candlestick data
    window: int
        window size of rolling average

    Returns
    -------
    avg_tr: pandas.Series
        average true range of tr
    '''
    avg_tr = tr.rolling(window).mean()
    avg_tr.name = 'avg_true_range_{}'.format(window)
    return avg_tr


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

    # store index and values names
    if candles.index.name:
        index_name = candles.index.name
    else:
        index_name = 'index'
    values_name = candles.name

    # reset index to allow later comparison of releative positions
    candles = candles.reset_index(drop=False)

    # calculate highs
    highs = candles.loc[candles[values_name] == candles[values_name].rolling(
        window=2 * min_int + 1, center=True).max()]

    # calculate index comparison list, by offsetting the index by one element
    compare_index = list(highs.index)
    compare_index.pop()
    compare_index.insert(0, 0)

    # if multiple values are equal to the minimum within the window, only take the first one
    highs = highs.loc[highs.index - min_int > compare_index]
    highs = highs.set_index(index_name)

    # recent_high = candles.iloc[-(min_int - 1):-1].max()
    # recent_high_idx = candles.iloc[-(min_int - 1):-1].idxmax()

    # if maximum of last min_int-1 candles is higher than last high append to highs for a lack of recent history
    # if not highs.empty:
    #     if recent_high > highs.iloc[-1]:
    #         highs.loc[recent_high_idx] = recent_high
    return highs[values_name]


def get_highs_diff(candles: pd.Series, min_int: int) -> pd.Series:
    '''
    Return highs of candles.
    Highs are defined as points within the series, where the sign of the derivative changes from positive to negative
    and that are preceeded and succeeded by min_int prices without a change in the sign of the derivative.

    Parameters
    -----------
    candles: pandas.Series
        price series to identify highs and lows in.
    min_int: int
        minimum number of preceeding and successing price derivatives without changing sign

    Returns
    ----------
    highs: pandas.Series
        identified highs
    '''

    # identify prices that are succeeded by min_int rising prices, i.e. positive differential
    # offset the series by 1 to exclude the price of the relative timestamp
    succeeding_falls = candles.diff().sort_index(
        ascending=False).rolling(min_int).max().sort_index().shift(-1) < 0

    # identify prices that are preceeded by min_int falling prices, i.e. negative differential
    preceeding_rises = candles.diff().rolling(min_int).min() > 0

    # calculate highs as points which are preceeded by falling prices and succeeded by rising prices
    highs = candles.loc[succeeding_falls * preceeding_rises.values]

    return highs


def get_alternate_highs_lows(candles: pd.Series, min_int: int, sma_diff: int,
                             min_int_diff: int) -> Tuple[pd.Series, pd.Series]:
    '''
    Get alternating highs and lows.
    Highs are defined of points with lower min_int successors and predecessors OR 
    points, where the sign of the price derivative of the sma changes from positive to negative
    and that are preceeded and succeeded by min_int prices without a change in the sign of the derivative.
    
    Lows are defined of points with highr min_int successors and predecessors OR 
    points, where the sign of the derivative of the sma changes from negative to positive
    and that are preceeded and succeeded by min_int prices without a change in the sign of the derivative.
    
    If there is no high between two lows, add maximum of candles_open and candles_close between lows as high.
    Follow same procedure for two consecutive highs.

    Parameters
    -----------
    candles: pandas.Series
        price series to identify highs and lows in.
    min_int: int
        minimum number of preceeding and successing prices to be lower than a price to be a high (analogous for lows)
    sma_diff: int
        the timeframe of the sma to consider for the derivative based highs and lows
    min_int_diff: int
        minimum number of preceeding and successing price derivatives of the sma without changing sign

    Returns
    ----------
    highs: pandas.Series
        identified highs
    lows: pandas.Series
        identified lows
    '''

    # calculate highs and lows based on maximum / minimum of sliding window
    highs = get_highs(candles=candles, min_int=min_int)
    lows = -get_highs(candles=-candles, min_int=min_int)

    # calculate relevant sma for price derivatives
    sma_difference = sma(data=candles, window=sma_diff)

    # calculate additional highs and lows based on the change of the sign of the derivative in the sma
    highs_diff = get_highs_diff(sma_difference, min_int=min_int_diff)
    lows_diff = -get_highs_diff(-sma_difference, min_int=min_int_diff)
    # get actual high in price data as maximum within sma_diff preceding prices
    highs_diff_indices = [
        candles.loc[:pd.Timestamp(idx)].tail(sma_diff).idxmax()
        for idx in highs_diff.index
    ]
    lows_diff_indices = [
        candles.loc[:pd.Timestamp(idx)].tail(sma_diff).idxmin()
        for idx in lows_diff.index
    ]

    # concatenate both highs and lows
    highs_index = highs.index.append(
        pd.Index(highs_diff_indices)).drop_duplicates().sort_values()
    lows_index = lows.index.append(
        pd.Index(lows_diff_indices)).drop_duplicates().sort_values()

    highs = candles.loc[highs_index]
    lows = candles.loc[lows_index]

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

    # check that highs and lows are not empty for stability
    if not highs.empty and not lows.empty:

        # if last price breaks recent high and last low was before last high, add minimum between last price and last high as low
        if candles[-1] >= highs[-1] and highs.index[-1] > lows.index[-1]:
            last_low_index = candles.loc[highs.index[-1]:].idxmin()
            last_low = candles.loc[highs.index[-1]:].min()
            lows[last_low_index] = last_low

        # if last price breaks recent low and last high was before last low, add maximum between last price and last low as high
        if candles[-1] <= lows[-1] and lows.index[-1] > highs.index[-1]:
            last_high_index = candles.loc[lows.index[-1]:].idxmax()
            last_high = candles.loc[lows.index[-1]:].max()
            highs[last_high_index] = last_high

        lows = lows.sort_index()
        highs = highs.sort_index()

    return highs, lows


def get_slopes_highs_lows(lows: pd.Series, highs: pd.Series,
                          freq: pd.Timedelta) -> pd.Series:
    '''
    Get the slopes of the lines connecting alternating highs and lows.

    Parameters
    ----------
    highs: pandas.Series
        highs of candles, indexed with the according pandas Datetime
    
    lows: pandas.Series
        lows of candles, indexed with the according pandas Datetime
    
    freq: pandas.Timedelta
        increments to consider between underlying price series to calculate the slope of the connecting lines

    Returns
    -------

    highs_lows_slope: pandas.Series
        slopes of the connection lines between highs and lows, indexed with the index of the endpoint of the connection line
    '''

    # concatenate highs and lows and sort by index to get alternating highs and lows
    highs_lows = highs.append(lows).sort_index()

    # create time series of 15 min candles with empty values
    dates = pd.date_range(start=highs_lows.index[0],
                          end=highs_lows.index[-1],
                          freq=freq)
    highs_lows_series = pd.Series(index=dates)

    # fill values of highs and lows
    highs_lows_series.loc[highs_lows.index] = highs_lows

    # linearly interpolate the rest of the values
    highs_lows_interpolate = highs_lows_series.interpolate()
    highs_lows_slope = highs_lows_interpolate.diff().loc[
        highs_lows.index].dropna()

    return highs_lows_slope
