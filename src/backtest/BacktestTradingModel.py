# !/usr/bin/env python
# coding: utf-8
import warnings

warnings.simplefilter(action='ignore', category=FutureWarning)
warnings.simplefilter(action='ignore', category=RuntimeWarning)

import pandas as pd
import json
from typing import Any, Dict, List
from src.TradingModel import TradingModel
from src.backtest.BacktestAccountData import BacktestAccountData
from src.backtest.BacktestMarketData import BacktestMarketData
from binance.client import Client
from src.endpoints.binance_functions import binance_to_bybit
# from src.endpoints.binance_functions import create_simulation_data
from src.endpoints.bybit_functions import create_simulation_data

from tqdm import tqdm
import json
import yaml
from dotenv import load_dotenv
import os

load_dotenv()

CONFIG_DIR = os.getenv('CONFIG_DIR')

# Load variables from the YAML file
with open(CONFIG_DIR, 'r') as file:
    config = yaml.safe_load(file)

# Access variables from the loaded data
BASE_CUR = config.get('base_cur', 'USDT')
PUBLIC_TOPICS = config.get('public_topics')
PRIVATE_TOPICS = config.get('private_topics')
PUBLIC_TOPICS_COLUMNS = config.get('public_topics_columns')
BACKTEST_SYMBOLS = config.get('backtest_symbols')
BINANCE_BYBIT_MAPPING = config.get('binance_bybit_mapping')
HIST_TICKERS = config.get('hist_tickers')


class BacktestTradingModel(TradingModel):
    '''
    Class that wraps the backtest trading model, backtest market data and backtest account data.
    '''

    # create new Model object
    def __init__(self,
                 model: Any,
                 http_session: Client,
                 symbols: List[str],
                 budget: Dict[str, Any],
                 topics: List[str] = PUBLIC_TOPICS,
                 topic_mapping: Dict[str, str] = BINANCE_BYBIT_MAPPING,
                 backtest_symbols: Dict[str, str] = BACKTEST_SYMBOLS,
                 model_storage: Dict[str, Any] = {},
                 model_args: Dict[str, Any] = {},
                 model_stats: Dict[str, Any] = {}):
        '''
        Parameters
        ----------
        model: Any
            function that holds the trading logic
        http_session: binance.client.Client
            open http connection to pull data from.
        symbols: List[str]
            list of symbols to incorporate into account data.
        budget: Dict[str, float]
            start budget for all tickers as dictionary with key = symbol, value= budget
        topics: List[str]
            all topics to store in market data object
        toppic_mapping: Dict[str,str]
            mapping between bybit websocket topics and binance symbols.
            It is used to map simulated bybit websocket messages to account symbols for data updates, which are indexed by binance tickers.
        backtest_symbols: Dict[str,str]
            mapping between bybit topics and binance symbols, used to simulate bybit websocket messages with binance data.
        model_storage: Dict[str, Any]
            additional storage so that the trading model can store results
        model_args: Dict[str, Any]
            optional additional parameters for the trading model
        model_stats: Dict[str, Any]
            optional additional statistics that can be stored during the backtest to be included into the trade report.
            each trade in each statistic must be indexed by the execution timestamp
        '''

        # initialize attributes and instantiate market and account data objects
        self.account = BacktestAccountData(symbols=symbols, budget=budget)
        self.market_data = BacktestMarketData(account=self.account,
                                              client=http_session,
                                              topics=topics,
                                              toppic_mapping=topic_mapping)

        self.topic_mapping = topic_mapping
        self.backtest_symbols = backtest_symbols
        self.topics = topics
        self.model = model
        self.model_storage = model_storage
        self.model_args = model_args
        self.model_stats = model_stats

        # list of bybit websocket messages for simulation
        self.bybit_messages = None

    def run_backtest(self,
                     symbols: Dict[str, str],
                     start_history: str,
                     start_str: str,
                     end_str: str,
                     slice_length: int = 50000,
                     save_output: bool = False) -> Dict[str, float]:
        '''
        Run a backtest by simulating websocket messages from bybit through historical klines from binance and return a performance report.
        Parameters
        ----------
        symbols: Dict[str, str]
            dictionary of relevant symbols for backtesting
            symbols for backtesting
            keys have format binance_ticker.binance_interval and values are coresponding bybit ws topics.
        start_history: str
            start of historical data to pull for model in format yyyy-mm-dd hh-mm-ss
            history will be pulled until start_str
        start_str: str
            start of simulation in format yyyy-mm-dd hh-mm-ss
        end_str: str
            end of simulation in format yyyy-mm-dd hh-mm-ss
        slice_length: int
            length of partial time series to use for simulations.
            Used to improve memory usage and speed up computation. Default is 50000.
        save_output: bool
            flag whether to export performance report and trade list to excel. Default is False

        Returns
        -------
        report: Dict[str, float]
            performance report
        '''

        # store initial budget for performance measures
        initial_budget = self.account.wallet[BASE_CUR]['available_balance']

        print('Loading historical data...')

        ###################### For Crypto Backtest with Binance ###########################################

        # read history from csv
        # for symbol in symbols.keys():
        #     history = pd.read_csv('src/backtest/data/history_{}_{}_{}.csv'.format(symbols[symbol],start_history,start_str), parse_dates=['start','end'], dtype={'open':float,'high':float,'low':float,'close':float,'volume':float,'turnover':float})
        #     history = history.set_index('end',drop=False)
        #     self.market_data.history[symbols[symbol]] = pd.concat([history, self.market_data.history[symbols[symbol]]])

        # add historical data for trading model
        # self.market_data.build_history(symbols=symbols,
        #                                start_str=start_history,
        #                                end_str=start_str)

        # write history to csv
        # for ticker in self.market_data.history.keys():
        #     self.market_data.history[ticker].to_csv('src/backtest/data/history_{}_{}_{}.csv'.format(ticker,start_history,start_str))

        ######################################################################################################

        print('Done!')

        # slice long time series into shorter time series for faster computation (OPTIONAL)
        # partial_series = helper_functions.slice_timestamps(
        #     start_str=start_str,
        #     end_str=end_str,
        #     freq='1min',
        #     slice_length=slice_length)

        partial_series = [[start_str, end_str]]

        for timestamps in partial_series:

            print('Creating simulation data...')

            ###################### For Crypto Backtest with Bybit or Binance ###########################################

            # read simulation data from json files
            # with open('src/backtest/data/klines_{}_{}.json'.format(timestamps[0],timestamps[1]), 'r') as f:
            #     klines = json.load(f)
            # with open('src/backtest/data/topics_{}_{}.json'.format(timestamps[0],timestamps[1]), 'r') as f:
            #       topics = json.load(f)

            # create simulation data via bybit
            klines, topics = create_simulation_data(symbols=symbols,
                                                    start_str=timestamps[0],
                                                    end_str=timestamps[1])

            # create simulation data via binance
            # klines, topics = binance_functions.create_simulation_data(
            #     session=self.market_data.client,
            #     symbols=symbols,
            #     start_str=str(timestamps[0]),
            #     end_str=str(timestamps[1]))

            # write simulation data to json files
            # with open(
            #         'src/backtest/data/klines_{}_{}.json'.format(
            #             timestamps[0], timestamps[1]), 'w') as f:
            #     json.dump(klines, f)
            # with open(
            #         'src/backtest/data/topics_{}_{}.json'.format(
            #             timestamps[0], timestamps[1]), 'w') as f:
            #     json.dump(topics, f)

            # format data to bybit websocket messages
            self.bybit_messages, self.account.simulation_data = binance_to_bybit(
                klines, topics=topics)

            ######################################################################################################

            # remove last elements of bybit messages that overlap with next partial series (two per topic)
            # this is due to the design of create_simulation_data to pull one extra candle per topic
            for symbol in symbols:
                self.bybit_messages.pop()
                self.bybit_messages.pop()

            print('Done!')

            # set starting timestamp
            self.account.timestamp = self.account.simulation_data.index[0][0]

            print('Simulating backtest from {} to {}'.format(
                timestamps[0], timestamps[1]))

            # iterate through formated simulation data and run backtest
            for msg in tqdm(self.bybit_messages):
                self.on_message(message=msg)

            # append simulation data to global simulation data
            # self.bybit_messages.extend(bybit_messages)
            # self.simulation_data = pd.concat(
            #     [self.simulation_data, simulation_data])

            print('Done!')

        # close remaining open positions
        for pos in self.account.positions.values():
            if pos['size'] > 0:
                if pos['side'].upper() == 'BUY':
                    side = 'SELL'
                else:
                    side = 'BUY'
                self.account.place_order(symbol=pos['symbol'],
                                         side=side,
                                         qty=pos['size'],
                                         order_type='Market',
                                         reduce_only=True)
        report = self.create_performance_report(initial_budget=initial_budget,
                                                start_str=start_str,
                                                end_str=end_str,
                                                save_output=save_output)

        return report

    def create_performance_report(
            self,
            initial_budget: float,
            start_str: str,
            end_str: str,
            save_output: bool = False) -> Dict[str, Dict[str, float]]:
        '''
        Create performance report after backtest.
        Report is created by iterating through executions and counting a trade if it exceeds or matches a previously open position.
        A trade is a winning trade if its price is better than the position price before any partial closings.

        Parameters
        ----------
        initial_budget: float
            initial budget of base currency at start of backtest
        start_str: str
            starting timestamp of backtest formatted as string
        end_str: str
            ending timestamp of backtest formatted as string
        save_output: bool
            flag whether to export performance report and trade list to excel. Default is False
        Returns
        -------
        report: Dict[str, Dict[str,float]]
            performance report
        '''
        # save model stats as json and excel
        with open(
                "evaluations/model_stats_{}_{}.json".format(start_str, end_str),
                "w") as outfile:
            json.dump(self.model_stats, outfile)
        pd.DataFrame(self.model_stats).to_excel(
            "evaluations/model_stats_{}_{}.xlsx".format(start_str, end_str))

        report = {}
        # iterate through all symbols with executed trades
        for symbol in [
                symbol for symbol in self.account.executions.keys()
                if self.account.executions[symbol].values()
        ]:

            # initialize kpis

            # sign, price, size and value of current position
            sign_pos = None
            pos_price = None
            pos_qty = 0
            pos_value = 0

            # initialize winning and total trades to zero
            # a winning trade is one
            wins = 0
            total_trades = 0

            # iterate through executions
            for exe in self.account.executions[symbol].values():

                # if trade opened a new position calculate new position value and continue
                if pos_qty == 0:
                    sign_pos = 2 * ((exe['side'].upper() == 'BUY') - 0.5)
                    pos_price = exe['price']
                    pos_qty = exe['exec_qty']
                    pos_value = pos_price * pos_qty
                    continue

                # calculate sign of new trade
                sign_new = 2 * ((exe['side'].upper() == 'BUY') - 0.5)

                # if trade was in same direction as position, calculate new position values and continue
                if sign_new == sign_pos:
                    pos_value += exe['price'] * exe['exec_qty']
                    pos_qty += exe['exec_qty']
                    pos_price = pos_value / pos_qty
                    continue

                # check if trade was a closing trade
                if exe['open'] == False:

                    # if trade was in opposite direction and exceeded or matched old position in size:
                    # check if trade was a winning trade
                    # open new position with execution price and residual quantity
                    if exe['exec_qty'] >= pos_qty:
                        if exe['price'] * sign_pos > pos_price * sign_pos:
                            wins += 1
                            total_trades += 1
                        else:
                            total_trades += 1

                        pos_price = exe['price']
                        pos_value = (exe['exec_qty'] - pos_qty) * exe['price']
                        sign_pos = sign_new
                        pos_qty = abs(exe['exec_qty'] - pos_qty)

                # if trade did not match or exceed old position, reduce old position, but keep position price
                else:
                    pos_value = abs(pos_value - exe['price'] * exe['exec_qty'])
                    pos_qty = abs(pos_qty - exe['exec_qty'])

            # calculate total trading return and return in percentage of initial budget
            trading_return = self.account.wallet[
                symbol[-len(BASE_CUR):]]['available_balance'] - initial_budget
            trading_return_percent = trading_return / initial_budget

            if total_trades > 0:
                wl_ratio = wins / total_trades
                avg_trade_return = trading_return / total_trades
                avg_trade_return_per = trading_return_percent / total_trades
            else:
                wl_ratio = 0
                avg_trade_return = 0
                avg_trade_return_per = 0

            # create performance report
            report[symbol] = {
                'initial_budget':
                    initial_budget,
                'final_budget':
                    self.account.wallet[symbol[-len(BASE_CUR):]]
                    ['available_balance'],
                'total_trades':
                    total_trades,
                'win_loss_ratio':
                    wl_ratio,
                'trading_return':
                    trading_return,
                'trading_return_percent':
                    trading_return_percent,
                'avg_trade_return':
                    avg_trade_return,
                'avg_trade_return_per':
                    avg_trade_return_per
            }

            if save_output:
                # extract values of model_args, and turn them into string
                if type(self.model_args) == dict:
                    model_args_str = list(map(str, self.model_args.values()))
                else:
                    model_args_str = str(self.model_args)

                # concatenate model_args_str to single string separated by '_'
                args_str = '_'.join(model_args_str)

                pd.DataFrame(report).to_excel(
                    'evaluations/performance_report_{}.xlsx'.format(args_str))
                trades = pd.DataFrame(
                    self.account.executions[symbol]).transpose()
                trades['trading_value'] = -2 * (
                    (trades['side'].apply(lambda x: x.upper()) == 'BUY') - 0.5
                ) * trades['exec_qty'] * trades['price'] - trades['exec_fee']

                # add potential trade statistics as additional columns
                for stat in self.model_stats.keys():
                    trades[stat] = None
                    # initialize last trade id
                    previous_id = None

                    # iterate through trade ids and add trade statistics
                    for id in trades.index:

                        # check if statisitics for current trade is available (indexed by trading time)
                        # if not then add "None"
                        if not str(trades.loc[id]['trade_time']
                                  ) in self.model_stats[stat].keys():

                            self.model_stats[stat][str(
                                trades.loc[id]['trade_time'])] = {}

                        # check if trade is an opening trade
                        if trades.loc[id]['open']:

                            if not 'long' in self.model_stats[stat][str(
                                    trades.loc[id]['trade_time'])].keys():
                                self.model_stats[stat][str(
                                    trades.loc[id]['trade_time'])]['long'] = ""

                            if not 'short' in self.model_stats[stat][str(
                                    trades.loc[id]['trade_time'])].keys():
                                self.model_stats[stat][str(
                                    trades.loc[id]['trade_time'])]['short'] = ""

                            # check if trade was long
                            if trades.loc[id]['side'].upper() == 'BUY':
                                try:
                                    trades.loc[id,
                                               stat] = self.model_stats[stat][
                                                   str(trades.loc[id]
                                                       ['trade_time'])]['long']
                                except:
                                    trades.loc[id, stat] = str(
                                        self.model_stats[stat][str(
                                            trades.loc[id]['trade_time'])]
                                        ['long'])
                            else:
                                try:
                                    trades.loc[id,
                                               stat] = self.model_stats[stat][
                                                   str(trades.loc[id]
                                                       ['trade_time'])]['short']
                                except:
                                    trades.loc[id, stat] = str(
                                        self.model_stats[stat][str(
                                            trades.loc[id]['trade_time'])]
                                        ['short'])

                        # otherwise add trade statisitics of open trade
                        else:
                            if not 'long' in self.model_stats[stat][str(
                                    trades.loc[previous_id]
                                ['trade_time'])].keys():
                                self.model_stats[stat][str(
                                    trades.loc[previous_id]
                                    ['trade_time'])]['long'] = ""

                            if not 'short' in self.model_stats[stat][str(
                                    trades.loc[previous_id]
                                ['trade_time'])].keys():
                                self.model_stats[stat][str(
                                    trades.loc[previous_id]
                                    ['trade_time'])]['short'] = ""

                            # check if open trade was long
                            if trades.loc[previous_id]['side'].upper() == 'BUY':
                                try:
                                    trades.loc[id,
                                               stat] = self.model_stats[stat][
                                                   str(trades.loc[previous_id]
                                                       ['trade_time'])]['long']
                                except:
                                    trades.loc[id, stat] = str(
                                        self.model_stats[stat][str(
                                            trades.loc[previous_id]
                                            ['trade_time'])]['long'])
                            else:
                                try:
                                    trades.loc[id,
                                               stat] = self.model_stats[stat][
                                                   str(trades.loc[previous_id]
                                                       ['trade_time'])]['short']
                                except:
                                    trades.loc[id, stat] = str(
                                        self.model_stats[stat][str(
                                            trades.loc[previous_id]
                                            ['trade_time'])]['short'])

                        # save previous trade id
                        previous_id = id

                # export report to excel
                trades.to_excel('evaluations/trade_list_{}_{}_{}.xlsx'.format(
                    args_str, start_str, end_str))
        return report
