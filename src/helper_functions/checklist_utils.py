import warnings

warnings.simplefilter(action='ignore', category=FutureWarning)
import pandas as pd
import numpy as np
from typing import Tuple, List, Any
from sklearn.linear_model import LinearRegression
from src.TradingModel import TradingModel
from src.helper_functions.statistics import get_alternate_highs_lows


def get_trading_window(data: pd.DataFrame,
                       window_size: int = 100,
                       include_entry=True) -> float:
    '''
    Get vertical size of trading screen in points.
    
    Parameters
    ----------
    data: pd.DataFrame
        historical candlestick data
    window_size: int
        number of candles that are present in the screen
    include_entry: bool
        whether to include the last sample within data (i.e. the entry bar)
    
    Returns
    -------
    trading_window: float
        verical size of trading window in points
    '''

    assert 'high' in data.columns
    assert 'low' in data.columns

    # calculate high and low of last "candle_window" candles as a reference point on how to scale visual inspections according to charts
    if include_entry:
        high_trading_window = data.iloc[-window_size:]['high'].max()
        low_trading_window = data.iloc[-window_size:]['low'].min()
    else:
        high_trading_window = data.iloc[-window_size:-1]['high'].max()
        low_trading_window = data.iloc[-window_size:-1]['low'].min()

    trading_window = abs(high_trading_window - low_trading_window)

    return trading_window


def get_sideways(entry_body: float,
                 trading_window: float,
                 sideways_factor: float = 2.0,
                 window_size: int = 100,
                 chart_height: float = 3.2,
                 chart_width: float = 4.2,
                 limit: int = 1500) -> int:
    '''
    Calculate number of sideways candles.
    Dependant on the size of the trading screen, size of the entry bar and a hyperparameter.

    Parameters
    ----------

    entry_body: float
        body of entry bar
    trading_window: float
        vertical size of trading window
    sideways_factor: float
        multiple of of historical candles to incorporate
    window_size: int
        number of candles that are in the trading screen
    chart_height: float
        verical size of trading screen
    chart_width: float
        horizontal size of trading screen
    limit: int
        absolute maximum of sideways to consider

    Returns
    -----------

    sideways_count: int
        number of candles that are in the sideways
    '''

    sideways_count = int(
        np.floor((entry_body / (trading_window + 0.00001)) * chart_height *
                 sideways_factor * (window_size / chart_width)))

    sideways_count = max(sideways_count, 2)
    sideways_count = min(sideways_count, limit)

    return sideways_count


def get_body(data: pd.DataFrame,
             column_1: str,
             column_2: str,
             start: int,
             end: int = 0) -> float:
    '''
    Calculate spread between column_1 and column_2 in the provided history.

    Parameters
    ----------
    data: pd.DataFrame
        historical candlestick data
    column_1: str
        name of column where to take the first value from
    column_2: str
        name of column where to take the second value from
    start: int
        start of the timeframe
    end: int
        end of the timeframe

    Returns
    ---------

    body: pd.Series
        series of difference between column_1 and column_2
    '''
    assert column_1 in data.columns
    assert column_2 in data.columns

    if end > 0:
        body = data.iloc[-start:-end][column_1] - data.iloc[-start:-end][
            column_2]
    else:
        body = data.iloc[-start:][column_1] - data.iloc[-start:][column_2]

    return body


def get_max_spread(data: pd.DataFrame,
                   column_1: str,
                   column_2: str,
                   start: int,
                   end: int = 0) -> float:
    '''
    Calculate maximum spread between column_1 and column_2 in the provided history.

    Parameters
    ----------
    data: pd.DataFrame
        historical candlestick data
    column_1: str
        name of column where to take the maximum value from
    column_2: str
        name of column where to take the minimum value from
    start: int
        start of the timeframe
    end: int
        end of the timeframe
    '''
    assert column_1 in data.columns
    assert column_2 in data.columns

    if end > 0:
        maximum = max(data.iloc[-start:-end][column_1].max(),
                      data.iloc[-start:-end][column_2].max())
        minimum = min(data.iloc[-start:-end][column_1].min(),
                      data.iloc[-start:-end][column_2].min())
    else:
        maximum = max(data.iloc[-start:][column_1].max(),
                      data.iloc[-start:][column_2].max())
        minimum = min(data.iloc[-start:][column_1].min(),
                      data.iloc[-start:][column_2].min())

    spread = maximum - minimum

    return spread


def get_trend_series(
        data: pd.DataFrame,
        entry_bar: pd.Series,
        ref_column: str = 'close') -> Tuple[pd.Series, pd.Timedelta]:
    '''
    check if last row of data is at same time as entry_bar. If not append entry_bar to data.

    Parameters
    ----------
    data: pd.DataFrame
        data where target series is in
    entry_bar: pd.Series
        last data received
    ref_column: str
        column of data that is target series

    Returns
    ----------
    trend_series: pd.Series
        data[ref_column] with appended entry_bar if appropriate.
    time_delta: pd.Timedelta
        time delta between entry bar and last element of trend series
    '''

    assert ref_column in entry_bar.index
    assert ref_column in data.columns

    trend_series = data['close'].copy()
    time_delta = entry_bar.name - data.iloc[-1].name

    # if last timestamp of topic and long term topic are not identical, append last timestamp of topic to long term topic
    if time_delta > pd.Timedelta(minutes=1):
        trend_series[entry_bar.name] = entry_bar[ref_column]

    return trend_series, time_delta


def get_linear_regression(data: pd.Series,
                          start: int,
                          end: int = 0) -> LinearRegression:
    '''
    perform linear regression on a partial series of data.

    Parameters
    ----------
    data: pd.Series
        series to fit the linear regression to
    
    start: int
        first element, counted backwards from end
    
    end: int
        last element, counted backwards from end

    Returns
    --------
    lr_results: LinearRegression
        sklearn linear regression object that is fit to the data
    '''

    # linear regression of sma_24 since reference index
    # scale x-axis between 0 and number of candles
    if end > 0:
        Y = data.iloc[-start:-end]
    else:
        Y = data.iloc[-start:]

    X = np.array(range(len(Y))).reshape(-1, 1)

    # calculate linear regression within sma_24 to identify a potential trend
    lr = LinearRegression()
    lr_results = lr.fit(X, Y)

    return lr_results


def get_smooth(data: pd.Series,
               max_dist: float,
               start: int,
               end: int = 0) -> Tuple[bool, float, float]:
    '''
    Determine if a time series is "smooth".
    The time series is smooth if it only oscilates within a corridor around its linear regression line.
    The size of the coridor is determined by max_dist.

    Parameters
    ----------
    data: pd.Series
        time series to observe
    max_dist: float
        maximum, one-sided width of corridor.
        width is measured by the orthogonal line upon the regression line.
    start: int
        first element of data to incorporate, counted backwards from end
    
    end: int
        last element of data to incorporate, counted backwards from end


    Returns
    ----------
    smooth: bool
        True if data is smooth, False otherwise
    max_dev_dist: float
        maximum absoulte distance of a point within data to the regression line.
    slope: float
        slope of regression line
    
    '''

    # linear regression of sma_8 over sideways candles
    # scale x-axis between 0 and number of candles
    if end > 0:
        data_reduced = data.iloc[-start:-end]
    else:
        data_reduced = data.iloc[-start:]

    X = np.array(range(len(data_reduced))).reshape(-1, 1)

    lr_results = get_linear_regression(data=data, start=start, end=end)
    # extract slope of regression line
    slope = lr_results.coef_[0]

    # determine corridor of sma_8 based on a fixed distance to the regression line
    # determine maximum point spread of sma_8 to its regression line
    # this is the shortest distance of a point to the corridor, i.e. the connection through a 90° angle

    # calculate vertical distance based on 90° angle distance based on the geometry through the regression slope
    alpha = np.arctan(slope)
    y_dist_lr = max_dist / np.cos(alpha)

    # calculate regression line through sideways
    reg_line = pd.Series(lr_results.predict(X), index=data_reduced.index)

    # calculate upper and lower corridor
    upper_limit_sma_8 = reg_line + y_dist_lr
    lower_limit_sma_8 = reg_line - y_dist_lr

    # calculate maximum absolute deviation along y axis
    max_dev = (data_reduced - reg_line).abs().max()

    # calculate shortest distance to regression line of that point (only used to evaluate the model)
    max_dev_dist = (max_dev * np.cos(alpha))

    # calculate points that are either below lower limit or above upper limit
    outliers_above = reg_line.loc[(reg_line > upper_limit_sma_8)]
    outliers_below = reg_line.loc[(reg_line < lower_limit_sma_8)]

    # count all outliers
    num_outliers = len(outliers_above) + len(outliers_below)

    # smooth: data must stay within a fixed corridor along its linear regression throughout the sideways
    smooth = (num_outliers == 0)

    return smooth, max_dev_dist, slope


def get_recent_high_low(data: pd.DataFrame, n: int) -> Tuple[float, float]:
    '''
    Calculate most recent high and low of data.
    A high is a point in data that is not exceeded by its preceeding and successing "n" points.
    Anologously for low.
    Return the last high and low of data according to the above definition

    Parameters
    -----------
    data: pd.Dataframe
        dataset to identify highs and lows in
    n: int
        determines how many preceeding and successing candles a high must exceed (anologously for low)

    Returns
    -----------
    last_low: float
        last low
    last_high: float
        last high
    '''
    # calculate last minimum and maximum before entry bar for drift assessment
    # maximum and minimum is smallest or largest point within the "n_drift" window
    rolling_lows = data.min(axis=1).rolling(n).min()
    rolling_highs = data.max(axis=1).rolling(n).max()

    last_lows = data.min(axis=1).loc[data.min(axis=1) == rolling_lows]
    last_highs = data.max(axis=1).loc[data.max(axis=1) == rolling_highs]

    if len(last_lows) > 0:
        last_low = data.min(axis=1).loc[data.min(
            axis=1) == rolling_lows].iloc[-1]
    else:
        last_low = -np.inf

    if len(last_highs) > 0:
        last_high = data.max(axis=1).loc[data.max(
            axis=1) == rolling_highs].iloc[-1]
    else:
        last_high = np.inf

    return last_low, last_high


def get_abrupt(data: pd.Series,
               n: int = 5,
               threshold: float = 2.0) -> Tuple[bool, pd.Series]:
    '''
    Determine if a time series shows abrupt changes.
    Abrupt changes are points that show both:
    a curvature with absolute value > "threshold" AND
    a change in the derivative

    Parameters
    ----------
    data: pd.Series
        time series to observe
    n: int
        number of points to look back for abruptness
    threshold: float
        threshold for absolute value of curvature
    
    Returns
    --------
    abrupt: bool
        True if data changes abrupt, False otherwise
    curvature: pd.Series
        series that shows the absolute values of the curvature along data
    '''
    # abrupt: change of sign in derivative and absolute value of curvature > 2
    # not allowed across last 5 candles
    derivative_change = (data.shift().diff().iloc[-n:] *
                         data.diff().iloc[-n:]) < 0
    curvature = data.diff().diff().iloc[-n:].abs()
    abrupt = (derivative_change * (curvature > threshold)).sum() > 0

    return abrupt, curvature


def get_volatile(data: pd.Series,
                 num_samples: int,
                 max_curvature: float,
                 start: int,
                 end: int = 0) -> bool:
    '''
    Determine if a time series is "volatile".
    The time series is volatile if there is at least one sample where:
    1. "num_samples" consecutive samples immediately prior and after the sample have the same slope
    2. the absolute value of the curvature at the sample is at least "max_curvature".

    Parameters
    ----------
    data: pd.Series
        time series to observe
    num_samples: int
        number of successors and predecessors without change in slope
    max_curvature: float
        threshold for absolute value of curvature of a sample and its successor to be volatile
    start: int
        first element of data to incorporate, counted backwards from end
    end: int
        last element of data to incorporate, counted backwards from end


    Returns
    ----------
    volatile: bool
        True if data is volatile, False otherwise
    '''

    # True if sign of slope changes between a sample and its predecessor
    slope_changes = (data.diff().shift(1) * data.diff()) < 0

    # True if sign of slope did not change in "num_samples" prior to sample
    consecutive_preceding_slopes = (slope_changes.apply(lambda x: not x)
                                   ).rolling(num_samples).max().shift(1) == 0

    # True if sign of slope did not change in "num_samples" after sample
    consecutive_succeeding_slopes = (
        slope_changes.apply(lambda x: not x)
    ).sort_index(
        ascending=False).rolling(num_samples).max().sort_index().shift(-1) == 0

    # absolute value of curvature at sample
    abs_curvature = data.diff().diff().abs()

    # absolute value of curvature of successor
    abs_curvature_successor = data.diff().diff().abs().shift(-1)

    # True if mean of curvature of sample and its predecessor is at least "max_curvature"
    abs_avg_curvature = (abs_curvature +
                         abs_curvature_successor) / 2 >= max_curvature

    # volatile is if all criteria are true
    if end > 0:
        volatile = (slope_changes * consecutive_preceding_slopes *
                    consecutive_succeeding_slopes *
                    abs_avg_curvature).iloc[-start:-end].fillna(0).max()
    else:
        volatile = (slope_changes * consecutive_preceding_slopes *
                    consecutive_succeeding_slopes *
                    abs_avg_curvature).iloc[-start:].fillna(0).max()

    return volatile


def get_strong(data: pd.Series,
               num_samples: int,
               threshold: float,
               start: int,
               end: int = 0,
               up=True) -> bool:
    '''
    Determine if a time series is "strong".
    The time series is "strong up" if at least "num_samples" of slopes in data exceed "threshold".
    The time series is "strong down" if at least "num_samples" of slopes in data are lower thab "threshold".


    Parameters
    ----------
    data: pd.Series
        time series to observe
    num_samples: int
        number of slopes to compare against threshold
    threshold: float
        threshold for value of slope
    start: int
        first element of data to incorporate, counted backwards from end
    end: int
        last element of data to incorporate, counted backwards from end


    Returns
    ----------
    strong: bool
        True if data is strong, False otherwise
    '''

    # calculate slopes of data
    if end > 0:
        slopes = data.diff().iloc[-start:-end]
    else:
        slopes = data.diff().iloc[-start:]

    # sort slopes starting with largest if up or with smallest if down
    slopes_sorted = slopes.sort_values(ascending=(not up))

    # determine direction of up or down
    dir = 1 if up else -1

    # strong if at least "num_samples" slopes exceed or fall short of threshold, depending on up or down
    strong = dir * slopes_sorted.iloc[num_samples - 1] > dir * threshold

    return strong


def get_flat(data: pd.Series,
             num_samples: int,
             threshold: float,
             start: int,
             end: int = 0) -> bool:
    '''
    Determine if a time series is "flat".
    The time series is "flat" if it is neither "strong down" nor "strong up" 

    Parameters
    ----------
    data: pd.Series
        time series to observe
    num_samples: int
        number of slopes to compare against threshold for "strong"
    threshold: float
        threshold for value of slope for "strong".
        threshold gets positive sign for up and negative sign for down.
    start: int
        first element of data to incorporate, counted backwards from end
    end: int
        last element of data to incorporate, counted backwards from end

    Returns
    ----------
    flat: bool
        True if data is flat, False otherwise
    '''

    # Determine strong up and strong down
    strong_up = get_strong(data=data,
                           num_samples=num_samples,
                           threshold=abs(threshold),
                           start=start,
                           end=end,
                           up=True)
    strong_down = get_strong(data=data,
                             num_samples=num_samples,
                             threshold=-abs(threshold),
                             start=start,
                             end=end,
                             up=False)

    # flat if neither strong up nor strong down
    flat = not (strong_up or strong_down)

    return flat


def get_increasing(data: pd.Series,
                   num_samples: int,
                   num_strong_samples: int,
                   slope_threshold: float,
                   start: int,
                   end: int = 0,
                   accelerating=True,
                   long=True) -> bool:
    '''
    Determine if a time series is "increasing".
    The time series is increasing if 
    1. the slope of at least "num_samples" in the series are increasing AND
    2. within the "num_samples" at least "num_strong_samples" must exceed "slope_threshold"
    The samples must not be consecutive.

    Parameters
    ----------
    data: pd.Series
        time series to observe
    num_samples: int
        number of slopes that must be increasing
    num_strong_samples: int
        number of samples within num_samples that must have a slope larger than "slope_threshold"
    slope_threshold: float
        threshold for slope
    start: int
        first element of data to incorporate, counted backwards from end
    end: int
        last element of data to incorporate, counted backwards from end
    accelerating: bool
        if True consider accelerating time series, otherwise consider slowing time series
    long: bool
        if True consider increasing time series, if False consider decreasing time series
    


    Returns
    ----------
    increasing: bool
        True if data is increasing, False otherwise
    '''

    # determine directions
    dir = 1 if long else -1
    dir_slope = 1 if accelerating else -1

    slope = dir_slope * abs(slope_threshold)

    # instantiate values with direction
    if end > 0:
        values = (dir * data).diff().iloc[-start:-end]
    else:
        values = (dir * data).diff().iloc[-start:]

    count_values = 1

    # instantiate strong slopes
    if values.iloc[0] > dir_slope * slope:
        count_slopes = 1
    else:
        count_slopes = 0

    # iterate through all values to choose as starting point
    for idx, value in values.iteritems():
        count_values2 = 1

        # iterate through all valuest to count all "chains" of increasing slopes
        for _, value2 in values[idx:].iteritems():

            # if next value is larger than previous value, increase counter and set new value
            if value2 > value:
                value = value2
                count_values2 += 1

                # if the value exceeds the threshold, increase the counter
                if value2 > dir_slope * slope:
                    count_slopes += 1

        # identify longest chain of increasing slopes
        count_values = max(count_values, count_values2)

    # increasing is true if longest chain exceeds threshold and strong slopes exceeds threshold
    increasing = (count_values >= num_samples) and (count_slopes >
                                                    num_strong_samples)

    return increasing


def get_sideways_yellow_squares(data: pd.DataFrame,
                                start: int,
                                end: int = 0,
                                column_1: str = 'open',
                                column_2: str = 'close',
                                long=True) -> bool:
    '''
    Determine if a time series shows "sideways".
    i.e. if at least one candle in the history has an open or close price that is above (for long) or below (for short) the open of the entry bar.

    Parameters
    ----------
    data: pd.DataFrame
        data where target series is in
    start: int
        start of the timeframe
    end: int
        end of the timeframe, i.e. entry bar
    column_1: str
        name of column where to take the open value from
    column_2: str
        name of column where to take the close value from
    long: bool
        whether sideways for long or short is required


    Returns
    ----------
    sideways: bool
        True if data shows sideways, False otherwise
    '''

    assert column_1 in data.columns
    assert column_2 in data.columns

    # determine direction of sideways
    dir = 1 if long else -1

    # calculate sideways data
    data_sideways = dir * data[[column_1, column_2]].iloc[-start:-(end + 1)]

    # extract open of entry bar
    if end > 0:
        open_entry_bar = dir * data[column_1].iloc[-end]
    else:
        open_entry_bar = dir * data[column_1].iloc[-1]

    # calculate maximum of open and close
    max_sideways = data_sideways.max().max()

    # determine sideways
    sideways = max_sideways > open_entry_bar

    return sideways


def get_price_phase(data: pd.Series,
                    min_int_highs_lows: int,
                    sma_diff_highs_lows: int,
                    min_int_diff_highs_lows: int,
                    threshold: float,
                    start: int,
                    end: int = 0) -> bool:
    '''
    Determine if a time series shows a "price phase".
    The time series shows a price phase if there is at least one section between consecutive highs and lows 
    within the series that show an absolute move of more than threshold.

    Parameters
    ----------
    data: pd.Series
        time series to observe
    min_int_highs_lows: int
        number of samples to consider for highs and lows
    sma_diff_highs_lows: int
        number of samples to consider for calculating sma in highs and lows
    min_int_diff_highs_lows: int
        number of samples to consider for comparing the sma for highs and lows
    threshold: float
        threshold for point change between highs and lows
    start: int
        first element of data to incorporate, counted backwards from end
    end: int
        last element of data to incorporate, counted backwards from end

    Returns
    ----------
    price_phase: bool
        True if data shows a price phase, False otherwise
    '''

    highs, lows = get_alternate_highs_lows(candles=data,
                                           min_int=min_int_highs_lows,
                                           sma_diff=sma_diff_highs_lows,
                                           min_int_diff=min_int_diff_highs_lows)
    if end > 0:
        index_start = data.index[-start]
        index_end = data.index[-end]
        sorted_highs_lows = pd.concat(
            [highs, lows]).sort_index(ascending=True).loc[index_start:index_end]
    else:
        index_start = data.iloc[-start].index
        sorted_highs_lows = pd.concat(
            [highs, lows]).sort_index(ascending=True).loc[index_start:]

    price_phase = sorted_highs_lows.diff().abs().max() > threshold

    return price_phase


def add_model_stats(model: TradingModel,
                    long: bool,
                    ts: str,
                    key: str,
                    value: Any = 1) -> TradingModel:
    '''
    Add statistics for trading rules to the model stats dictionary to later assign the values to the trades
    '''
    trade_dir = 'long' if long else 'short'
    if key not in model.model_stats.keys():
        model.model_stats[key] = {}

    if ts not in model.model_stats[key].keys():
        model.model_stats[key][ts] = {}

    model.model_stats[key][ts][trade_dir] = value

    return model
