# !/usr/bin/env python
# coding: utf-8

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
                                              topics=topics)
        self.model = model
        self.model_storage = model_storage
        self.model_args = model_args

        # initialize empty simulation data

        # formatted dataframe of binance candles
        self.simulation_data = None

        # list of bybit websocket messages
        self.bybit_messages = None

    def run_backtest(self, symbols: Dict[str, str], start_str: str,
                     end_str: str) -> None:
        '''
        Run a backtest by simulating websocket messages from bybit through historical klines from binance.

        Parameters
        ----------
        symbols: Dict[str, str]
            dictionary of relevant symbols for backtesting
            symbols for backtesting
            keys have format binance_ticker.binacne_interval and values are coresponding bybit ws topics.
        start_str: str
            start of simulation in format yyyy-mm-dd hh-mm-ss
        end_str: str
            end of simulation in format yyyy-mm-dd hh-mm-ss

        Returns
        -------
        '''
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

        # iterate through formated simulation data and run backtest
        for msg in self.bybit_messages:
            self.on_message(message=msg)
            self.account.timestamp = self.market_data.history[BACKTEST_SYMBOLS[
                list(BACKTEST_SYMBOLS.keys())[0]]].index[-1]

        return None
