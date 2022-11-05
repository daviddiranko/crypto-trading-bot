# !/usr/bin/env python
# coding: utf-8

import pandas as pd
import json
from typing import Any, Dict
from dotenv import load_dotenv
import os
from pybit import usdt_perpetual
from .endpoints.bybit_functions import *

load_dotenv()

PUBLIC_TOPICS = eval(os.getenv('PUBLIC_TOPICS'))
PRIVATE_TOPICS = eval(os.getenv('PRIVATE_TOPICS'))


class AccountData:
    '''
    Class to provide the account interface. 
    It stores real time account data such as wallet balance or open trades.
    It provides a http api for trading
    '''

    # initialize account data object with current values
    def __init__(self, http_session: usdt_perpetual.HTTP, symbols: List[str] = None):
        '''
        Parameters
        ----------
        http_session: usdt_perpetual.HTTP
            open http connection for account data initialization and trading
        symbols: List[str]
            optional list of symbols to incorporate. If no list is provided, all available symbols are incorporated.
        Attributes
        ----------
        self.session: usdt_perpetual.HTTP
            open http connection for account data initialization and trading
        self.positions: Dict[str, Dict[str, any]]
            dict of current open positions, indexed by symbol
        self.executions = Dict[str, Dict[str, any]]
            dict of executed orders, i.e. trading history, indexed by execution id
        self.orders = Dict[str, Dict[str, any]]
            dict of unfilled orders, indexed by order id
        self.stop_orders = Dict[str, Dict[str, any]]
            dict of unfilled stop orders, indexed by stop order id
        self.wallet = Dict[str, Dict[str, Any]]
            wallet data, indexed by symbol
            each symbol is indexed to another dict that holds balance, margin etc. for that symbol
        '''

        self.session = http_session

        # pull current account data
        account_data = initialize_account_data(session=self.session, symbols=symbols)
        self.positions = account_data['position']
        self.executions = account_data['execution']
        self.orders = account_data['order']
        self.stop_orders = account_data['stop_order']
        self.wallet = account_data['wallet']

    def on_message(self, message: json) -> Dict[str, Any]:
        '''
        Receive account data message and store in appropriate attributes

        Parameters
        ----------
        msg: json
            message received from api, i.e. data to store
        
        Returns
        ---------
        self.[msg['topic]]: Dict[str, Any]
            extracted data from message
        '''

        # extract message
        msg = json.loads(message)

        try:
            # extract topic
            topic = msg['topic']

            # check if topic is a private topic
            if topic in PRIVATE_TOPICS:

                # extract data of message
                data = msg['data']

                # store data in correct attribute
                if topic == PRIVATE_TOPICS[0]:
                    self.positions = {pos['symbol']: pos for pos in data}
                    return self.positions
                elif topic == PRIVATE_TOPICS[1]:
                    self.executions = {exe['exec_id']: exe for exe in data}
                    return self.executions
                elif topic == PRIVATE_TOPICS[2]:
                    self.orders = {order['order_id']: order for order in data}
                    return self.orders
                elif topic == PRIVATE_TOPICS[3]:
                    self.stop_orders = {
                        stop_order['stop_order_id']: stop_order
                        for stop_order in data
                    }
                    return self.stop_orders
                elif topic == PRIVATE_TOPICS[4]:
                    self.wallet = data[0]
                    return self.wallet

            else:
                print('topic: {} is not known'.format(topic))
                print(message)
                return False

        except:
            print('AccountData: No data received!')
            print(message)
            return False

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
                    order_link_id: str = None,
                    reduce_only: bool = False,
                    close_on_trigger: bool = False,
                    position_idx: int = None) -> Dict[str, Any]:
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

        Returns
        -------
        response: Dict[str, Any]
            response body from bybit
        '''

        response = place_conditional_order(session=self.session,
            symbol=symbol,
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

    def place_conditional_order(
            self,
            symbol: str,
            order_type: str,
            side: str,
            qty: int,
            price: float,
            base_price: float,
            stop_px: float,
            time_in_force: str = "FillOrKill",
            trigger_by: str = "LastPrice",
            order_link_id: str = None,
            reduce_only: bool = False,
            close_on_trigger: bool = False) -> Dict[str, Any]:
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

        Returns
        -------
        response: Dict[str, Any]
            response body from bybit
        '''

        response = place_conditional_order(session=self.session,
            symbol=symbol,
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
        