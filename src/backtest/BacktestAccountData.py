# !/usr/bin/env python
# coding: utf-8

import pandas as pd
import json
from typing import Any, Dict, List
from dotenv import load_dotenv
import os
from binance.client import Client
from src.endpoints import binance_functions
from src.AccountData import AccountData
load_dotenv()

PUBLIC_TOPICS = eval(os.getenv('PUBLIC_TOPICS'))
PRIVATE_TOPICS = eval(os.getenv('PRIVATE_TOPICS'))


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
            "entry_price": 0.0,
            "liq_price": 0.0,
            "bust_price": 0.0,
            "leverage": 1,
            "order_margin": 0,
            "position_margin": 0.0} for symbol in symbols}
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
                    take_proft: float = None,
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
        prices = binance_functions.format_historical_klines(msg)
        low = prices.iloc[0]['low']
        high = prices.iloc[0]['high']
        
        # determine execution price according to direction of the trade
        if order_type=='Market':
            trade_price = (side=='Buy')*high + (side=='Sell')*low
        
        # TODO send correct messages to update all account endpoints


        return None

    def new_market_data(kline: Dict[str, Any]) -> bool:
        '''
        If new candle is received update all orders, executions, positions and wallet.

        Parameters
        ----------
        kline: Dict[str, Any]
            new candle stick data
        '''

        # TODO 
        # check positions for stop loss and take profit -> close position and update orders, executions and wallet
        # check limit orders for triggers -> open position and update orders, executions and wallet
        # update positions and wallet according to close price -> update balances, margins, etc.

        return True