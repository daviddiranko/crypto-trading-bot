import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)

from typing import Dict, Any
from src.TradingModel import TradingModel
from src.helper_functions.statistics import sma, get_alternate_highs_lows
import numpy as np
from sklearn.linear_model import LinearRegression
from src.endpoints.bybit_functions import *


def checklist_model(model: TradingModel):
    '''
    checklist-based trend following model
    '''

    # declare ticker
    # ticker = 'BTCUSDT'
    ticker = model.model_args['ticker']

    # declare topics
    topic = 'candle.1.{}'.format(ticker)
    long_term_topic = 'candle.5.{}'.format(ticker)
    trend_topic = 'candle.15.{}'.format(ticker)
    short_term_topic = 'candle.1.{}'.format(ticker)

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

    # High and low definition: set number of consecutive candles that must be smaller/larger than mhigh/low
    n_candles = 15
    # n_candles = model.model_args['n_candles']

    # Sideways: multiple of length of entry bar to incorporate into the sideways candles
    sideways_factor = 2
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
    candle_window = 75
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
    high_factor = 0.0
    # high_factor = model.model_args['param']

    # High and low definition: set factor that the last low must be above the previous low to be a higher low
    retracement_factor = 0.0
    # retracement_factor = model.model_args['param']

    ######################################## END PARAMETERS ########################################

    ######################################## DEFINITION VARIABLES ########################################

    # last relevant candles for strategy
    entry_bar = model.market_data.history[topic].iloc[-1]
    last_trend_candle = model.market_data.history[trend_topic].iloc[-1]
    last_short_term_candle = model.market_data.history[short_term_topic].iloc[-1]
    last_long_term_candle = model.market_data.history[long_term_topic].iloc[-1]

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
        min_int=n_candles)
    
    trend_series = model.market_data.history[trend_topic]['close'].copy()

    # if last timestamp of topic and trend topic are not identical, append last timestamp of topic to trend topic
    if topic_trend_topic_delta>pd.Timedelta(minutes=1):
        trend_series[entry_bar.name]=entry_bar['close']

    # calculate alternating highs and lows of trend line
    highs_trend, lows_trend = get_alternate_highs_lows(
        candles=trend_series,
        min_int=n_candles)

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
    
    # determine number of decimals to round the trading prices
    decimals = 6-len(str(int(entry_bar['low'])))

    # determine risk limit for trading according to maximum usdt trading value with leverage 20 on bybit
    if ticker=='BTCUSDT':
        risk_limit = 500000
    elif ticker=='ETHUSDT':
        risk_limit = 300000
    else:
        risk_limit = 30000

    # determine maximum trade quantity according to bybit
    if ticker=='BTCUSDT':
        max_qty = 100
    elif ticker=='ETHUSDT':
        max_qty = 1500
    else:
        max_qty = 100000

    # set stop loss as low price of entry candle
    stop_loss_long = np.round(entry_bar['low'], decimals)
    stop_loss_short = np.round(entry_bar['high'], decimals)

    take_profit_long = None
    take_profit_short = None

    # exit strategy for long side
    if (model.account.positions[ticker]['size'] >
            0.0) and model.account.positions[ticker]['side'] == 'Buy':
        
        new_stop_loss_long = np.round(
                max(model.model_storage['entry_close_1_long'],
                    model.model_storage['entry_open_1_long']) -
                0.5 * model.model_storage['entry_open_close_1_long'], decimals)

        new_stop_loss_long_2 = np.round(
                max(model.model_storage['entry_close_1_long'],
                    model.model_storage['entry_open_1_long']) -
                0.25 * model.model_storage['entry_open_close_1_long'], decimals)

        # if the last close price is below the sma_8, close position
        if (entry_bar['close'] < sma_8[-1]):
            model.account.place_order(
                symbol=ticker,
                side='Sell',
                qty=model.account.positions[ticker]['size'] + 0.1,
                order_type='Market',
                stop_loss=None,
                take_profit=None,
                reduce_only=True)
        
        # if the last closing price is above the trade price + the trading fee, adjust stop loss to the trade price + the trading fee
        elif (last_short_term_candle['close'] > np.round(last_trade['price'] * 1.0012, decimals)) and (np.round(last_trade['price'] * 1.0012, decimals) > model.account.positions[ticker]['stop_loss']):
            model.account.set_stop_loss(symbol=ticker,
                                        side='Buy',
                                        stop_loss=np.round(
                                            last_trade['price'] * 1.0012, decimals))
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
                    qty=model.account.positions[ticker]['size'] + 0.1,
                    order_type='Market',
                    stop_loss=None,
                    take_profit=None,
                    reduce_only=True)

        # exit function since position is still open
        return None

    # exit strategy for the short side
    if (model.account.positions[ticker]['size'] >
            0.0) and model.account.positions[ticker]['side'] == 'Sell':

        new_stop_loss_short = np.round(
                min(model.model_storage['entry_close_1_short'],
                    model.model_storage['entry_open_1_short']) +
                0.5 * model.model_storage['entry_open_close_1_short'], decimals)
        
        new_stop_loss_short_2 = np.round(
                min(model.model_storage['entry_close_1_short'],
                    model.model_storage['entry_open_1_short']) +
                0.25 * model.model_storage['entry_open_close_1_short'], decimals)

        # if there are three highs in a row or the last price is above the sma_8, close position
        if (entry_bar['close'] > sma_8[-1]):
            model.account.place_order(
                symbol=ticker,
                side='Buy',
                qty=model.account.positions[ticker]['size'] + 0.1,
                order_type='Market',
                stop_loss=None,
                take_profit=None,
                reduce_only=True)
        
        # if the last closing price is below the trade price - the trading fee, adjust the stop loss to the trade price - the trading fee
        elif (last_short_term_candle['close'] < np.round(last_trade['price'] * 0.9988, decimals)) and (np.round(
                                            last_trade['price'] * 0.9988, decimals) < model.account.positions[ticker]['stop_loss']):
            model.account.set_stop_loss(symbol=ticker,
                                        side='Sell',
                                        stop_loss=np.round(
                                            last_trade['price'] * 0.9988, decimals))
            
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
            
        # if the last closing price is below the trade price, adjust the stop loss to the trade price
        elif (last_short_term_candle['close'] < last_trade['price']) and (last_trade['price'] < model.account.positions[ticker]['stop_loss']):
            model.account.set_stop_loss(symbol=ticker,
                                        side='Sell',
                                        stop_loss=last_trade['price'])
            model.model_storage['exit_short_lower_highs'].append(last_short_term_candle['open'])
        
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
                    qty=model.account.positions[ticker]['size'] + 0.1,
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
        
        # update last received candle to current candle
        model.model_storage['entry_bar_time'] = model.market_data.history[
            topic].iloc[-1].name
        
        ######################################## CHECKLIST LONG ########################################

        #################### 1 TREND ####################

        # 1.1 Higher lows: last low must be higher than previous low
        # check if there are at least two highs and two lows for stability of calculations
        rules+=1
        if len(lows_trend) > 1 and not highs_trend.empty:

            # higher lows, but retracement of last low of maximum retracement_factor x difference between last high and second last low
            if lows_trend.iloc[-1] > lows_trend.iloc[-2] + abs(highs_trend.iloc[-1]-lows_trend.iloc[-2])*retracement_factor:
                long_checklist+=1

        # 1.2 Above purple: close of entry bar must be above 24 sma (Non-negotiable)
        core_rules += 1
        if sma_24[-1] < entry_bar['close']:
            core_long_checklist += 1

        # 1.3 Purple strong, smooth, flat or increasing:linear regression of trend line since second last low has positive slope
        rules+=1
        if slope_sma_long>0:
            long_checklist += 1

        # 1.4 Above blue: close of entry bar must be above sma8
        core_rules += 1
        if sma_8[-1] < entry_bar['close']:
            core_long_checklist += 1
        
        # 1.5 Blue strong, smooth, flat or increasing (Non-negotiable)
        core_rules += 1
        if sma_8.iloc[-1]-sma_8.iloc[-trend_candles]>=0:
            core_long_checklist+=1

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
        rules += 1
        if model.market_data.history[topic].iloc[-2][
                'close'] - model.market_data.history[topic].iloc[
                    -drift_length - 1]['open'] <= drift_height * open_close_1:
            long_checklist += 1            

        # 2.6 Minimum number of sideways candles are required (this ensures that the entry bar is large enough)
        core_rules += 1
        if sideways_count >= minimum_sideways:
            core_checklist += 1

        # #################### END 2 TIME ####################

        # #################### 3 BAR ####################

        # all on 1min candles

        # 3.1 Entry bar in opposite 1/5ths: the wigs of the entry bar must be smaller equal 20% of the candle (High to low) (Non-negotiable)
        core_rules += 1
        if (opposite_fifths * high_low_1 >=
                low_open_1) and (opposite_fifths * high_low_1 >= high_close_1):
            core_long_checklist += 1
        
        # 3.2 Breaking of a significant high (50% of entry bar): 50% of the entry bar must be above last high
        # check if there are at least two highs and two lows for stability of calculations
        rules += 1
        if not highs_trend.empty:

            # at least the "high_factor" fraction of the body of the entry bar has to be above the preceding high
            if highs_trend.iloc[-1] + high_factor * open_close_1 < entry_bar['close']:
                long_checklist += 1

        # 3.3 Is entry bar a surprise? (Picture) (Non-negotiable):
        # 3.3.1 Amplitude of sideways must be smaller than body of entry bar
        core_rules += 1
        if sideways_count_max - sideways_count_min <= surprise_factor * open_close_1:
            core_checklist += 1
        
        # 3.3.2 body of entry bar must be a significant part of the trading screen
        core_rules += 1
        if open_close_1 >= surprise_factor_2 * high_low_candle_window:
            core_checklist += 1
        
        # 3.4 Blue entry bar: close of entry bar must be greater than open of entry bar (Non-negotiable)
        core_rules += 1
        if entry_bar['close'] > entry_bar['open']:
            core_long_checklist += 1

        #################### END BAR ####################

        ######################################## END CHECKLIST LONG ########################################

        ######################################## CHECKLIST SHORT ########################################

        #################### 1 TREND ####################

        # 1.1 Lower highs: last high must be lower than previous high
        # check if there are at least two highs and two lows for stability of calculations
        if len(highs_trend) > 1 and not lows_trend.empty:

            # lower highs_trend, but retracement of last high of maximum retracement_factor x difference between last low and second last high
            if highs_trend.iloc[-1] < highs_trend.iloc[-2] - abs(lows_trend.iloc[-1]-highs_trend.iloc[-2])*retracement_factor:
                short_checklist+=1

        # 1.2 Above purple: close of entry bar must be above 24 sma
        if sma_24[-1] > entry_bar['close']:
            core_short_checklist += 1

        # 1.3 Purple strong, smooth, flat or decreasig : linear regression of trend line since second last high has negative slope
        if slope_sma_short<0:
            short_checklist += 1

        # 1.4 Above blue: close of entry bar must be below sma8
        if sma_8[-1] > entry_bar['close']:
            core_short_checklist += 1
        
        # 1.5 Blue strong, smooth, flat or increasing
        if sma_8.iloc[-1]-sma_8.iloc[-trend_candles]<=0:
            core_short_checklist+=1

        # #################### END 1 TREND ####################

        # #################### 2 TIME ####################

        # all on 1min candles

        # 2.5 No drift: little to no drift prior to entry bar        
        if model.market_data.history[topic].iloc[
                -drift_length - 1]['open'] - model.market_data.history[
                    topic].iloc[-2]['close'] <= drift_height * open_close_1:
           short_checklist += 1

        # #################### END 2 TIME ####################

        # #################### 3 BAR ####################

        # all on 1min candles

        # 3.1 Entry bar in opposite 1/5ths: the wigs of the entry bar must be smaller equal 20% of the candle (High to low) (Non-negotiable)
        if (opposite_fifths * high_low_1 >=
                high_open_1) and (opposite_fifths * high_low_1 >= low_close_1):
            core_short_checklist += 1
        
        # 3.2 Breaking of a significant low (50% of entry bar): 50% of the entry bar must be below last low
        # check if there are at least two highs and two lows for stability of calculations
        if not lows_trend.empty:

            # at least the "high_factor" fraction of the body of the entry bar has to be below the preceding low
            if lows_trend.iloc[-1] - high_factor * open_close_1 > entry_bar['close']:
                short_checklist += 1

        # 3.4 Red entry bar: close of entry bar must be smaller than open of entry bar
        if entry_bar['close'] < entry_bar['open']:
            core_short_checklist += 1

        #################### END BAR ####################

        ######################################## END CHECKLIST SHORT ########################################

        # calculate score across all rules
        confidence_score_long = (long_checklist + checklist + 1) / rules
        confidence_score_short = (short_checklist + checklist + 1) / rules

        confidence_score_core_long = (core_long_checklist + core_checklist) / core_rules
        confidence_score_core_short = (core_short_checklist + core_checklist) / core_rules

        # determine trading quantity
        # buy_qty = 100 / entry_bar['close']
        # buy_qty = np.round(buy_qty, 3)

        # buy with all available balance
        buy_qty = min(0.95*model.account.wallet[ticker[-4:]]['available_balance'], risk_limit)/ entry_bar['close']
        buy_qty = np.round(buy_qty, 5-decimals)

        # if all rules apply for the long strategy and there is no current open position, place buy order
        if (confidence_score_core_long
                == 1.0) and (confidence_score_long >= 1) and (model.account.positions[ticker]['size'] == 0.0):

            # set leverage to 20 or lower so that if stop loss is hit, it occurs a maximum loss of 40%
            leverage_ratio = 1-(stop_loss_long/entry_bar['close'])
            leverage = int(np.min([20, np.ceil(0.4/leverage_ratio)]))

            # leverage=1
            # for real trading, set leverage of position to leverage, for backtesting just scale position size
            buy_qty=min(leverage*buy_qty,max_qty)

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
            buy_qty=min(leverage*buy_qty,max_qty)

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