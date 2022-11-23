# !/usr/bin/env python
# coding: utf-8

import pandas as pd
import json
from dotenv import load_dotenv
import os
from typing import Any, Dict
from src.backtest.BacktestMarketData import BacktestMarketData
from src.backtest.BacktestAccountData import BacktestAccountData
from src.TradingModel import TradingModel

load_dotenv()

PUBLIC_TOPICS = eval(os.getenv('PUBLIC_TOPICS'))
PRIVATE_TOPICS = eval(os.getenv('PRIVATE_TOPICS'))

HIST_TICKERS = eval(os.getenv('HIST_TICKERS'))


class BacktestTradingModel(TradingModel):
    '''
    Class that wraps the backtest trading model, backtest market data and backtest account data.
    '''

    # create new Model object
    def __init__(self,
                 market_data: BacktestMarketData,
                 account: BacktestAccountData,
                 model: Any,
                 model_storage: Dict[str, Any] = {},
                 model_args: Dict[str, Any] = {}):
        '''
        Parameters
        ----------

        market_data: MarketData
            MarketData object that stores relevant market data
        account: AccountData
            AccountData object that stores relevant account data
        model: Any
            function that holds the trading logic
        model_storage: Dict[str, Any]
            additional storage so that the trading model can store results
        model_args: Dict[str, Any]
            optional additional parameters for the trading model
        '''

        # initialize attributes through inheritance from trading model
        super().__init__(market_data, account, model, model_storage, model_args)
