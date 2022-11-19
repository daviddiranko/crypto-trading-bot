# !/usr/bin/env python
# coding: utf-8

import pandas as pd
from typing import Any, Dict, List
from dotenv import load_dotenv
import os
from binance.client import Client
from src.endpoints import binance_functions, bybit_functions
from src.AccountData import AccountData

load_dotenv()

PUBLIC_TOPICS = eval(os.getenv('PUBLIC_TOPICS'))
PRIVATE_TOPICS = eval(os.getenv('PRIVATE_TOPICS'))

PUBLIC_TOPIC_MAPPING = eval(os.getenv('PUBLIC_TOPIC_MAPPING'))

class BacktestAccountData(AccountData):
    '''
    Class to provide the account interface for backtesting. 
    It stores artificial account data such as wallet balance or open trades.
    '''

    # initialize account data object with current values
    def __init__(self,
                binance_client: Client,
                 symbols: List[str],
                 budget: float = 1000.0):
        '''
        Parameters
        ----------
        binance_client: binance.client.Client
            binance http client to pull historical prices to mock a backtesting order
        symbols: List[str]
            optional list of symbols to incorporate. If no list is provided, all available symbols are incorporated.
        budget: float
            start budget for all tickers

        Attributes
        ----------
        self.session: binance_client: binance.client.Client
            binance http client to pull historical prices to mock a backtesting order
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

        self.sesion = binance_client
        self.positions = {symbol: {"symbol": symbol,
            "size": 0.0,
            "side": "Buy",
            "position_value": 0.0,
            "take_profit": 0.0,
            "stop_loss": 0.0} for symbol in symbols}
        self.executions = {symbol: {} for symbol in symbols}
        self.orders = {symbol: {} for symbol in symbols}
        self.stop_orders = {symbol: {} for symbol in symbols}
        self.wallet = {symbol:{{
            "coin": symbol,
            "available_balance": budget,
            "wallet_balance": budget
        }} for symbol in symbols}

    def place_order(self,
                    symbol: str,
                    order_type: str,
                    side: str,
                    qty: int,
                    order_time: pd.Timestamp,
                    price: float = None,
                    stop_loss: float = None,
                    take_profit: float = None,
                    reduce_only: bool = False) -> Dict[str, Any]:
        '''
        Place a mock order for backtesting.
        by updating account data acco.

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
        order_time: pandas.Timestamp
            order time. Necessary to pull correct historical price
        price: float
            if order_type="Limit": limit price for the order
        stop_loss: float
            stop loss price of order
        take_profit: float
            stop price to take profits
        reduce_only: bool = False
            If true, the position can only reduce in size and no stop loss or profit taking is possible.
            Use reduce_only = True if you want to close entire positions by setting a large quantity

        Returns
        -------
        response: Dict[str, Any]
            response body from bybit
        '''
        # order time + 1 second
        order_time_1 = pd.Timestamp(order_time.value+1000000000)

        # pull historical kline
        kline = msg = self.session.get_historical_klines(symbol, start_str=str(order_time), end_str= str(order_time_1),interval='1m')

        # format klines and extract high and low
        quotes = binance_functions.format_historical_klines(msg)
        low = quotes.iloc[0]['low']
        high = quotes.iloc[0]['high']
        
        # determine execution price according to direction of the trade
        if order_type=='Market':
            trade_price = (side=='Buy')*high + (side=='Sell')*low
            
            # determine direction of trade buy=1, sell=-1
            sign = ((side=='Buy')-0.5)*2

            # determine direction of old positions
            pos_old_1 = self.positions[symbol[:3]]
            pos_old_2 = self.positions[symbol[3:]]

            sign_old_1 = ((pos_old_1['side']=='Buy')-0.5)*2
            sign_old_2 = ((pos_old_2['side']=='Buy')-0.5)*2

            # determine actually traded qty
            true_qty = (1-reduce_only)*qty+reduce_only*pos_old_1['size']
            # update positions
            self.update_positions([{
                "symbol": symbol[:3],
                "size": abs(sign_old_1*pos_old_1['size']+sign*true_qty),
                "side": ["Buy" if sign_old_1*pos_old_1['size']+sign*true_qty>0 else "Sell"][0],
                "position_value": abs(sign_old_1*pos_old_1['position_value']+sign*true_qty*trade_price),
                "take_profit": take_profit or pos_old_1['take_profit'],
                "stop_loss": stop_loss or pos_old_1['stop_loss']
                },{
                "symbol": symbol[3:],
                "size": abs(sign_old_2*pos_old_2['size']-sign*true_qty*trade_price),
                "side": ["Buy" if sign_old_2*pos_old_2['size']-sign*true_qty>0 else "Sell"][0],
                "position_value": abs(sign_old_2*pos_old_2['position_value']-sign*true_qty*trade_price),
                "take_profit": pos_old_2['take_profit'],
                "stop_loss": pos_old_2['stop_loss']
                }])
            
            old_wallet_1 = self.wallet[symbol[:3]]
            old_wallet_2 = self.wallet[symbol[3:]]
            
            # update wallets
            self.update_wallet([{
                "coin": symbol[:3],
                "available_balance": old_wallet_1["available_balnce"]+sign*true_qty,
                "wallet_balance": old_wallet_1["available_balnce"]+sign*true_qty
            }, {
                "coin": symbol[3:],
                "available_balance": old_wallet_2["available_balnce"]-sign*true_qty*trade_price-0.0001*true_qty*trade_price,
                "wallet_balance": old_wallet_2["available_balnce"]-sign*true_qty*trade_price-0.0001*true_qty*trade_price
            }])

            # update executions
            self.update_executions([{
                "symbol": symbol,
                "side": side,
                "order_id": len(self.executions["symbol"].keys())+1,
                "exec_id": len(self.executions["symbol"].keys())+1,
                "price": trade_price,
                "order_qty": true_qty,
                "exec_type": "Trade",
                "exec_qty": true_qty,
                "exec_fee": 0.0001*true_qty*trade_price,
                "trade_time": order_time
            }])
        
        # TODO send correct messages to update all account endpoints


        return None

    def new_market_data(self, topic: str, data: Dict[str, Any]) -> bool:
        '''
        If new candle is received update all orders, executions, positions and wallet.

        Parameters
        ----------
        topic: str
            public topic of data
        data: Dict[str, Any]
            new candle stick data
        '''

        # TODO 
        # check positions for stop loss and take profit -> close position and update orders, executions and wallet
        # check limit orders for triggers -> open position and update orders, executions and wallet
        # update positions and wallet according to close price -> update balances, margins, etc.

        # iterate through potential stop losses or take profits
        for pos in self.positions[PUBLIC_TOPIC_MAPPING[topic][:3]]:
            side =pos['side']
            symbol = PUBLIC_TOPIC_MAPPING[topic]

            if pos['stop_loss']>=data['low']:
                # determine direction of trade buy=1, sell=-1
                sign = ((side=='Buy')-0.5)*2
                trade_price = pos['stop_loss']
                # determine direction of old positions
                pos_old_1 = self.positions[symbol[:3]]
                pos_old_2 = self.positions[symbol[3:]]

                sign_old_1 = ((pos_old_1['side']=='Buy')-0.5)*2
                sign_old_2 = ((pos_old_2['side']=='Buy')-0.5)*2

                # determine actually traded qty
                true_qty = pos_old_1['size']
                # update positions
                self.update_positions([{
                    "symbol": symbol[:3],
                    "size": abs(sign_old_1*pos_old_1['size']+sign*true_qty),
                    "side": ["Buy" if sign_old_1*pos_old_1['size']+sign*true_qty>0 else "Sell"][0],
                    "position_value": abs(sign_old_1*pos_old_1['position_value']+sign*true_qty*trade_price),
                    "take_profit": None,
                    "stop_loss": None
                    },{
                    "symbol": symbol[3:],
                    "size": abs(sign_old_2*pos_old_2['size']-sign*true_qty*trade_price),
                    "side": ["Buy" if sign_old_2*pos_old_2['size']-sign*true_qty>0 else "Sell"][0],
                    "position_value": abs(sign_old_2*pos_old_2['position_value']-sign*true_qty*trade_price),
                    "take_profit": pos_old_2['take_profit'],
                    "stop_loss": pos_old_2['stop_loss']
                    }])
                
                old_wallet_1 = self.wallet[symbol[:3]]
                old_wallet_2 = self.wallet[symbol[3:]]
                
                # update wallets
                self.update_wallet([{
                    "coin": symbol[:3],
                    "available_balance": old_wallet_1["available_balnce"]+sign*true_qty,
                    "wallet_balance": old_wallet_1["available_balnce"]+sign*true_qty
                }, {
                    "coin": symbol[3:],
                    "available_balance": old_wallet_2["available_balnce"]-sign*true_qty*trade_price-0.0001*true_qty*trade_price,
                    "wallet_balance": old_wallet_2["available_balnce"]-sign*true_qty*trade_price-0.0001*true_qty*trade_price
                }])

                # update executions
                self.update_executions([{
                    "symbol": symbol,
                    "side": side,
                    "order_id": len(self.executions["symbol"].keys())+1,
                    "exec_id": len(self.executions["symbol"].keys())+1,
                    "price": trade_price,
                    "order_qty": true_qty,
                    "exec_type": "Trade",
                    "exec_qty": true_qty,
                    "exec_fee": 0.0001*true_qty*trade_price,
                    "trade_time": data['end']
                }])
            
            
        return True