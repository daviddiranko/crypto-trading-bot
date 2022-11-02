# !/usr/bin/env python
# coding: utf-8

import pandas as pd
import json
from typing import Any, Dict
from dotenv import load_dotenv
import os
from pybit import usdt_perpetual
load_dotenv()

PUBLIC_TOPICS = eval(os.getenv('PUBLIC_TOPICS'))
PRIVATE_TOPICS = eval(os.getenv('PRIVATE_TOPICS'))


class AccountData:
    '''
    Class to provide the account interface. 
    It stores real time account data such as wallet balance or open trades.
    It provides a http api for trading
    '''
    
    # initialize empty account data object
    def __init__(self, http_session: usdt_perpetual.HTTP): 
        '''
        Attributes
        ----------
        self.session: usdt_perpetual.HTTP
            open http connection for trading
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

        self.session = http_session
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

         # extract message
        msg = json.loads(message)

        try:
            # extract topic
            topic = msg['topic']

            # check if topic is a private topic
            if topic in PRIVATE_TOPICS:
                
                # extract data of message
                data = msg['data']['result']

                # store data in correct attribute
                if topic==PRIVATE_TOPICS[0]:
                    self.positions = data
                elif topic==PRIVATE_TOPICS[1]:
                    self.executions = data
                elif topic==PRIVATE_TOPICS[2]:
                    self.orders = data
                elif topic==PRIVATE_TOPICS[3]:
                    self.wallet = data
                elif topic==PRIVATE_TOPICS[4]:
                    self.greeks = data
                else:
                    print('topic: {} is not known'.format(topic))
                    print(message)

            else:
                print('topic: {} is not known'.format(topic))
                print(message)

        except:
            print('AccountData: No data received!')
            print(message)

        return None
    

    def place_order(self, 
                    symbol: str,
                    order_type: str,
                    side: str,
                    qty: int,
                    price: float,
                    stop_loss: float,
                    take_proft: float,
                    time_in_force: str = "FillOrKill",
                    sl_trigger_by: str = "LastPrice",
                    tp_trigger_by: str = "LastPrice",
                    order_link_id: str= None,
                    reduce_only: bool = False,
                    close_on_trigger: bool = False,
                    position_idx: int = None):
        '''
        Place a regular active order.

        Parameters
        ----------
        symbol: str
            trading pair
        order_type: str
            Type of order.
            Options:
                "Limit"
                "Market"
        side: str
            which side to trade
            Options:
                "Buy"
                "Sell"
        qty: int
            number of contracts to trade
        price: float
            if order_type="Limit": limit price for the order
        stop_loss: float
            stop loss price of order
        take_profit: float
            stop price to take profits
        time_in_force: str = "FillOrKill"
            "Time in Force" strategy
            Options:
                "GooTillCancelled": The order will remain valid until it is fully executed or manually cancelled by the trader.
                "FillOrKill": The order must be immediately executed at the order price or better, otherwise, it will be completely cancelled and partially filled contracts will not be allowed.
                "ImmediateOrCancel": The order must be filled immediately at the order limit price or better. If the order cannot be filled immediately, the unfilled contracts will be cancelled.
        sl_trigger_by: str = "LastPrice"
            the type of reported price to use as market reference for the stop loss
            Options:
                "LastPrice": Last traded price
                "IndexPrice": ?
                "MarkPrice": Last market price
        tp_trigger_by: str = "LastPrice"
            the type of reported price to use as market reference for taking profits.
            Options:
                "LastPrice": Last traded price
                "IndexPrice": ?
                "MarkPrice": Last market price
        order_link_id: str = None
            Optional unique order id to identify order
        reduce_only: bool = False
            If true, the position can only reduce in size and no stop loss or profit taking is possible.
        close_on_trigger: bool = False
            This flag will enforce liquidiation of other positions if trigger is met and not enough margin is available.
            Only relevant for a closing orders. It can only reduce your position not increase it.
        position_idx: integer
            Position idx, used to identify positions in different position modes. Required if you are under One-Way Mode:
            0-One-Way Mode
            1-Buy side of both side mode
            2-Sell side of both side mode
        '''
        
        response = self.session.place_conditional_order(symbol=symbol,
                                                    order_type=order_type,
                                                    side=side,
                                                    qty=qty,
                                                    price=price,
                                                    stop_loss=stop_loss,
                                                    take_proft=take_proft,
                                                    time_in_force=time_in_force,
                                                    sl_trigger_by=sl_trigger_by,
                                                    tp_trigger_by=tp_trigger_by,
                                                    order_link_id=order_link_id,
                                                    reduce_only=reduce_only,
                                                    close_on_trigger=close_on_trigger,
                                                    position_idx=position_idx)
        return response

    
    def place_conditional_order(self, 
                                symbol: str,
                                order_type: str,
                                side: str,
                                qty: int,
                                price: float,
                                base_price: float,
                                stop_px: float,
                                time_in_force: str = "FillOrKill",
                                trigger_by: str = "LastPrice",
                                order_link_id: str= None,
                                reduce_only: bool = False,
                                close_on_trigger: bool = False):
        '''
        Place a conditional order.

        Parameters
        ----------
        symbol: str
            trading pair
        order_type: str
            Type of order.
            Options:
                "Limit"
                "Market"
        side: str
            which side to trade
            Options:
                "Buy"
                "Sell"
        qty: int
            number of contracts to trade
        price: float
            if order_type="Limit": limit price for the order
        base_price: float
            price that is compared to stop_px to determine the expected direction of the current conditional order.
            stop_px > max(market price, base_price) --> order is executed by rising market price
            stop_px < min(market price, base_price) --> order is executed by falling price
        stop_px: float
            stop price of order. Can be stop loss or take profit, based on direction of conditional order.
        time_in_force: str = "FillOrKill"
            "Time in Force" strategy
            Options:
                "GooTillCancelled": The order will remain valid until it is fully executed or manually cancelled by the trader.
                "FillOrKill": The order must be immediately executed at the order price or better, otherwise, it will be completely cancelled and partially filled contracts will not be allowed.
                "ImmediateOrCancel": The order must be filled immediately at the order limit price or better. If the order cannot be filled immediately, the unfilled contracts will be cancelled.
        trigger_by: str = "LastPrice"
            the type of reported price to use as market reference.
            Options:
                "LastPrice": Last traded price
                "IndexPrice": ?
                "MarkPrice": Last market price
        order_link_id: str = None
            Optional unique order id to identify order
        reduce_only: bool = False
            If true, the position can only reduce in size and no stop loss or profit taking is possible.
        close_on_trigger: bool = False
            This flag will enforce liquidiation of other positions if trigger is met and not enough margin is available.
            Only relevant for a closing orders. It can only reduce your position not increase it.
        '''
        
        response = self.session.place_conditional_order(symbol=symbol,
                                                    order_type=order_type,
                                                    side=side,
                                                    qty=qty,
                                                    price=price,
                                                    base_price=base_price,
                                                    stop_px=stop_px,
                                                    time_in_force=time_in_force,
                                                    trigger_by=trigger_by,
                                                    order_link_id=order_link_id,
                                                    reduce_only=reduce_only,
                                                    close_on_trigger=close_on_trigger)
        return response
    
   