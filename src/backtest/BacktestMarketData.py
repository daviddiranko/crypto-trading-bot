# !/usr/bin/env python
# coding: utf-8

import pandas as pd
import json
from dotenv import load_dotenv
import os
from typing import List, Dict, Any
from src.endpoints.bybit_functions import format_klines
from src.MarketData import MarketData
from src.backtest.BacktestAccountData import BacktestAccountData

load_dotenv()

PUBLIC_TOPICS = eval(os.getenv('PUBLIC_TOPICS'))
PRIVATE_TOPICS = eval(os.getenv('PRIVATE_TOPICS'))

PUBLIC_TOPICS_COLUMNS = eval(os.getenv('PUBLIC_TOPICS_COLUMNS'))

HIST_TICKERS = eval(os.getenv('HIST_TICKERS'))


class BacktestMarketData(MarketData):
    '''
    Class to provide historical market data for backtesting
    '''

    # create new backtesting marketdata object through inheritance from MarketData
    def __init__(self, account: BacktestAccountData, topics: List[str] = PUBLIC_TOPICS):
        '''
        Parameters
        ----------
        account: BacktestAccountData
            account data object to send new market data point to.
            Necessary to update real time account data endpoints like positions, open orders etc.
        topics: List[str]
            all topics to store

        Attributes
        ----------

        self.history: Dict[str, pandas.DataFrame]
            dictionary that stores historical data.
            the dictionary is indexed by the topic and stores a dataframe of candlesticks, indexed by the close timestamp.
        
        self.account: BacktestAccountData
            account data object to send new market data point to.
            Necessary to update real time account data endpoints like positions, open orders etc.
        '''

        super().__init__(self, topics)
        self.account = account

    def on_message(self, message: json) -> Dict[str, Any]:
        '''
        Receive new market data and store the data in the appropriate history, indexed by the topic.
        The last row is the current candle and gets updated until candle is full.
        Additionally trigger new_market_data function of account to update real time account data endpoints.

        Parameters
        ----------
        msg: json
            message received from api, i.e. data to store

        Returns
        ----------
        data: Dict[str, Any]
            extracted data
        '''
        # extract message
        msg = json.loads(message)

        try:
            # extract topic
            topic = msg['topic']

            # check if topic is in private topics
            if topic in PUBLIC_TOPICS:

                # extract candlestick data
                data = format_klines(msg=msg)

                # add to history
                self.history[topic].loc[data['end']] = data

                # trigger account data update
                self.account.new_market_data(data)

                return data
            else:
                print('topic: {} is not known'.format(topic))
                print(message)
                return False

        except:
            print('MarketData: No data received!')
            print(message)

            return False
