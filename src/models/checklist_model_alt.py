import warnings

warnings.simplefilter(action='ignore', category=FutureWarning)

from typing import Dict, Any
from src.TradingModel import TradingModel
from src.helper_functions.statistics import sma, get_alternate_highs_lows, get_slopes_highs_lows, true_range
import numpy as np
from sklearn.linear_model import LinearRegression
from src.endpoints.bybit_functions import *
import os
from dotenv import load_dotenv

load_dotenv()

BASE_CUR = os.getenv('BASE_CUR')


def checklist_model(model: TradingModel, ticker: str, trading_freq: int):
    '''
    checklist-based trend following model
    '''

    # declare ticker
    # ticker = 'RTYUSD'
    ticker = ticker
    # declare topics
    topic = 'candle.5.{}'.format(ticker)
    long_term_topic = 'candle.5.{}'.format(ticker)
    trend_topic = 'candle.15.{}'.format(ticker)
    short_term_topic = 'candle.1.{}'.format(ticker)
    exit_topic = 'candle.5.{}'.format(ticker)

    # # declare topics
    # topic = 'candle.1.{}'.format(ticker)
    # long_term_topic = 'candle.1.{}'.format(ticker)
    # trend_topic = 'candle.15.{}'.format(ticker)
    # short_term_topic = 'candle.1.{}'.format(ticker)
    # exit_topic = 'candle.1.{}'.format(ticker)

    # initialize checklist counter and total rules counter
    long_checklist = 0
    short_checklist = 0
    core_long_checklist = 0
    core_short_checklist = 0
    checklist = 0
    core_checklist = 0
    rules = 0
    core_rules = 0

    ######################################## PARAMETERS ########################################

    # High and low definition: set number of consecutive candles that must be smaller/larger than high/low
    n_candles = 11
    # n_candles = model.model_args['n_candles']

    # High and low definition: Determine the sma of the trend candles to consider for the calculation of the derivative
    high_low_sma = 8
    # high_low_sma = model.model_args['n_candles']

    # High and low definition: set number of consecutive trend candles where derivative does not change,
    # but derivative changes at the point in the middle
    n_candles_diff = 5
    # n_candles_diff = model.model_args['n_candles']

    # number of preceeding candles that must not be below candle to be minimum for drift assessment
    n_candles_drift = 5

    # Sideways: multiple of length of entry bar to incorporate into the sideways candles
    sideways_factor = 1
    # sideways_factor = model.model_args['param']

    # Sideways for core: multiple of length of entry bar to incorporate into the sideways candles
    sideways_factor_core = 1
    # sideways_factor = model.model_args['param']

    # Sideways: all candles in sideways must be smaller eqal factor times entry bar
    small_bars_50 = 0.5
    # small_bars_50 = model.model_args['param']

    # Sideways: last 2 candles before entry bar must be smaller equal parameter times entry bar
    small_bars_25 = 0.25
    # small_bars_25 = model.model_args['param']

    # Opposite 1/5ths: the wigs of the entry bar must be smaller equal 20% of the candle (High to low)
    opposite_fifths = 0.25
    # opposite_fifths = model.model_args['param']

    # Opposite 1/5ths: the wigs of the entry bar must be smaller equal 20% of the candle (High to low)
    opposite_fifths_2 = 0.8
    # opposite_fifths = model.model_args['param']

    # number of candles to consider for strategy
    candle_window = 100
    # candle_window = model.model_args['candle_window']

    # chart width in Trading iew
    chart_width = 4.2

    # Chart height in TradingView
    chart_height = 3.2

    # minimum amount of calculated sideways candles required for potential entry
    minimum_sideways = 10

    # number of candles before entry candle to watch for drift
    drift_length = 5
    # drift_length = model.model_args['param']

    # open of first drift candle to close of candle prior to entry bar must be smaller than drift_height times body of entry bar
    drift_height = 0.35
    # drift_height = model.model_args['param']

    # amount of drift between last low and open of entrybar relative to body of entry bar to not have drift
    drift_factor = 1.0

    # multiple of body of entry bar that amplitude (i.e. maximum open or close - minimum of open or close) of sideways candles can have
    surprise_factor = 1.0
    # surprise_factor = model.model_args['param']

    # percentage of trading screen height (i.e. maximum high to minimum low within candle_window) the entry bar has to fill to be a surprise.
    surprise_factor_2 = 0.3
    # surprise_factor_2 = model.model_args['param']

    # maximum amplitude of sma8 (blue) during sideways, measured as percentage of trading screen
    blue_amplitude = 0.25
    # blue_amplitude = model.model_args['param']

    # maximum amplitude of sma8 (blue) during sideways, measured as percentage of entry bar body
    blue_amplitude_2 = 0.4

    # Blue increasing: determine number of candles to require a trend in before entering (increase in sma8)
    trend_candles = 3
    # trend_candles = model.model_args['param']

    # High and low definition: last high must be 50% higher than previous high
    # To be a breaking high, 50% of the entry candle body has to above the preceding high
    high_factor = 0.5
    # high_factor = model.model_args['param']

    # High and low definition: set factor that the last low must be above the previous low to be a higher low
    retracement_factor = 0.5
    # retracement_factor = model.model_args['param']

    # Set maximum relative difference between highs / lows to count as support or resistance
    support_resistance_diff = 0.001
    # support_resistance_diff = model.model_args['param']

    # maximum slope of purple for rule 1.10.1
    slope_purple_param = 0.3
    # slope_purple_param = model.model_args['param']

    # maximum slope of purple for rule 1.10.1
    sma_flat_param = 0.3
    # sma_flat_param = model.model_args['param']

    # maximum relative value for true range in true range rule
    tr_max = 20 / 1800
    # tr_max = model.model_args['param']

    # maximum relative slope of sideways, measured relative to size of trading screen
    max_slope_sideways = 0.7
    # max_slope_sideways = model.model_args['param']

    # candles within sideways that if trend in direction of entrybar show a RED FLAG
    max_trend_candles = 4
    count_trend_candles = 5

    # maximum amplitude of consecutive trending candles relative to entrybar
    max_trend_amplitude = 0.75

    # fraction of entry bar that must exceed entry bar channel
    sideways_channel = 0.0

    # determine minimum movement of entry bar in fraction to open price
    minimum_movement = 0.0028

    # maximum slope within last five candles to fulfill the "strong" criterium
    strong_param = 0.5

    # maximum distance between purple and blue and blue and entrybar in relation to current price level
    max_distance_sync = 3 / 1800

    # maximum distance of sma_8 to its regression line relative to size of trading screen
    max_sma_8_dist = 1.0

    # maximum absolute slope of sma_8
    max_slope_blue = 0.8

    # maximum slope of close price of sideways candles
    max_slope_sideways = 0.8

    # tolerance of sma8 exit strategy
    sma_8_exit_tolerance = 3 / 1800

    # absolute threshold for candle in exit strategy to be "sizable"
    sizable_body_exit_abs = 0.5 / 1800

    # relative threshold to trading window for candle in exit strategy to be "sizable"
    sizable_body_exit_rel = 0.02

    # profit threshold to adjust stop loss to trade price
    take_profit_stoploss = 2.0 / 1800

    # set tick size of orders as number of decimal digits
    # 0 rounds on whole numbers, negative numbers round integers on whole "tens"
    tick_size = 1

    ######################################## END PARAMETERS ########################################

    ######################################## DEFINITION VARIABLES ########################################

    # last relevant candles for strategy
    entry_bar = model.market_data.history[topic].iloc[-1]
    last_trend_candle = model.market_data.history[trend_topic].iloc[-1]
    last_short_term_candle = model.market_data.history[short_term_topic].iloc[
        -1]
    last_long_term_candle = model.market_data.history[long_term_topic].iloc[-1]
    last_exit_candle = model.market_data.history[exit_topic].iloc[-1]

    # Only proceed if new 5min candle is received, i.e. ignore 1m candles
    # Remove if actions are performed for 1m candles
    if entry_bar.name <= model.model_storage['entry_bar_time']:
        return None

    # check timedelta between trend topic and topic to ensure that is not larger than 14 minutes
    # if larger, then new topic candle was received before new trend topic and one must wait until new trend topic arrives
    topic_trend_topic_delta = entry_bar.name - last_trend_candle.name

    # check timedelta between long term topic and topic to ensure that is not larger than 4 minutes
    # if larger, then new topic candle was received before new long term topic and one must wait until new long term topic arrives
    topic_long_term_topic_delta = entry_bar.name - last_long_term_candle.name

    # simple moving averages
    sma_24 = sma(model.market_data.history[long_term_topic]['close'], window=24)
    sma_8 = sma(model.market_data.history[long_term_topic]['close'], window=8)

    # calculate various spreads of entry bar
    high_low_1 = abs(entry_bar['high'] - entry_bar['low'])
    low_open_1 = abs(entry_bar['open'] - entry_bar['low'])
    high_open_1 = abs(entry_bar['open'] - entry_bar['high'])
    high_close_1 = abs(entry_bar['high'] - entry_bar['close'])
    open_close_1 = abs(entry_bar['close'] - entry_bar['open'])
    low_close_1 = abs(entry_bar['close'] - entry_bar['low'])

    # calculate body of two candles before entry bar
    body_3_1 = (model.market_data.history[topic].iloc[-3:-1]['close'] -
                model.market_data.history[topic].iloc[-3:-1]['open']).abs()

    # calculate high and low of last "candle_window" candles as a reference point on how to scale visual inspections according to charts
    high_candle_window = model.market_data.history[topic].iloc[-candle_window:][
        'high'].max()
    low_candle_window = model.market_data.history[topic].iloc[-candle_window:][
        'low'].min()
    high_low_candle_window = abs(high_candle_window - low_candle_window)

    # count sideways according to chart visuals
    sideways_count = max(
        int(
            np.floor((open_close_1 /
                      (high_low_candle_window + 0.00001)) * chart_height *
                     sideways_factor * (candle_window / chart_width))), 2)

    # count core sideways (1 x entrybar) according to chart visuals
    sideways_count_core = max(
        int(
            np.floor((open_close_1 /
                      (high_low_candle_window + 0.00001)) * chart_height *
                     sideways_factor_core * (candle_window / chart_width))), 2)

    # calculate the body of the sideways candles
    body_sideway_count_1 = (
        model.market_data.history[topic].iloc[-sideways_count:-1]['close'] -
        model.market_data.history[topic].iloc[-sideways_count:-1]['open']
    ).abs()

    # calculate the body of the core sideways candles
    body_sideway_count_core_1 = (
        model.market_data.history[topic].iloc[-sideways_count_core:-1]['close']
        - model.market_data.history[topic].iloc[-sideways_count_core:-1]['open']
    ).abs()

    long_term_series = model.market_data.history[long_term_topic]['close'].copy(
    )

    # if last timestamp of topic and long term topic are not identical, append last timestamp of topic to long term topic
    if topic_long_term_topic_delta > pd.Timedelta(minutes=1):
        long_term_series[entry_bar.name] = entry_bar['close']

    # calculate alternating highs and lows of trading line
    highs, lows = get_alternate_highs_lows(candles=long_term_series,
                                           min_int=n_candles,
                                           sma_diff=high_low_sma,
                                           min_int_diff=n_candles_diff)

    trend_series = model.market_data.history[trend_topic]['close'].copy()

    # calculate frequency of trend series, the minimum is necessary to prevent distortions during time shifts
    freq = (trend_series.index[1:] - trend_series.index[:-1]).min()

    # if last timestamp of topic and trend topic are not identical, append last timestamp of topic to trend topic
    if topic_trend_topic_delta > pd.Timedelta(minutes=1):
        trend_series[entry_bar.name] = entry_bar['close']

    # calculate alternating highs and lows of trend line
    highs_trend, lows_trend = get_alternate_highs_lows(
        candles=trend_series,
        min_int=n_candles,
        sma_diff=high_low_sma,
        min_int_diff=n_candles_diff)

    # calculate the last resistance line as two consecutive highs that are close together and not succeed by a higher high
    resistances = highs_trend.loc[(
        highs_trend.diff() / highs_trend).abs() <= support_resistance_diff]
    if not resistances.empty:
        highs_over_resistance = highs_trend.loc[highs_trend > (
            resistances[-1] * (1 + 1.1 * support_resistance_diff))]
    else:
        highs_over_resistance = pd.Series()

    # check if highs_over_resistance is not empty for stability of calculation
    if not highs_over_resistance.empty:

        # check if last high that exceeds resistance was prior to establishment of resistance:
        if highs_over_resistance.index[-1] < resistances.index[-1]:
            resistance = resistances[-1] * (1 + 1.1 * support_resistance_diff)
        else:
            resistance = None

    elif not resistances.empty:
        resistance = resistances[-1] * (1 + 1.1 * support_resistance_diff)
    else:
        resistance = None

    # calculate the last support line as two consecutive lows that are close together and not broken by a lower low
    supports = lows_trend.loc[(lows_trend.diff() /
                               lows_trend).abs() <= support_resistance_diff]
    if not supports.empty:
        lows_under_support = lows_trend.loc[lows_trend < (
            supports[-1] * (1 - 1.1 * support_resistance_diff))]
    else:
        lows_under_support = pd.Series()

    # check if lows_under_support is not empty for stability of calculation
    if not lows_under_support.empty:

        # check if last low that breaks support was prior to establishment of support:
        if lows_under_support.index[-1] < supports.index[-1]:
            support = supports[-1] * (1 - 1.1 * support_resistance_diff)
        else:
            support = None
    elif not supports.empty:
        support = supports[-1] * (1 - 1.1 * support_resistance_diff)
    else:
        support = None

    # calculate slopes of connection lines between highs and lows of trend series
    high_low_slopes_trend = get_slopes_highs_lows(lows=lows_trend,
                                                  highs=highs_trend,
                                                  freq=freq)

    # calculate maximum spread between open and close prices of sideways candles
    sideways_count_max = max(
        model.market_data.history[topic].iloc[-sideways_count:-1]['open'].max(),
        model.market_data.history[topic].iloc[-sideways_count:-1]
        ['close'].max())
    sideways_count_min = min(
        model.market_data.history[topic].iloc[-sideways_count:-1]['open'].min(),
        model.market_data.history[topic].iloc[-sideways_count:-1]
        ['close'].min())

    # reference index is first sideways candles
    ref_index = model.market_data.history[topic].index[-sideways_count]

    # linear regression of sma_24 since reference index
    # scale x-axis between 0 and number of candles
    purple = sma_24.loc[ref_index:]
    X_purple = np.array(range(len(purple))).reshape(-1, 1)

    # calculate linear regression within sma_24 to identify a potential trend
    sk_lr_purple = LinearRegression()
    sk_results_purple = sk_lr_purple.fit(X_purple, purple)

    # extract slope of regression line
    slope_purple = sk_results_purple.coef_[0]

    slope_sideways = sma_24.diff().loc[ref_index:]

    # check if at no point 3 candles in a row have a slope of less than -0.3
    slope_sideways_long = ((slope_sideways < -slope_purple_param
                           ).rolling(3).sum() == 3.0).sum() == 0

    # check if at no point 3 candles in a row have a slope of more than 0.3
    slope_sideways_short = ((
        slope_sideways > slope_purple_param).rolling(3).sum() == 3.0).sum() == 0

    # Define increasing (with respect to sma24)

    # increasing: curvature across last 5 candles > 0
    increasing_purple = (sma_24.diff().diff().iloc[-5:].min() > 0)

    # decreasing: curvature across last 5 candles < 0
    decreasing_purple = (sma_24.diff().diff().iloc[-5:].max() < 0)

    # Define smooth, strong, flat and increasing (all with respect to sma8)

    # increasing: curvature across last 5 candles > 0
    increasing_blue = (sma_8.diff().diff().iloc[-5:].min() > 0)

    # decreasing: curvature across last 5 candles < 0
    decreasing_blue = (sma_8.diff().diff().iloc[-5:].max() < 0)

    # filter all time points thar have three consecutive increases or decreases
    # series shows if it was increase or decrease through the sign
    consecutive_increase = sma_8.diff().iloc[-sideways_count:].loc[(
        sma_8.diff().iloc[-sideways_count:] > 0).rolling(3).sum() == 3.0]
    consecutive_decrease = sma_8.diff().iloc[-sideways_count:].loc[(
        sma_8.diff().iloc[-sideways_count:] < 0).rolling(3).sum() == 3.0]

    # concatenate both series and sort by index to get alternating series
    consecutives = pd.concat([consecutive_increase,
                              consecutive_decrease]).sort_index()

    # show change in slope by multiplying each entry (=slope) with its successor
    # a change in the slope is identified by a negative sign (increasing to decreasing or vice versa)
    changing_signs = (consecutives * consecutives.shift(1) < 0).sum()

    # determine last indices that had three consecutive signs in their slopes and
    # first indices that had three consecutive signs in their slope after a shift in slope
    before_indices = consecutives.loc[consecutives *
                                      consecutives.shift(-1) < 0].index
    after_indices = consecutives.loc[
        consecutives * consecutives.shift(1) < 0].index.map(
            lambda x: sma_8.diff().index[sma_8.diff().index < x][-2])

    # determine slopes of prices before and after consecutive change in direction
    slopes_before_change = sma_8.diff().loc[before_indices].reset_index(
        drop=True)
    slopes_after_change = sma_8.diff().loc[after_indices].reset_index(drop=True)

    # determine curvature of price change
    curvatures_at_change = (slopes_after_change - slopes_before_change).abs()

    # linear regression of sma_8 over sideways candles
    # scale x-axis between 0 and number of candles
    sideways_sma_8 = sma_8.iloc[-sideways_count:-1]
    X_sideways_sma_8 = np.array(range(len(sideways_sma_8))).reshape(-1, 1)

    # calculate linear regression within sideways candles to define a corridor for the sma_8
    lr_sideways_sma_8 = LinearRegression()
    lr_sideways_sma_8_results = lr_sideways_sma_8.fit(X_sideways_sma_8,
                                                      sideways_sma_8)

    # extract slope of regression line
    slope_blue = lr_sideways_sma_8_results.coef_[0]

    # determine corridor of sma_8 based on a fixed distance to the regression line
    # the corridor is relative to the size of the trading screen
    # determine maximum point spread of sma_8 to its regression line
    # this is the shortest distance of a point to the corridor, i.e. the connection through a 90° angle
    lr_dist = max_sma_8_dist * high_low_candle_window

    # calculate vertical distance based on 90° angle distance based on the geometry through the regression slope
    alpha = np.arctan(slope_blue)
    y_dist_lr = lr_dist / np.cos(alpha)

    # calculate regression line through sideways
    sma_8_reg_line = pd.Series(lr_sideways_sma_8_results.predict(
        X_sideways_sma_8.reshape(-1, 1)),
                               index=sideways_sma_8.index)

    # calculate upper and lower corridor
    upper_limit_sma_8 = sma_8_reg_line + y_dist_lr
    lower_limit_sma_8 = sma_8_reg_line - y_dist_lr

    # calculate maximum absolute deviation along y axis of sma_8
    max_dev_sma_8 = (sideways_sma_8 - sma_8_reg_line).abs().max()

    # calculate shortest distance to regression line of that point (only used to evaluate the model)
    # calculate relative to the size of the trading screen
    dist_max_dev_sma_8 = (max_dev_sma_8 *
                          np.cos(alpha)) / high_low_candle_window

    # calculate points that are either below lower limit or above upper limit
    outliers_sma_8_above = sma_8_reg_line.loc[(sma_8_reg_line >
                                               upper_limit_sma_8)]
    outliers_sma_8_below = sma_8_reg_line.loc[(sma_8_reg_line <
                                               lower_limit_sma_8)]

    # count all outliers
    num_outliers = len(outliers_sma_8_above) + len(outliers_sma_8_below)

    # smooth: maximum 2 changes in slopes, but only count changes if they persist for at least 3 candles AND curvature at change <2
    # smooth = changing_signs<=2 and (curvatures_at_change>=2).sum()==0

    # smooth: sma_8 must stay within a fixed corridor along its linear regression throughout the sideways
    smooth = (num_outliers == 0)

    # strong: mean of slopes across last 5 candles > 0.5 for long and < -0.5 for short
    strong_long = sma_8.diff().iloc[-5:].mean() > strong_param
    strong_short = sma_8.diff().iloc[-5:].mean() < -strong_param

    # flat: no three candles in a row can have a slope of more than 0.3 or less than -0.3
    flat_increase = ((sma_8.diff().iloc[-sideways_count:-5] >
                      sma_flat_param).rolling(3).sum() == 3.0).sum() == 0
    flat_decrease = ((sma_8.diff().iloc[-sideways_count:-5] <
                      -sma_flat_param).rolling(3).sum() == 3.0).sum() == 0
    flat = flat_increase and flat_decrease

    # calculate true range of second half of sideways, excluding entry bar
    tr = true_range(
        model.market_data.history[topic].iloc[-int((sideways_count + 1) /
                                                   2):-1])

    # calculate mean value of largest three candles
    tr_large = tr.sort_values().iloc[-3:].mean()

    # linear regression over sideways candles
    # scale x-axis between 0 and number of candles
    sideways_candles = model.market_data.history[topic].iloc[-sideways_count:-1]
    X_sideways_candles = np.array(range(len(
        sideways_candles['close']))).reshape(-1, 1)

    # calculate linear regression within sideways candles to identify a potential trend
    lr_sideways = LinearRegression()
    lr_sideways_results = lr_sideways.fit(X_sideways_candles,
                                          sideways_candles['close'])

    # extract slope of regression line
    slope_sideways_lr = lr_sideways_results.coef_[0]

    # calculate total increase of regression line over the sideways
    # y_lr_sideways_start = lr_sideways.predict(X_sideways_candles[0].reshape(1, -1))
    # y_lr_sideways_end = lr_sideways.predict(X_sideways_candles[-1].reshape(1, -1))
    # total_lr_sideways_increase = y_lr_sideways_end - y_lr_sideways_start

    # calculate consecutive candles within sideways that are in direction of entrybar

    # calculate boolean series with blue candles = True and red candles = False
    blue_candles_sideways = (sideways_candles['open'] <
                             sideways_candles['close'])
    red_candles_sideways = (sideways_candles['open'] >
                            sideways_candles['close'])

    if len(blue_candles_sideways) >= count_trend_candles:
        # calculate maximum amount of red / blue candles within reference window
        consecutive_blues = blue_candles_sideways.rolling(
            count_trend_candles).sum().max()

        # # calculate number of rolling windows that are equal to the maximum (this leads to an upper bound on the length of a consecutive trend series)
        # num_consecutive_blues = (blue_candles_sideways.rolling(count_trend_candles).sum() == blue_candles_sideways.rolling(count_trend_candles).sum().max()).sum()

        # # calculate longest consecutive series of increasing candles
        # max_consecutive_blues = int(blue_candles_sideways.rolling(count_trend_candles + num_consecutive_blues -1).sum().max())
        # max_consecutive_blues_index = blue_candles_sideways.rolling(count_trend_candles + num_consecutive_blues -1).sum().idxmax()

        # # calculate amplitude of price movement
        # start_trend_blue = sideways_candles.loc[:max_consecutive_blues_index].iloc[-max_consecutive_blues]['open']
        # end_trend_blue = sideways_candles.loc[:].iloc[-1]['close']
        # amplitude_blue = abs(end_trend_blue - start_trend_blue)

        # calculate maximum positive price movement within 5 candles
        amplitude = (
            sideways_candles['close'] -
            sideways_candles['open']).rolling(count_trend_candles).sum().max()

        if amplitude > 0:
            amplitude_blue = amplitude
        else:
            amplitude_blue = 0

    else:
        amplitude_blue = np.inf
        consecutive_blues = np.inf

    if len(red_candles_sideways) >= count_trend_candles:
        # calculate maximum amount of red / blue candles within reference window
        consecutive_reds = red_candles_sideways.rolling(
            count_trend_candles).sum().max()

        # # calculate number of rolling windows that are equal to the maximum (this leads to an upper bound on the length of a consecutive trend series)
        # num_consecutive_reds = (red_candles_sideways.rolling(count_trend_candles).sum() == red_candles_sideways.rolling(count_trend_candles).sum().max()).sum()

        # # calculate longest consecutive series of increasing candles
        # max_consecutive_reds = int(red_candles_sideways.rolling(count_trend_candles + num_consecutive_reds -1).sum().max())
        # max_consecutive_reds_index = red_candles_sideways.rolling(count_trend_candles + num_consecutive_reds -1).sum().idxmax()

        # # calculate amplitude of price movement
        # start_trend_red = sideways_candles.loc[:max_consecutive_reds_index].iloc[-max_consecutive_reds]['open']
        # end_trend_red = sideways_candles.loc[:max_consecutive_reds_index].iloc[-1]['close']
        # amplitude_red = abs(end_trend_red - start_trend_red)

        # calculate maximum negative price movement within 5 candles
        amplitude = (
            sideways_candles['close'] -
            sideways_candles['open']).rolling(count_trend_candles).sum().min()

        if amplitude < 0:
            amplitude_red = -amplitude
        else:
            amplitude_red = 0

    else:
        amplitude_red = np.inf
        consecutive_reds = np.inf

    # calculate reference window for rule 3.3.2
    reference_candles = min(sideways_count, 10)

    # calculate maximum and minimum prices within reference window for rule 3.3.2
    min_reference = min(
        model.market_data.history[topic].iloc[-reference_candles:-1]
        ['open'].min(),
        model.market_data.history[topic].iloc[-reference_candles:-1]
        ['close'].min())
    max_reference = max(
        model.market_data.history[topic].iloc[-reference_candles:-1]
        ['open'].max(),
        model.market_data.history[topic].iloc[-reference_candles:-1]
        ['close'].max())

    # calculate last minimum and maximum before entry bar for drift assessment
    rolling_mins = sideways_candles[[
        'open', 'close'
    ]].min(axis=1).rolling(n_candles_drift).min()
    rolling_maxs = sideways_candles[[
        'open', 'close'
    ]].max(axis=1).rolling(n_candles_drift).max()

    last_mins = sideways_candles[[
        'open', 'close'
    ]].min(axis=1).loc[sideways_candles[['open', 'close']].min(
        axis=1) == rolling_mins]
    last_maxs = sideways_candles[[
        'open', 'close'
    ]].max(axis=1).loc[sideways_candles[['open', 'close']].max(
        axis=1) == rolling_maxs]

    if len(last_mins) > 0:
        last_min = sideways_candles[[
            'open', 'close'
        ]].min(axis=1).loc[sideways_candles[['open', 'close']].min(
            axis=1) == rolling_mins].iloc[-1]
    else:
        last_min = -np.inf

    if len(last_maxs) > 0:
        last_max = sideways_candles[[
            'open', 'close'
        ]].max(axis=1).loc[sideways_candles[['open', 'close']].max(
            axis=1) == rolling_maxs].iloc[-1]
    else:
        last_max = np.inf

    ######################################## END DEFINITION VARIABLES ########################################

    ######################################## EXIT STRATEGY ########################################

    # identify last trade
    if model.account.executions[ticker].keys():
        last_trade = model.account.executions[ticker][list(
            model.account.executions[ticker].keys())[-1]]

    # set stop loss as low price of entry candle
    stop_loss_long = entry_bar['low']
    stop_loss_short = entry_bar['high']

    take_profit_long = None
    take_profit_short = None

    # exit strategy for long side
    if (model.account.positions[ticker]['size'] >
            0.0) and model.account.positions[ticker]['side'] == 'Buy':

        new_stop_loss_long = np.round(
            max(model.model_storage['entry_close_1_long'],
                model.model_storage['entry_open_1_long']) -
            0.5 * model.model_storage['entry_open_close_1_long'], tick_size)

        # check if last candle is in the profit zone, otherwise increase exit candle counter
        if last_exit_candle['close'] < last_trade['price']:
            model.model_storage['exit_candles'] += 1

        # if the last close price is below the sma_8 - some tolerance, close position
        if (last_exit_candle['close'] <
            (sma_8[-1] - sma_8_exit_tolerance * last_exit_candle['close'])):
            model.account.place_order(
                symbol=ticker,
                side='Sell',
                qty=np.ceil(model.account.positions[ticker]['size']),
                order_type='Market',
                stop_loss=None,
                take_profit=None,
                reduce_only=True)

        # if after 3 candles the trade is still not in the profit zone and the last candle is red, exit the trade
        elif (model.model_storage['exit_candles'] >=
              3) and (last_exit_candle['close'] < last_exit_candle['open']):
            model.account.place_order(
                symbol=ticker,
                side='Sell',
                qty=np.ceil(model.account.positions[ticker]['size']),
                order_type='Market',
                stop_loss=None,
                take_profit=None,
                reduce_only=True)

        # if the last closing price is above the trade price + 0.25 * body of entry bar
        # or above the trade price + 5 points, adjust stop loss to the trade price + the trading fee
        elif (
            ((last_exit_candle['close'] > np.round(
                last_trade['price'] + 0.1 *
                model.model_storage['entry_open_close_1_long'], tick_size)) or
             (last_exit_candle['close'] > np.round(
                 last_trade['price'] +
                 last_exit_candle['close'] * take_profit_stoploss, tick_size)))
                and (np.round(last_trade['price'] + 0.1, tick_size) >
                     model.account.positions[ticker]['stop_loss'])):

            model.account.set_stop_loss(symbol=ticker,
                                        side='Buy',
                                        stop_loss=np.round(
                                            last_trade['price'] + 0.1,
                                            tick_size))

            # check if open of candle was above trade price and candle is blue candle, then add it as first higher low
            if (min(last_exit_candle['open'], last_exit_candle['close']) >=
                    last_trade['price']) and (last_exit_candle['close'] >
                                              last_exit_candle['open']):
                if len(model.model_storage['exit_long_higher_lows']) == 0:
                    model.model_storage['exit_long_higher_lows'].append(
                        min(last_exit_candle['open'],
                            last_exit_candle['close']))
                elif min(
                        last_exit_candle['open'], last_exit_candle['close']
                ) and (last_exit_candle['close'] > last_exit_candle['open']
                      ) < model.model_storage['exit_long_higher_lows'][-1]:
                    model.model_storage['exit_long_higher_lows'].append(
                        min(last_exit_candle['open'],
                            last_exit_candle['close']))

        # otherwise, increase stop loss to the traded price minus 0.5 times the entry body
        elif (new_stop_loss_long < last_exit_candle['close']) and (
                new_stop_loss_long >
                model.account.positions[ticker]['stop_loss']):

            model.account.set_stop_loss(symbol=ticker,
                                        side='Buy',
                                        stop_loss=new_stop_loss_long)

        # if stop loss is already in the profit zone:
        # track higher lows and exit as soon as 2 lows are broken
        # only count candles that have "sizable" body
        elif (
            (last_trade['price'] < model.account.positions[ticker]['stop_loss'])
                and (abs(last_exit_candle['open'] - last_exit_candle['close']) >
                     min(sizable_body_exit_rel * high_low_candle_window,
                         sizable_body_exit_abs * last_exit_candle['close']))):

            # set reference for higher low
            if len(model.model_storage['exit_long_higher_lows']) > 0:
                higher_low = model.model_storage['exit_long_higher_lows'][-1]
            else:
                higher_low = 0

            # if new candle is higher low and candle is blue, add to higher lows list
            if ((last_exit_candle['open'] > higher_low) and
                (last_exit_candle['close'] > higher_low) and
                (last_exit_candle['close'] > last_exit_candle['open'])):

                model.model_storage['exit_long_higher_lows'].append(
                    min(last_exit_candle['open'], last_exit_candle['close']))

                # if higher lows list exceeds 2, pop first low as only last two are relevant
                # and increase stop loss to first higher low
                if len(model.model_storage['exit_long_higher_lows']) > 2:

                    model.model_storage['exit_long_higher_lows'].pop(0)

                    # model.account.set_stop_loss(symbol=ticker,
                    #                         side='Buy',
                    #                         stop_loss=np.round(model.model_storage['exit_long_higher_lows'][0] + 0.1, tick_size))

            # if new candle is not a higher low and breaks the second highest low, exit the trade
            elif len(model.model_storage['exit_long_higher_lows']) > 1:
                if min(last_exit_candle['open'], last_exit_candle['close']
                      ) < model.model_storage['exit_long_higher_lows'][-2]:
                    model.account.place_order(
                        symbol=ticker,
                        side='Sell',
                        qty=np.ceil(model.account.positions[ticker]['size']),
                        order_type='Market',
                        stop_loss=None,
                        take_profit=None,
                        reduce_only=True)

        # update last received candle to current candle
        model.model_storage['entry_bar_time'] = model.market_data.history[
            topic].iloc[-1].name

        # exit function since position is still open
        return None

    # exit strategy for the short side
    if (model.account.positions[ticker]['size'] >
            0.0) and model.account.positions[ticker]['side'] == 'Sell':

        new_stop_loss_short = np.round(
            min(model.model_storage['entry_close_1_short'],
                model.model_storage['entry_open_1_short']) +
            0.5 * model.model_storage['entry_open_close_1_short'], tick_size)

        # check if last candle is in the profit zone, otherwise increase exit candle counter
        if last_exit_candle['close'] > last_trade['price']:
            model.model_storage['exit_candles'] += 1

        # if there are three highs in a row or the last price is above the sma_8 + some tolerance, close position
        if (last_exit_candle['close'] >
            (sma_8[-1] + sma_8_exit_tolerance * last_exit_candle['close'])):
            model.account.place_order(
                symbol=ticker,
                side='Buy',
                qty=np.ceil(model.account.positions[ticker]['size']),
                order_type='Market',
                stop_loss=None,
                take_profit=None,
                reduce_only=True)

        # if after 3 candles the trade is still not in the profit zone and last candle is blue, exit the trade
        elif (model.model_storage['exit_candles'] >=
              3) and (last_exit_candle['close'] > last_exit_candle['open']):
            model.account.place_order(
                symbol=ticker,
                side='Buy',
                qty=np.ceil(model.account.positions[ticker]['size']),
                order_type='Market',
                stop_loss=None,
                take_profit=None,
                reduce_only=True)

        # if the last closing price is below the trade price - 0.25 * body of entry bar
        # or below the trade price - 5 points, adjust the stop loss to the trade price - the trading fee
        elif (
            ((last_exit_candle['close'] < np.round(
                last_trade['price'] - 0.1 *
                model.model_storage['entry_open_close_1_short'], tick_size)) or
             (last_exit_candle['close'] < np.round(
                 last_trade['price'] -
                 last_exit_candle['close'] * take_profit_stoploss, tick_size)))
                and (np.round(last_trade['price'] - 0.1, tick_size) <
                     model.account.positions[ticker]['stop_loss'])):

            model.account.set_stop_loss(symbol=ticker,
                                        side='Sell',
                                        stop_loss=np.round(
                                            last_trade['price'] - 0.1,
                                            tick_size))

            # check if open and close of candle was below trade price and candle was red, then add it as first lower high
            if ((max(last_exit_candle['open'], last_exit_candle['close']) <=
                 last_trade['price']) and
                (last_exit_candle['open'] > last_exit_candle['close'])):

                if len(model.model_storage['exit_short_lower_highs']) == 0:
                    model.model_storage['exit_short_lower_highs'].append(
                        max(last_exit_candle['open'],
                            last_exit_candle['close']))
                elif max(
                        last_exit_candle['open'], last_exit_candle['close']
                ) > model.model_storage['exit_short_lower_highs'][-1] and (
                        last_exit_candle['open'] > last_exit_candle['close']):
                    model.model_storage['exit_short_lower_highs'].append(
                        max(last_exit_candle['open'],
                            last_exit_candle['close']))

        # otherwise, decrease stop loss to the traded price plus 0.5 times the entry body
        elif ((new_stop_loss_short > last_exit_candle['close']) and
              (new_stop_loss_short <
               model.account.positions[ticker]['stop_loss'])):

            model.account.set_stop_loss(symbol=ticker,
                                        side='Sell',
                                        stop_loss=new_stop_loss_short)

        # if stop loss is already in the profit zone:
        # track lower highs and exit as soon as 2 highs are broken
        # only count candles that have "sizable" body
        elif (
            (last_trade['price'] > model.account.positions[ticker]['stop_loss'])
                and (abs(last_exit_candle['open'] - last_exit_candle['close']) >
                     min(sizable_body_exit_rel * high_low_candle_window,
                         sizable_body_exit_abs * last_exit_candle['close']))):

            # set reference for lower high
            if len(model.model_storage['exit_short_lower_highs']) > 0:
                lower_high = model.model_storage['exit_short_lower_highs'][-1]
            else:
                lower_high = np.inf

            # if new candle is lower high and candle is red, add to lower highs list
            if ((last_exit_candle['open'] < lower_high) and
                (last_exit_candle['close'] < lower_high) and
                (last_exit_candle['open'] > last_exit_candle['close'])):

                model.model_storage['exit_short_lower_highs'].append(
                    max(last_exit_candle['open'], last_exit_candle['close']))

                # if higher lows list exceeds 2, pop first low as only last two are relevant
                # and decrease stop loss to first lower high
                if len(model.model_storage['exit_short_lower_highs']) > 2:

                    model.model_storage['exit_short_lower_highs'].pop(0)

                    # model.account.set_stop_loss(symbol=ticker,
                    #                         side='Sell',
                    #                         stop_loss=np.round(model.model_storage['exit_short_lower_highs'][0] - 0.1, tick_size))

            # if new candle is not a higher low and breaks the second highest low, exit the trade
            elif len(model.model_storage['exit_short_lower_highs']) > 1:
                if max(last_exit_candle['open'], last_exit_candle['close']
                      ) > model.model_storage['exit_short_lower_highs'][-2]:
                    model.account.place_order(
                        symbol=ticker,
                        side='Buy',
                        qty=np.ceil(model.account.positions[ticker]['size']),
                        order_type='Market',
                        stop_loss=None,
                        take_profit=None,
                        reduce_only=True)

        # update last received candle to current candle
        model.model_storage['entry_bar_time'] = model.market_data.history[
            topic].iloc[-1].name

        # exit function since position is still open
        return None

    ######################################## END EXIT STRATEGY ########################################

    # only trade during trading hours (8:30 - 16:00)
    if (entry_bar.name.hour * 60 + entry_bar.name.minute <=
            510) or (entry_bar.name.hour * 60 + entry_bar.name.minute >= 960):
        return None

    # only trade if new data from topic is received
    # and topic, long term topic and trend topic data have arrived if all are expected
    if (entry_bar.name > model.model_storage['entry_bar_time']
       ) and topic_trend_topic_delta < pd.Timedelta(
           minutes=15) and topic_long_term_topic_delta < pd.Timedelta(
               minutes=5):

        ################################ REMOVE IN PRODUCTION ####################################################################

        # calculate timestamp to correctly index additional information to display in the analysis excel file
        ts = str(entry_bar.name)

        # get next available timestamp
        # short_term_history_index = model.account.simulation_data.loc[model.account.simulation_data.index.get_level_values(1)=='candle.1.{}'.format(ticker)].index
        # exec_time_index = short_term_history_index[short_term_history_index.get_level_values(0)>entry_bar.name][0]

        # ts = model.account.simulation_data.loc[exec_time_index]['start']

        #######################################################################################################################

        # update last received candle to current candle
        model.model_storage['entry_bar_time'] = model.market_data.history[
            topic].iloc[-1].name

        ######################################## CHECKLIST LONG ########################################

        #################### 1 TREND ####################

        # 1.1 Higher lows: last low must be higher than previous low
        # check if there are at least one high and two lows for stability of calculations
        # rules+=1
        if len(lows_trend) > 1 and not highs_trend.empty:

            # higher lows
            if lows_trend.iloc[-1] > lows_trend.iloc[-2]:
                # long_checklist+=1

                if '1.1' not in model.model_stats.keys():
                    model.model_stats['1.1'] = {}

                model.model_stats['1.1'][ts] = {}
                model.model_stats['1.1'][ts]['long'] = 1

        # 1.2 Higher lows with retracement: last low must be higher than previous low + retracement_factor * difference between last high and second last low
        # check if there are at least one high and two lows for stability of calculations
        # rules+=1
        if len(lows_trend) > 1 and not highs_trend.empty:

            # higher lows, but retracement of last low of maximum retracement_factor x difference between last high and second last low
            if lows_trend.iloc[-1] > lows_trend.iloc[-2] + abs(
                    highs_trend.iloc[-1] -
                    lows_trend.iloc[-2]) * (1 - retracement_factor):
                # long_checklist+=1

                if '1.2' not in model.model_stats.keys():
                    model.model_stats['1.2'] = {}

                model.model_stats['1.2'][ts] = {}
                model.model_stats['1.2'][ts]['long'] = abs(
                    highs_trend.iloc[-1] -
                    lows_trend.iloc[-1]) / abs(highs_trend.iloc[-1] -
                                               lows_trend.iloc[-2])

        # 1.3 Breaking of a significant high
        # check if there is at least one for stability of calculations
        rules += 1
        if not highs_trend.empty:

            # entry bar has to be above the preceding high
            if highs_trend.iloc[-1] < entry_bar['close']:
                long_checklist += 1

                if '1.3' not in model.model_stats.keys():
                    model.model_stats['1.3'] = {}

                model.model_stats['1.3'][ts] = {}
                model.model_stats['1.3'][ts]['long'] = 1

        # 1.4 Breaking of a significant high (50% of entry bar): 50% of the entry bar must be above last high
        # check if there are is at least one high for stability of calculations
        # rules += 1
        if not highs_trend.empty:

            # at least the "high_factor" fraction of the body of the entry bar has to be above the preceding high
            if highs_trend.iloc[-1] + high_factor * open_close_1 < entry_bar[
                    'close']:
                # long_checklist += 1

                if '1.4' not in model.model_stats.keys():
                    model.model_stats['1.4'] = {}

                model.model_stats['1.4'][ts] = {}
                model.model_stats['1.4'][ts]['long'] = (
                    entry_bar['close'] - highs_trend.iloc[-1]) / open_close_1

        # # 1.5 breaking of a resistance line:
        # # check if resistance exists for stability of calculation
        # # rules += 1
        # if resistance:
        #     if entry_bar['close']>resistance:
        #         # long_checklist += 1

        #         if '1.5' not in model.model_stats.keys():
        #             model.model_stats['1.5']={}

        #         model.model_stats['1.5'][ts] = {}
        #         model.model_stats['1.5'][ts]['long'] = resistance

        # # 1.6 Higher high: last high must exceed second last high
        # # check if there are at least two highs for stability of calculations
        # # rules += 1
        # if len(highs_trend)>1:
        #     if highs_trend.iloc[-1] > highs_trend.iloc[-2]:
        #         # long_checklist += 1

        #         if '1.6' not in model.model_stats.keys():
        #             model.model_stats['1.6']={}

        #         model.model_stats['1.6'][ts] = {}
        #         model.model_stats['1.6'][ts]['long'] = 1

        # # 1.7 Time phase after Price phase: Only enter after a time phase, predecessed by a price phase
        # # check if there are at least two slopes for stability of calculations
        # # rules += 1
        # if len(high_low_slopes_trend)>1:
        #     if high_low_slopes_trend[-1]<0 and high_low_slopes_trend[-2]>0:
        #         # long_checklist += 1

        #         if '1.7' not in model.model_stats.keys():
        #             model.model_stats['1.7']={}

        #         model.model_stats['1.7'][ts] = {}
        #         model.model_stats['1.7'][ts]['long'] = 1

        # # 1.8 Price phase stronger than time phase: slope of price phase must be larger than slope of time phase
        # # check if there are at least two slopes for stability of calculations
        # # rules += 1
        # if len(high_low_slopes_trend)>1:
        #     if abs(high_low_slopes_trend[-1]) < abs(high_low_slopes_trend[-2]):
        #         # checklist += 1

        #         if '1.8' not in model.model_stats.keys():
        #             model.model_stats['1.8']={}

        #         model.model_stats['1.8'][ts] = {}
        #         model.model_stats['1.8'][ts]['long'] = high_low_slopes_trend[-2]
        #         model.model_stats['1.8'][ts]['short'] = high_low_slopes_trend[-2]

        # 1.9 Above purple: close of entry bar must be above 24 sma (Non-negotiable)
        core_rules += 1
        if sma_24[-1] < entry_bar['close']:
            core_long_checklist += 1

            if '1.9' not in model.model_stats.keys():
                model.model_stats['1.9'] = {}

            model.model_stats['1.9'][ts] = {}
            model.model_stats['1.9'][ts]['long'] = 1

        # 1.10.1 Curvature purple: slope of regression flat or in direction of trade
        rules += 1
        if (slope_purple /
                high_low_candle_window) * candle_window > -slope_purple_param:
            long_checklist += 1

            if '1.10.1' not in model.model_stats.keys():
                model.model_stats['1.10.1'] = {}

            model.model_stats['1.10.1'][ts] = {}
            model.model_stats['1.10.1'][ts]['long'] = (
                slope_purple / high_low_candle_window) * candle_window

        # # 1.10.2 Curvature purple: slope of regression flat or in direction of trade
        # # check if at no point 3 candles in a row have a slope of less than -0.3
        # # rules += 1
        # if slope_sideways_long:
        #     # long_checklist += 1

        #     if '1.10.2' not in model.model_stats.keys():
        #         model.model_stats['1.10.2']={}

        #     model.model_stats['1.10.2'][ts] = {}
        #     model.model_stats['1.10.2'][ts]['long'] = 1

        # 1.10.3 Purple not slowing
        # check if curvature of last 5 points is not negative
        rules += 1
        if not decreasing_purple:
            long_checklist += 1

            if '1.10.3' not in model.model_stats.keys():
                model.model_stats['1.10.3'] = {}

            model.model_stats['1.10.3'][ts] = {}
            model.model_stats['1.10.3'][ts]['long'] = 1

        # # 1.11 Above blue: close of entry bar must be above sma8
        # # rules += 1
        # if sma_8[-1] < entry_bar['close']:
        #     # long_checklist += 1

        #     if '1.11' not in model.model_stats.keys():
        #         model.model_stats['1.11']={}

        #     model.model_stats['1.11'][ts] = {}
        #     model.model_stats['1.11'][ts]['long'] = 1

        # # 1.12.1 Curvature of blue:
        # # strong
        # # rules += 1
        # if (strong_long):
        #     # long_checklist += 1

        #     if '1.12.1' not in model.model_stats.keys():
        #         model.model_stats['1.12.1']={}

        #     model.model_stats['1.12.1'][ts] = {}
        #     model.model_stats['1.12.1'][ts]['long'] = 1

        # # 1.12.2 Curvature of blue:
        # # smooth
        # # rules += 1
        # if (smooth):
        #     # checklist += 1

        #     if '1.12.2' not in model.model_stats.keys():
        #         model.model_stats['1.12.2']={}

        #     model.model_stats['1.12.2'][ts] = {}
        #     model.model_stats['1.12.2'][ts]['long'] = dist_max_dev_sma_8
        #     model.model_stats['1.12.2'][ts]['short'] = dist_max_dev_sma_8

        # # 1.12.3 Curvature of blue:
        # # flat
        # # rules += 1
        # if (flat):
        #     # checklist += 1

        #     if '1.12.3' not in model.model_stats.keys():
        #         model.model_stats['1.12.3']={}

        #     model.model_stats['1.12.3'][ts] = {}
        #     model.model_stats['1.12.3'][ts]['long'] = 1
        #     model.model_stats['1.12.3'][ts]['short'] = 1

        # # 1.12.4 Curvature of blue:
        # # increasing
        # # rules += 1
        # if (increasing):
        #     # long_checklist += 1

        #     if '1.12.4' not in model.model_stats.keys():
        #         model.model_stats['1.12.4']={}

        #     model.model_stats['1.12.4'][ts] = {}
        #     model.model_stats['1.12.4'][ts]['long'] = 1

        # # 1.12.5 slope of blue:
        # # slope_blue
        # # rules += 1
        # if (slope_blue<max_slope_blue):
        #     # long_checklist += 1

        #     if '1.12.5' not in model.model_stats.keys():
        #         model.model_stats['1.12.5']={}

        #     model.model_stats['1.12.5'][ts] = {}
        #     model.model_stats['1.12.5'][ts]['long'] = slope_blue

        # 1.12.6 volatility of blue:
        # amplitude of blue within sideways relative to entry bar
        rules += 1
        if (sma_8.iloc[-sideways_count:].max() - sma_8.iloc[-sideways_count:].
                min()) / open_close_1 <= blue_amplitude_2:
            checklist += 1

            if '1.12.6' not in model.model_stats.keys():
                model.model_stats['1.12.6'] = {}

            model.model_stats['1.12.6'][ts] = {}
            model.model_stats['1.12.6'][ts]['long'] = (
                sma_8.iloc[-sideways_count:].max() -
                sma_8.iloc[-sideways_count:].min()) / open_close_1
            model.model_stats['1.12.6'][ts]['short'] = (
                sma_8.iloc[-sideways_count:].max() -
                sma_8.iloc[-sideways_count:].min()) / open_close_1

        # 1.12.7 amplitude of blue must not exceed fixed percentage of trading screen
        rules += 1
        if (sma_8.iloc[-sideways_count:].max() -
                sma_8.iloc[-sideways_count:].min()
           ) <= blue_amplitude * high_low_candle_window:
            checklist += 1

            if '1.12.7' not in model.model_stats.keys():
                model.model_stats['1.12.7'] = {}

            model.model_stats['1.12.7'][ts] = {}
            model.model_stats['1.12.7'][ts]['long'] = (
                sma_8.iloc[-sideways_count:].max() -
                sma_8.iloc[-sideways_count:].min()) / high_low_candle_window
            model.model_stats['1.12.7'][ts]['short'] = (
                sma_8.iloc[-sideways_count:].max() -
                sma_8.iloc[-sideways_count:].min()) / high_low_candle_window

        # 1.12.8 blue not slowing
        # check if curvature of last 5 points is not negative
        rules += 1
        if not decreasing_blue:
            long_checklist += 1

            if '1.12.8' not in model.model_stats.keys():
                model.model_stats['1.12.8'] = {}

            model.model_stats['1.12.8'][ts] = {}
            model.model_stats['1.12.8'][ts]['long'] = 1

        ###################### END 1 TREND ####################

        ###################### 2 TIME ####################

        # 2.1 Significant sideways (1-2 times of entry bar): sideways must be at most small_bars_50 times entry bar (Non-negotiable times 1 of entry bar)
        # 2.2 Small bars in sideways: All sideway candles must be smaller equal 50% of entry bar (Non-negotiable)
        rules += 1
        # core_rules += 1
        if (body_sideway_count_core_1 >= small_bars_50 * high_low_1).sum() == 0:
            checklist += 1
            # core_checklist += 1

            if '2.2' not in model.model_stats.keys():
                model.model_stats['2.2'] = {}

            model.model_stats['2.2'][ts] = {}
            model.model_stats['2.2'][ts][
                'long'] = body_sideway_count_core_1.max()
            model.model_stats['2.2'][ts][
                'short'] = body_sideway_count_core_1.max()

        # 2.3 Small bars in sideways: The two candles before the entry bar must be smaller equal 25% of the entry bar (Non-negotiable)
        rules += 1
        # core_rules += 1
        if (body_3_1 >= small_bars_25 * high_low_1).sum() == 0:
            checklist += 1
            # core_checklist += 1

            if '2.3' not in model.model_stats.keys():
                model.model_stats['2.3'] = {}

            model.model_stats['2.3'][ts] = {}
            model.model_stats['2.3'][ts]['long'] = body_3_1.max()
            model.model_stats['2.3'][ts]['short'] = body_3_1.max()

        # # 2.4 Volatility: Looking at last 20 candles excluding entry bar
        # # Mean value of largest 3 true ranges must be lower than tr_max * close of entry bar
        # # rules += 1
        # if tr_large < (tr_max * entry_bar['close']):
        #     # checklist += 1

        #     if '2.4' not in model.model_stats.keys():
        #         model.model_stats['2.4']={}

        #     model.model_stats['2.4'][ts] = {}
        #     model.model_stats['2.4'][ts]['long'] = tr_large
        #     model.model_stats['2.4'][ts]['short'] = tr_large

        # # 2.5.1 Purple and Blue in Sync: Small distance between sma8 and sma24 at entrybar
        # # rules += 1
        # if abs(sma_8.iloc[-1] - sma_24.iloc[-1]) < max_distance_sync*entry_bar['open']:
        #     # checklist += 1

        #     if '2.5.1' not in model.model_stats.keys():
        #         model.model_stats['2.5.1']={}

        #     model.model_stats['2.5.1'][ts] = {}
        #     model.model_stats['2.5.1'][ts]['long'] = sma_8.iloc[-1] - sma_24.iloc[-1]
        #     model.model_stats['2.5.1'][ts]['short'] = sma_8.iloc[-1] - sma_24.iloc[-1]

        # # 2.5.2 Blue and Entry bar in Sync: Small distance between sma8 and entrybar
        # # rules += 1
        # if (min(entry_bar['open'], entry_bar['close']) - max_distance_sync*entry_bar['open']) < sma_8.iloc[-1] < (max(entry_bar['open'], entry_bar['close']) + max_distance_sync*entry_bar['open']):
        #     # checklist += 1

        #     if '2.5.2' not in model.model_stats.keys():
        #         model.model_stats['2.5.2']={}

        #     model.model_stats['2.5.2'][ts] = {}
        #     model.model_stats['2.5.2'][ts]['long'] = [(min(entry_bar['open'], entry_bar['close']) - max_distance_sync*entry_bar['open']), (max(entry_bar['open'], entry_bar['close']) + max_distance_sync*entry_bar['open'])]
        #     model.model_stats['2.5.2'][ts]['short'] = [(min(entry_bar['open'], entry_bar['close']) - max_distance_sync*entry_bar['open']), (max(entry_bar['open'], entry_bar['close']) + max_distance_sync*entry_bar['open'])]

        # # 2.6 sideways not prior to price phase
        # # rules += 1
        # if not highs_trend.empty:

        #     if model.market_data.history[topic].index[-sideways_count] >= highs_trend.index[-1]:
        #         # long_checklist += 1

        #         if '2.6' not in model.model_stats.keys():
        #             model.model_stats['2.6']={}

        #         model.model_stats['2.6'][ts] = {}
        #         model.model_stats['2.6'][ts]['long'] = model.market_data.history[topic].index[-sideways_count]

        # 2.7 Amplitude of sideways must be smaller than body of entry bar
        rules += 1
        if sideways_count_max - sideways_count_min <= surprise_factor * open_close_1:
            checklist += 1

            if '2.7' not in model.model_stats.keys():
                model.model_stats['2.7'] = {}

            model.model_stats['2.7'][ts] = {}
            model.model_stats['2.7'][ts][
                'long'] = sideways_count_max - sideways_count_min
            model.model_stats['2.7'][ts][
                'short'] = sideways_count_max - sideways_count_min

        # 2.8.1 no trend in sideways: calculated via linear regression over sideways
        rules += 1
        if (abs(slope_sideways_lr) /
                high_low_candle_window) * candle_window < max_slope_sideways:
            checklist += 1

            if '2.8.1' not in model.model_stats.keys():
                model.model_stats['2.8.1'] = {}

            model.model_stats['2.8.1'][ts] = {}
            model.model_stats['2.8.1'][ts]['long'] = (
                slope_sideways_lr / high_low_candle_window) * candle_window
            model.model_stats['2.8.1'][ts]['short'] = (
                slope_sideways_lr / high_low_candle_window) * candle_window

        # # 2.8.2 no trend in sideways: calculated via linear regression over sideways
        # # rules += 1
        # if slope_sideways_lr < max_slope_sideways:
        #     # long_checklist += 1

        #     if '2.8.2' not in model.model_stats.keys():
        #         model.model_stats['2.8.2']={}

        #     model.model_stats['2.8.2'][ts] = {}
        #     model.model_stats['2.8.2'][ts]['long'] = slope_sideways_lr

        # # 2.9.1 no positive drift within sideways: measured by consecutive candles mocving in direction of entrybar
        # # rules += 1
        # if  consecutive_blues < max_trend_candles:
        #     # checklist +=1

        #     if '2.9.1' not in model.model_stats.keys():
        #         model.model_stats['2.9.1']={}

        #     model.model_stats['2.9.1'][ts] = {}
        #     model.model_stats['2.9.1'][ts]['long'] = consecutive_blues
        #     model.model_stats['2.9.1'][ts]['short'] = consecutive_blues

        # # 2.9.2 no negative drift within sideways: measured by consecutive candles mocving in direction of entrybar
        # # rules += 1
        # if  consecutive_reds < max_trend_candles:
        #     # checklist +=1

        #     if '2.9.2' not in model.model_stats.keys():
        #         model.model_stats['2.9.2']={}

        #     model.model_stats['2.9.2'][ts] = {}
        #     model.model_stats['2.9.2'][ts]['long'] = consecutive_reds
        #     model.model_stats['2.9.2'][ts]['short'] = consecutive_reds

        # # 2.9.3 no positive drift within sideways: measured by total price movement performed by consecutive candles within sideways relative to body of entry bar
        # # rules += 1
        # if  amplitude_blue < max_trend_amplitude*open_close_1:
        #     # checklist +=1

        #     if '2.9.3' not in model.model_stats.keys():
        #         model.model_stats['2.9.3']={}

        #     model.model_stats['2.9.3'][ts] = {}
        #     model.model_stats['2.9.3'][ts]['long'] = amplitude_blue
        #     model.model_stats['2.9.3'][ts]['short'] = amplitude_blue

        # # 2.9.4 no negative drift within sideways: measured by total price movement performed by consecutive candles within sideways relative to body of entry bar
        # # rules += 1
        # if  amplitude_red < max_trend_amplitude*open_close_1:
        #     # checklist +=1

        #     if '2.9.4' not in model.model_stats.keys():
        #         model.model_stats['2.9.4']={}

        #     model.model_stats['2.9.4'][ts] = {}
        #     model.model_stats['2.9.4'][ts]['long'] = amplitude_red
        #     model.model_stats['2.9.4'][ts]['short'] = amplitude_red

        # 2.9.5 No drift: little to no drift prior to entry bar
        rules += 1
        if (entry_bar['open'] - last_min) <= open_close_1 * drift_factor:
            long_checklist += 1

            if '2.9.5' not in model.model_stats.keys():
                model.model_stats['2.9.5'] = {}

            model.model_stats['2.9.5'][ts] = {}
            model.model_stats['2.9.5'][ts]['long'] = (entry_bar['open'] -
                                                      last_min) / open_close_1

        # 2.6 Minimum number of sideways candles are required (this ensures that the entry bar is large enough)
        # core_rules += 1
        # if sideways_count >= minimum_sideways:
        #     core_checklist += 1

        # #################### END 2 TIME ####################

        # #################### 3 BAR ####################

        # all on 1min candles

        # 3.1 Entry bar in opposite 1/5ths: the wigs of the entry bar must be smaller equal 20% of the candle (High to low) (Non-negotiable)
        rules += 1
        # core_rules += 1
        if (opposite_fifths * high_low_1 >=
                low_open_1) and (opposite_fifths * high_low_1 >= high_close_1):
            long_checklist += 1
            # core_long_checklist += 1

            if '3.1' not in model.model_stats.keys():
                model.model_stats['3.1'] = {}

            model.model_stats['3.1'][ts] = {}
            model.model_stats['3.1'][ts]['long'] = 1

        # # 3.1.1 Entry bar in opposite 1/5ths: the wigs of the entry bar must be smaller equal 20% of the candle (High to low) (Non-negotiable)
        # # rules += 1
        # # core_rules += 1
        # if (opposite_fifths_2 * high_low_1 >=
        #         low_open_1):
        #     # long_checklist += 1
        #     # core_long_checklist += 1

        #     if '3.1.1' not in model.model_stats.keys():
        #         model.model_stats['3.1.1']={}

        #     model.model_stats['3.1.1'][ts] = {}
        #     model.model_stats['3.1.1'][ts]['long'] = low_open_1/high_low_1

        # # 3.1.2 Entry bar in opposite 1/5ths: the wigs of the entry bar must be smaller equal 20% of the candle (High to low) (Non-negotiable)
        # # rules += 1
        # # core_rules += 1
        # if (opposite_fifths_2 * high_low_1 >= high_close_1):
        #     # long_checklist += 1
        #     # core_long_checklist += 1

        #     if '3.1.2' not in model.model_stats.keys():
        #         model.model_stats['3.1.2']={}

        #     model.model_stats['3.1.2'][ts] = {}
        #     model.model_stats['3.1.2'][ts]['long'] = high_close_1/high_low_1

        # 3.2 + 3.3 Is entry bar a surprise? (Picture) (Non-negotiable):

        # 3.2 Entry bar shows a significant price move
        core_rules += 1
        if open_close_1 >= minimum_movement * entry_bar['open']:
            core_checklist += 1

            if '3.2' not in model.model_stats.keys():
                model.model_stats['3.2'] = {}

            model.model_stats['3.2'][ts] = {}
            model.model_stats['3.2'][ts]['long'] = open_close_1
            model.model_stats['3.2'][ts]['short'] = open_close_1

        # # 3.3.1 space between sideways and entry bar: fraction of entry bar that exceeds maximum of sideways
        # # rules += 1
        # if  sideways_count_max < entry_bar['close'] - sideways_channel * open_close_1 :
        #     # long_checklist +=1

        #     if '3.3.1' not in model.model_stats.keys():
        #         model.model_stats['3.3.1']={}

        #     model.model_stats['3.3.1'][ts] = {}
        #     model.model_stats['3.3.1'][ts]['long'] = (entry_bar['close']-sideways_count_max)/open_close_1

        # # 3.3.2 space between sideways and entry bar: fraction of entry bar that exceeds maximum of last 10 candles
        # # alternative to 3.3.1
        # # rules += 1
        # if  max_reference < entry_bar['close'] - sideways_channel * open_close_1:
        #     # long_checklist +=1

        #     if '3.3.2' not in model.model_stats.keys():
        #         model.model_stats['3.3.2']={}

        #     model.model_stats['3.3.2'][ts] = {}
        #     model.model_stats['3.3.2'][ts]['long'] = (entry_bar['close']-max_reference)/open_close_1

        # 3.4 Blue entry bar: close of entry bar must be greater than open of entry bar (Non-negotiable)
        core_rules += 1
        if entry_bar['close'] > entry_bar['open']:
            core_long_checklist += 1

            if '3.4' not in model.model_stats.keys():
                model.model_stats['3.4'] = {}

            model.model_stats['3.4'][ts] = {}
            model.model_stats['3.4'][ts]['long'] = 1

        # # 3.5 body of entry bar must be a significant part of the trading screen
        # # rules += 1
        # if open_close_1 >= surprise_factor_2 * high_low_candle_window:
        #     # checklist += 1

        #     if '3.5' not in model.model_stats.keys():
        #         model.model_stats['3.5']={}

        #     model.model_stats['3.5'][ts] = {}
        #     model.model_stats['3.5'][ts]['long'] = open_close_1/high_low_candle_window
        #     model.model_stats['3.5'][ts]['short'] = open_close_1/high_low_candle_window

        #################### END BAR ####################

        ######################################## END CHECKLIST LONG ########################################

        ######################################## CHECKLIST SHORT ########################################

        #################### 1 TREND ####################

        # 1.1 Lower highs: last high must be lower than previous high
        # check if there are at least two highs and one low for stability of calculations
        if len(highs_trend) > 1 and not lows_trend.empty:

            # lower highs_trend, but retracement of last high of maximum retracement_factor x difference between last low and second last high
            if highs_trend.iloc[-1] < highs_trend.iloc[-2]:
                # short_checklist+=1

                if '1.1' not in model.model_stats.keys():
                    model.model_stats['1.1'] = {}

                if ts not in model.model_stats['1.1'].keys():
                    model.model_stats['1.1'][ts] = {}

                model.model_stats['1.1'][ts]['short'] = 1

        # 1.2 Lower highs with retracement: last high must be lower than previous high - retracement_factor * difference between las low and second last high
        # check if there are at least two highs and one low for stability of calculations
        if len(highs_trend) > 1 and not lows_trend.empty:

            # lower highs_trend, but retracement of last high of maximum retracement_factor x difference between last low and second last high
            if highs_trend.iloc[-1] < highs_trend.iloc[-2] - abs(
                    lows_trend.iloc[-1] -
                    highs_trend.iloc[-2]) * (1 - retracement_factor):
                # short_checklist+=1

                if '1.2' not in model.model_stats.keys():
                    model.model_stats['1.2'] = {}

                if ts not in model.model_stats['1.2'].keys():
                    model.model_stats['1.2'][ts] = {}

                model.model_stats['1.2'][ts]['short'] = abs(
                    lows_trend.iloc[-1] -
                    highs_trend.iloc[-1]) / abs(lows_trend.iloc[-1] -
                                                highs_trend.iloc[-2])

        # 1.3 Purple strong, smooth, flat or decreasig : linear regression of trend line since second last high has negative slope
        # if slope_sma_short<0:
        #     short_checklist += 1

        # 1.5 Blue strong, smooth, flat or increasing
        # if sma_8.iloc[-1]-sma_8.iloc[-trend_candles]<=0:
        #     core_short_checklist+=1

        # 1.3 Breaking of a significant low
        # check if there is at least one low for stability of calculations
        if not lows_trend.empty:

            # the body of the entry bar has to be below the preceding low
            if lows_trend.iloc[-1] > entry_bar['close']:
                short_checklist += 1

                if '1.3' not in model.model_stats.keys():
                    model.model_stats['1.3'] = {}

                if ts not in model.model_stats['1.3'].keys():
                    model.model_stats['1.3'][ts] = {}

                model.model_stats['1.3'][ts]['short'] = 1

        # 1.4 Breaking of a significant low (50% of entry bar): 50% of the entry bar must be below last low
        # check if there is at least one low for stability of calculations
        if not lows_trend.empty:

            # at least the "high_factor" fraction of the body of the entry bar has to be below the preceding low
            if lows_trend.iloc[-1] - high_factor * open_close_1 > entry_bar[
                    'close']:
                # short_checklist += 1

                if '1.4' not in model.model_stats.keys():
                    model.model_stats['1.4'] = {}

                if ts not in model.model_stats['1.4'].keys():
                    model.model_stats['1.4'][ts] = {}

                model.model_stats['1.4'][ts]['short'] = (
                    lows_trend.iloc[-1] - entry_bar['close']) / open_close_1

        # # 1.5 breaking of a support line:
        # # check if support exists for stability of calculation
        # if support:
        #     if entry_bar['close']<support:
        #         # short_checklist += 1

        #         if '1.5' not in model.model_stats.keys():
        #             model.model_stats['1.5']={}

        #         if ts not in model.model_stats['1.5'].keys():
        #             model.model_stats['1.5'][ts] = {}

        #         model.model_stats['1.5'][ts]['short'] = support

        # # 1.6 lower low: last low must be lower thab second last low
        # # check if there are at least two lows for stability of calculations
        # if len(lows_trend)>1:
        #     if lows_trend.iloc[-1] < lows_trend.iloc[-2]:
        #         # short_checklist += 1

        #         if '1.6' not in model.model_stats.keys():
        #             model.model_stats['1.6']={}

        #         if ts not in model.model_stats['1.6'].keys():
        #             model.model_stats['1.6'][ts] = {}

        #         model.model_stats['1.6'][ts]['short'] = 1

        # # 1.7 Time phase after Price phase: Only enter after a time phase, predecessed by a price phase
        # # check if there are at least two slopes for stability of calculations
        # if len(high_low_slopes_trend)>1:
        #     if high_low_slopes_trend[-1]>0 and high_low_slopes_trend[-2]<0:
        #         # short_checklist += 1

        #         if '1.7' not in model.model_stats.keys():
        #             model.model_stats['1.7']={}

        #         if ts not in model.model_stats['1.7'].keys():
        #             model.model_stats['1.7'][ts] = {}

        #         model.model_stats['1.7'][ts]['short'] = 1

        # 1.9 Below purple: close of entry bar must be below 24 sma
        if sma_24[-1] > entry_bar['close']:
            core_short_checklist += 1

            if '1.9' not in model.model_stats.keys():
                model.model_stats['1.9'] = {}

            if ts not in model.model_stats['1.9'].keys():
                model.model_stats['1.9'][ts] = {}

            model.model_stats['1.9'][ts]['short'] = 1

        # 1.10.1 Curvature purple: slope of regression flat or in direction of trade
        if (slope_purple /
                high_low_candle_window) * candle_window < slope_purple_param:
            short_checklist += 1

            if '1.10.1' not in model.model_stats.keys():
                model.model_stats['1.10.1'] = {}

            if ts not in model.model_stats['1.10.1'].keys():
                model.model_stats['1.10.1'][ts] = {}

            model.model_stats['1.10.1'][ts]['short'] = (
                slope_purple / high_low_candle_window) * candle_window

        # # 1.10.2 Curvature purple: slope of regression flat or in direction of trade
        # # check if at no point 3 candles in a row have a slope of less than -0.3
        # if slope_sideways_short:
        #     # short_checklist += 1

        #     if '1.10.2' not in model.model_stats.keys():
        #         model.model_stats['1.10.2']={}

        #     if ts not in model.model_stats['1.10.2'].keys():
        #         model.model_stats['1.10.2'][ts] = {}

        #     model.model_stats['1.10.2'][ts]['short'] = 1

        # 1.10.3 Purple not accelerating
        # check if curvature at last 5 points is not positive
        if not increasing_purple:
            short_checklist += 1

            if '1.10.3' not in model.model_stats.keys():
                model.model_stats['1.10.3'] = {}

            if ts not in model.model_stats['1.10.3'].keys():
                model.model_stats['1.10.3'][ts] = {}

            model.model_stats['1.10.3'][ts]['short'] = 1

        # # 1.11 Above blue: close of entry bar must be below sma8
        # if sma_8[-1] > entry_bar['close']:
        #     # short_checklist += 1

        #     if '1.11' not in model.model_stats.keys():
        #         model.model_stats['1.11']={}

        #     if ts not in model.model_stats['1.11'].keys():
        #         model.model_stats['1.11'][ts] = {}

        #     model.model_stats['1.11'][ts]['short'] = 1

        # # 1.12.1 Curvature of blue:
        # # strong
        # if (strong_short):
        #     # short_checklist += 1

        #     if '1.12.1' not in model.model_stats.keys():
        #         model.model_stats['1.12.1']={}

        #     if ts not in model.model_stats['1.12.1'].keys():
        #         model.model_stats['1.12.1'][ts] = {}

        #     model.model_stats['1.12.1'][ts]['short'] = 1

        # # 1.12.4 Curvature of blue:
        # # flat and decreasing
        # if (decreasing):
        #     # short_checklist += 1

        #     if '1.12.4' not in model.model_stats.keys():
        #         model.model_stats['1.12.4']={}

        #     if ts not in model.model_stats['1.12.4'].keys():
        #         model.model_stats['1.12.4'][ts] = {}

        #     model.model_stats['1.12.4'][ts]['short'] = 1

        # # 1.12.5 slope of blue:
        # # slope_blue
        # if (slope_blue>-max_slope_blue):
        #     # short_checklist += 1

        #     if '1.12.5' not in model.model_stats.keys():
        #         model.model_stats['1.12.5']={}

        #     if ts not in model.model_stats['1.12.5'].keys():
        #         model.model_stats['1.12.5'][ts] = {}

        #     model.model_stats['1.12.5'][ts]['short'] = slope_blue

        # 1.12.8 blue not slowing
        # check if curvature of last 5 points is not negative
        if not increasing_blue:
            short_checklist += 1

            if '1.12.8' not in model.model_stats.keys():
                model.model_stats['1.12.8'] = {}

            if ts not in model.model_stats['1.12.8'].keys():
                model.model_stats['1.12.8'][ts] = {}

            model.model_stats['1.12.8'][ts]['short'] = 1

        # #################### END 1 TREND ####################

        # #################### 2 TIME ####################

        # # 2.6 sideways not prior to price phase
        # if not lows_trend.empty:
        #     if model.market_data.history[topic].index[-sideways_count] >= lows_trend.index[-1]:
        #         # short_checklist += 1

        #         if '2.6' not in model.model_stats.keys():
        #             model.model_stats['2.6']={}

        #         if ts not in model.model_stats['2.6'].keys():
        #             model.model_stats['2.6'][ts] = {}

        #         model.model_stats['2.6'][ts]['short'] = model.market_data.history[topic].index[-sideways_count]

        # 2.5 No drift: little to no drift prior to entry bar
        # if model.market_data.history[topic].iloc[
        #         -drift_length - 1]['open'] - model.market_data.history[
        #             topic].iloc[-2]['close'] <= drift_height * open_close_1:
        #    short_checklist += 1

        # # 2.8.2 no trend in sideways: calculated via linear regression over sideways
        # if slope_sideways_lr > -max_slope_sideways:
        #     # short_checklist += 1

        #     if '2.8.2' not in model.model_stats.keys():
        #         model.model_stats['2.8.2']={}

        #     if ts not in model.model_stats['2.8.2'].keys():
        #             model.model_stats['2.8.2'][ts] = {}

        #     model.model_stats['2.8.2'][ts]['short'] = slope_sideways_lr

        # 2.9.5 No drift: little to no drift prior to entry bar
        if (last_max - entry_bar['open']) <= open_close_1 * drift_factor:
            short_checklist += 1

            if '2.9.5' not in model.model_stats.keys():
                model.model_stats['2.9.5'] = {}

            if ts not in model.model_stats['2.9.5'].keys():
                model.model_stats['2.9.5'][ts] = {}

            model.model_stats['2.9.5'][ts]['short'] = (
                last_max - entry_bar['open']) / open_close_1

        # #################### END 2 TIME ####################

        # #################### 3 BAR ####################

        # all on 1min candles

        # 3.1 Entry bar in opposite 1/5ths: the wigs of the entry bar must be smaller equal 20% of the candle (High to low) (Non-negotiable)
        if (opposite_fifths * high_low_1 >=
                high_open_1) and (opposite_fifths * high_low_1 >= low_close_1):
            short_checklist += 1
            # core_short_checklist += 1

            if '3.1' not in model.model_stats.keys():
                model.model_stats['3.1'] = {}

            if ts not in model.model_stats['3.1'].keys():
                model.model_stats['3.1'][ts] = {}

            model.model_stats['3.1'][ts]['short'] = 1

        # # 3.1.1 Entry bar in opposite 1/5ths: the wigs of the entry bar must be smaller equal 20% of the candle (High to low) (Non-negotiable)
        # if (opposite_fifths_2 * high_low_1 >=
        #         high_open_1):
        #     # short_checklist += 1
        #     # core_short_checklist += 1

        #     if '3.1.1' not in model.model_stats.keys():
        #         model.model_stats['3.1.1']={}

        #     if ts not in model.model_stats['3.1.1'].keys():
        #         model.model_stats['3.1.1'][ts] = {}

        #     model.model_stats['3.1.1'][ts]['short'] = high_open_1/high_low_1

        # # 3.1.2 Entry bar in opposite 1/5ths: the wigs of the entry bar must be smaller equal 20% of the candle (High to low) (Non-negotiable)
        # if (opposite_fifths_2 * high_low_1 >= low_close_1):
        #     # short_checklist += 1
        #     # core_short_checklist += 1

        #     if '3.1.2' not in model.model_stats.keys():
        #         model.model_stats['3.1.2']={}

        #     if ts not in model.model_stats['3.1.2'].keys():
        #         model.model_stats['3.1.2'][ts] = {}

        #     model.model_stats['3.1.2'][ts]['short'] = low_close_1/high_low_1

        # # 3.3.1 space between sideways and entry bar: fraction of entry bar that exceeds maximum of sideways
        # if  sideways_count_min > entry_bar['close'] + sideways_channel * open_close_1 :
        #      # short_checklist +=1

        #     if '3.3.1' not in model.model_stats.keys():
        #         model.model_stats['3.3.1']={}

        #     if ts not in model.model_stats['3.3.1'].keys():
        #         model.model_stats['3.3.1'][ts] = {}

        #     model.model_stats['3.3.1'][ts]['short'] = (sideways_count_min-entry_bar['close'])/open_close_1

        # # 3.3.2 space between sideways and entry bar: fraction of entry bar that exceeds maximum of last 10 candles
        # # alternative to 3.3.1
        # if  min_reference > entry_bar['close'] + sideways_channel * open_close_1:
        #     # short_checklist +=1

        #     if '3.3.2' not in model.model_stats.keys():
        #         model.model_stats['3.3.2']={}

        #     if ts not in model.model_stats['3.3.2'].keys():
        #         model.model_stats['3.3.2'][ts] = {}

        #     model.model_stats['3.3.2'][ts]['short'] = (min_reference-entry_bar['close'])/open_close_1

        # 3.4 Red entry bar: close of entry bar must be smaller than open of entry bar
        if entry_bar['close'] < entry_bar['open']:
            core_short_checklist += 1

            if '3.4' not in model.model_stats.keys():
                model.model_stats['3.4'] = {}

            if ts not in model.model_stats['3.4'].keys():
                model.model_stats['3.4'][ts] = {}

            model.model_stats['3.4'][ts]['short'] = 1

        #################### END BAR ####################

        ######################################## END CHECKLIST SHORT ########################################

        # calculate score across all rules

        #################### REMOVE IF NON CORE-RULES ARE APPLIED ###########################################
        # rules = 1
        #####################################################################################################

        confidence_score_long = (long_checklist + checklist) / rules
        confidence_score_short = (short_checklist + checklist) / rules

        confidence_score_core_long = (core_long_checklist +
                                      core_checklist) / core_rules
        confidence_score_core_short = (core_short_checklist +
                                       core_checklist) / core_rules

        # determine trading quantity
        # buy_qty = 100 / entry_bar['close']
        # buy_qty = np.round(buy_qty, tick_size)

        # buy with all available balance
        buy_qty = 0.95 * model.account.wallet[
            ticker[-len(BASE_CUR):]]['available_balance'] / entry_bar['close']

        ################# REMOVE IN PRODUCTION ##################################################################################################################

        # export_dates = pd.to_datetime(['02.10.2022  23:00:00', '12.10.2022  09:35:00', '12.10.2022  21:25:00', '13.10.2022  21:35:00', '20.10.2022  18:00:00', '23.10.2022  19:40:00', '31.10.2022  09:50:00', '02.11.2022  14:05:00', '27.12.2022  23:20:00'], dayfirst=True)
        # export_dates = pd.to_datetime(['20.10.2022  00:20:00','20.10.2022  00:25:00','20.10.2022  00:30:00','20.10.2022  00:35:00'], dayfirst=True)

        # export_dates = pd.to_datetime([
        # '03.10.2022  19:20:00',
        # '03.10.2022  22:00:00',
        # '04.10.2022  09:35:00',
        # '04.10.2022  19:05:00',
        # '05.10.2022  10:05:00',
        # '07.10.2022  07:25:00',
        # '10.10.2022  13:50:00',
        # '23.10.2022  19:40:00'], dayfirst=True)

        # export_dates = pd.to_datetime([
        # '03.10.2022  14:55:00',
        # '07.10.2022  12:25:00',
        # '23.12.2022  08:30:00',
        # '12.10.2022  00:05:00',
        # '10.10.2022  21:40:00'], dayfirst=True)

        # if entry_bar['end'] in export_dates:
        #     export = {}
        #     export['open'] = last_exit_candle['open']
        #     export['close'] = last_exit_candle['close']
        #     export['high'] = last_exit_candle['high']
        #     export['low'] = last_exit_candle['low']
        #     export['entry_close_1_long'] = model.model_storage['entry_close_1_long']
        #     export['entry_open_1_long'] = model.model_storage['entry_open_1_long']
        #     export['entry_open_close_1_long'] = model.model_storage['entry_open_close_1_long']
        #     try:
        #         export['new_stop_loss_long'] = new_stop_loss_long
        #     except:
        #         export['new_stop_loss_long'] = None
        #     export['stop_loss'] = model.account.positions[ticker]['stop_loss']
        #     export['last_trade'] = str(last_trade)
        #     export['higher_low_list_exit'] = str(model.model_storage['exit_long_higher_lows'])

        #     export['Last low'] = lows_trend.iloc[-1]
        #     export['open_close_1'] = open_close_1
        #     export['total_lr_sideways_increase'] = total_lr_sideways_increase
        #     export['consecutive_blues'] = consecutive_blues
        #     export['consecutive_reds'] = consecutive_reds
        #     export['amplitude_blue'] = amplitude_blue
        #     export['amplitude_red'] = amplitude_red
        #     export['abs(sma_8.iloc[-1] - sma_24.iloc[-1])'] = abs(sma_8.iloc[-1] - sma_24.iloc[-1])
        #     export["entry_bar['open']"] = entry_bar['open']
        #     export["entry_bar['close']"] = entry_bar['close']
        #     export["sma_8.iloc[-1]"] = sma_8.iloc[-1]
        #     export["abs(sma_8.iloc[-1] - entry_bar['close'])"] = abs(sma_8.iloc[-1] - entry_bar['close'])
        #     export["max_reference"] = max_reference
        #     export["min_reference"] = min_reference

        #     export['Previous 5 highs'] = highs_trend.iloc[-5:]
        #     export['Previous 5 lows'] = lows_trend.iloc[-5:]
        #     export['Retracement_factor'] = retracement_factor
        #     export['retracement_long'] = lows_trend.iloc[-2] + abs(highs_trend.iloc[-1]-lows_trend.iloc[-2])*(1-retracement_factor)
        #     export['retracement_short'] = highs_trend.iloc[-2] - abs(lows_trend.iloc[-1]-highs_trend.iloc[-2])*(1-retracement_factor)
        #     export['Support'] = support
        #     export['Resistance'] = resistance
        #     export['High_low_slopes_trend (-1)'] = high_low_slopes_trend.iloc[-1]
        #     export['High_low_slopes_trend (-2)'] = high_low_slopes_trend.iloc[-2]
        #     export['Slope_purple (linear regression Steigung)'] = slope_purple
        #     export['Slope_sideways_long'] = slope_sideways_long
        #     export['Slope_sideways_short'] = slope_sideways_short

        # export['sideways_count_min'] = sideways_count_min
        # export['sideways_count_max'] = sideways_count_max
        # export['Sideways_count'] = sideways_count
        # export['Strong_long'] = strong_long
        # export['Strong_short'] = strong_short
        # export['Smooth'] = smooth
        # export['Increasing'] = increasing
        # export['Decreasing'] = decreasing
        # export['Flat'] = flat

        # export_df = pd.DataFrame(data=export, index=[0])
        # export_df = (export_df.T)
        # export_df.to_excel('export_{}.xlsx'.format(entry_bar['end']))

        ##################################################################################################################

        # if all rules apply for the long strategy and there is no current open position, place buy order
        if (confidence_score_core_long
                == 1.0) and (confidence_score_long >= 1) and (
                    model.account.positions[ticker]['size'] == 0.0):

            # set leverage to 20 or lower so that if stop loss is hit, it occurs a maximum loss of 40%
            leverage_ratio = 1 - (stop_loss_long / entry_bar['close'])
            leverage = int(np.min([20, np.ceil(0.4 / leverage_ratio)]))

            # leverage=1
            # for real trading, set leverage of position to leverage, for backtesting just scale position size
            # buy_qty=leverage*buy_qty
            # buy_qty = np.round(buy_qty, tick_size)
            buy_qty = 50

            try:
                model.account.session.set_leverage(symbol=ticker,
                                                   buy_leverage=str(leverage),
                                                   sell_leverage=str(leverage))
            except:
                pass

            model.account.place_order(symbol=ticker,
                                      side='Buy',
                                      qty=buy_qty,
                                      order_type='Market',
                                      stop_loss=stop_loss_long,
                                      take_profit=take_profit_long)

            model.model_storage['entry_open_close_1_long'] = open_close_1
            model.model_storage['entry_close_1_long'] = entry_bar['close']
            model.model_storage['entry_open_1_long'] = entry_bar['open']
            model.model_storage['exit_long_higher_lows'] = []
            model.model_storage['exit_candles'] = 0

        # if all rules apply for the short strategy and there is no current open position, place sell order
        if (confidence_score_core_short
                == 1.0) and (confidence_score_short >= 1) and (
                    model.account.positions[ticker]['size'] == 0.0):

            # set leverage to 20 or lower so that if stop loss is hit, it occurs a maximum loss of 40%
            leverage_ratio = (stop_loss_short / entry_bar['close']) - 1
            leverage = int(np.min([20, np.ceil(0.4 / leverage_ratio)]))

            # leverage = 1
            # for real trading, set leverage of position to leverage, for backtesting just scale position size
            # buy_qty=leverage*buy_qty
            # buy_qty = np.round(buy_qty, tick_size)
            buy_qty = 50

            try:
                model.account.session.set_leverage(symbol=ticker,
                                                   buy_leverage=str(leverage),
                                                   sell_leverage=str(leverage))
            except:
                pass

            model.account.place_order(symbol=ticker,
                                      side='Sell',
                                      qty=buy_qty,
                                      order_type='Market',
                                      stop_loss=stop_loss_short,
                                      take_profit=take_profit_short)
            model.model_storage['entry_open_close_1_short'] = open_close_1
            model.model_storage['entry_close_1_short'] = entry_bar['close']
            model.model_storage['entry_open_1_short'] = entry_bar['open']
            model.model_storage['exit_short_lower_highs'] = []
            model.model_storage['exit_candles'] = 0
