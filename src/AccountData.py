# !/usr/bin/env python
# coding: utf-8

import pandas as pd
import json
from typing import Any, Dict
from dotenv import load_dotenv
import os

load_dotenv()

PUBLIC_TOPICS = eval(os.getenv('PUBLIC_TOPICS'))
PRIVATE_TOPICS = eval(os.getenv('PRIVATE_TOPICS'))


class AccountData:
    '''
    Class to provide account data such as wallet balance or open trades
    '''
    
    # initialize empty account data object
    def __init__(self): 
        '''
        Attributes
        ----------

        self.positions: List[Dict[str, any]]
            list of current open positions
        self.executions = List[Dict[str, any]]
            list of executed orders, i.e. trading history
        self.orders = List[Dict[str, any]]
            list of unfilled orders
        self.wallet = Dict[str, any]
            wallet data, such as balance, margin etc.
        self.greeks = List[Dict[str, any]]
            greeks of traded coins
        '''

        self.positions=[]
        self.executions = []
        self.orders = []
        self.wallet = {}
        self.greeks = []
        

    def on_message(self, message:json):
        '''
        Receive account data message and store in appropriate attributes

        Parameters
        ----------
        msg: json
            message received from api, i.e. data to store
        '''

        # extract message and its topic
        msg = json.loads(message)
        topic = msg['topic']

        # check if topic is a private topic
        if topic in PRIVATE_TOPICS:
            
            # extract data of message
            data = msg['data']['result']

            # store data in correct attribute
            if topic=="user.position.unifiedAccount":
                self.positions = data
            elif topic=="user.execution.unifiedAccount":
                self.executions = data
            elif topic=="user.order.unifiedAccount":
                self.orders = data
            elif topic=="user.wallet.unifiedAccount":
                self.wallet = data
            elif topic=="user.greeks.unifiedAccount":
                self.greeks = data
            else:
                print('topic: {} is not known'.format(topic))
                print(message)

        else:
            print('topic: {} is not known'.format(topic))
            print(message)
        
        return None
    
   