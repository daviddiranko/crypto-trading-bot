# !/usr/bin/env python
# coding: utf-8

import pandas as pd
import json
from dotenv import load_dotenv
import os
from typing import Any, Dict, List
from .MarketData import MarketData
from .AccountData import AccountData
from pybit import usdt_perpetual

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
                 model: Any,
                 http_session: usdt_perpetual.HTTP,
                 symbols: List[str] = None,
                 topics: List[str] = PUBLIC_TOPICS,
                 model_storage: Dict[str, Any] = {},
                 model_args: Dict[str, Any] = {}):
        '''
        Parameters
        ----------
        model: Any
            function that holds the trading logic
        http_session: usdt_perpetual.HTTP
            open http connection for account data initialization and trading
        symbols: List[str]
            optional list of symbols to incorporate into account data. If no list is provided, all available symbols are incorporated.
        topics: List[str]
            all topics to store in market data object
        model_storage: Dict[str, Any]
            additional storage so that the trading model can store results
        model_args: Dict[str, Any]
            optional additional parameters for the trading model
        '''

        # initialize attributes and instantiate market and account data objects
        self.market_data = MarketData(topics=topics)
        self.account = AccountData(http_session=http_session, symbols=symbols)
        self.model = model
        self.model_storage = model_storage
        self.model_args = model_args

    def on_message(self, message: json) -> bool:
        '''
        Upon reception of new websocket data, forward to either MarketData or AccountData object

        Parameters
        ----------
        msg: json
            message received from api, i.e. data to store
        '''
        # extract message
        msg = json.loads(message)

        if 'topic' in msg.keys():
            # extract topic
            topic = msg['topic']
            # if public topic, forward to market_data and trigger model
            if topic in PUBLIC_TOPICS:

                response = self.market_data.on_message(message)
                self.model(model=self)
                return response

            # if private topic, forward to account
            elif topic in PRIVATE_TOPICS:

                response = self.account.on_message(message)
                return response

            else:
                print('topic: {} is not known'.format(topic))
                print(message)
                return False

        else:
            # print('TradingModel.on_message: Could not process ws message: \n{}'.format(message))
            return False
