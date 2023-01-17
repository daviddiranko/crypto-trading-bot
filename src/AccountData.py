# !/usr/bin/env python
# coding: utf-8
import warnings

warnings.simplefilter(action='ignore', category=FutureWarning)
import pandas as pd
import json
from typing import Any, Dict, List
from dotenv import load_dotenv
import os
from pybit import usdt_perpetual
from .endpoints.bybit_functions import *
import time

load_dotenv()

PUBLIC_TOPICS = eval(os.getenv('PUBLIC_TOPICS'))
PRIVATE_TOPICS = eval(os.getenv('PRIVATE_TOPICS'))

BYBIT_TEST_ENDPOINT = os.getenv('BYBIT_TEST_ENDPOINT')
BYBIT_TEST_KEY = os.getenv('BYBIT_TEST_KEY')
BYBIT_TEST_SECRET = os.getenv('BYBIT_TEST_SECRET')


class AccountData:
    '''
    Class to provide the account interface. 
    It stores real time account data such as wallet balance or open trades.
    It provides a http api for trading
    '''

    # initialize account data object with current values
    def __init__(self, http_session: usdt_perpetual.HTTP, symbols: List[str]):
        '''
        Parameters
        ----------
        http_session: usdt_perpetual.HTTP
            open http connection for account data initialization and trading
        symbols: List[str]
            list of symbols to incorporate.
        Attributes
        ----------
        self.session: usdt_perpetual.HTTP
            open http connection for account data initialization and trading
        self.positions: Dict[str, Dict[str, any]]
            dict of current open positions, indexed by symbol
        self.executions = Dict[str, Dict[str, Dict[str, Any]]]
            Executions are organized in a 3 layer dict.
            The first layer is indexed by the symbol and holds all executions for that symbol
            These executions are organized in another dict, indexed by the order id
            This dictionary holds the third dictionary with the execution information
        self.orders = Dict[str, Dict[str, Dict[str, Any]]]
            Orders are organized in a 3 layer dict.
            The first layer is indexed by the symbol and holds all orders for that symbol
            These orders are organized in another dict, indexed by the order id
            This dictionary holds the third dictionary with the order information
        self.stop_orders = Dict[str, Dict[str, Dict[str, Any]]]
            Stop orders are organized in a 3 layer dict.
            The first layer is indexed by the symbol and holds all stop orders for that symbol
            These stop orders are organized in another dict, indexed by the order id
            This dictionary holds the third dictionary with the stop order information
        self.wallet = Dict[str, Dict[str, Any]]
            wallet data, indexed by symbol
            each symbol is indexed to another dict that holds balance, margin etc. for that symbol
        '''

        self.session = http_session

        # pull current account data
        account_data = None
        while account_data == None:
            try:
                account_data = initialize_account_data(session=self.session,
                                                       symbols=symbols)
            except:
                self.session = usdt_perpetual.HTTP(endpoint=BYBIT_TEST_ENDPOINT,
                                                   api_key=BYBIT_TEST_KEY,
                                                   api_secret=BYBIT_TEST_SECRET)
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
                    self.update_positions(msg=data)
                    return self.positions
                elif topic == PRIVATE_TOPICS[1]:
                    self.update_executions(msg=data)
                    return self.executions
                elif topic == PRIVATE_TOPICS[2]:
                    self.update_orders(msg=data)
                    return self.orders
                elif topic == PRIVATE_TOPICS[3]:
                    self.update_stop_orders(msg=data)
                    return self.stop_orders
                elif topic == PRIVATE_TOPICS[4]:
                    self.update_wallet(msg=data)
                    return self.wallet

            else:
                print('topic: {} is not known'.format(topic))
                print(message)
                return False

        except:
            print('AccountData: No data received!')
            print(message)
            return False

    def update_positions(
            self, msg: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        '''
        Update open positions.

        Parameters
        ----------
        msg: List[Dict[str, Any]]
            data from websocket message as list of positions to update
        
        Returns
        -------
        self.positions: Dict[str, Dict[str, any]]
            updated positions
        '''
        # iterate through list and update propagated positions
        for pos in msg:
            self.positions[pos['symbol']] = pos

        return self.positions

    def update_executions(
            self, msg: List[Dict[str,
                                 Any]]) -> Dict[str, Dict[str, Dict[str, Any]]]:
        '''
        Update executions.

        Parameters
        ----------
        msg: List[Dict[str, Any]]
            data from websocket message as list of new executions
        
        Returns
        -------
        self.executions: Dict[str, Dict[str, Dict[str, Any]]]
            updated executions
        '''
        # iterate through list and update propagated executions
        for exec in msg:
            self.executions[exec['symbol']][exec['order_id']] = exec

        return self.executions

    def update_orders(
            self, msg: List[Dict[str,
                                 Any]]) -> Dict[str, Dict[str, Dict[str, Any]]]:
        '''
        Update orders.

        Parameters
        ----------
        msg: List[Dict[str, Any]]
            data from websocket message as list of new orders
        
        Returns
        -------
        self.orders: Dict[str, Dict[str, Dict[str, Any]]]
            updated orders
        '''
        # iterate through list and update propagated orders
        for order in msg:
            self.orders[order['symbol']][order['order_id']] = order

        return self.orders

    def update_stop_orders(
            self, msg: List[Dict[str,
                                 Any]]) -> Dict[str, Dict[str, Dict[str, Any]]]:
        '''
        Update stop orders.

        Parameters
        ----------
        msg: List[Dict[str, Any]]
            data from websocket message as list of new stop orders
        
        Returns
        -------
        self.orders: Dict[str, Dict[str, Dict[str, Any]]]
            updated stop orders
        '''
        # iterate through list and update propagated stop orders
        for stop_order in msg:
            self.stop_orders[stop_order['symbol']][
                stop_order['stop_order_id']] = stop_order

        return self.stop_orders

    def update_wallet(self, msg: List[Dict[str,
                                           Any]]) -> Dict[str, Dict[str, Any]]:
        '''
        Update wallet.

        Parameters
        ----------
        msg: List[Dict[str, Any]]
            data from websocket message as list of wallet balances to update
        
        Returns
        -------
        self.wallet: Dict[str, Dict[str, any]]
            updated wallet
        '''
        # iterate through list and update propagated wallet balances
        for wallet in msg:

            # if no coin is propagated then it is USDT
            if 'coin' in wallet.keys():
                self.wallet[wallet['coin']] = wallet
            else:
                self.wallet['USDT'] = wallet

        return self.wallet

    def place_order(self,
                    symbol: str,
                    order_type: str,
                    side: str,
                    qty: int,
                    price: float = None,
                    stop_loss: float = None,
                    take_profit: float = None,
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
                "GoodTillCancelled": The order will remain valid until it is fully executed or manually cancelled by the trader.
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
            Use reduce_only = True if you want to close entire positions by setting a large quantity
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
        response = None
        counter = 0
        while response == None and counter < 2:
            try:
                response = place_order(session=self.session,
                                       symbol=symbol,
                                       order_type=order_type,
                                       side=side,
                                       qty=qty,
                                       price=price,
                                       stop_loss=stop_loss,
                                       take_profit=take_profit,
                                       time_in_force=time_in_force,
                                       sl_trigger_by=sl_trigger_by,
                                       tp_trigger_by=tp_trigger_by,
                                       order_link_id=order_link_id,
                                       reduce_only=reduce_only,
                                       close_on_trigger=close_on_trigger,
                                       position_idx=position_idx)
            except:
                time.sleep(5)
                self.session = usdt_perpetual.HTTP(endpoint=BYBIT_TEST_ENDPOINT,
                                                   api_key=BYBIT_TEST_KEY,
                                                   api_secret=BYBIT_TEST_SECRET)
                counter += 1
        return response

    def place_conditional_order(
            self,
            symbol: str,
            order_type: str,
            side: str,
            qty: int,
            price: float = None,
            base_price: float = None,
            stop_px: float = None,
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
        response = None
        counter = 0
        while response == None and counter < 2:
            try:
                response = place_conditional_order(
                    session=self.session,
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
            except:
                self.session = usdt_perpetual.HTTP(endpoint=BYBIT_TEST_ENDPOINT,
                                                   api_key=BYBIT_TEST_KEY,
                                                   api_secret=BYBIT_TEST_SECRET)
                time.sleep(5)
                counter += 1
        return response

    def set_stop_loss(self, symbol: str, side: str, stop_loss: float):
        '''
        Set stop loss of open position.

        Parameters
        ----------
        symbol: str
            symbol of position to set stop loss in
        side: str
            side of open position to set stop loss in
        stop_loss: float
            stop loss to set
        '''
        response = None
        counter = 0
        while response == None and counter < 2:
            try:
                response = self.session.set_trading_stop(symbol=symbol,
                                                         side=side,
                                                         stop_loss=stop_loss)
            except:
                self.session = usdt_perpetual.HTTP(endpoint=BYBIT_TEST_ENDPOINT,
                                                   api_key=BYBIT_TEST_KEY,
                                                   api_secret=BYBIT_TEST_SECRET)
                time.sleep(5)
                counter += 1
        return response

    def set_take_profit(self, symbol: str, side: str, take_profit: float):
        '''
        Set stop loss of open position.

        Parameters
        ----------
        symbol: str
            symbol of position to set stop loss in
        side: str
            side of open position to set stop loss in
        take_profit: float
            take profit to set
        '''
        response = None
        counter = 0
        while response == None and counter < 2:
            try:
                response = self.session.set_trading_stop(
                    symbol=symbol, side=side, take_profit=take_profit)
            except:
                self.session = usdt_perpetual.HTTP(endpoint=BYBIT_TEST_ENDPOINT,
                                                   api_key=BYBIT_TEST_KEY,
                                                   api_secret=BYBIT_TEST_SECRET)
                time.sleep(5)
                counter += 1
        return response
