# !/usr/bin/env python
# coding: utf-8

import pandas as pd
from typing import Any, Dict, List
from dotenv import load_dotenv
import os
from binance.client import Client
from src.endpoints import binance_functions
from src.AccountData import AccountData
import itertools

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
    def __init__(self, binance_client: Client, symbols: List[str],
                 budget: Dict[str, float]):
        '''
        Parameters
        ----------
        binance_client: binance.client.Client
            binance http client to pull historical prices to mock a backtesting order
        symbols: List[str]
            optional list of symbols to incorporate. If no list is provided, all available symbols are incorporated.
        budget: Dict[str, float]
            start budget for all tickers as dictionary with key = symbol, value= budget

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

        # build all possible tuples from symbols
        symbol_tuples = [
            list(s)[0] + list(s)[1]
            for s in list(itertools.product(symbols, repeat=2))
        ]

        self.session = binance_client
        self.positions = {
            symbol: {
                "symbol": symbol,
                "size": 0.0,
                "side": "Buy",
                "position_value": 0.0,
                "take_profit": 0.0,
                "stop_loss": 0.0
            } for symbol in symbol_tuples
        }
        self.executions = {symbol: {} for symbol in symbol_tuples}
        self.orders = {symbol: {} for symbol in symbol_tuples}
        self.stop_orders = {symbol: {} for symbol in symbol_tuples}
        self.wallet = {
            symbol: {
                "coin": symbol,
                "available_balance": budget[symbol],
                "wallet_balance": budget[symbol]
            } for symbol in symbols
        }

    def place_order(self,
                    symbol: str,
                    side: str,
                    qty: int,
                    order_time: pd.Timestamp,
                    order_type: str = 'Market',
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
        side: str
            which side to trade
            Options:
                "Buy"
                "Sell"
        qty: int
            number of contracts to trade
        order_time: pandas.Timestamp
            order time. Necessary to pull correct historical price
        order_type: str
            Type of order. Currently only market orders are supported.
        price: float
            if order_type="Limit": limit price for the order -> Currently not supported.
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
            response body for execution
        '''
        # order time + 1 minute
        order_time_1 = pd.Timestamp(order_time.value + 60000000000)

        # pull historical kline
        msg = self.session.get_historical_klines(symbol,
                                                 start_str=str(order_time),
                                                 end_str=str(order_time_1),
                                                 interval='1m')

        # format klines and extract high and low
        quotes = binance_functions.format_historical_klines(msg)
        low = quotes.iloc[0]['low']
        high = quotes.iloc[0]['high']

        if order_type == 'Market':

            # determine execution price according to direction of the trade
            trade_price = (side == 'Buy') * high + (side == 'Sell') * low

            # execute trade
            execution = self.execute(symbol=symbol,
                                     side=side,
                                     qty=qty,
                                     execution_time=order_time_1,
                                     trade_price=trade_price,
                                     stop_loss=stop_loss,
                                     take_profit=take_profit,
                                     reduce_only=reduce_only)

        return execution

    def execute(self,
                symbol: str,
                side: str,
                qty: int,
                execution_time: pd.Timestamp,
                trade_price: float,
                stop_loss: float,
                take_profit: float,
                reduce_only: bool = False) -> Dict[str, Any]:
        '''
        Execute mock order, profit taking or stop losses.
        Update positions, wallets and executions.

        Parameters
        ----------
        symbol: str
            trading pair
        side: str
            which side to trade
            Options:
                "Buy"
                "Sell"
        qty: int
            number of contracts to trade
        execution_time: pandas.Timestamp
            execution timestamp
        trade_price: float
            execution price
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
            response body for execution
        '''

        # determine sign of trade, buy=1, sell=-1
        sign = ((side == 'Buy') - 0.5) * 2

        # determine direction of old position
        pos = self.positions[symbol]

        sign_pos = ((pos['side'] == 'Buy') - 0.5) * 2

        # determine actually traded qty, since the reduce_only flag only reduces the trade
        true_qty = (1 - reduce_only) * qty + reduce_only * min(qty, pos['size'])

        # determine sides of new positions
        if sign_pos * pos['size'] + sign * true_qty > 0:
            side_pos = "Buy"
        else:
            side_pos = "Sell"

        # determine average position prize
        if pos['size'] != 0:
            pos_price = pos['position_value'] / pos['size']
        else:
            pos_price = trade_price

        # update positions
        self.update_positions([{
            "symbol":
                symbol,
            "size":
                abs(sign_pos * pos['size'] + sign * true_qty),
            "side":
                side_pos,
            "position_value":
                abs(sign_pos * pos['position_value'] +
                    sign * true_qty * pos_price),
            "take_profit":
                take_profit,
            "stop_loss":
                stop_loss
        }])

        wallet_1 = self.wallet[symbol[:3]]
        wallet_2 = self.wallet[symbol[3:]]

        # update wallets
        self.update_wallet([{
            "coin":
                symbol[:3],
            "available_balance":
                wallet_1["available_balance"] + sign * true_qty,
            "wallet_balance":
                wallet_1["available_balance"] + sign * true_qty
        }, {
            "coin":
                symbol[3:],
            "available_balance":
                wallet_2["available_balance"] - sign * true_qty * trade_price -
                0.0001 * true_qty * trade_price,
            "wallet_balance":
                wallet_2["available_balance"] - sign * true_qty * trade_price -
                0.0001 * true_qty * trade_price
        }])

        # update executions
        execution = {
            "symbol": symbol,
            "side": side,
            "order_id": len(self.executions[symbol].keys()) + 1,
            "exec_id": len(self.executions[symbol].keys()) + 1,
            "price": trade_price,
            "order_qty": true_qty,
            "exec_type": "Trade",
            "exec_qty": true_qty,
            "exec_fee": 0.0001 * true_qty * trade_price,
            "trade_time": execution_time
        }
        self.update_executions([execution])

        return execution

    def new_market_data(self, topic: str,
                        data: Dict[str, Any]) -> List[Dict[str, Any]]:
        '''
        If new candle is received update all orders, executions, positions and wallet.

        Parameters
        ----------
        topic: str
            public topic of data
        data: Dict[str, Any]
            new candle stick data
        
        Returns
        --------
        pos: Dict[str, Any]
            updated position of traded symbol
        '''

        # extract symbol from topic
        symbol = PUBLIC_TOPIC_MAPPING[topic]

        # determine direction of old position
        pos = self.positions[symbol]

        side = pos['side']

        # check if stop loss is triggered
        if pos['stop_loss']:
            stop_loss = (side == 'Buy') * pos['stop_loss'] > data['low'] or pos[
                'stop_loss'] < (side == 'Sell') * data['high']
        else:
            stop_loss = False

        # check if take profit is triggered
        if pos['take_profit']:
            take_profit = pos['take_profit'] < (side == 'Buy') * data[
                'high'] or (side == 'Sell') * pos['take_profit'] > data['low']
        else:
            take_profit = False

        if stop_loss or take_profit:

            # trade takes other side than pos
            if side == "Sell":
                side_new = "Buy"
            else:
                side_new = "Sell"

            # trade price is either stop loss or take profit, depending on which was triggered
            # or-clause is added for stability if stop loss or take profit is None
            trade_price = max(stop_loss * (pos['stop_loss'] or 0),
                              take_profit * (pos['take_profit'] or 0))

            # execute trade
            self.execute(symbol=symbol,
                         side=side_new,
                         qty=pos['size'],
                         execution_time=data['end'],
                         trade_price=trade_price,
                         stop_loss=None,
                         take_profit=None,
                         reduce_only=True)

            # determine direction of new position
            pos = self.positions[symbol]

        # update position value according to new close price
        pos['position_value'] = pos['size'] * data['close']

        return pos
