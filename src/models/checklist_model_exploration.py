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
    ticker = 'BTCUSDT'
    # ticker = model.model_args['ticker']

    # declare topic
    topic = 'candle.5.{}'.format(ticker)
    trend_topic = 'candle.15.{}'.format(ticker)

    # initialize checklist counter and total rules counter
    long_checklist = 0
    short_checklist = 0
    checklist = 0
    total_rules = 0

    ######################################## PARAMETERS ########################################

    # High and low definition: set number of consecutive candles that must be smaller/larger than mhigh/low
    n_candles = 15
    # n_candles = model.model_args['n_candles']

    # High and low definition: last high must be 50% higher than previous high
    # To be a breaking high, 50% of the entry candle body has to above the preceding high
    high_factor = 0.5
    # high_factor = model.model_args['high_factor']

    # High and low definition: set factor that the last low must be above the previous low to be a higher low
    retracement_factor = 0.5
    # retracement_factor = model.model_args['retracement_factor']

    # Drift: set maximum slope of sideways candles to qualify as trend-free
    max_abs_slope = 0.005
    # max_abs_slope = model.model_args['max_abs_slope']

    # Blue increasing: determine number of candles to require a trend in before entering (increase in sma8)
    trend_candles = 3
    # trend_candles = model.model_args['trend_candles']

    # Sideways: multiple of length of entry bar to incorporate into the sideways candles
    sideways_factor = 2
    # sideways_factor = model.model_args['sideways_factor']

    # Sideways: all candles in sideways must be smaller eqal factor times entry bar
    small_bars_50 = 0.5
    # small_bars_50 = model.model_args['small_bars_50']

    # Sideways: last 2 candles before entry bar must be smaller equal parameter times entry bar
    # small_bars_25 = 0.25
    small_bars_25 = model.model_args['small_bars_25']

    # Opposite 1/5ths: the wigs of the entry bar must be smaller equal 20% of the candle (High to low)
    opposite_fifths = 0.2
    # opposite_fifths = model.model_args['opposite_fifths']

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

    # open of first drift candle to close of candle prior to entry bar must be smaller than drift_height times body of entry bar
    drift_height = 0.2
    
    # multiple of body of entry bar that amplitude (i.e. maximum open or close - minimum of open or close) of sideways candles can have
    surprise_factor = 1.3

    # percentage of trading screen height (i.e. maximum high to minimum low within candle_window) the entry bar has to fill to be a surprise.
    # 0.2 is currently best, 0.15 and 0.1 is too small
    surprise_factor_2 = 0.2

    ######################################## END PARAMETERS ########################################

    ######################################## DEFINITION VARIABLES ########################################

    # last relevant candle for strategy
    last_price = model.market_data.history[topic].iloc[-1]
    last_trend_price = model.market_data.history[trend_topic].iloc[-1]

    # check timedelta between trend topic and topic to ensure that is not larger than 10 minutes
    # if larger, then new topic candle was received before new trend topic and one must wait until new trend topic arrives
    topic_trend_topic_delta = last_price.name - last_trend_price.name

    # only trade if new data from topic is received
    # and both topic and trend topic data have arrived if both are expected
    if (last_price.name > model.model_storage['last_price_time']) and topic_trend_topic_delta<pd.Timedelta(minutes=15):

        # update last received candle to current candle
        model.model_storage['last_price_time'] = model.market_data.history[
            topic].iloc[-1].name

        # simple moving averages
        sma_24 = sma(model.market_data.history[topic]['close'], window=24)
        sma_8 = sma(model.market_data.history[topic]['close'], window=8)

        # calculate various spreads of entry bar
        high_low_1 = abs(last_price['high'] - last_price['low'])
        low_open_1 = abs(last_price['open'] - last_price['low'])
        high_open_1 = abs(last_price['open'] - last_price['high'])
        high_close_1 = abs(last_price['high'] - last_price['close'])
        open_close_1 = abs(last_price['close'] - last_price['open'])
        low_close_1 = abs(last_price['close'] - last_price['low'])

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
                    (open_close_1 / high_low_candle_window) * chart_height *
                    sideways_factor * (candle_window / chart_width))), 2)

        # calculate the body of the sideways candles
        body_sideway_count_1 = (
            model.market_data.history[topic].iloc[-sideways_count:-1]['close'] -
            model.market_data.history[topic].iloc[-sideways_count:-1]['open']
        ).abs()

        # calculate the mean of open and close of the sideways candles
        sideways_mean = np.mean([
            model.market_data.history[topic].iloc[-sideways_count:-1]['close'],
            model.market_data.history[topic].iloc[-sideways_count:-1]['open']
        ],
                                axis=0)

        trend_series = model.market_data.history[trend_topic]['close'].copy()

        # if last timestamp of topic and trend topic are not identical, append last timestamp of topic to trend topic
        if topic_trend_topic_delta>pd.Timedelta(minutes=1):
            trend_series[last_price.name]=last_price['close']

        # calculate alternating highs and lows of trend line
        highs_trend, lows_trend = get_alternate_highs_lows(
            candles=trend_series,
            min_int=n_candles)
        
        # calculate alternating highs and lows of trading line
        highs, lows = get_alternate_highs_lows(
            candles=model.market_data.history[topic]['close'],
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
        
        # calculate drift reference points
        drift_max = max(
            model.market_data.history[topic].iloc[-sideways_count:-drift_length]
            ['open'].max(),
            model.market_data.history[topic].iloc[-sideways_count:-drift_length]
            ['close'].max())
        drift_min = min(
            model.market_data.history[topic].iloc[-sideways_count:-drift_length]
            ['open'].min(),
            model.market_data.history[topic].iloc[-sideways_count:-drift_length]
            ['close'].min())

        # scale x-axis between 0 and number of candles
        X = np.array(range(sideways_count - 1)).reshape(-1, 1)

        # scale means of open and close prices by high-low spread of last 75 candles to normalize the slope of the candles
        Y = sideways_mean / high_low_candle_window

        # calculate linear regression within sideways candles to identify a potential trend
        sk_lr = LinearRegression()
        sk_results = sk_lr.fit(X, Y)

        # extract slope of regression line
        slope = sk_results.coef_[0]

        # linear regression of sma_24 since second last low of trading line for long side
        # scale x-axis between 0 and number of candles
        trend_series_long = sma_24.loc[lows.index[-2]:]
        X_sma_long = np.array(range(len(trend_series_long))).reshape(-1, 1)

        # scale sma_24 by high-low spread of last 75 candles to normalize the slope of the candles
        Y_sma_long = trend_series_long / high_low_candle_window

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
        Y_sma_short = trend_series_short / high_low_candle_window

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
        stop_loss_long = np.ceil(last_price['low'])
        stop_loss_short = np.floor(last_price['high'])

        # set take profit to last price plus 1/4 times the body of the entry candle
        # take_profit_long = np.ceil(last_price['close'] + 0.25 * high_low_1)
        # take_profit_short = np.floor(last_price['close'] - 0.25 * high_low_1)

        take_profit_long = None
        take_profit_short = None

        # last 3 candles
        last_3_candles = model.market_data.history[topic].iloc[-3:]

        # exit strategy for long side
        if (model.account.positions[ticker]['size'] >
                0.0) and model.account.positions[ticker]['side'] == 'Buy':
            
            new_stop_loss_long = np.ceil(
                    max(model.model_storage['entry_close_1_long'],
                        model.model_storage['entry_open_1_long']) -
                    0.5 * model.model_storage['entry_open_close_1_long'])

            new_stop_loss_long_2 = np.ceil(
                    max(model.model_storage['entry_close_1_long'],
                        model.model_storage['entry_open_1_long']) -
                    0.25 * model.model_storage['entry_open_close_1_long'])

            # if there are three lows in a row or the last close price is below the sma_8, close position
            if ((last_3_candles['close'] > last_3_candles['open']).sum()
                    == 0) or (last_price['close'] < sma_8[-1]):
                model.account.place_order(
                    symbol=ticker,
                    side='Sell',
                    qty=model.account.positions[ticker]['size'] + 0.1,
                    order_type='Market',
                    stop_loss=None,
                    take_profit=None,
                    reduce_only=True)
            
            # otherwise if the stop loss is below the traded price, increase stop loss to the traded price minus 0.5 times the entry body
            elif model.account.positions[ticker]['stop_loss'] < last_trade[
                    'price'] and (new_stop_loss_long < last_price['close']) and (new_stop_loss_long > model.account.positions[ticker]['stop_loss']):

                model.account.set_stop_loss(symbol=ticker,
                                                side='Buy',
                                                stop_loss=new_stop_loss_long)
            
            # otherwise if the stop loss is below the traded price, increase stop loss to the traded price minus 0.25 times the entry body
            elif model.account.positions[ticker]['stop_loss'] < last_trade[
                    'price'] and (new_stop_loss_long_2 < last_price['close']) and (new_stop_loss_long_2 > model.account.positions[ticker]['stop_loss']):

                model.account.set_stop_loss(symbol=ticker,
                                                side='Buy',
                                                stop_loss=new_stop_loss_long_2)
            
            # if the last closing price is above the trade price + the trading fee, adjust stop loss to the trade price + the trading fee
            elif (last_price['close'] > np.ceil(last_trade['price'] * 1.0012)) and (np.ceil(last_trade['price'] * 1.0012) > model.account.positions[ticker]['stop_loss']):
                model.account.set_stop_loss(symbol=ticker,
                                            side='Buy',
                                            stop_loss=np.ceil(
                                                last_trade['price'] * 1.0012))

            # if the last closing price is above the trade price, adjust stop loss to the trade price
            elif (last_price['close'] > last_trade['price']) and (last_trade['price']> model.account.positions[ticker]['stop_loss']):
                model.account.set_stop_loss(symbol=ticker,
                                            side='Buy',
                                            stop_loss=last_trade['price'])

            # exit function since position is still open
            return None

        # exit strategy for the short side
        if (model.account.positions[ticker]['size'] >
                0.0) and model.account.positions[ticker]['side'] == 'Sell':
            
            new_stop_loss_short = np.floor(
                    min(model.model_storage['entry_close_1_short'],
                        model.model_storage['entry_open_1_short']) +
                    0.5 * model.model_storage['entry_open_close_1_short'])
            
            new_stop_loss_short_2 = np.floor(
                    min(model.model_storage['entry_close_1_short'],
                        model.model_storage['entry_open_1_short']) +
                    0.25 * model.model_storage['entry_open_close_1_short'])

            # if there are three highs in a row or the last price is above the sma_8, close position
            if ((last_3_candles['close'] < last_3_candles['open']).sum()
                    == 0) or (last_price['close'] > sma_8[-1]):
                model.account.place_order(
                    symbol=ticker,
                    side='Buy',
                    qty=model.account.positions[ticker]['size'] + 0.1,
                    order_type='Market',
                    stop_loss=None,
                    take_profit=None,
                    reduce_only=True)
            
            # otherwise if the stop loss is above the traded price, decrease stop loss to the traded price plus 0.5 times the entry body
            elif model.account.positions[ticker]['stop_loss'] > last_trade[
                    'price'] and (new_stop_loss_short > last_price['close']) and (new_stop_loss_short < model.account.positions[ticker]['stop_loss']):

                model.account.set_stop_loss(symbol=ticker,
                                                side='Sell',
                                                stop_loss=new_stop_loss_short)
            
            # otherwise if the stop loss is above the traded price, decrease stop loss to the traded price plus 0.75 times the entry body
            elif model.account.positions[ticker]['stop_loss'] > last_trade[
                    'price'] and (new_stop_loss_short_2 > last_price['close']) and (new_stop_loss_short_2 < model.account.positions[ticker]['stop_loss']):

                model.account.set_stop_loss(symbol=ticker,
                                                side='Sell',
                                                stop_loss=new_stop_loss_short_2)

            # if the last closing price is below the trade price - the trading fee, adjust the stop loss to the trade price - the trading fee
            elif (last_price['close'] < np.floor(last_trade['price'] * 0.9988)) and (np.floor(
                                                last_trade['price'] * 0.9988) < model.account.positions[ticker]['stop_loss']):
                model.account.set_stop_loss(symbol=ticker,
                                            side='Sell',
                                            stop_loss=np.floor(
                                                last_trade['price'] * 0.9988))

            # if the last closing price is below the trade price, adjust the stop loss to the trade price
            elif (last_price['close'] < last_trade['price']) and (last_trade['price'] < model.account.positions[ticker]['stop_loss']):
                model.account.set_stop_loss(symbol=ticker,
                                            side='Sell',
                                            stop_loss=last_trade['price'])

            # exit function since position is still open
            return None

        ######################################## END EXIT STRATEGY ########################################

        ######################################## CHECKLIST LONG ########################################

        # Next steps:
        # @ Dave produce backtests for 2.5 1.1, 3.2, 1.6 (removed 1.5, 1.3 to obtain more trades, these rules seem very strict)
        # @Vroni and Dave: Set basic rules (1.2, 1.4, 2.1, 2.2, 2.3, 2.6, 3.1, 3.4) and tune parameters of those rules (v3)
        # @Dave added 3.3.1 to above rules (v4)
        # @Dave increased maximum amplitude to 1.2 * body of entry bar (v5)
        # @Dave increased maximum amplitude to 1.3 * body of entry bar (v6)
        # @Dave activate "old" 2.5 to not allow significant drift in last 5 candles (v7)
        # @Dave restricted drift_height from 0.25 to 0.2 (v8)
        # (v8) trades 13 of the promising 41 trades -> pretty good
        # restriction of amplitude of sideways to body of entry bar "kills" some promising trades
        # -> increasing "surprise_factor" to 1.5 decreases performance significantly, 1.3 seems to be optimal
        # fast increase of stop loss to entry price stops out some promising trades
        # @Dave increase stop loss to maximal 0.5 times entry bar (v9)
        # @Dave increase stop loss first to 0.5 times entry bar and then into profit (v10) -> reduces loss a lot
        # @Dave increase stop loss first to 0.5 times entry bar, then to 0.75 times entry bar and then into profit (v11, v12)
        # next steps is to avoid more losers without sacrificing the winners


        # Then add additional rules (1.5, ...) to test whether they have a value add (test for alpha and beta in Excel)
        # Should we incorporate highs and lows rules in strategy? If yes, maybe release parameters to 0
        # Perspective: Test rules for longer time period, e.g., 2020-2023; check alpha and beta error: what trades did we trade that we should not have traded (alpha) and what trades did we not trade that we should have traded (beta)? Alpha makes us add more rules to eliminate wrong trades and beta makes us adjust parameters and test performance with other parameters
        # Erster Anschein: Checklist bis einschließlich 2.3 traded viele der identifizierten opportunities, aber zu viel noise
        # Regel 3.3.1 bringt keinen value add. Macht insgesamt die Hälfte an Trades im Vergleich zu 2.3 aber nur 36% der "guten" Trades
        # Verpasste opportunities scheitern an opposite fifths oder dass 2 candles vor entry candle zu groß


        # Vroni 2/2/23: add rules 1.3, 1.5, 3.2, 1.1
        # Vroni 2/2/23: 1.3 could implement linear regression or increase for the last candles (linear regression seit dem vorletzten low für long strategy und seit dem vorletzten high für short strategy)
        # Vroni 2/2/23: 1.5 Dave can implement three correct forms of blue and can ausschließen abflachende und volatile kurven
        # Vroni 2/2/23: 1.1 und 3.2 start with higher lows und breaking highs (faktor 0, also es muss gerade so höher sein als das vorherige)

        # next steps: adjust 1.3 for highs and lows in 5min chart
        # Dave see new rule 1.3 (v14)
        # next steps: backtest 4 versions (core strategy, +2 rules, +20% entry bar, +linear regression on purple) for all 8 quarters in 2021 and 2022
        # next steps: implement in bybit


        #################### 1 TREND ####################

        # 1.1 Higher lows: last low must be higher than previous low
        # check if there are at least two highs and two lows for stability of calculations
        # total_rules+=1
        # if len(lows_trend) > 1 and not highs_trend.empty:

        #     # higher lows, but retracement of last low of maximum retracement_factor x difference between last high and second last low
        #     if lows_trend.iloc[-1] > lows_trend.iloc[-2] + abs(highs_trend.iloc[-1]-lows_trend.iloc[-2])*retracement_factor:
        #         long_checklist+=1

        # 1.2 Above purple: close of entry bar must be above 24 sma (Non-negotiable)
        total_rules += 1
        if sma_24[-1] < last_price['close']:
            long_checklist += 1

        # 1.3 Purple strong, smooth, flat or increasing:linear regression of trend line since second last low has positive slope
        total_rules+=1
        if slope_sma_long>0:
            long_checklist += 1

        # 1.3 Purple strong, smooth, flat or increasing: trend line has positive slope or positive curvature
        # total_rules += 1
        # if (sma_24.diff().iloc[-trend_candles:] < 0).sum() == 0 and (
        #         sma_24.diff().diff().iloc[-trend_candles:] <= 0).sum() == 0:
        #     long_checklist += 1

        # 1.4 Above blue: close of entry bar must be above sma8
        total_rules += 1
        if sma_8[-1] < last_price['close']:
            long_checklist += 1

        # 1.5 Blue strong, smooth, flat or increasing (Non-negotiable)
        # total_rules += 1
        # if sma_8.iloc[-1]-sma_8.iloc[-trend_candles]>=0:
        #     long_checklist+=1

        # if (sma_8.diff().iloc[-trend_candles:] < 0).sum() == 0 and (
        #         sma_8.diff().diff().iloc[-trend_candles:] <= 0).sum() == 0:
        #     long_checklist += 1

        # 1.6 Purple and blue in sync: sma24 and sma8 must cross entry bar
        # total_rules += 1
        # if (last_price['low'] < sma_8.iloc[-1] < last_price['high']) and (
        #         last_price['low'] < sma_24.iloc[-1] < last_price['high']):
        #     checklist += 1

        # #################### END 1 TREND ####################

        # #################### 2 TIME ####################

        # 2.1 Significant sideways (1-2 times of entry bar): sideways must be at most small_bars_50 times entry bar (Non-negotiable times 1 of entry bar)
        # 2.2 Small bars in sideways: All sideway candles must be smaller equal 50% of entry bar (Non-negotiable)
        total_rules += 1
        if (body_sideway_count_1 >= small_bars_50 * high_low_1).sum() == 0:
            checklist += 1

        # 2.3 Small bars in sideways: The two candles before the entry bar must be smaller equal 25% of the entry bar (Non-negotiable)
        total_rules += 1
        if (body_3_1 >= small_bars_25 * high_low_1).sum() == 0:
            checklist += 1

        # 2.4 (NOT TESTED YET) No volatility (ATR)
        # Rule to be defined and added

        # 2.5 No drift: little to no drift prior to entry bar
        total_rules += 1
        # if last_price['open']<=drift_max:
        #     long_checklist+=1
        
        if model.market_data.history[topic].iloc[-2][
                'close'] - model.market_data.history[topic].iloc[
                    -drift_length - 1]['open'] <= drift_height * open_close_1:
            long_checklist += 1            

        # 2.6 Minimum number of sideways candles are required (this ensures that the entry bar is large enough)
        total_rules += 1
        if sideways_count >= minimum_sideways:
            checklist += 1

        # #################### END 2 TIME ####################

        # #################### 3 BAR ####################

        # 3.1 Entry bar in opposite 1/5ths: the wigs of the entry bar must be smaller equal 20% of the candle (High to low) (Non-negotiable)
        total_rules += 1
        if (opposite_fifths * high_low_1 >=
                low_open_1) and (opposite_fifths * high_low_1 >= high_close_1):
            long_checklist += 1

        # 3.2 Breaking of a significant high (50% of entry bar): 50% of the entry bar must be above last high
        # check if there are at least two highs and two lows for stability of calculations
        # total_rules += 1
        # if not highs_trend.empty:

        #     # at least the "high_factor" fraction of the body of the entry bar has to be above the preceding high
        #     if highs_trend.iloc[-1] + high_factor * open_close_1 < last_price['close']:
        #         long_checklist += 1

        # 3.3 Is entry bar a surprise? (Picture) (Non-negotiable):
        # 3.3.1 Amplitude of sideways must be smaller than body of entry bar
        total_rules += 1
        if sideways_count_max - sideways_count_min <= surprise_factor * open_close_1:
            checklist += 1
        
        # 3.3.2 body of entry bar must be a significant part of the trading screen
        total_rules += 1
        if open_close_1 >= surprise_factor_2 * high_low_candle_window:
            checklist += 1
        
        # otherwise allow trend in trend candles
        # THIS RULE IS NOT PART OF THE INITIAL TRADING SYSTEM
        # elif (drift_max - drift_min <= surprise_factor * open_close_1): 
        #     if ((model.market_data.history[topic].iloc[-drift_length:-1]['close'] - model.market_data.history[topic].iloc[-drift_length:-1]['open'])<0).sum()==0:
        #         long_checklist+=1
        #     elif ((model.market_data.history[topic].iloc[-drift_length:-1]['close'] - model.market_data.history[topic].iloc[-drift_length:-1]['open'])>0).sum()==0:
        #         short_checklist+=1

        # 3.3.2 No trend in sideways
        # total_rules += 1
        # if abs(slope) < max_abs_slope:
        #     checklist += 1

        # 3.4 Blue entry bar: close of entry bar must be greater than open of entry bar (Non-negotiable)
        total_rules += 1
        if last_price['close'] > last_price['open']:
            long_checklist += 1

        #################### END BAR ####################

        ######################################## END CHECKLIST LONG ########################################

        ######################################## CHECKLIST SHORT ########################################

        #################### 1 TREND ####################

        # 1.1 Lower highs: last high must be lower than previous high
        # check if there are at least two highs and two lows for stability of calculations
        # if len(highs_trend) > 1 and not lows_trend.empty:

        #     # lower highs_trend, but retracement of last high of maximum retracement_factor x difference between last low and second last high
        #     if highs_trend.iloc[-1] < highs_trend.iloc[-2] - abs(lows_trend.iloc[-1]-highs_trend.iloc[-2])*retracement_factor:
        #         short_checklist+=1

        # 1.2 Above purple: close of entry bar must be above 24 sma
        if sma_24[-1] > last_price['close']:
            short_checklist += 1

        # 1.3 Purple strong, smooth, flat or decreasig : linear regression of trend line since second last high has negative slope
        if slope_sma_short<0:
            short_checklist += 1

        # 1.3 Purple strong, smooth, flat or decreasing: trend line has negative slope or negative curvature
        # if (sma_24.diff().iloc[-trend_candles:] > 0).sum() == 0 and (
        #         sma_24.diff().diff().iloc[-trend_candles:] >= 0).sum() == 0:
        #     short_checklist += 1

        # 1.4 Above blue: close of entry bar must be below sma8
        if sma_8[-1] > last_price['close']:
            short_checklist += 1

        # 1.5 Blue strong, smooth, flat or increasing
        # if sma_8.iloc[-1]-sma_8.iloc[-trend_candles]<=0:
        #     short_checklist+=1

        # if (sma_8.diff().iloc[-trend_candles:] > 0).sum() == 0 and (
        #         sma_8.diff().diff().iloc[-trend_candles:] >= 0).sum() == 0:
        #     short_checklist += 1

        # #################### END 1 TREND ####################

        # #################### 2 TIME ####################

        # 2.5 No drift: little to no drift prior to entry bar        
        # if last_price['open']>=drift_min:
        #     short_checklist+=1
        
        if model.market_data.history[topic].iloc[
                -drift_length - 1]['open'] - model.market_data.history[
                    topic].iloc[-2]['close'] <= drift_height * open_close_1:
           short_checklist += 1

        # #################### END 2 TIME ####################

        # #################### 3 BAR ####################

        # 3.1 Entry bar in opposite 1/5ths: the wigs of the entry bar must be smaller equal 20% of the candle (High to low) (Non-negotiable)
        if (opposite_fifths * high_low_1 >=
                high_open_1) and (opposite_fifths * high_low_1 >= low_close_1):
            short_checklist += 1

        # 3.2 Breaking of a significant low (50% of entry bar): 50% of the entry bar must be below last low
        # check if there are at least two highs and two lows for stability of calculations
        # if not lows_trend.empty:

        #     # at least the "high_factor" fraction of the body of the entry bar has to be below the preceding low
        #     if lows_trend.iloc[-1] - high_factor * open_close_1 > last_price['close']:
        #         short_checklist += 1

        # 3.4 Red entry bar: close of entry bar must be smaller than open of entry bar
        if last_price['close'] < last_price['open']:
            short_checklist += 1

        #################### END BAR ####################

        ######################################## END CHECKLIST SHORT ########################################

        # calculate score across all rules
        confidence_score_long = (long_checklist + checklist) / total_rules
        confidence_score_short = (short_checklist + checklist) / total_rules

        # determine trading quantity
        # buy_qty = 100 / last_price['close']
        # buy_qty = np.round(buy_qty, 3)

        # buy with all available balance
        buy_qty = model.account.wallet[ticker[-4:]]['available_balance']/ last_price['close']
        buy_qty = np.round(buy_qty, 3)

        # if all rules apply for the long strategy and there is no current open position, place buy order
        if (confidence_score_long
                == 1.0) and (model.account.positions[ticker]['size'] == 0.0):

            # set leverage so that if stop loss is hit, it occurs a maximum loss of 10% and cap leverage at 20
            leverage_ratio = 1-(stop_loss_long/last_price['close'])
            # leverage = np.min([20, np.ceil(0.2/leverage_ratio)])
            leverage = np.ceil(0.2/leverage_ratio)

            # for real trading, set leverage of position to leverage, for backtesting just scale position size
            buy_qty=leverage*buy_qty

            # try:
            #     model.account.session.set_leverage(symbol=ticker,
            #                           buy_leverage=leverage)
            # except:
            #     pass

            model.account.place_order(symbol=ticker,
                                      side='Buy',
                                      qty=buy_qty,
                                      order_type='Market',
                                      stop_loss=stop_loss_long,
                                      take_profit=take_profit_long)
            model.model_storage['entry_open_close_1_long'] = open_close_1
            model.model_storage['entry_close_1_long'] = last_price['close']
            model.model_storage['entry_open_1_long'] = last_price['open']
            
            ts = str(pd.Timestamp(model.market_data.history[topic].iloc[-1]['end'])+pd.Timedelta(minutes=1))
            if 'sideways_std' not in model.model_stats.keys():
                model.model_stats['sideways_std']={}

            model.model_stats['sideways_std'][ts] = model.market_data.history[topic].iloc[-sideways_count:-1]['close'].std()

            if 'sideways_sma_8_std' not in model.model_stats.keys():
                model.model_stats['sideways_sma_8_std']={}

            model.model_stats['sideways_sma_8_std'][ts] = sma_8.iloc[-sideways_count:-1].std()

            if 'sideways_sma_24_std' not in model.model_stats.keys():
                model.model_stats['sideways_sma_24_std']={}

            model.model_stats['sideways_sma_24_std'][ts] = sma_24.iloc[-sideways_count:-1].std()

            if 'last_low' not in model.model_stats.keys():
                model.model_stats['last_low']={}

            model.model_stats['last_low'][ts] = lows[-1]

            if 'last_low_idx' not in model.model_stats.keys():
                model.model_stats['last_low_idx']={}

            model.model_stats['last_low_idx'][ts] = lows.index[-1]
            
            if 'second_last_low' not in model.model_stats.keys():
                model.model_stats['second_last_low']={}

            model.model_stats['second_last_low'][ts] = lows[-2]

            if 'second_last_low_idx' not in model.model_stats.keys():
                model.model_stats['second_last_low_idx']={}

            model.model_stats['second_last_low_idx'][ts] = lows.index[-2]

            if 'last_high' not in model.model_stats.keys():
                model.model_stats['last_high']={}

            model.model_stats['last_high'][ts] = highs[-1]

            if 'last_high_idx' not in model.model_stats.keys():
                model.model_stats['last_high_idx']={}

            model.model_stats['last_high_idx'][ts] = highs.index[-1]

            if 'second_last_high' not in model.model_stats.keys():
                model.model_stats['second_last_high']={}

            model.model_stats['second_last_high'][ts] = highs[-2]

            if 'second_last_high_idx' not in model.model_stats.keys():
                model.model_stats['second_last_high_idx']={}

            model.model_stats['second_last_high_idx'][ts] = highs.index[-2]

            if 'long_sma24_slope' not in model.model_stats.keys():
                model.model_stats['long_sma24_slope']={}

            model.model_stats['long_sma24_slope'][ts] = slope_sma_long

            if 'short_sma24_slope' not in model.model_stats.keys():
                model.model_stats['short_sma24_slope']={}

            model.model_stats['short_sma24_slope'][ts] = slope_sma_short

            # last_exec = list(model.account.executions['BTCUSDT'].keys())[-1]
            # highs.to_excel('highs_{}.xlsx'.format(last_price.name))
            # lows.to_excel('lows_{}.xlsx'.format(last_price.name))

        # if all rules apply for the short strategy and there is no current open position, place sell order
        if (confidence_score_short
                == 1.0) and (model.account.positions[ticker]['size'] == 0.0):
            
            # set leverage so that if stop loss is hit, it occurs a maximum loss of 10% and cap leverage at 20
            leverage_ratio = (stop_loss_short/last_price['close'])-1
            # leverage = np.min([20, np.ceil(0.2/leverage_ratio)])
            leverage = np.ceil(0.2/leverage_ratio)

            # for real trading, set leverage of position to leverage, for backtesting just scale position size
            buy_qty=leverage*buy_qty

            # try:
            #     model.account.session.set_leverage(symbol=ticker,
            #                           sell_leverage=leverage)
            # except:
            #     pass

            model.account.place_order(symbol=ticker,
                                      side='Sell',
                                      qty=buy_qty,
                                      order_type='Market',
                                      stop_loss=stop_loss_short,
                                      take_profit=take_profit_short)
            model.model_storage['entry_open_close_1_short'] = open_close_1
            model.model_storage['entry_close_1_short'] = last_price['close']
            model.model_storage['entry_open_1_short'] = last_price['open']
            
            ts = str(pd.Timestamp(model.market_data.history[topic].iloc[-1]['end'])+pd.Timedelta(minutes=1))

            if 'sideways_std' not in model.model_stats.keys():
                model.model_stats['sideways_std']={}

            model.model_stats['sideways_std'][ts] = model.market_data.history[topic].iloc[-sideways_count:-1]['close'].std()
            
            if 'sideways_sma_8_std' not in model.model_stats.keys():
                model.model_stats['sideways_sma_8_std']={}

            model.model_stats['sideways_sma_8_std'][ts] = sma_8.iloc[-sideways_count:-1].std()

            if 'sideways_sma_24_std' not in model.model_stats.keys():
                model.model_stats['sideways_sma_24_std']={}

            model.model_stats['sideways_sma_24_std'][ts] = sma_24.iloc[-sideways_count:-1].std()
            
            if 'last_low' not in model.model_stats.keys():
                model.model_stats['last_low']={}

            model.model_stats['last_low'][ts] = lows[-1]

            if 'last_low_idx' not in model.model_stats.keys():
                model.model_stats['last_low_idx']={}

            model.model_stats['last_low_idx'][ts] = lows.index[-1]
            
            if 'second_last_low' not in model.model_stats.keys():
                model.model_stats['second_last_low']={}

            model.model_stats['second_last_low'][ts] = lows[-2]

            if 'second_last_low_idx' not in model.model_stats.keys():
                model.model_stats['second_last_low_idx']={}

            model.model_stats['second_last_low_idx'][ts] = lows.index[-2]

            if 'last_high' not in model.model_stats.keys():
                model.model_stats['last_high']={}

            model.model_stats['last_high'][ts] = highs[-1]

            if 'last_high_idx' not in model.model_stats.keys():
                model.model_stats['last_high_idx']={}

            model.model_stats['last_high_idx'][ts] = highs.index[-1]

            if 'second_last_high' not in model.model_stats.keys():
                model.model_stats['second_last_high']={}

            model.model_stats['second_last_high'][ts] = highs[-2]

            if 'second_last_high_idx' not in model.model_stats.keys():
                model.model_stats['second_last_high_idx']={}

            model.model_stats['second_last_high_idx'][ts] = highs.index[-2]

            if 'long_sma24_slope' not in model.model_stats.keys():
                model.model_stats['long_sma24_slope']={}

            model.model_stats['long_sma24_slope'][ts] = slope_sma_long

            if 'short_sma24_slope' not in model.model_stats.keys():
                model.model_stats['short_sma24_slope']={}

            model.model_stats['short_sma24_slope'][ts] = slope_sma_short
