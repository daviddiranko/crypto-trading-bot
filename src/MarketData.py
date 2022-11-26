# !/usr/bin/env python
# coding: utf-8

import pandas as pd
import json
from dotenv import load_dotenv
import os
from typing import List, Dict, Any
from src.endpoints.bybit_functions import format_klines
from binance.client import Client
from src.endpoints.binance_functions import format_historical_klines

load_dotenv()

PUBLIC_TOPICS = eval(os.getenv('PUBLIC_TOPICS'))
PRIVATE_TOPICS = eval(os.getenv('PRIVATE_TOPICS'))

PUBLIC_TOPICS_COLUMNS = eval(os.getenv('PUBLIC_TOPICS_COLUMNS'))

HIST_TICKERS = eval(os.getenv('HIST_TICKERS'))


class MarketData:
    '''
    Class to provide real time market data
    '''

    # create new marketdata object with empty dataframe
    def __init__(self, client: Client, topics: List[str] = PUBLIC_TOPICS):
        '''
        Parameters
        ----------
        client: binance.client.Client
            http session to pull historical data from
        topics: List[str]
            all topics to store

        Attributes
        ----------

        self.history: Dict[str, pandas.DataFrame]
            dictionary that stores historical data.
            the dictionary is indexed by the topic and stores a dataframe of candlesticks, indexed by the close timestamp.
        '''

        # initialize history with empty dataframes and add client
        self.history = {}
        self.client = client

        for topic in topics:
            self.history[topic] = pd.DataFrame(columns=PUBLIC_TOPICS_COLUMNS)

    def on_message(self, message: json) -> Dict[str, Any]:
        '''
        Receive new market data and store the data in the appropriate history, indexed by the topic.
        The last row is the current candle and gets updated until candle is full.

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
            if topic in PUBLIC_TOPICS:

                # extract candlestick data
                data = format_klines(msg=msg)

                # add to history
                self.history[topic].loc[data['end']] = data

                return data
            else:
                # print('MarketData.on_message: topic: {} is not known\n{}'.format(topic,message))
                return False

        else:
            # print('MarketData.on_message: Could not process ws message:\n{}'.format(message))
            return False

    def add_history(self, topic: str, data: pd.DataFrame) -> pd.DataFrame:
        '''
        add historical candlestick data
        provided dataframe must be indexed by the end date of the candle.

        Parameters
        ----------

        topic: str
            topic for which to add data
        data: pandas.DataFrame
            the data to add
        
        Return
        ---------
        self.history[topic]: pd.DataFrame
            entire history of topic
        '''
        self.history[topic] = pd.concat([data, self.history[topic]])

        # self.history[topic] = self.history[topic].sort_index()

        return self.history[topic]

    def build_history(self, symbols: Dict[str, str], start_str: str,
                      end_str: str) -> Dict[str, pd.DataFrame]:
        '''
        Build market data history for trading model.

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
        self.history: Dict[str, pandas.DataFrame]
            market data history
        '''
        for symbol in symbols.keys():
            # load history as list of lists from binance
            ticker, interval = symbol.split('.')
            msg = self.client.get_historical_klines(symbol=ticker,
                                                    start_str=start_str,
                                                    end_str=end_str,
                                                    interval=interval)

            # format payload to dataframe
            klines = format_historical_klines(msg)

            self.add_history(topic=symbols[symbol], data=klines)
        return self.history
