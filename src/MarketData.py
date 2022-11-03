# !/usr/bin/env python
# coding: utf-8

import pandas as pd
import json
from dotenv import load_dotenv
import os
from typing import List
from src.endpoints.bybit_functions import format_klines

load_dotenv()

PUBLIC_TOPICS = eval(os.getenv('PUBLIC_TOPICS'))
PRIVATE_TOPICS = eval(os.getenv('PRIVATE_TOPICS'))

HIST_TICKERS = eval(os.getenv('HIST_TICKERS'))


class MarketData:
    '''
    Class to provide real time market data
    '''

    # create new marketdata object with empty dataframe
    def __init__(self, topics: List[str]):
        '''
        Parameters
        ----------

        topics: List[str]
            all topics to store

        Attributes
        ----------

        self.history: Dict[str, pandas.DataFrame]
            dictionary that stores historical data.
            the dictionary is indexed by the topic and stores a dataframe of candlesticks, indexed by the close timestamp.
        '''

        # initialize history with empty dataframes
        self.history = {}

        for topic in topics:
            self.history[topic] = pd.DataFrame()

    def on_message(self, message: json):
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

        try:
            # extract topic
            topic = msg['topic']

            # check if topic is in private topics
            if topic in PUBLIC_TOPICS:

                # extract candlestick data
                data = format_klines(msg=msg['data'][0])

                # add to history
                self.history[topic].loc[data['end']] = data

                return data
            else:
                print('topic: {} is not known'.format(topic))
                print(message)
                return False

        except:
            print('MarketData: No data received!')
            print(message)

            return False

    def add_history(self, topic: str, data: pd.DataFrame):
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

        return self.history[topic]
