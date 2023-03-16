# !/usr/bin/env python
# coding: utf-8

import warnings

warnings.simplefilter(action='ignore', category=FutureWarning)
import pandas as pd
from typing import Any, Dict, List
from src.AccountData import AccountData
import itertools

from dotenv import load_dotenv
import os

load_dotenv()

BASE_CUR = os.getenv('BASE_CUR')

class BacktestAccountData(AccountData):
    '''
    Class to provide the account interface for backtesting. 
    It stores artificial account data such as wallet balance or open trades.
    '''

    # initialize account data object with current values
    def __init__(self, symbols: List[str], budget: Dict[str, float]):
        '''
        Parameters
        ----------
        symbols: List[str]
            list of symbols to incorporate.
        budget: Dict[str, float]
            start budget for all tickers as dictionary with key = symbol, value= budget

        Attributes
        ----------
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
        self.timestamp = pandas.Timestamp
            current timestamp in backtesting simulation
        self.simulation_data: pandas.DataFrame
            simulation data for backtesting, used in account for trade pricing.
        '''

        # build all possible tuples from symbols
        symbol_tuples = [
            list(s)[0] + list(s)[1]
            for s in list(itertools.product(symbols, repeat=2))
        ]
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
        self.timestamp = None

        # initialize empty simulation data
        # formatted dataframe of binance candles
        self.simulation_data = None

    def place_order(self,
                    symbol: str,
                    side: str,
                    qty: int,
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
        # order_time_1 = pd.Timestamp(self.timestamp.value + 60000000000)

        # get next available timestamp
        short_term_history_index = self.simulation_data.loc[self.simulation_data.index.get_level_values(1)=='candle.1.{}'.format(symbol)].index
        exec_time_index = short_term_history_index[short_term_history_index.get_level_values(0)>self.timestamp][0]
        
        # get quotes from simulation data
        # quotes = self.simulation_data.loc[(order_time_1,
        #                                    'candle.1.{}'.format(symbol))]
        quotes = self.simulation_data.loc[exec_time_index]

        execution_time = quotes['start']
        price_sell = quotes['open']
        price_buy = quotes['open']

        if order_type == 'Market':

            # determine execution price according to direction of the trade
            trade_price = (side == 'Buy') * price_buy + (side
                                                         == 'Sell') * price_sell

            # execute trade
            execution = self.execute(symbol=symbol,
                                     side=side,
                                     qty=qty,
                                     execution_time=execution_time,
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

        # determine average position prize and determine if trade is openede or closed
        if pos['size'] != 0:
            pos_price = pos['position_value'] / pos['size']

            # if traded qty is equal to position qty, but in different direction, the trade was closed
            if (sign_pos != sign) and true_qty == pos['size']:
                open = False
            else:
                open = True
        else:
            pos_price = trade_price
            open = True

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

        wallet_1 = self.wallet[symbol[:-len(BASE_CUR)]]
        wallet_2 = self.wallet[symbol[-len(BASE_CUR):]]

        # update wallets
        self.update_wallet([{
            "coin":
                symbol[:-len(BASE_CUR)],
            "available_balance":
                wallet_1["available_balance"] + sign * true_qty,
            "wallet_balance":
                wallet_1["available_balance"] + sign * true_qty
        }, {
            "coin":
                symbol[-len(BASE_CUR):],
            "available_balance":
                wallet_2["available_balance"] - sign * true_qty * trade_price -
                1.37,
            #     0.0006 * true_qty * trade_price,
            "wallet_balance":
                wallet_2["available_balance"] - sign * true_qty * trade_price -
                1.37, 
            #    0.0006 * true_qty * trade_price
        }])

        # update executions
        execution = {
            "symbol": symbol,
            "side": side,
            "open": open,
            "order_id": len(self.executions[symbol].keys()) + 1,
            "exec_id": len(self.executions[symbol].keys()) + 1,
            "price": trade_price,
            "order_qty": true_qty,
            "exec_type": "Trade",
            "exec_qty": true_qty,
            # "exec_fee": 0.0006 * true_qty * trade_price,
            "exec_fee": 1.37,
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

        # determine direction of old position
        pos = self.positions[topic]

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
            self.execute(symbol=topic,
                         side=side_new,
                         qty=pos['size'],
                         execution_time=data['end'],
                         trade_price=trade_price,
                         stop_loss=None,
                         take_profit=None,
                         reduce_only=True)

            # determine direction of new position
            pos = self.positions[topic]

        # update position value according to new close price
        pos['position_value'] = pos['size'] * data['close']

        return pos

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
        self.positions[symbol]['stop_loss'] = stop_loss
        return self.positions[symbol]

    def set_take_profit(self, symbol: str, side: str, take_profit: float):
        '''
        Set take profit of open position.

        Parameters
        ----------
        symbol: str
            symbol of position to set take profit in
        side: str
            side of open position to set take profit in
        take_profit: float
            take profit to set
        '''
        self.positions[symbol]['take_profit'] = take_profit
        return self.positions[symbol]
