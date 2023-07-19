# !/usr/bin/env python
# coding: utf-8
import warnings

warnings.simplefilter(action='ignore', category=FutureWarning)
warnings.simplefilter(action='ignore', category=RuntimeWarning)

import pandas as pd
import json
from dotenv import load_dotenv
import os
from typing import List, Dict, Any
from src.endpoints.bybit_functions import format_klines
from src.MarketData import MarketData
from src.backtest.BacktestAccountData import BacktestAccountData
from binance.client import Client

load_dotenv()

PUBLIC_TOPICS = eval(os.getenv('PUBLIC_TOPICS'))
PRIVATE_TOPICS = eval(os.getenv('PRIVATE_TOPICS'))

PUBLIC_TOPICS_COLUMNS = eval(os.getenv('PUBLIC_TOPICS_COLUMNS'))
BACKTEST_SYMBOLS = eval(os.getenv('BACKTEST_SYMBOLS'))
BINANCE_BYBIT_MAPPING = eval(os.getenv('BINANCE_BYBIT_MAPPING'))

HIST_TICKERS = eval(os.getenv('HIST_TICKERS'))


class BacktestMarketData(MarketData):
    '''
    Class to provide historical market data for backtesting
    '''

    # create new backtesting marketdata object through inheritance from MarketData
    def __init__(self,
                 account: BacktestAccountData,
                 client: Client,
                 topics: List[str] = PUBLIC_TOPICS,
                 toppic_mapping: Dict[str, str] = BINANCE_BYBIT_MAPPING):
        '''
        Parameters
        ----------
        account: BacktestAccountData
            account data object to send new market data point to.
            Necessary to update real time account data endpoints like positions, open orders etc.
        client: binance.client.Client
            http session to pull historical data from
        topics: List[str]
            all topics to store
        toppic_mapping: Dict[str,str]
            mapping between bybit websocket topics and binance symbols.
            It is used to map simulated bybit websocket messages to account symbols for data updates, which are indexed by binance tickers.

        Attributes
        ----------

        self.history: Dict[str, pandas.DataFrame]
            dictionary that stores historical data.
            the dictionary is indexed by the topic and stores a dataframe of candlesticks, indexed by the close timestamp.   
        self.account: BacktestAccountData
            account data object to send new market data point to.
            Necessary to update real time account data endpoints like positions, open orders etc.
        self.simulation_data: pandas.DataFrame
            formatted binance candles for backtesting
        self.bybit_messages: List[Dict[str, Any]]
            formatted candles from self.simulation data that simulate bybit websocket messages
        '''

        super().__init__(client, topics)
        self.account = account
        self.binance_bybit_mapping = toppic_mapping

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

        if 'topic' in msg.keys():
            # extract topic
            topic = msg['topic']

            # check if topic is in private topics
            if topic in self.topics:

                # extract candlestick data
                data = format_klines(msg=msg)

                # add to history
                self.history[topic].loc[data['end']] = data

                # update timestamp of account
                self.account.timestamp = self.history[self.topics[0]].index[-1]

                # restrict history to last 1000 datapoints
                self.history[topic] = self.history[topic].iloc[-2000:]

                # if new market data is received (i.e. one minute candle), trigger account data update
                if topic == self.topics[0]:
                    self.account.new_market_data(
                        topic=self.binance_bybit_mapping[topic], data=data)

                return data
            else:
                # print('BacktestMarketData.on_message: topic: {} is not known \n{}'.format(topic, message))
                return False

        else:
            # print('BacktestMarketData.on_message: Could not process message:{}'.format(message))

            return False
