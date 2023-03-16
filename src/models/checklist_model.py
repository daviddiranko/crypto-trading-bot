import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)

from typing import Dict, Any
from src.TradingModel import TradingModel
from src.helper_functions.statistics import sma, get_alternate_highs_lows, get_slopes_highs_lows
import numpy as np
from sklearn.linear_model import LinearRegression
from src.endpoints.bybit_functions import *
import os
from dotenv import load_dotenv

load_dotenv()

BASE_CUR = os.getenv('BASE_CUR')

def checklist_model(model: TradingModel):
    '''
    checklist-based trend following model
    '''

    # declare ticker
    # ticker = 'RTYUSD'
    ticker = model.model_args['ticker']

    # declare topics
    # topic = 'candle.1.{}'.format(ticker)
    topic = 'candle.5.{}'.format(ticker)
    long_term_topic = 'candle.5.{}'.format(ticker)
    trend_topic = 'candle.15.{}'.format(ticker)
    short_term_topic = 'candle.5.{}'.format(ticker)

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

    # Sideways: multiple of length of entry bar to incorporate into the sideways candles
    sideways_factor = 1
    # sideways_factor = model.model_args['param']

    # Sideways: all candles in sideways must be smaller eqal factor times entry bar
    small_bars_50 = 0.5
    # small_bars_50 = model.model_args['param']

    # Sideways: last 2 candles before entry bar must be smaller equal parameter times entry bar
    small_bars_25 = 0.25
    # small_bars_25 = model.model_args['param']

    # Opposite 1/5ths: the wigs of the entry bar must be smaller equal 20% of the candle (High to low)
    opposite_fifths = 0.2
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

    # multiple of body of entry bar that amplitude (i.e. maximum open or close - minimum of open or close) of sideways candles can have
    surprise_factor = 1.2
    # surprise_factor = model.model_args['param']

    # percentage of trading screen height (i.e. maximum high to minimum low within candle_window) the entry bar has to fill to be a surprise.
    # 0.2 is currently best, 0.15 and 0.1 is too small
    surprise_factor_2 = 0.2
    # surprise_factor_2 = model.model_args['param']

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

    # set tick size of orders as number of decimal digits
    # 0 rounds on whole numbers, negative numbers round integers on whole "tens"
    tick_size = 1

    ######################################## END PARAMETERS ########################################

    ######################################## DEFINITION VARIABLES ########################################

    # last relevant candles for strategy
    entry_bar = model.market_data.history[topic].iloc[-1]
    last_trend_candle = model.market_data.history[trend_topic].iloc[-1]
    last_short_term_candle = model.market_data.history[short_term_topic].iloc[-1]
    last_long_term_candle = model.market_data.history[long_term_topic].iloc[-1]
    

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
    high_candle_window = model.market_data.history[topic].iloc[
        -candle_window:]['high'].max()
    low_candle_window = model.market_data.history[topic].iloc[
        -candle_window:]['low'].min()
    high_low_candle_window = abs(high_candle_window - low_candle_window)

    # count sideways according to chart visuals
    sideways_count = max(
        int(
            np.floor(
                (open_close_1 / (high_low_candle_window+0.00001)) * chart_height *
                sideways_factor * (candle_window / chart_width))), 2)

    # calculate the body of the sideways candles
    body_sideway_count_1 = (
        model.market_data.history[topic].iloc[-sideways_count:-1]['close'] -
        model.market_data.history[topic].iloc[-sideways_count:-1]['open']
    ).abs()

    long_term_series = model.market_data.history[long_term_topic]['close'].copy()

    # if last timestamp of topic and long term topic are not identical, append last timestamp of topic to long term topic
    if topic_long_term_topic_delta>pd.Timedelta(minutes=1):
        long_term_series[entry_bar.name]=entry_bar['close']

    # calculate alternating highs and lows of trading line
    highs, lows = get_alternate_highs_lows(
        candles=long_term_series,
        min_int=n_candles,
        sma_diff=high_low_sma,
        min_int_diff=n_candles_diff)
    
    trend_series = model.market_data.history[trend_topic]['close'].copy()

    # calculate frequency of trend series, the minimum is necessary to prevent distortions during time shifts
    freq = (trend_series.index[1:]-trend_series.index[:-1]).min()

    # if last timestamp of topic and trend topic are not identical, append last timestamp of topic to trend topic
    if topic_trend_topic_delta>pd.Timedelta(minutes=1):
        trend_series[entry_bar.name]=entry_bar['close']

    # calculate alternating highs and lows of trend line
    highs_trend, lows_trend = get_alternate_highs_lows(
        candles=trend_series,
        min_int=n_candles, 
        sma_diff=high_low_sma, 
        min_int_diff=n_candles_diff)

    # calculate the last resistance line as two consecutive highs that are close together and not succeed by a higher high
    resistances = highs_trend.loc[(highs_trend.diff()/highs_trend).abs()<=support_resistance_diff]
    if not resistances.empty:
        highs_over_resistance = highs_trend.loc[highs_trend>(resistances[-1]*(1+1.1*support_resistance_diff))]
    else:
        highs_over_resistance = pd.Series()

    # check if highs_over_resistance is not empty for stability of calculation
    if not highs_over_resistance.empty:

        # check if last high that exceeds resistance was prior to establishment of resistance:
        if highs_over_resistance.index[-1] < resistances.index[-1]:
            resistance = resistances[-1]*(1+1.1*support_resistance_diff)
        else:
            resistance = None
            
    elif not resistances.empty:
        resistance = resistances[-1]*(1+1.1*support_resistance_diff)
    else:
        resistance = None
    
    # calculate the last support line as two consecutive lows that are close together and not broken by a lower low
    supports = lows_trend.loc[(lows_trend.diff()/lows_trend).abs()<=support_resistance_diff]
    if not supports.empty:
        lows_under_support = lows_trend.loc[lows_trend<(supports[-1]*(1-1.1*support_resistance_diff))]
    else:
        lows_under_support = pd.Series()

    # check if lows_under_support is not empty for stability of calculation
    if not lows_under_support.empty:

        # check if last low that breaks support was prior to establishment of support:
        if lows_under_support.index[-1] < supports.index[-1]:
            support = supports[-1]*(1-1.1*support_resistance_diff)
        else:
            support = None
    elif not supports.empty:
        support = supports[-1]*(1-1.1*support_resistance_diff)
    else:
        support = None

    # calculate slopes of connection lines between highs and lows of trend series
    high_low_slopes_trend = get_slopes_highs_lows(lows=lows_trend, highs=highs_trend, freq=freq)
    

    # calculate maximum spread between open and close prices of sideways candles
    sideways_count_max = max(
        model.market_data.history[topic].iloc[-sideways_count:-1]
        ['open'].max(),
        model.market_data.history[topic].iloc[-sideways_count:-1]
        ['close'].max())
    sideways_count_min = min(
        model.market_data.history[topic].iloc[-sideways_count:-1]
        ['open'].min(),
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
    slope_sideways_long = ((slope_sideways<-slope_purple_param).rolling(3).sum()==3.0).sum()==0

    # check if at no point 3 candles in a row have a slope of more than 0.3
    slope_sideways_short = ((slope_sideways>slope_purple_param).rolling(3).sum()==3.0).sum()==0


    # Define smooth, strong, flat and increasing (all with respect to sma8)

    # increasing: mean of curvature across last 5 candles > 0 AND last slope > 0
    increasing = (sma_8.diff().diff().iloc[-5:].mean()>0) and (sma_8.diff().iloc[-1]>0)

    # decreasing: mean of curvature across last 5 candles < 0 AND last slope < 0
    decreasing = (sma_8.diff().diff().iloc[-5:].mean()<0) and (sma_8.diff().iloc[-1]<0)

    # filter all time points thar have three consecutive increases or decreases
    # series shows if it was increase or decrease through the sign
    consecutive_increase = sma_8.diff().iloc[-sideways_count:].loc[(sma_8.diff().iloc[-sideways_count:]>0).rolling(3).sum()==3.0]
    consecutive_decrease = sma_8.diff().iloc[-sideways_count:].loc[(sma_8.diff().iloc[-sideways_count:]<0).rolling(3).sum()==3.0]

    # concatenate both series and sort by index to get alternating series
    consecutives = pd.concat([consecutive_increase,consecutive_decrease]).sort_index()

    # show change in slope by multiplying each entry (=slope) with its successor
    # a change in the slope is identified by a negative sign (increasing to decreasing or vice versa)
    changing_signs = (consecutives*consecutives.shift(1)<0).sum()

    # determine last indices that had three consecutive signs in their slopes and 
    # first indices that had three consecutive signs in their slope after a shift in slope
    before_indices = consecutives.loc[consecutives*consecutives.shift(-1)<0].index
    after_indices = consecutives.loc[consecutives*consecutives.shift(1)<0].index.map(lambda x: sma_8.diff().index[sma_8.diff().index<x][-2])
    
    # determine slopes of prices before and after consecutive change in direction
    slopes_before_change = sma_8.diff().loc[before_indices].reset_index(drop=True)
    slopes_after_change = sma_8.diff().loc[after_indices].reset_index(drop=True)

    # determine curvature of price change
    curvatures_at_change = (slopes_after_change - slopes_before_change).abs()

    # smooth: maximum 2 changes in slopes, but only count changes if they persist for at least 3 candles AND curvature at change <2 
    smooth = changing_signs<=2 and (curvatures_at_change>=2).sum()==0

    # strong: mean of slopes across last 5 candles > 0.5 for long and < -0.5 for short
    strong_long = sma_8.diff().iloc[-5:].mean() > 0.5
    strong_short = sma_8.diff().iloc[-5:].mean() < -0.5

    # flat: no three candles in a row can have a slope of more than 0.3 or less than -0.3
    flat_increase = ((sma_8.diff().iloc[-sideways_count:-5]>sma_flat_param).rolling(3).sum()==3.0).sum()==0
    flat_decrease = ((sma_8.diff().iloc[-sideways_count:-5]<-sma_flat_param).rolling(3).sum()==3.0).sum()==0
    flat = flat_increase and flat_decrease


    # linear regression of sma_24 since second last low of trading line for long side
    # scale x-axis between 0 and number of candles
    trend_series_long = sma_24.loc[lows.index[-2]:]
    X_sma_long = np.array(range(len(trend_series_long))).reshape(-1, 1)

    # scale sma_24 by high-low spread of last 75 candles to normalize the slope of the candles
    Y_sma_long = trend_series_long / (high_low_candle_window+0.00001)

    # calculate linear regression within sma_24 to identify a potential trend
    sk_lr_sma_long = LinearRegression()
    sk_results_sma_long = sk_lr_sma_long.fit(X_sma_long, Y_sma_long)

    # extract slope of regression line
    slope_sma_long = sk_results_sma_long.coef_[0]

    # linear regression of sma_24 since second last high of trading line for short side
    # scale x-axis between 0 and number of candles
    trend_series_short = sma_24.loc[highs.index[-2]:]
    X_sma_short = np.array(range(len(trend_series_short))).reshape(-1, 1)

    # scale sma_24 by high-low spread of last 75 candles to normalize the slope of the candles
    Y_sma_short = trend_series_short / (high_low_candle_window+0.00001)

    # calculate linear regression within sma_24 to identify a potential trend
    sk_lr_sma_short = LinearRegression()
    sk_results_sma_short = sk_lr_sma_short.fit(X_sma_short, Y_sma_short)

    # extract slope of regression line
    slope_sma_short = sk_results_sma_short.coef_[0]


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
        
        new_stop_loss_long = np.round(max(model.model_storage['entry_close_1_long'],
                            model.model_storage['entry_open_1_long']) - 0.5 * model.model_storage['entry_open_close_1_long'], tick_size)

        new_stop_loss_long_2 = np.round(max(model.model_storage['entry_close_1_long'],
                            model.model_storage['entry_open_1_long']) - 0.25 * model.model_storage['entry_open_close_1_long'], tick_size)

        # if the last close price is below the sma_8, close position
        if (entry_bar['close'] < sma_8[-1]):
            model.account.place_order(
                symbol=ticker,
                side='Sell',
                qty=np.ceil(model.account.positions[ticker]['size']),
                order_type='Market',
                stop_loss=None,
                take_profit=None,
                reduce_only=True)
        
        # if the last closing price is above the trade price + the trading fee, adjust stop loss to the trade price + the trading fee
        elif (last_short_term_candle['close'] > np.round(last_trade['price'] + 0.1, tick_size)) and (np.round(last_trade['price'] + 0.1, tick_size) > model.account.positions[ticker]['stop_loss']):
            
            model.account.set_stop_loss(symbol=ticker,
                                        side='Buy',
                                        stop_loss=np.round(
                                            last_trade['price'] + 0.1, tick_size))
            model.model_storage['exit_long_higher_lows'].append(last_short_term_candle['open'])

        # otherwise if the stop loss is below the traded price, but above 0.75 times entry bar, 
        # increase stop loss to the traded price minus 0.25 times the entry body
        elif model.account.positions[ticker]['stop_loss'] < last_trade[
                'price'] and (new_stop_loss_long_2 < last_short_term_candle['close']) and (new_stop_loss_long_2 > model.account.positions[ticker]['stop_loss']):

            model.account.set_stop_loss(symbol=ticker,
                                            side='Buy',
                                            stop_loss=new_stop_loss_long_2)

        # otherwise if the stop loss is below the traded price - 0.25 times entry bar, but above - 0.5 times entry bar,
        # increase stop loss to the traded price minus 0.5 times the entry body
        elif model.account.positions[ticker]['stop_loss'] < last_trade[
                'price'] and (new_stop_loss_long < last_short_term_candle['close']) and (new_stop_loss_long_2 >= last_short_term_candle['close']) and (new_stop_loss_long > model.account.positions[ticker]['stop_loss']):

            model.account.set_stop_loss(symbol=ticker,
                                            side='Buy',
                                            stop_loss=new_stop_loss_long)
            
        # if stop loss is already in the profit zone:
        # track higher lows and exit as soon as 2 lows are broken
        # only count candles that have "sizable" body
        elif len(model.model_storage['exit_long_higher_lows'])>0 and (abs(last_short_term_candle['open']-last_short_term_candle['close'])>0.02*model.model_storage['entry_open_close_1_long']):
            
            # if new candle is higher low, add to higher lows list
            if (last_short_term_candle['open']>model.model_storage['exit_long_higher_lows'][-1]) and (last_short_term_candle['close']>model.model_storage['exit_long_higher_lows'][-1]):
            
                model.model_storage['exit_long_higher_lows'].append(min(last_short_term_candle['open'],last_short_term_candle['close']))

                # if higher lows list exceeds 2, pop first low as only last two are relevant
                if len(model.model_storage['exit_long_higher_lows'])>2:
                    
                    model.model_storage['exit_long_higher_lows'].pop(0)
            
            # if new candle is not a higher low and breaks the second highest low, exit the trade
            elif len(model.model_storage['exit_long_higher_lows'])>1:
                if min(last_short_term_candle['open'],last_short_term_candle['close']) < model.model_storage['exit_long_higher_lows'][-2]:
                    model.account.place_order(
                    symbol=ticker,
                    side='Sell',
                    qty=np.ceil(model.account.positions[ticker]['size']),
                    order_type='Market',
                    stop_loss=None,
                    take_profit=None,
                    reduce_only=True)

        # exit function since position is still open
        return None

    # exit strategy for the short side
    if (model.account.positions[ticker]['size'] >
            0.0) and model.account.positions[ticker]['side'] == 'Sell':
 
        new_stop_loss_short = np.round(min(model.model_storage['entry_close_1_short'],
                                model.model_storage['entry_open_1_short']) + 0.5 * model.model_storage['entry_open_close_1_short'], tick_size)
        
        new_stop_loss_short_2 = np.round(min(model.model_storage['entry_close_1_short'],
                    model.model_storage['entry_open_1_short']) + 0.25 * model.model_storage['entry_open_close_1_short'], tick_size)

        # if there are three highs in a row or the last price is above the sma_8, close position
        if (entry_bar['close'] > sma_8[-1]):
            model.account.place_order(
                symbol=ticker,
                side='Buy',
                qty=np.ceil(model.account.positions[ticker]['size']),
                order_type='Market',
                stop_loss=None,
                take_profit=None,
                reduce_only=True)
        
        # if the last closing price is below the trade price - the trading fee, adjust the stop loss to the trade price - the trading fee
        elif (last_short_term_candle['close'] < np.round(last_trade['price'] - 0.1, tick_size)) and (
                                            np.round(last_trade['price'] - 0.1, tick_size) < model.account.positions[ticker]['stop_loss']):
            model.account.set_stop_loss(symbol=ticker,
                                        side='Sell',
                                        stop_loss=
                                            np.round(last_trade['price'] - 0.1, tick_size))
            
            model.model_storage['exit_short_lower_highs'].append(last_short_term_candle['open'])
            
        # otherwise if the stop loss is above the traded price, but below 0.75 times entry bar, 
        # increase stop loss to the traded price plus 0.25 times the entry body
        elif model.account.positions[ticker]['stop_loss'] > last_trade[
                'price'] and (new_stop_loss_short_2 > last_short_term_candle['close']) and (new_stop_loss_short_2 < model.account.positions[ticker]['stop_loss']):

            model.account.set_stop_loss(symbol=ticker,
                                            side='Sell',
                                            stop_loss=new_stop_loss_short_2)

        # otherwise if the stop loss is above the traded price + 0.25 times entry bar, but below + 0.5 times entry bar,
        # increase stop loss to the traded price plus 0.5 times the entry body
        elif model.account.positions[ticker]['stop_loss'] > last_trade[
                'price'] and (new_stop_loss_short > last_short_term_candle['close']) and (new_stop_loss_short_2 <= last_short_term_candle['close']) and (new_stop_loss_short < model.account.positions[ticker]['stop_loss']):

            model.account.set_stop_loss(symbol=ticker,
                                            side='Sell',
                                            stop_loss=new_stop_loss_short)
        
        # if stop loss is already in the profit zone:
        # track higher lows and exit as soon as 2 lows are broken
        # only count candles that have "sizable" body
        elif len(model.model_storage['exit_short_lower_highs'])>0 and (abs(last_short_term_candle['open']-last_short_term_candle['close'])>0.02*model.model_storage['entry_open_close_1_short']):
            
            # if new candle is higher low, add to higher lows list
            if (last_short_term_candle['open']<model.model_storage['exit_short_lower_highs'][-1]) and (last_short_term_candle['close']<model.model_storage['exit_short_lower_highs'][-1]):
            
                model.model_storage['exit_short_lower_highs'].append(max(last_short_term_candle['open'],last_short_term_candle['close']))

                # if higher lows list exceeds 2, pop first low as only last two are relevant
                if len(model.model_storage['exit_short_lower_highs'])>2:
                    
                    model.model_storage['exit_short_lower_highs'].pop(0)
            
            # if new candle is not a higher low and breaks the second highest low, exit the trade
            elif len(model.model_storage['exit_short_lower_highs'])>1:
                if max(last_short_term_candle['open'],last_short_term_candle['close']) > model.model_storage['exit_short_lower_highs'][-2]:
                    model.account.place_order(
                    symbol=ticker,
                    side='Buy',
                    qty=np.ceil(model.account.positions[ticker]['size']),
                    order_type='Market',
                    stop_loss=None,
                    take_profit=None,
                    reduce_only=True)

        # exit function since position is still open
        return None

    ######################################## END EXIT STRATEGY ########################################
    
    # only trade if new data from topic is received
    # and topic, long term topic and trend topic data have arrived if all are expected
    if (entry_bar.name > model.model_storage['entry_bar_time']) and topic_trend_topic_delta<pd.Timedelta(minutes=15) and topic_long_term_topic_delta<pd.Timedelta(minutes=5):
        
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
                    model.model_stats['1.1']={}

                model.model_stats['1.1'][ts] = {}
                model.model_stats['1.1'][ts]['long'] = 1
        
        # 1.2 Higher lows with retracement: last low must be higher than previous low + retracement_factor * difference between last high and second last low
        # check if there are at least one high and two lows for stability of calculations
        # rules+=1
        if len(lows_trend) > 1 and not highs_trend.empty:

            # higher lows, but retracement of last low of maximum retracement_factor x difference between last high and second last low
            if lows_trend.iloc[-1] > lows_trend.iloc[-2] + abs(highs_trend.iloc[-1]-lows_trend.iloc[-2])*(1-retracement_factor):
                # long_checklist+=1

                if '1.2' not in model.model_stats.keys():
                    model.model_stats['1.2']={}

                model.model_stats['1.2'][ts] = {}
                model.model_stats['1.2'][ts]['long'] = 1

        # 1.3 Purple strong, smooth, flat or increasing:linear regression of trend line since second last low has positive slope
        # rules+=1
        # if slope_sma_long>0:
        #     long_checklist += 1
        
        # # 1.5 Blue strong, smooth, flat or increasing (Non-negotiable)
        # core_rules += 1
        # if sma_8.iloc[-1]-sma_8.iloc[-trend_candles]>=0:
        #     core_long_checklist+=1

        # 1.3 Breaking of a significant high
        # check if there is at least one for stability of calculations
        # rules += 1
        if not highs_trend.empty:

            # entry bar has to be above the preceding high
            if highs_trend.iloc[-1] < entry_bar['close']:
                # long_checklist += 1

                if '1.3' not in model.model_stats.keys():
                    model.model_stats['1.3']={}

                model.model_stats['1.3'][ts] = {}
                model.model_stats['1.3'][ts]['long'] = 1
        
        # 1.4 Breaking of a significant high (50% of entry bar): 50% of the entry bar must be above last high
        # check if there are is at least one high for stability of calculations
        # rules += 1
        if not highs_trend.empty:

            # at least the "high_factor" fraction of the body of the entry bar has to be above the preceding high
            if highs_trend.iloc[-1] + high_factor * open_close_1 < entry_bar['close']:
                # long_checklist += 1

                if '1.4' not in model.model_stats.keys():
                    model.model_stats['1.4']={}

                model.model_stats['1.4'][ts] = {}
                model.model_stats['1.4'][ts]['long'] = 1
        
        # 1.5 breaking of a resistance line: 
        # check if resistance exists for stability of calculation
        # rules += 1
        if resistance:
            if entry_bar['close']>resistance:
                # long_checklist += 1

                if '1.5' not in model.model_stats.keys():
                    model.model_stats['1.5']={}

                model.model_stats['1.5'][ts] = {}
                model.model_stats['1.5'][ts]['long'] = 1
        
        # 1.6 Higher high: last high must exceed second last high
        # check if there are at least two highs for stability of calculations
        # rules += 1
        if len(highs_trend)>1:
            if highs_trend.iloc[-1] > highs_trend.iloc[-2]:
                # long_checklist += 1

                if '1.6' not in model.model_stats.keys():
                    model.model_stats['1.6']={}

                model.model_stats['1.6'][ts] = {}
                model.model_stats['1.6'][ts]['long'] = 1
        
        # 1.7 Time phase after Price phase: Only enter after a time phase, predecessed by a price phase
        # check if there are at least two slopes for stability of calculations
        # rules += 1
        if len(high_low_slopes_trend)>1:
            if high_low_slopes_trend[-1]<0 and high_low_slopes_trend[-2]>0:
                # long_checklist += 1

                if '1.7' not in model.model_stats.keys():
                    model.model_stats['1.7']={}

                model.model_stats['1.7'][ts] = {}
                model.model_stats['1.7'][ts]['long'] = 1
        
        # 1.8 Price phase stronger than time phase: slope of price phase must be larger than slope of time phase
        # check if there are at least two slopes for stability of calculations
        # rules += 1
        if len(high_low_slopes_trend)>1:
            if abs(high_low_slopes_trend[-1]) < abs(high_low_slopes_trend[-2]):
                # checklist += 1

                if '1.8' not in model.model_stats.keys():
                    model.model_stats['1.8']={}

                model.model_stats['1.8'][ts] = {}
                model.model_stats['1.8'][ts]['long'] = 1
                model.model_stats['1.8'][ts]['short'] = 1
        
        # 1.9 Above purple: close of entry bar must be above 24 sma (Non-negotiable)
        core_rules += 1
        if sma_24[-1] < entry_bar['close']:
            core_long_checklist += 1

            if '1.9' not in model.model_stats.keys():
                model.model_stats['1.9']={}

            model.model_stats['1.9'][ts] = {}
            model.model_stats['1.9'][ts]['long'] = 1
        
        # 1.10.1 Curvature purple: slope of regression flat or in direction of trade
        # rules += 1
        if slope_purple > -slope_purple_param:
            # long_checklist += 1

            if '1.10.1' not in model.model_stats.keys():
                model.model_stats['1.10.1']={}

            model.model_stats['1.10.1'][ts] = {}
            model.model_stats['1.10.1'][ts]['long'] = 1
        
        # 1.10.2 Curvature purple: slope of regression flat or in direction of trade
        # rules += 1
        if slope_sideways_long:
            # long_checklist += 1

            if '1.10.2' not in model.model_stats.keys():
                model.model_stats['1.10.2']={}

            model.model_stats['1.10.2'][ts] = {}
            model.model_stats['1.10.2'][ts]['long'] = 1

        # 1.11 Above blue: close of entry bar must be above sma8
        # rules += 1
        if sma_8[-1] < entry_bar['close']:
            # long_checklist += 1

            if '1.11' not in model.model_stats.keys():
                model.model_stats['1.11']={}

            model.model_stats['1.11'][ts] = {}
            model.model_stats['1.11'][ts]['long'] = 1
        
        # 1.12 Curvature of blue:
        # strong and smooth or
        # smooth and increasing or
        # flat and increasing
        # rules += 1
        if (strong_long and smooth) or (smooth and increasing) or (flat and increasing):
            # long_checklist += 1

            if '1.12' not in model.model_stats.keys():
                model.model_stats['1.12']={}

            model.model_stats['1.12'][ts] = {}
            model.model_stats['1.12'][ts]['long'] = 1

        # #################### END 1 TREND ####################

        # #################### 2 TIME ####################

        # all on 1min candles

        # 2.1 Significant sideways (1-2 times of entry bar): sideways must be at most small_bars_50 times entry bar (Non-negotiable times 1 of entry bar)
        # 2.2 Small bars in sideways: All sideway candles must be smaller equal 50% of entry bar (Non-negotiable)
        core_rules += 1
        if (body_sideway_count_1 >= small_bars_50 * high_low_1).sum() == 0:
            core_checklist += 1

        # 2.3 Small bars in sideways: The two candles before the entry bar must be smaller equal 25% of the entry bar (Non-negotiable)
        core_rules += 1
        if (body_3_1 >= small_bars_25 * high_low_1).sum() == 0:
            core_checklist += 1

        # 2.5 No drift: little to no drift prior to entry bar
        # rules += 1
        # if model.market_data.history[topic].iloc[-2][
        #         'close'] - model.market_data.history[topic].iloc[
        #             -drift_length - 1]['open'] <= drift_height * open_close_1:
        #     long_checklist += 1            

        # 2.6 Minimum number of sideways candles are required (this ensures that the entry bar is large enough)
        # core_rules += 1
        # if sideways_count >= minimum_sideways:
        #     core_checklist += 1

        # #################### END 2 TIME ####################

        # #################### 3 BAR ####################

        # all on 1min candles

        # 3.1 Entry bar in opposite 1/5ths: the wigs of the entry bar must be smaller equal 20% of the candle (High to low) (Non-negotiable)
        core_rules += 1
        if (opposite_fifths * high_low_1 >=
                low_open_1) and (opposite_fifths * high_low_1 >= high_close_1):
            core_long_checklist += 1

        # 3.3 Is entry bar a surprise? (Picture) (Non-negotiable):
        # 3.3.1 Amplitude of sideways must be smaller than body of entry bar
        # core_rules += 1
        # if sideways_count_max - sideways_count_min <= surprise_factor * open_close_1:
        #     core_checklist += 1
        
        # 3.3.2 body of entry bar must be a significant part of the trading screen
        # core_rules += 1
        # if open_close_1 >= surprise_factor_2 * high_low_candle_window:
        #     core_checklist += 1
        
        # 3.4 Blue entry bar: close of entry bar must be greater than open of entry bar (Non-negotiable)
        # core_rules += 1
        # if entry_bar['close'] > entry_bar['open']:
        #     core_long_checklist += 1

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
                    model.model_stats['1.1']={}

                if ts not in model.model_stats['1.1'].keys():
                    model.model_stats['1.1'][ts] = {}

                model.model_stats['1.1'][ts]['short'] = 1
        
        # 1.2 Lower highs with retracement: last high must be lower than previous high - retracement_factor * difference between las low and second last high
        # check if there are at least two highs and one low for stability of calculations
        if len(highs_trend) > 1 and not lows_trend.empty:

            # lower highs_trend, but retracement of last high of maximum retracement_factor x difference between last low and second last high
            if highs_trend.iloc[-1] < highs_trend.iloc[-2] - abs(lows_trend.iloc[-1]-highs_trend.iloc[-2])*(1-retracement_factor):
                # short_checklist+=1

                if '1.2' not in model.model_stats.keys():
                    model.model_stats['1.2']={}

                if ts not in model.model_stats['1.2'].keys():
                    model.model_stats['1.2'][ts] = {}

                model.model_stats['1.2'][ts]['short'] = 1

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
                # short_checklist += 1

                if '1.3' not in model.model_stats.keys():
                    model.model_stats['1.3']={}

                if ts not in model.model_stats['1.3'].keys():
                    model.model_stats['1.3'][ts] = {}

                model.model_stats['1.3'][ts]['short'] = 1
        
        # 1.4 Breaking of a significant low (50% of entry bar): 50% of the entry bar must be below last low
        # check if there is at least one low for stability of calculations
        if not lows_trend.empty:

            # at least the "high_factor" fraction of the body of the entry bar has to be below the preceding low
            if lows_trend.iloc[-1] - high_factor * open_close_1 > entry_bar['close']:
                # short_checklist += 1

                if '1.4' not in model.model_stats.keys():
                    model.model_stats['1.4']={}

                if ts not in model.model_stats['1.4'].keys():
                    model.model_stats['1.4'][ts] = {}

                model.model_stats['1.4'][ts]['short'] = 1
        
        # 1.5 breaking of a support line: 
        # check if support exists for stability of calculation
        if support:
            if entry_bar['close']<support:
                # short_checklist += 1

                if '1.5' not in model.model_stats.keys():
                    model.model_stats['1.5']={}

                if ts not in model.model_stats['1.5'].keys():
                    model.model_stats['1.5'][ts] = {}

                model.model_stats['1.5'][ts]['short'] = 1
        
        # 1.6 lower low: last low must be lower thab second last low
        # check if there are at least two lows for stability of calculations
        if len(lows_trend)>1:
            if lows_trend.iloc[-1] < lows_trend.iloc[-2]:
                # short_checklist += 1

                if '1.6' not in model.model_stats.keys():
                    model.model_stats['1.6']={}

                if ts not in model.model_stats['1.6'].keys():
                    model.model_stats['1.6'][ts] = {}

                model.model_stats['1.6'][ts]['short'] = 1
        
        # 1.7 Time phase after Price phase: Only enter after a time phase, predecessed by a price phase
        # check if there are at least two slopes for stability of calculations
        if len(high_low_slopes_trend)>1:
            if high_low_slopes_trend[-1]>0 and high_low_slopes_trend[-2]<0:
                # short_checklist += 1

                if '1.7' not in model.model_stats.keys():
                    model.model_stats['1.7']={}

                if ts not in model.model_stats['1.7'].keys():
                    model.model_stats['1.7'][ts] = {}

                model.model_stats['1.7'][ts]['short'] = 1
        
        # 1.9 Above purple: close of entry bar must be above 24 sma
        if sma_24[-1] > entry_bar['close']:
            core_short_checklist += 1

            if '1.9' not in model.model_stats.keys():
                    model.model_stats['1.9']={}

            if ts not in model.model_stats['1.9'].keys():
                model.model_stats['1.9'][ts] = {}

            model.model_stats['1.9'][ts]['short'] = 1
        
        # 1.10.1 Curvature purple: slope of regression flat or in direction of trade
        if slope_purple < slope_purple_param:
            # short_checklist += 1

            if '1.10.1' not in model.model_stats.keys():
                model.model_stats['1.10.1']={}

            if ts not in model.model_stats['1.10.1'].keys():
                model.model_stats['1.10.1'][ts] = {}

            model.model_stats['1.10.1'][ts]['short'] = 1

        # 1.10.2 Curvature purple: slope of regression flat or in direction of trade
        if slope_sideways_short:
            # short_checklist += 1

            if '1.10.2' not in model.model_stats.keys():
                model.model_stats['1.10.2']={}

            if ts not in model.model_stats['1.10.2'].keys():
                model.model_stats['1.10.2'][ts] = {}

            model.model_stats['1.10.2'][ts]['short'] = 1
        
        # 1.11 Above blue: close of entry bar must be below sma8
        if sma_8[-1] > entry_bar['close']:
            # short_checklist += 1

            if '1.11' not in model.model_stats.keys():
                model.model_stats['1.11']={}

            if ts not in model.model_stats['1.11'].keys():
                model.model_stats['1.11'][ts] = {}

            model.model_stats['1.11'][ts]['short'] = 1
        
        # 1.12 Curvature of blue:
        # strong and smooth or
        # smooth and decreasing or
        # flat and decreasing
        if (strong_short and smooth) or (smooth and decreasing) or (flat and decreasing):
            # short_checklist += 1

            if '1.12' not in model.model_stats.keys():
                model.model_stats['1.12']={}

            if ts not in model.model_stats['1.12'].keys():
                model.model_stats['1.12'][ts] = {}

            model.model_stats['1.12'][ts]['short'] = 1

        # #################### END 1 TREND ####################

        # #################### 2 TIME ####################

        # all on 1min candles

        # 2.5 No drift: little to no drift prior to entry bar        
        # if model.market_data.history[topic].iloc[
        #         -drift_length - 1]['open'] - model.market_data.history[
        #             topic].iloc[-2]['close'] <= drift_height * open_close_1:
        #    short_checklist += 1

        # #################### END 2 TIME ####################

        # #################### 3 BAR ####################

        # all on 1min candles

        # 3.1 Entry bar in opposite 1/5ths: the wigs of the entry bar must be smaller equal 20% of the candle (High to low) (Non-negotiable)
        if (opposite_fifths * high_low_1 >=
                high_open_1) and (opposite_fifths * high_low_1 >= low_close_1):
            core_short_checklist += 1

        # 3.4 Red entry bar: close of entry bar must be smaller than open of entry bar
        # if entry_bar['close'] < entry_bar['open']:
        #     core_short_checklist += 1

        #################### END BAR ####################

        ######################################## END CHECKLIST SHORT ########################################

        # calculate score across all rules



        #################### REMOVE IF NON CORE-RULES ARE APPLIED ###########################################
        rules = 1
        #####################################################################################################



        confidence_score_long = (long_checklist + checklist + 1) / rules
        confidence_score_short = (short_checklist + checklist + 1) / rules

        confidence_score_core_long = (core_long_checklist + core_checklist) / core_rules
        confidence_score_core_short = (core_short_checklist + core_checklist) / core_rules

        # determine trading quantity
        # buy_qty = 100 / entry_bar['close']
        # buy_qty = np.round(buy_qty, tick_size)

        # buy with all available balance
        buy_qty = 0.95*model.account.wallet[ticker[-len(BASE_CUR):]]['available_balance']/ entry_bar['close']

        # if all rules apply for the long strategy and there is no current open position, place buy order
        if (confidence_score_core_long
                == 1.0) and (confidence_score_long >= 1) and (model.account.positions[ticker]['size'] == 0.0):

            # set leverage to 20 or lower so that if stop loss is hit, it occurs a maximum loss of 40%
            leverage_ratio = 1-(stop_loss_long/entry_bar['close'])
            leverage = int(np.min([20, np.ceil(0.4/leverage_ratio)]))

            # leverage=1
            # for real trading, set leverage of position to leverage, for backtesting just scale position size
            # buy_qty=leverage*buy_qty
            # buy_qty = np.round(buy_qty, tick_size)
            buy_qty = 50

            try:
                model.account.session.set_leverage(symbol=ticker,
                                        buy_leverage=str(leverage),
                                        sell_leverage = str(leverage))
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

        # if all rules apply for the short strategy and there is no current open position, place sell order
        if (confidence_score_core_short
                == 1.0) and (confidence_score_short >= 1) and (model.account.positions[ticker]['size'] == 0.0):
            
            # set leverage to 20 or lower so that if stop loss is hit, it occurs a maximum loss of 40%
            leverage_ratio = (stop_loss_short/entry_bar['close'])-1
            leverage = int(np.min([20, np.ceil(0.4/leverage_ratio)]))
            
            # leverage = 1
            # for real trading, set leverage of position to leverage, for backtesting just scale position size
            # buy_qty=leverage*buy_qty
            # buy_qty = np.round(buy_qty, tick_size)
            buy_qty = 50

            try:
                model.account.session.set_leverage(symbol=ticker,
                                        buy_leverage = str(leverage),
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
            model.model_storage['exit_short_lower_highs']=[]