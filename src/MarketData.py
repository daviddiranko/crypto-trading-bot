# !/usr/bin/env python
# coding: utf-8

import pandas as pd
import json

class MarketData:
    '''
    Class to provide real time market data
    '''
    
    # create new marketdata object with empty dataframe
    def __init__(self): 
        '''
        Parameters
        ----------

        '''     
        self.history = pd.DataFrame()
        

    def on_message(self, message: json):
        '''
        Add new candlestick data
        dataframe is indexed by the end date of the candle.
        The last row is the current candle and gets updated until candle is full.

        Parameters
        ----------
        msg: pandas.DataFrame
            message received from api, i.e. data to store
        '''

        kline = json.loads(message)

        try:
            if kline['data']:
                kline['data'][0]['start'] = pd.to_datetime(kline['data'][0]['start'],unit='s')
                kline['data'][0]['end'] = pd.to_datetime(kline['data'][0]['end'],unit='s')
                self.history.loc[kline['data'][0]['end']]=kline['data'][0]
        except:
            print('Message was not candlestick data')
            print(message)
        
        return None
    
    def add_history(self, data: pd.DataFrame):
        '''
        add historical candlestick data
        provided dataframe must be indexed by the end date of the candle.
        '''
        self.history = pd.concat([data,self.history])
    
   