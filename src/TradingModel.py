# !/usr/bin/env python
# coding: utf-8

import pandas as pd
import json
from dotenv import load_dotenv
import os
from typing import Any, Dict
from .MarketData import MarketData
from .AccountData import AccountData

load_dotenv()

PUBLIC_TOPICS = eval(os.getenv('PUBLIC_TOPICS'))
PRIVATE_TOPICS = eval(os.getenv('PRIVATE_TOPICS'))

HIST_TICKERS = eval(os.getenv('HIST_TICKERS'))


class TradingModel:
    '''
    Class that wraps the trading model, market data and account data
    '''

    # create new Model object
    def __init__(self,
                 market_data: MarketData,
                 account: AccountData,
                 model: Any,
                 model_storage: Dict[str, Any] = {},
                 **model_args: Dict[str, Any]):
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
        model_args: *kwargs
            optional additional parameters for the trading model
        '''

        # initialize history with empty dataframes
        self.market_data = market_data
        self.account = account
        self.model = model
        self.model_storage = model_storage
        self.model_args = model_args

    def on_message(self, message: json):
        '''
        Upon reception of new websocket data, forward to either MarketData or AccountData object

        Parameters
        ----------
        msg: json
            message received from api, i.e. data to store
        '''
        # extract message
        msg = json.loads(message)

        try:
            # extract topic
            topic = msg['topic']

            # if public topic, forward to market_data and trigger model
            if topic in PUBLIC_TOPICS:

                self.market_data.on_message(message)
                self.model(self, **self.model_args)

            # if private topic, forward to account
            elif topic in PRIVATE_TOPICS:

                self.account.on_message(message)

            else:
                print('topic: {} is not known'.format(topic))
                print(message)

        except:
            print('TradingModel: No data received!')
            print(message)

        return None
