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
    long_term_topic = 'candle.{}.{}'.format(trading_freq, ticker)
    trend_15_topic = 'candle.15.{}'.format(ticker)
    trend_5_topic = 'candle.5.{}'.format(ticker)
    min_action_topic = 'candle.{}.{}'.format(trading_freq, ticker)
    exit_topic = 'candle.{}.{}'.format(1, ticker)

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
    threshold_price_phase_abs = 10

    # relative threshold for price phase within sideways (compared to entry bar)
    threshold_price_phase_rel = 0.8

    # High and low definition: last high must be 50% higher than previous high
    # To be a breaking high, 50% of the entry candle body has to above the preceding high
    high_factor = 0.3
    # high_factor = 0.5
    # high_factor = model.model_args['param']

    # maximum absolute value of true range for two candles before entry bar
    ATR_small_bars_25 = 10 / 2000

    # maximum relative slope of sideways, measured relative to size of trading screen
    # (suggestion 0.6-0.7)
    max_slope_sideways = 0.6
    # max_slope_sideways = model.model_args['param']

    # determine minimum movement of entry bar in fraction to open price
    minimum_movement = 2 / 2000
    maximum_movement = 10 / 2000

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

    # set tick size of orders as number of decimal digits
    # 0 rounds on whole numbers, negative numbers round integers on whole "tens"
    tick_size = 1

    ######################################## END PARAMETERS ########################################

    ######################################## DEFINITION VARIABLES ########################################

    # last relevant candles for strategy
    try:
        entry_bar = model.market_data.history[topic].iloc[-1]
        last_exit_candle = model.market_data.history[exit_topic].iloc[-1]
        last_action_candle = model.market_data.history[min_action_topic].iloc[
            -1]
    except:
        print('No data available!')
        return None

    # Only proceed if new action topic candle is received, i.e. ignore all smaller candles
    # Adjust "action_freq" if actions are performed for smaller candles
    if last_action_candle.name <= model.model_storage['action_bar_time']:
        print('No new action data!')
        return None
    else:
        # update last received action candle to current candle
        model.model_storage['action_bar_time'] = model.market_data.history[
            min_action_topic].iloc[-1].name

    # simple moving averages
    sma_8 = sma(model.market_data.history[long_term_topic]['close'], window=8)

    # calculate various spreads of entry bar
    high_low_1 = abs(entry_bar['high'] - entry_bar['low'])
    low_open_1 = abs(entry_bar['open'] - entry_bar['low'])
    high_open_1 = abs(entry_bar['open'] - entry_bar['high'])
    high_close_1 = abs(entry_bar['high'] - entry_bar['close'])
    open_close_1 = abs(entry_bar['close'] - entry_bar['open'])
    low_close_1 = abs(entry_bar['close'] - entry_bar['low'])

    # calculate high and low of last "candle_window" candles as a reference point on how to scale visual inspections according to charts
    high_low_candle_window = get_trading_window(
        data=model.market_data.history[topic],
        window_size=candle_window,
        include_entry=True)

    ######################################## END DEFINITION VARIABLES ########################################

    ######################################## EXIT STRATEGY ########################################

    # check for open positions
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
                side='Sell',
                qty=int(np.ceil(model.account.positions[ticker]['size'])),
                expiry=expiry,
                order_type='Market',
                stop_loss=None,
                take_profit=None,
                reduce_only=True)

        # if the last closing price is above the trade price + 0.25 * body of entry bar
        # or above the trade price + 5 points, adjust stop loss to the trade price + the trading fee
        elif (((last_exit_candle['close'] > np.round(
                last_trade['price'] +
                0.1 * model.model_storage['entry_open_close_1_long'],
                tick_size)) or (last_exit_candle['close'] > np.round(
                    last_trade['price'] + last_exit_candle['close'] *
                    take_profit_stoploss, tick_size))) and
                (np.round(last_trade['price'] + 0.1, tick_size) >
                model.account.positions[ticker]['stop_loss'])):

            model.account.set_stop_loss(
                symbol=ticker,
                side='Buy',
                position_id=model.account.positions[ticker]['position_id'],
                stop_loss=np.round(last_trade['price'] + 0.1, tick_size))

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

            model.account.set_stop_loss(
                symbol=ticker,
                side='Buy',
                position_id=model.account.positions[ticker]['position_id'],
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
                    #                         side='Buy',
                    #                         stop_loss=np.round(model.model_storage['exit_long_higher_lows'][0] + 0.1, tick_size))

            # if new candle is not a higher low and breaks the second highest low, exit the trade
            elif len(model.model_storage['exit_long_higher_lows']) > 1:
                if min(last_exit_candle['open'], last_exit_candle['close']
                        ) < model.model_storage['exit_long_higher_lows'][-2]:
                    model.account.place_order(
                        symbol=ticker,
                        side='Sell',
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
            0.0) and model.account.positions[ticker]['side'] == 'Sell':

        new_stop_loss_short = np.round(
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
                side='Buy',
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
                side='Buy',
                qty=int(np.ceil(model.account.positions[ticker]['size'])),
                order_type='Market',
                expiry=expiry,
                stop_loss=None,
                take_profit=None,
                reduce_only=True)

        # if the last closing price is below the trade price - 0.25 * body of entry bar
        # or below the trade price - 5 points, adjust the stop loss to the trade price - the trading fee
        elif (((last_exit_candle['close'] < np.round(
                last_trade['price'] -
                0.1 * model.model_storage['entry_open_close_1_short'],
                tick_size)) or (last_exit_candle['close'] < np.round(
                    last_trade['price'] - last_exit_candle['close'] *
                    take_profit_stoploss, tick_size))) and
                (np.round(last_trade['price'] - 0.1, tick_size) <
                model.account.positions[ticker]['stop_loss'])):

            model.account.set_stop_loss(
                symbol=ticker,
                side='Sell',
                position_id=model.account.positions[ticker]['position_id'],
                stop_loss=np.round(last_trade['price'] - 0.1, tick_size))

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

            model.account.set_stop_loss(
                symbol=ticker,
                side='Sell',
                position_id=model.account.positions[ticker]['position_id'],
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
                    #                         side='Sell',
                    #                         stop_loss=np.round(model.model_storage['exit_short_lower_highs'][0] - 0.1, tick_size))

            # if new candle is not a higher low and breaks the second highest low, exit the trade
            elif len(model.model_storage['exit_short_lower_highs']) > 1:
                if max(last_exit_candle['open'], last_exit_candle['close']
                        ) > model.model_storage['exit_short_lower_highs'][-2]:
                    model.account.place_order(
                        symbol=ticker,
                        side='Buy',
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
    # if (entry_bar.name.hour * 60 + entry_bar.name.minute <=
    #         510) or (entry_bar.name.hour * 60 + entry_bar.name.minute >= 960):
    #     return None

    # only trade if new data from topic is received
    # and topic, long term topic and trend topic data have arrived if all are expected
    if (entry_bar.name > model.model_storage['entry_bar_time']):

        ################################ REMOVE IN PRODUCTION ####################################################################

        # calculate timestamp to correctly index additional information to display in the analysis excel file
        ts = str(entry_bar.name)

        #######################################################################################################################

        # update last received candle to current candle
        model.model_storage['entry_bar_time'] = model.market_data.history[
            topic].iloc[-1].name

        # calculate score across all rules

        #################### REMOVE IF NON CORE-RULES ARE APPLIED ###########################################
        rules = 1
        checklist = 0
        if entry_bar['open'] > entry_bar['close']:
            short_checklist = 1
            long_checklist = 0
        else:
            short_checklist = 0
            long_checklist = 1
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

            # for real trading, set leverage of position to leverage, for backtesting just scale position size
            # buy_qty=leverage*buy_qty
            # buy_qty = np.round(buy_qty, tick_size)
            buy_qty = 1

            response = model.account.place_order(symbol=ticker,
                                      side='BUY',
                                      qty=buy_qty,
                                      order_type='MARKET',
                                      expiry=expiry,
                                      stop_loss=stop_loss_long,
                                      take_profit=take_profit_long)

            print('Trade long!')
            print(response)

            model.model_storage['entry_open_close_1_long'] = open_close_1
            model.model_storage['entry_close_1_long'] = entry_bar['close']
            model.model_storage['entry_open_1_long'] = entry_bar['open']
            model.model_storage['exit_long_higher_lows'] = []
            model.model_storage['exit_candles'] = 0

        # if all rules apply for the short strategy and there is no current open position, place sell order
        if (confidence_score_core_short
                == 1.0) and (confidence_score_short >= 1) and (
                    model.account.positions[ticker]['size'] == 0.0):

            # for real trading, set leverage of position to leverage, for backtesting just scale position size
            # buy_qty=leverage*buy_qty
            # buy_qty = np.round(buy_qty, tick_size)
            buy_qty = 1

            response = model.account.place_order(symbol=ticker,
                                      side='SELL',
                                      qty=buy_qty,
                                      order_type='Market',
                                      expiry=expiry,
                                      stop_loss=stop_loss_short,
                                      take_profit=take_profit_short)
            print('Trade short!')
            print(response)

            model.model_storage['entry_open_close_1_short'] = open_close_1
            model.model_storage['entry_close_1_short'] = entry_bar['close']
            model.model_storage['entry_open_1_short'] = entry_bar['open']
            model.model_storage['exit_short_lower_highs'] = []
            model.model_storage['exit_candles'] = 0
