# !/usr/bin/env python
# coding: utf-8
import warnings

warnings.simplefilter(action='ignore', category=FutureWarning)
import pandas as pd
import json
from dotenv import load_dotenv
import os
from typing import Any, Dict, List
from src.TradingModel import TradingModel
from src.backtest.BacktestAccountData import BacktestAccountData
from src.backtest.BacktestMarketData import BacktestMarketData
from binance.client import Client
from src.endpoints.binance_functions import binance_to_bybit, create_simulation_data
from tqdm import tqdm

load_dotenv()

PUBLIC_TOPICS = eval(os.getenv('PUBLIC_TOPICS'))
PRIVATE_TOPICS = eval(os.getenv('PRIVATE_TOPICS'))

HIST_TICKERS = eval(os.getenv('HIST_TICKERS'))

BACKTEST_SYMBOLS = eval(os.getenv('BACKTEST_SYMBOLS'))


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
                 model_storage: Dict[str, Any] = {},
                 model_args: Dict[str, Any] = {}):
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
        model_storage: Dict[str, Any]
            additional storage so that the trading model can store results
        model_args: Dict[str, Any]
            optional additional parameters for the trading model
        '''

        # initialize attributes and instantiate market and account data objects
        self.account = BacktestAccountData(binance_client=http_session,
                                           symbols=symbols,
                                           budget=budget)
        self.market_data = BacktestMarketData(account=self.account,
                                              client=http_session,
                                              topics=topics)
        self.model = model
        self.model_storage = model_storage
        self.model_args = model_args

        # initialize empty simulation data
        # formatted dataframe of binance candles
        self.simulation_data = None

        # list of bybit websocket messages
        self.bybit_messages = None

    def run_backtest(self, symbols: Dict[str, str], start_history: str,
                     start_str: str, end_str: str) -> Dict[str, float]:
        '''
        Run a backtest by simulating websocket messages from bybit through historical klines from binance and return a performance report.
        Parameters
        ----------
        symbols: Dict[str, str]
            dictionary of relevant symbols for backtesting
            symbols for backtesting
            keys have format binance_ticker.binacne_interval and values are coresponding bybit ws topics.
        start_history: str
            start of historical data to pull for model in format yyyy-mm-dd hh-mm-ss
            history will be pulled until start_str
        start_str: str
            start of simulation in format yyyy-mm-dd hh-mm-ss
        end_str: str
            end of simulation in format yyyy-mm-dd hh-mm-ss

        Returns
        -------
        report: Dict[str, float]
            performance report
        '''

        # store initial budget for performance measures
        initial_budget = self.account.wallet['USDT']['available_balance']

        # create simulation data
        klines, topics = create_simulation_data(session=self.account.session,
                                                symbols=symbols,
                                                start_str=start_str,
                                                end_str=end_str)

        # format data to bybit websocket messages
        self.bybit_messages, self.simulation_data = binance_to_bybit(
            klines, topics=topics)

        # set starting timestamp
        self.account.timestamp = self.simulation_data.index[0][0]

        # add historical data for trading model
        self.market_data.build_history(symbols=symbols,
                                       start_str=start_history,
                                       end_str=start_str)

        # iterate through formated simulation data and run backtest
        for msg in tqdm(self.bybit_messages):
            self.on_message(message=msg)
            self.account.timestamp = self.market_data.history[BACKTEST_SYMBOLS[
                list(BACKTEST_SYMBOLS.keys())[0]]].index[-1]

        # close remaining open positions
        for pos in self.account.positions.values():
            if pos['size'] > 0:
                if pos['side'] == 'Buy':
                    side = 'Sell'
                else:
                    side = 'Buy'
                self.account.place_order(symbol=pos['symbol'],
                                         side=side,
                                         qty=pos['size'],
                                         reduce_only=True)
        report = self.create_performance_report(initial_budget=initial_budget)

        return report

    def create_performance_report(self,
                                  initial_budget: float) -> Dict[str, float]:
        '''
        Create performance report after backtest.
        Report is created by iterating through executions and counting a trade if it exceeds or matches a previously open position.
        A trade is a winning trade if its price is better than the position price before any partial closings.

        Parameters
        ----------
        initial_budget: float
            initial budget of USDT at start of backtest
        
        Returns
        -------
        report: Dict[str, float]
            performance report
        '''

        # initialize kpis

        # sign, price, size and value of current position
        sign_pos = None
        pos_price = None
        open = False
        pos_qty = 0
        pos_value = 0

        # initialize winning and total trades to zero
        # a winning trade is one
        wins = 0
        total_trades = 0

        # iterate through executions
        for exe in self.account.executions['BTCUSDT'].values():

            # if trade opened a new position calculate new position value and continue
            if pos_qty == 0:
                sign_pos = 2 * ((exe['side'] == 'Buy') - 0.5)
                pos_price = exe['price']
                pos_qty = exe['exec_qty']
                pos_value = pos_price * pos_qty
                continue

            # calculate sign of new trade
            sign_new = 2 * ((exe['side'] == 'Buy') - 0.5)

            # if trade was in same direction as position, calculate new position values and continue
            if sign_new == sign_pos:
                pos_value += exe['price'] * exe['exec_qty']
                pos_qty += exe['exec_qty']
                pos_price = pos_value / pos_qty
                continue

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

            # if trade did not match or exceed old position, reduce old position, but keep position price
            else:
                pos_value = abs(pos_value - exe['price'] * exe['exec_qty'])
                pos_qty = abs(pos_qty - exe['exec_qty'])

        # calculate total trading return and return in percentage of initial budget
        trading_return = self.account.wallet['USDT'][
            'available_balance'] - initial_budget
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
        report = {
            'initial_budget': initial_budget,
            'final_budget': self.account.wallet['USDT']['available_balance'],
            'total_trades': total_trades,
            'win_loss_ratio': wl_ratio,
            'trading_return': trading_return,
            'trading_return_percent': trading_return_percent,
            'avg_trade_return': avg_trade_return,
            'avg_trade_return_per': avg_trade_return_per
        }

        return report
