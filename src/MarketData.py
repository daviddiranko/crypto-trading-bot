# !/usr/bin/env python
# coding: utf-8

import pandas as pd
import json
from dotenv import load_dotenv
import os

load_dotenv()

PUBLIC_TOPICS = eval(os.getenv('PUBLIC_TOPICS'))
PRIVATE_TOPICS = eval(os.getenv('PRIVATE_TOPICS'))

HIST_TICKERS = eval(os.getenv('HIST_TICKERS'))

class MarketData:
    '''
    Class to provide real time market data
    '''
    
    # create new marketdata object with empty dataframe
    def __init__(self): 
        '''
        Attributes
        ----------
        self.history: pandas.DataFrame
            dataframe of minutely candlesticks, indexed by the close timestamp
        '''     
        self.history = pd.DataFrame()
        

    def on_message(self, message: json):
        '''
        Receive new market data
        dataframe is indexed by the end date of the candle.
        The last row is the current candle and gets updated until candle is full.

        Parameters
        ----------
        msg: pandas.DataFrame
            message received from api, i.e. data to store
        '''
        # extract message and its topic
        msg = json.loads(message)
        topic = msg['topic']

        # check if topic is in private topics
        if topic in PUBLIC_TOPICS:

            # extract candlestick data
            data = msg['data'][0]
            data['start'] = pd.to_datetime(data['start'],unit='s')
            data['end'] = pd.to_datetime(data['end'],unit='s')
            self.history.loc[data['end']] = data

        else:
            print('topic: {} is not known'.format(topic))
            print(message)
        
        return None
    
    def add_history(self, data: pd.DataFrame):
        '''
        add historical candlestick data
        provided dataframe must be indexed by the end date of the candle.
        '''
        self.history = pd.concat([data,self.history])
    
   