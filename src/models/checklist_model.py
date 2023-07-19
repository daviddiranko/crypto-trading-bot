import warnings

warnings.simplefilter(action='ignore', category=FutureWarning)
warnings.simplefilter(action='ignore', category=RuntimeWarning)

from typing import Dict, Any
from src.TradingModel import TradingModel
from src.helper_functions.statistics import sma, get_alternate_highs_lows, get_slopes_highs_lows, true_range
import numpy as np
from sklearn.linear_model import LinearRegression
from src.endpoints.bybit_functions import *
from src.helper_functions.checklist_utils import *
from src.helper_functions.helper_functions import custom_round
import os
from dotenv import load_dotenv

load_dotenv()

CONTRACT_CUR = os.getenv('CONTRACT_CUR')


def checklist_model(model: TradingModel, ticker: str, trading_freq: int):
    '''
    checklist-based trend following model
    '''

    # declare ticker
    # ticker = 'RTYUSD'
    ticker = ticker
    trading_freq = trading_freq
    expiry = model.model_args['expiries'][ticker]

    # frequency to determine trading strategy
    # trading_freq = 5

    # frequency to check updates in exit strategy, must be at least as frequent as trading_freq
    min_action_freq = trading_freq

    # declare topics
    topic = 'candle.{}.{}'.format(trading_freq, ticker)
    trend_15_topic = 'candle.15.{}'.format(ticker)
    trend_5_topic = 'candle.5.{}'.format(ticker)
    min_action_topic = 'candle.{}.{}'.format(min_action_freq, ticker)
    exit_topic = 'candle.{}.{}'.format(trading_freq, ticker)

    # initialize checklist counter and total rules counter
    long_checklist = 0
    short_checklist = 0
    long_checklist = 0
    short_checklist = 0
    checklist = 0
    checklist = 0
    rules = 0
    rules = 0

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
    sideways_factor = 2

    # sideways_factor = model.model_args['param']

    # Sideways: all candles in sideways must be smaller eqal factor times entry bar
    small_bars_50 = 0.50
    # small_bars_50 = model.model_args['param']

    # Sideways: last 2 candles before entry bar must be smaller equal parameter times entry bar
    small_bars_25 = 0.25
    # small_bars_25 = model.model_args['param']

    # Opposite 1/5ths: the wigs of the entry bar must be smaller equal 20% of the candle (High to low)
    opposite_fifths = 0.3
    # opposite_fifths = 0.2
    # opposite_fifths = model.model_args['param']

    # number of candles to consider for strategy
    candle_window = 100
    # candle_window = model.model_args['candle_window']

    # chart width in Trading iew
    chart_width = 4.2

    # Chart height in TradingView
    chart_height = 3.2

    # amount of drift between last low and open of entrybar relative to body of entry bar to not have drift
    # (suggestion 0,5-0,8)
    # drift_factor = 0.6
    drift_factor = 0.6

    # multiple of body of entry bar that amplitude (i.e. maximum open or close - minimum of open or close) of sideways candles can have
    # (suggestion 1-1,3)
    amplitude_factor = 2
    # surprise_factor = model.model_args['param']

    # maximum amplitude of sma8 (blue) during sideways, measured as percentage of entry bar body
    blue_amplitude_2 = 0.4

    # absolute threshold for price phase within sideways
    threshold_price_phase_abs = 10/1800

    # relative threshold for price phase within sideways (compared to entry bar)
    threshold_price_phase_rel = 0.8

    # High and low definition: last high must be 50% higher than previous high
    # To be a breaking high, 50% of the entry candle body has to above the preceding high
    high_factor = 0.3
    # high_factor = 0.5
    # high_factor = model.model_args['param']

    # maximum absolute value of true range for two candles before entry bar
    ATR_small_bars_25 = 10 / 1800

    # maximum relative slope of sideways, measured relative to size of trading screen
    # (suggestion 0.6-0.7)
    max_slope_sideways = 0.6
    # max_slope_sideways = model.model_args['param']

    # determine minimum movement of entry bar in fraction to open price
    minimum_movement = 2 / 1800
    maximum_movement = 10 / 1800

    # maximum distance of sma_8 to its regression line relative to size of entry bar
    max_sma_8_dist = 1.0

    # maximum relative slope of sma_8
    max_slope_blue = 5.0

    # tolerance of sma8 exit strategy
    sma_8_exit_tolerance = 3 / 1800

    # absolute threshold for candle in exit strategy to be "sizable"
    sizable_body_exit_abs = 0.5 / 1800

    # relative threshold to trading window for candle in exit strategy to be "sizable"
    sizable_body_exit_rel = 0.02

    # profit threshold to adjust stop loss to trade price
    take_profit_stoploss = 2.0 / 1800

    # set tick size of orders as float increment
    tick_size = model.model_args['tick_sizes'][ticker]

    # threshold for dividing between flat and strong in purple and blue
    threshold_sma = 0.2/1800

    # threshold for curvature of blue to be abrupt
    threshold_abrupt = 2.0/1800

    # critical curvature for an extrema to be volatile (in blue)
    curvature_volatile = 1.0/1800


    ######################################## END PARAMETERS ########################################

    ######################################## DEFINITION VARIABLES ########################################

    # last relevant candles for strategy
    try:
        entry_bar = model.market_data.history[topic].iloc[-1]
        last_exit_candle = model.market_data.history[exit_topic].iloc[-1]
        last_action_candle = model.market_data.history[min_action_topic].iloc[
            -1]
        _ = model.market_data.history[trend_15_topic].iloc[-1]
        _ = model.market_data.history[trend_5_topic].iloc[-1]
    except:
        return None

    # Only proceed if new action topic candle is received, i.e. ignore all smaller candles
    # Adjust "action_freq" if actions are performed for smaller candles
    if last_action_candle.name <= model.model_storage['action_bar_time']:
        return None
    else:
        # update last received action candle to current candle
        model.model_storage['action_bar_time'] = model.market_data.history[
            min_action_topic].iloc[-1].name

    # simple moving averages
    sma_24 = sma(model.market_data.history[trend_5_topic]['close'], window=24)
    sma_8 = sma(model.market_data.history[trend_5_topic]['close'], window=8)

    # calculate various spreads of entry bar
    high_low_1 = abs(entry_bar['high'] - entry_bar['low'])
    low_open_1 = abs(entry_bar['open'] - entry_bar['low'])
    high_open_1 = abs(entry_bar['open'] - entry_bar['high'])
    high_close_1 = abs(entry_bar['high'] - entry_bar['close'])
    open_close_1 = abs(entry_bar['close'] - entry_bar['open'])
    low_close_1 = abs(entry_bar['close'] - entry_bar['low'])

    # calculate body of two candles before entry bar
    body_3_1 = get_body(data=model.market_data.history[topic],
                        column_1='close',
                        column_2='open',
                        start=3,
                        end=1).abs()

    # calculate atr of two candles before entry bar
    atr_3_1 = true_range(data=model.market_data.history[topic].iloc[-3:-1])

    # calculate high and low of last "candle_window" candles as a reference point on how to scale visual inspections according to charts
    high_low_candle_window = get_trading_window(
        data=model.market_data.history[topic],
        window_size=candle_window,
        include_entry=True)

    high_low_candle_window_ex_entry = get_trading_window(
        data=model.market_data.history[topic],
        window_size=candle_window,
        include_entry=False)

    # count sideways according to chart visuals
    sideways_count = get_sideways(entry_body=open_close_1,
                                  trading_window=high_low_candle_window,
                                  sideways_factor=sideways_factor,
                                  window_size=candle_window,
                                  chart_height=chart_height,
                                  chart_width=chart_width)

    # count core sideways (1 x entrybar) according to chart visuals
    sideways_count_core = get_sideways(entry_body=open_close_1,
                                       trading_window=high_low_candle_window,
                                       sideways_factor=sideways_factor,
                                       window_size=candle_window,
                                       chart_height=chart_height,
                                       chart_width=chart_width)

    # calculate the body of the core sideways candles
    body_sideway_count_core_1 = get_body(data=model.market_data.history[topic],
                                         column_1='close',
                                         column_2='open',
                                         start=sideways_count_core,
                                         end=1).abs()

    
    # get trend series with appended entry bar if necessary
    # also get timedeltas between trend series and entry bar
    trend_series_15, topic_trend_topic_15_delta = get_trend_series(
        data=model.market_data.history[trend_15_topic],
        entry_bar=entry_bar,
        ref_column='close')

    trend_series_5, topic_trend_topic_5_delta = get_trend_series(
        data=model.market_data.history[trend_5_topic],
        entry_bar=entry_bar,
        ref_column='close')

    # print(trend_series_15)
    # calculate alternating highs and lows of trend line
    highs_trend_15, lows_trend_15 = get_alternate_highs_lows(
        candles=trend_series_15,
        min_int=n_candles,
        sma_diff=high_low_sma,
        min_int_diff=n_candles_diff)

    # calculate alternating highs and lows of trend line
    highs_trend_5, lows_trend_5 = get_alternate_highs_lows(
        candles=trend_series_5,
        min_int=n_candles,
        sma_diff=high_low_sma,
        min_int_diff=n_candles_diff)

    # calculate maximum spread between open and close prices of sideways candles
    sideways_spread = get_max_spread(data=model.market_data.history[topic],
                                     column_1='open',
                                     column_2='close',
                                     start=sideways_count,
                                     end=1)

    # determine if purple is flat or strong
    purple_strong_up = get_strong(data=sma_24,
                                  num_samples=11,
                                  threshold=threshold_sma*entry_bar['close'],
                                  start=15,
                                  end=-1,
                                  up=True)

    purple_strong_down = get_strong(data=sma_24,
                                    num_samples=11,
                                    threshold=-threshold_sma*entry_bar['close'],
                                    start=15,
                                    end=-1,
                                    up=False)

    purple_flat = not (purple_strong_down or purple_strong_up)

    sk_results_purple = get_linear_regression(data=sma_24,
                                            start=sideways_count,
                                            end=0)

    # extract slope of regression line
    slope_purple = sk_results_purple.coef_[0]

    # Define increasing (with respect to sma24)
    purple_increasing = get_increasing(data=sma_24,
                                       num_samples=5,
                                       num_strong_samples=3,
                                       slope_threshold=threshold_sma*entry_bar['close'],
                                       start=10,
                                       end=0,
                                       accelerating=True,
                                       long=True)

    purple_decreasing = get_increasing(data=sma_24,
                                       num_samples=5,
                                       num_strong_samples=3,
                                       slope_threshold=threshold_sma*entry_bar['close'],
                                       start=10,
                                       end=0,
                                       accelerating=True,
                                       long=False)

    # Define increasing (with respect to sma8)
    blue_increasing = get_increasing(data=sma_8,
                                     num_samples=5,
                                     num_strong_samples=3,
                                     slope_threshold=threshold_sma*entry_bar['close'],
                                     start=10,
                                     end=0,
                                     accelerating=True,
                                     long=True)

    blue_decreasing = get_increasing(data=sma_8,
                                     num_samples=5,
                                     num_strong_samples=3,
                                     slope_threshold=threshold_sma*entry_bar['close'],
                                     start=10,
                                     end=0,
                                     accelerating=True,
                                     long=False)

    # Define slowing (with respect to sma24)
    purple_slowing_long = get_increasing(data=sma_24,
                                         num_samples=5,
                                         num_strong_samples=3,
                                         slope_threshold=threshold_sma*entry_bar['close'],
                                         start=10,
                                         end=0,
                                         accelerating=False,
                                         long=False)

    purple_slowing_short = get_increasing(data=sma_24,
                                          num_samples=5,
                                          num_strong_samples=3,
                                          slope_threshold=threshold_sma*entry_bar['close'],
                                          start=10,
                                          end=0,
                                          accelerating=False,
                                          long=True)

    # Define slowing (with respect to sma8)
    blue_slowing_long = get_increasing(data=sma_8,
                                       num_samples=5,
                                       num_strong_samples=3,
                                       slope_threshold=threshold_sma*entry_bar['close'],
                                       start=10,
                                       end=0,
                                       accelerating=False,
                                       long=False)

    blue_slowing_short = get_increasing(data=sma_8,
                                        num_samples=5,
                                        num_strong_samples=3,
                                        slope_threshold=threshold_sma*entry_bar['close'],
                                        start=10,
                                        end=0,
                                        accelerating=False,
                                        long=True)

    # Define sideways yellow squares
    sideways_yellow_squares_long = get_sideways_yellow_squares(
        data=model.market_data.history[topic],
        start=sideways_count,
        end=0,
        long=True)

    sideways_yellow_squares_short = get_sideways_yellow_squares(
        data=model.market_data.history[topic],
        start=sideways_count,
        end=0,
        long=False)

    # determine if there is a price phase in sideways
    price_phase = get_price_phase(data=model.market_data.history[topic]['close'],
                                  min_int_highs_lows=5,
                                  sma_diff_highs_lows=8,
                                  min_int_diff_highs_lows=5,
                                  threshold=min(
                                      threshold_price_phase_abs*entry_bar['close'],
                                      threshold_price_phase_rel * open_close_1),
                                  start=sideways_count,
                                  end=1)

    # abrupt: change of sign in derivative and absolute value of curvature > 2
    # not allowed across last 5 candles
    abrupt_blue, large_curvature = get_abrupt(data=sma_8, n=5, threshold=threshold_abrupt*entry_bar['close'])

    # determine size of corridor for smooth relative to entry bar
    max_dist = 0.5 * open_close_1 * max_sma_8_dist
    _, _, slope_blue = get_smooth(data=sma_8,
                                  max_dist=max_dist,
                                  start=sideways_count,
                                  end=1)

    volatile = get_volatile(data=sma_8,
                            num_samples=5,
                            max_curvature=curvature_volatile*entry_bar['close'],
                            start=sideways_count,
                            end=0)

    # linear regression over sideways candles
    # scale x-axis between 0 and number of candles
    sideways_candles = model.market_data.history[topic].iloc[-sideways_count:-1]
    lr_sideways_results = get_linear_regression(
        data=model.market_data.history[topic]['close'],
        start=sideways_count,
        end=1)
    # extract slope of regression line
    slope_sideways_lr = lr_sideways_results.coef_[0]

    last_min, last_max = get_recent_high_low(
        data=sideways_candles[['open', 'close']], n=n_candles_drift)

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
            0.0) and model.account.positions[ticker]['side'].upper() == 'BUY':

        new_stop_loss_long = custom_round(
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
                side='SELL',
                qty=int(np.ceil(model.account.positions[ticker]['size'])),
                order_type='Market',
                expiry=expiry,
                stop_loss=None,
                take_profit=None,
                reduce_only=True)

        # if after 3 candles the trade is still not in the profit zone and the last candle is red, exit the trade
        elif (model.model_storage['exit_candles'] >=
                3) and (last_exit_candle['close'] < last_exit_candle['open']):
            model.account.place_order(
                symbol=ticker,
                side='SELL',
                qty=int(np.ceil(model.account.positions[ticker]['size'])),
                expiry=expiry,
                order_type='Market',
                stop_loss=None,
                take_profit=None,
                reduce_only=True)

        # if the last closing price is above the trade price + 0.25 * body of entry bar
        # or above the trade price + 5 points, adjust stop loss to the trade price + the trading fee
        elif (((last_exit_candle['close'] > custom_round(
                last_trade['price'] +
                0.1 * model.model_storage['entry_open_close_1_long'],
                tick_size)) or (last_exit_candle['close'] > custom_round(
                    last_trade['price'] + last_exit_candle['close'] *
                    take_profit_stoploss, tick_size))) and
                (custom_round(last_trade['price'] + 0.1, tick_size) >
                model.account.positions[ticker]['stop_loss'])):

            model.account.set_stop_loss(symbol=ticker,
                                        side='BUY',
                                        stop_loss=custom_round(
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
                                        side='BUY',
                                        stop_loss=new_stop_loss_long)

        # if stop loss is already in the profit zone:
        # track higher lows and exit as soon as 2 lows are broken
        # only count candles that have "sizable" body
        elif ((last_trade['price'] <
                model.account.positions[ticker]['stop_loss']) and
                (abs(last_exit_candle['open'] - last_exit_candle['close']) >
                min(sizable_body_exit_rel * high_low_candle_window,
                    sizable_body_exit_abs * last_exit_candle['close']))):

            # set reference for higher low
            if len(model.model_storage['exit_long_higher_lows']) > 0:
                higher_low = model.model_storage['exit_long_higher_lows'][
                    -1]
            else:
                higher_low = 0

            # if new candle is higher low and candle is blue, add to higher lows list
            if ((last_exit_candle['open'] > higher_low) and
                (last_exit_candle['close'] > higher_low) and
                (last_exit_candle['close'] > last_exit_candle['open'])):

                model.model_storage['exit_long_higher_lows'].append(
                    min(last_exit_candle['open'],
                        last_exit_candle['close']))

                # if higher lows list exceeds 2, pop first low as only last two are relevant
                # and increase stop loss to first higher low
                if len(model.model_storage['exit_long_higher_lows']) > 2:

                    model.model_storage['exit_long_higher_lows'].pop(0)

                    # model.account.set_stop_loss(symbol=ticker,
                    #                         side='BUY',
                    #                         stop_loss=np.round(model.model_storage['exit_long_higher_lows'][0] + 0.1, tick_size))

            # if new candle is not a higher low and breaks the second highest low, exit the trade
            elif len(model.model_storage['exit_long_higher_lows']) > 1:
                if min(last_exit_candle['open'], last_exit_candle['close']
                        ) < model.model_storage['exit_long_higher_lows'][-2]:
                    model.account.place_order(
                        symbol=ticker,
                        side='SELL',
                        qty=int(
                            np.ceil(
                                model.account.positions[ticker]['size'])),
                        order_type='Market',
                        expiry=expiry,
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
            0.0) and model.account.positions[ticker]['side'].upper() == 'SELL':

        new_stop_loss_short = custom_round(
            min(model.model_storage['entry_close_1_short'],
                model.model_storage['entry_open_1_short']) +
            0.5 * model.model_storage['entry_open_close_1_short'],
            tick_size)

        # check if last candle is in the profit zone, otherwise increase exit candle counter
        if last_exit_candle['close'] > last_trade['price']:
            model.model_storage['exit_candles'] += 1

        # if there are three highs in a row or the last price is above the sma_8 + some tolerance, close position
        if (last_exit_candle['close'] >
            (sma_8[-1] + sma_8_exit_tolerance * last_exit_candle['close'])):
            model.account.place_order(
                symbol=ticker,
                side='BUY',
                qty=int(np.ceil(model.account.positions[ticker]['size'])),
                order_type='Market',
                expiry=expiry,
                stop_loss=None,
                take_profit=None,
                reduce_only=True)

        # if after 3 candles the trade is still not in the profit zone and last candle is blue, exit the trade
        elif (model.model_storage['exit_candles'] >=
                3) and (last_exit_candle['close'] > last_exit_candle['open']):
            model.account.place_order(
                symbol=ticker,
                side='BUY',
                qty=int(np.ceil(model.account.positions[ticker]['size'])),
                order_type='Market',
                expiry=expiry,
                stop_loss=None,
                take_profit=None,
                reduce_only=True)

        # if the last closing price is below the trade price - 0.25 * body of entry bar
        # or below the trade price - 5 points, adjust the stop loss to the trade price - the trading fee
        elif (((last_exit_candle['close'] < custom_round(
                last_trade['price'] -
                0.1 * model.model_storage['entry_open_close_1_short'],
                tick_size)) or (last_exit_candle['close'] < custom_round(
                    last_trade['price'] - last_exit_candle['close'] *
                    take_profit_stoploss, tick_size))) and
                (custom_round(last_trade['price'] - 0.1, tick_size) <
                model.account.positions[ticker]['stop_loss'])):

            model.account.set_stop_loss(symbol=ticker,
                                        side='SELL',
                                        stop_loss=custom_round(
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
                        last_exit_candle['open'] >
                        last_exit_candle['close']):
                    model.model_storage['exit_short_lower_highs'].append(
                        max(last_exit_candle['open'],
                            last_exit_candle['close']))

        # otherwise, decrease stop loss to the traded price plus 0.5 times the entry body
        elif ((new_stop_loss_short > last_exit_candle['close']) and
                (new_stop_loss_short <
                model.account.positions[ticker]['stop_loss'])):

            model.account.set_stop_loss(symbol=ticker,
                                        side='SELL',
                                        stop_loss=new_stop_loss_short)

        # if stop loss is already in the profit zone:
        # track lower highs and exit as soon as 2 highs are broken
        # only count candles that have "sizable" body
        elif ((last_trade['price'] >
                model.account.positions[ticker]['stop_loss']) and
                (abs(last_exit_candle['open'] - last_exit_candle['close']) >
                min(sizable_body_exit_rel * high_low_candle_window,
                    sizable_body_exit_abs * last_exit_candle['close']))):

            # set reference for lower high
            if len(model.model_storage['exit_short_lower_highs']) > 0:
                lower_high = model.model_storage['exit_short_lower_highs'][
                    -1]
            else:
                lower_high = np.inf

            # if new candle is lower high and candle is red, add to lower highs list
            if ((last_exit_candle['open'] < lower_high) and
                (last_exit_candle['close'] < lower_high) and
                (last_exit_candle['open'] > last_exit_candle['close'])):

                model.model_storage['exit_short_lower_highs'].append(
                    max(last_exit_candle['open'],
                        last_exit_candle['close']))

                # if higher lows list exceeds 2, pop first low as only last two are relevant
                # and decrease stop loss to first lower high
                if len(model.model_storage['exit_short_lower_highs']) > 2:

                    model.model_storage['exit_short_lower_highs'].pop(0)

                    # model.account.set_stop_loss(symbol=ticker,
                    #                         side='SELL',
                    #                         stop_loss=np.round(model.model_storage['exit_short_lower_highs'][0] - 0.1, tick_size))

            # if new candle is not a higher low and breaks the second highest low, exit the trade
            elif len(model.model_storage['exit_short_lower_highs']) > 1:
                if max(last_exit_candle['open'], last_exit_candle['close']
                        ) > model.model_storage['exit_short_lower_highs'][-2]:
                    model.account.place_order(
                        symbol=ticker,
                        side='BUY',
                        qty=int(
                            np.ceil(
                                model.account.positions[ticker]['size'])),
                        order_type='Market',
                        expiry=expiry,
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
       ) and topic_trend_topic_15_delta < pd.Timedelta(
           minutes=15) and topic_trend_topic_5_delta < pd.Timedelta(
                   minutes=5):

        ################################ REMOVE IN PRODUCTION ####################################################################

        # calculate timestamp to correctly index additional information to display in the analysis excel file
        ts = str(entry_bar.name)

        #######################################################################################################################

        # update last received candle to current candle
        model.model_storage['entry_bar_time'] = model.market_data.history[
            topic].iloc[-1].name

        ######################################## CHECKLIST LONG ########################################

        #################### 1 TREND ####################

        # 1.1.1 Higher lows on 15 min chart: last low must be higher than previous low
        # check if there are at least one high and two lows for stability of calculations
        # rules+=1
        if len(lows_trend_15) > 1 and not highs_trend_15.empty:

            # higher lows
            if lows_trend_15.iloc[-1] > lows_trend_15.iloc[-2]:
                # long_checklist+=1

                add_model_stats(model=model, long=True, ts=ts, key='1.1.1')

        # # 1.1.1.1 Higher lows on 5 min chart or 15 min chart: last low must be higher than previous low on one of the two time frames
        # # check if there are at least one high and two lows for stability of calculations
        # # rules+=1
        # if (len(lows_trend_5) > 1 and
        #         not highs_trend_5.empty) and (len(lows_trend_15) > 1 and
        #                                       not highs_trend_15.empty):

        #     # higher lows
        #     if (lows_trend_5.iloc[-1] > lows_trend_5.iloc[-2]) or (
        #             lows_trend_15.iloc[-1] > lows_trend_15.iloc[-2]):
        #         # long_checklist+=1

        #         add_model_stats(model=model, long=True, ts=ts, key='1.1.1.1')

        # 1.1.2 Higher lows on 5 min chart: last low must be higher than previous low
        # check if there are at least one high and two lows for stability of calculations
        # rules+=1
        if len(lows_trend_5) > 1 and not highs_trend_5.empty:

            # higher lows
            if lows_trend_5.iloc[-1] > lows_trend_5.iloc[-2]:
                # long_checklist+=1

                add_model_stats(model=model, long=True, ts=ts, key='1.1.2')

        # # 1.4.2 Breaking of a significant high (50% of entry bar) on 5 min chart: 50% of the entry bar must be above last high
        # # check if there are is at least one high for stability of calculations
        # # rules += 1
        # if not highs_trend_5.empty:

        #     # at least the "high_factor" fraction of the body of the entry bar has to be above the preceding high
        #     if highs_trend_5.iloc[-1] + high_factor * open_close_1 < entry_bar[
        #             'close']:
        #         # long_checklist += 1

        #         add_model_stats(model=model, long=True, ts=ts, key='1.4.2', value=(entry_bar['close'] - highs_trend_5.iloc[-1]) / open_close_1)

        # 1.9 Above purple: close of entry bar must be above 24 sma (Non-negotiable)
        rules += 1
        if sma_24[-1] < entry_bar['close']:
            long_checklist += 1

            add_model_stats(model=model, long=True, ts=ts, key='1.9')

        # 1.10.1 Curvature purple: slope of regression flat or in direction of trade
        # rules += 1
        if purple_flat or purple_strong_up:
            # long_checklist += 1

            add_model_stats(model=model, long=True, ts=ts, key='1.10.1')

        # 1.10.3 Purple not slowing
        # check if curvature of last 5 points is not negative
        # rules += 1
        if not purple_slowing_long:
            # long_checklist += 1

            add_model_stats(model=model, long=True, ts=ts, key='1.10.3')

        # 1.10.4 Purple increasing
        # rules += 1
        if purple_increasing:
            # long_checklist += 1

            add_model_stats(model=model, long=True, ts=ts, key='1.10.4')

        # 1.12.2 Curvature of blue:
        # not volatile
        # rules += 1
        if (not volatile):
            # checklist += 1

            add_model_stats(model=model, long=True, ts=ts, key='1.12.2')
            add_model_stats(model=model, long=False, ts=ts, key='1.12.2')

        # # 1.12.5 slope of blue:
        # # slope_blue
        # # rules += 1
        # if (slope_blue /
        #         high_low_candle_window) * candle_window < max_slope_blue:
        #     # long_checklist += 1

        #     add_model_stats(model=model, long=True, ts=ts, key='1.12.5', value=(slope_blue / high_low_candle_window) * candle_window)

        # # 1.12.6 volatility of blue:
        # # amplitude of blue within sideways relative to entry bar
        # rules += 1
        # if (sma_8.iloc[-sideways_count:].max() - sma_8.iloc[-sideways_count:].
        #         min()) / open_close_1 <= blue_amplitude_2:
        #     checklist += 1

        #     add_model_stats(model=model, long=True, ts=ts, key='1.12.6', value=(sma_8.iloc[-sideways_count:].max() - sma_8.iloc[-sideways_count:].min()) / open_close_1)
        #     add_model_stats(model=model, long=False, ts=ts, key='1.12.6', value=(sma_8.iloc[-sideways_count:].max() - sma_8.iloc[-sideways_count:].min()) / open_close_1)

        # 1.12.8 blue not slowing
        # check if curvature of last 5 points is not negative
        # rules += 1
        if not blue_slowing_long:
            # long_checklist += 1

            add_model_stats(model=model, long=True, ts=ts, key='1.12.8')

        # 1.12.9 blue not abrupt
        # check if sma8 of last 5 candles does not have a direction change of the slope with a high curvature (abs)
        # rules += 1
        if not abrupt_blue:
            # checklist += 1

            add_model_stats(model=model,
                            long=True,
                            ts=ts,
                            key='1.12.9',
                            value=large_curvature)
            add_model_stats(model=model,
                            long=False,
                            ts=ts,
                            key='1.12.9',
                            value=large_curvature)

        ###################### END 1 TREND ####################

        ###################### 2 TIME ####################

        # 2.1 Significant sideways (1-2 times of entry bar): sideways must be at most small_bars_50 times entry bar (Non-negotiable times 1 of entry bar)
        # 2.2 Small bars in sideways: All sideway candles must be smaller equal 50% of entry bar (Non-negotiable)
        rules += 1
        if (body_sideway_count_core_1 >= small_bars_50 * high_low_1).sum() == 0:
            checklist += 1

            add_model_stats(model=model,
                            long=True,
                            ts=ts,
                            key='2.2',
                            value=body_sideway_count_core_1.max())
            add_model_stats(model=model,
                            long=False,
                            ts=ts,
                            key='2.2',
                            value=body_sideway_count_core_1.max())

        # 2.3 Small bars in sideways: The two candles before the entry bar must be smaller equal 25% of the entry bar (Non-negotiable)
        rules += 1
        if (body_3_1 >= small_bars_25 * high_low_1).sum() == 0:
            checklist += 1

            add_model_stats(model=model,
                            long=True,
                            ts=ts,
                            key='2.3',
                            value=body_3_1.max())
            add_model_stats(model=model,
                            long=False,
                            ts=ts,
                            key='2.3',
                            value=body_3_1.max())

        # 2.3.2 Small bars in sideways: The ATR of the two candles before the entry bar must be smaller a total value ATR_small_bars_25
        rules += 1
        if (atr_3_1 >= ATR_small_bars_25 * entry_bar['close']).sum() == 0:
            checklist += 1

            add_model_stats(model=model,
                            long=True,
                            ts=ts,
                            key='2.3.2',
                            value=atr_3_1.max())
            add_model_stats(model=model,
                            long=False,
                            ts=ts,
                            key='2.3.2',
                            value=atr_3_1.max())

        # 2.7 Amplitude of sideways must be smaller than body of entry bar
        # rules += 1
        # if sideways_spread <= amplitude_factor * open_close_1:
        #     checklist += 1

        #     add_model_stats(model=model, long=True, ts=ts, key='2.7', value=(sideways_spread) / open_close_1)
        #     add_model_stats(model=model, long=False, ts=ts, key='2.7', value=(sideways_spread) / open_close_1)

        # 2.8.1 no trend in sideways: calculated via linear regression over sideways
        rules += 1
        if (abs(slope_sideways_lr) / high_low_candle_window_ex_entry
           ) * candle_window < max_slope_sideways:
            checklist += 1

            add_model_stats(
                model=model,
                long=True,
                ts=ts,
                key='2.8.1',
                value=(slope_sideways_lr / high_low_candle_window_ex_entry) *
                candle_window)
            add_model_stats(
                model=model,
                long=False,
                ts=ts,
                key='2.8.1',
                value=(slope_sideways_lr / high_low_candle_window_ex_entry) *
                candle_window)

        # 2.9.5 No drift: little to no drift prior to entry bar
        rules += 1
        if (entry_bar['open'] - last_min) <= open_close_1 * drift_factor:
            long_checklist += 1

            add_model_stats(model=model,
                            long=True,
                            ts=ts,
                            key='2.9.5',
                            value=(entry_bar['open'] - last_min) / open_close_1)

        # # 2.10 sideways yellow squares
        # # rules += 1
        # if sideways_yellow_squares_long:
        #     # long_checklist += 1

        #     add_model_stats(model=model, long=True, ts=ts, key='2.10')

        # 2.11 no price phase in sideways
        rules += 1
        if not price_phase:
            checklist += 1

            add_model_stats(model=model, long=True, ts=ts, key='2.11')
            add_model_stats(model=model, long=False, ts=ts, key='2.11')
        # #################### END 2 TIME ####################

        # #################### 3 BAR ####################

        # 3.1 Entry bar in opposite 1/5ths: the wigs of the entry bar must be smaller equal 20% of the candle (High to low) (Non-negotiable)
        rules += 1
        if (opposite_fifths * high_low_1 >=
                low_open_1) and (opposite_fifths * high_low_1 >= high_close_1):
            long_checklist += 1

            add_model_stats(model=model,
                            long=True,
                            ts=ts,
                            key='3.1',
                            value=max(low_open_1, high_close_1) / high_low_1)

        # 3.2 Entry bar shows a significant price move
        rules += 1
        if open_close_1 >= minimum_movement * entry_bar[
                'open'] and open_close_1 <= maximum_movement * entry_bar['open']:
            checklist += 1

            add_model_stats(model=model,
                            long=True,
                            ts=ts,
                            key='3.2',
                            value=open_close_1)
            add_model_stats(model=model,
                            long=False,
                            ts=ts,
                            key='3.2',
                            value=open_close_1)

        # 3.4 Blue entry bar: close of entry bar must be greater than open of entry bar (Non-negotiable)
        rules += 1
        if entry_bar['close'] > entry_bar['open']:
            long_checklist += 1

            add_model_stats(model=model, long=True, ts=ts, key='3.4')

        # 3.5.1 Breaking of a significant high on 15 min chart
        # check if there is at least one for stability of calculations
        # rules += 1
        if not highs_trend_15.empty:

            # entry bar has to be above the preceding high
            if highs_trend_15.iloc[-1] < entry_bar['close']:
                # long_checklist += 1

                add_model_stats(
                    model=model,
                    long=True,
                    ts=ts,
                    key='3.5.1',
                    value=(entry_bar['close'] - highs_trend_15.iloc[-1]) /
                    open_close_1)

        # 3.5.2 Breaking of a significant high on 5 min chart
        # check if there is at least one for stability of calculations
        rules += 1
        if not highs_trend_5.empty:

            # entry bar has to be above the preceding high
            if highs_trend_5.iloc[-1] < entry_bar['close']:
                long_checklist += 1

                add_model_stats(
                    model=model,
                    long=True,
                    ts=ts,
                    key='3.5.2',
                    value=(entry_bar['close'] - highs_trend_5.iloc[-1]) /
                    open_close_1)

        #################### END BAR ####################

        ######################################## END CHECKLIST LONG ########################################

        ######################################## CHECKLIST SHORT ########################################

        #################### 1 TREND ####################

        # 1.1.1 Lower highs on 15 min chart: last high must be lower than previous high
        # check if there are at least two highs and one low for stability of calculations
        if len(highs_trend_15) > 1 and not lows_trend_15.empty:

            # lower highs_trend_15, but retracement of last high of maximum retracement_factor x difference between last low and second last high
            if highs_trend_15.iloc[-1] < highs_trend_15.iloc[-2]:
                # short_checklist+=1

                add_model_stats(model=model, long=False, ts=ts, key='1.1.1')

        # # 1.1.1.1 Lower highs on 5 min chart or 15 min chart: last low must be higher than previous low on one of the two time frames
        # # check if there are at least two highs and onw low for stability of calculations
        # if (len(highs_trend_5) > 1 and
        #         not lows_trend_5.empty) and (len(highs_trend_15) > 1 and
        #                                      not lows_trend_15.empty):

        #     # lower highs
        #     if (highs_trend_5.iloc[-1] < highs_trend_5.iloc[-2]) or (
        #             highs_trend_15.iloc[-1] < highs_trend_15.iloc[-2]):
        #         # short_checklist+=1

        #         add_model_stats(model=model, long=False, ts=ts, key='1.1.1.1')

        # 1.1.2 Lower highs on 5 min chart: last high must be lower than previous high
        # check if there are at least two highs and one low for stability of calculations
        if len(highs_trend_5) > 1 and not lows_trend_5.empty:

            # lower highs_trend_15, but retracement of last high of maximum retracement_factor x difference between last low and second last high
            if highs_trend_5.iloc[-1] < highs_trend_5.iloc[-2]:
                # short_checklist+=1

                add_model_stats(model=model, long=False, ts=ts, key='1.1.2')

        # # 1.4.2 Breaking of a significant low (50% of entry bar) on 5 min chart: 50% of the entry bar must be below last low
        # # check if there is at least one low for stability of calculations
        # if not lows_trend_5.empty:

        #     # at least the "high_factor" fraction of the body of the entry bar has to be below the preceding low
        #     if lows_trend_5.iloc[-1] - high_factor * open_close_1 > entry_bar[
        #             'close']:
        #         # short_checklist += 1

        #         add_model_stats(model=model, long=False, ts=ts, key='1.4.2', value=(lows_trend_5.iloc[-1] - entry_bar['close']) / open_close_1)

        # 1.9 Below purple: close of entry bar must be below 24 sma
        if sma_24[-1] > entry_bar['close']:
            short_checklist += 1

            add_model_stats(model=model, long=False, ts=ts, key='1.9')

        # 1.10.1 Curvature purple: slope of regression flat or in direction of trade
        if purple_flat or purple_strong_down:
            # short_checklist += 1

            add_model_stats(model=model, long=False, ts=ts, key='1.10.1')

        # 1.10.3 Purple not slowing
        if not purple_slowing_short:
            # short_checklist += 1

            add_model_stats(model=model, long=False, ts=ts, key='1.10.3')

        # 1.10.4 Purple accelerating
        if purple_decreasing:
            # short_checklist += 1

            add_model_stats(model=model, long=False, ts=ts, key='1.10.4')

        # # 1.12.5 slope of blue:
        # # slope_blue
        # if (slope_blue /
        #         high_low_candle_window) * candle_window > -max_slope_blue:
        #     # short_checklist += 1

        #     add_model_stats(model=model, long=False, ts=ts, key='1.12.5', value=(slope_blue / high_low_candle_window) * candle_window)

        # 1.12.8 blue not slowing
        # check if curvature of last 5 points is not negative
        if not blue_slowing_short:
            # short_checklist += 1

            add_model_stats(model=model, long=False, ts=ts, key='1.12.8')

        # #################### END 1 TREND ####################

        # #################### 2 TIME ####################

        # 2.9.5 No drift: little to no drift prior to entry bar
        if (last_max - entry_bar['open']) <= open_close_1 * drift_factor:
            short_checklist += 1

            add_model_stats(model=model,
                            long=False,
                            ts=ts,
                            key='2.9.5',
                            value=(last_max - entry_bar['open']) / open_close_1)

        # # 2.10 sideways yellow squares
        # if sideways_yellow_squares_short:
        #    # short_checklist += 1

        #     add_model_stats(model=model, long=False, ts=ts, key='2.10')
        # #################### END 2 TIME ####################

        # #################### 3 BAR ####################

        # 3.1 Entry bar in opposite 1/5ths: the wigs of the entry bar must be smaller equal 20% of the candle (High to low) (Non-negotiable)
        if (opposite_fifths * high_low_1 >=
                high_open_1) and (opposite_fifths * high_low_1 >= low_close_1):
            short_checklist += 1

            add_model_stats(model=model,
                            long=False,
                            ts=ts,
                            key='3.1',
                            value=max(high_open_1, low_close_1) / high_low_1)

        # 3.4 Red entry bar: close of entry bar must be smaller than open of entry bar
        if entry_bar['close'] < entry_bar['open']:
            short_checklist += 1

            add_model_stats(model=model, long=False, ts=ts, key='3.4')

        # 3.5.1 Breaking of a significant low on 15 min chart
        # check if there is at least one low for stability of calculations
        if not lows_trend_15.empty:

            # the body of the entry bar has to be below the preceding low
            if lows_trend_15.iloc[-1] > entry_bar['close']:
                # short_checklist += 1

                add_model_stats(
                    model=model,
                    long=False,
                    ts=ts,
                    key='3.5.1',
                    value=(lows_trend_15.iloc[-1] - entry_bar['close']) /
                    open_close_1)

        # 3.5.2 Breaking of a significant low on 5 min chart
        # check if there is at least one low for stability of calculations
        if not lows_trend_5.empty:

            # the body of the entry bar has to be below the preceding low
            if lows_trend_5.iloc[-1] > entry_bar['close']:
                short_checklist += 1

                add_model_stats(
                    model=model,
                    long=False,
                    ts=ts,
                    key='3.5.2',
                    value=(lows_trend_5.iloc[-1] - entry_bar['close']) /
                    open_close_1)

        #################### END BAR ####################

        ######################################## END CHECKLIST SHORT ########################################

        # calculate score across all rules

        #################### REMOVE IF NON CORE-RULES ARE APPLIED ###########################################
        # rules = 1
        #####################################################################################################

        confidence_score_long = (long_checklist + checklist) / rules
        confidence_score_short = (short_checklist + checklist) / rules

        confidence_score_core_long = (long_checklist + checklist) / rules
        confidence_score_core_short = (short_checklist + checklist) / rules

        # determine trading quantity
        # buy_qty = 100 / entry_bar['close']
        # buy_qty = np.round(buy_qty, tick_size)

        # buy with all available balance
        buy_qty = 0.95 * model.account.wallet[CONTRACT_CUR][
            'available_balance'] / entry_bar['close']

        ##################################################################################################################

        # if all rules apply for the long strategy and there is no current open position, place buy order
        if (confidence_score_core_long
                == 1.0) and (confidence_score_long >= 1) and (
                    model.account.positions[ticker]['size'] == 0.0):

            buy_qty = 1

            print('Trade long! \n  symbol: {} \n qty: {} \n expiry: {} \n stop loss: {} \n take profit: {}'.format(ticker, buy_qty, expiry, stop_loss_long, take_profit_long))
            model.account.place_order(symbol=ticker,
                                      side='BUY',
                                      qty=buy_qty,
                                      order_type='MARKET',
                                      expiry=expiry,
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

            buy_qty = 1
            print('Trade long! \n  symbol: {} \n qty: {} \n expiry: {} \n stop loss: {} \n take profit: {}'.format(ticker, buy_qty, expiry, stop_loss_short, take_profit_long))
            model.account.place_order(symbol=ticker,
                                      side='SELL',
                                      qty=buy_qty,
                                      order_type='MARKET',
                                      expiry=expiry,
                                      stop_loss=stop_loss_short,
                                      take_profit=take_profit_short)
            model.model_storage['entry_open_close_1_short'] = open_close_1
            model.model_storage['entry_close_1_short'] = entry_bar['close']
            model.model_storage['entry_open_1_short'] = entry_bar['open']
            model.model_storage['exit_short_lower_highs'] = []
            model.model_storage['exit_candles'] = 0
