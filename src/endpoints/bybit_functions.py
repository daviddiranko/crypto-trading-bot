import pandas as pd
from typing import List, Dict, Any
from pybit import usdt_perpetual
from dotenv import load_dotenv
import os
import itertools

load_dotenv()
PRIVATE_TOPICS = eval(os.getenv('PRIVATE_TOPICS'))


def format_klines(msg: Dict[str, Any]) -> Dict[str, Any]:
    '''
    Format candlestick data received by bybit websocket

    Parameters
    ----------
    msg: Dict[str, Any]
        extracted json payload

    Returns
    -------
    df: Dict[str, Any]
        formatted json payload
    '''

    # extract candlestick data
    data = msg['data'][0]
    data['start'] = pd.to_datetime(data['start'], unit='s')
    data['end'] = pd.to_datetime(data['end'], unit='s')
    data['open'] = float(data['open'])
    data['close'] = float(data['close'])
    data['high'] = float(data['high'])
    data['low'] = float(data['low'])
    data['volume'] = float(data['volume'])
    data['turnover'] = float(data['turnover'])

    return data


def initialize_account_data(
        session: usdt_perpetual.HTTP,
        symbols: List[str] = None) -> Dict[str, Dict[str, Any]]:
    '''
    Initialize account data by pulling current values from bybit via http request.

    Parameters
    ---------
    session: usdt_perpetual.HTTP
        active bybit http session
    symbols: List[str]
            optional list of symbols to incorporate. If no list is provided, all available symbols are incorporated.
    Returns
    -------
    account_data: Dict[str, Dict[str, Any]]
        received account data
        index of first dictionary is the endpoint, e.g. "wallet" and the value is the extracted data
    '''
    # initialize account data
    account_data = {topic: None for topic in PRIVATE_TOPICS}

    # pull current position data
    position = session.my_position()['result']

    # pull current wallet data
    wallet = session.get_wallet_balance()['result']

    # if symbol list is provided, restrict results to that list
    if symbols:
        # build all possible tuples from symbols
        symbol_tuples = [
            list(s)[0] + list(s)[1]
            for s in list(itertools.product(symbols, repeat=2))
        ]
        account_data['position'] = {
            pos['data']['symbol']: pos['data']
            for pos in position
            if pos['data']['symbol'] in symbol_tuples
        }
        account_data['wallet'] = {symbol: wallet[symbol] for symbol in symbols}
    else:
        account_data['position'] = {
            pos['data']['symbol']: pos['data'] for pos in position
        }
        account_data['wallet'] = wallet

    # pull current order, stop order and execution data for every symbol
    orders = {symbol: None for symbol in account_data['position'].keys()}
    stop_orders = {symbol: None for symbol in account_data['position'].keys()}
    executions = {symbol: None for symbol in account_data['position'].keys()}

    # organize orders, stop orders and executions in a 3 layer dict.
    # The first layer is indexed by the symbol and holds all orders or executions per symbol
    # These orders or executions are organized as dictionaries, indexed by the order id and hold another dictionary with the order information
    for symbol in orders.keys():
        order_list = session.query_active_order(symbol=symbol)['result']
        orders[symbol] = {
            order['order_id']: order
            for order in order_list
            if order['order_status'] not in
            ['Rejected', 'Cancelled', 'Deactivated', 'Filled'] and
            not order['stop_loss']
        }
        stop_orders[symbol] = {
            order['order_id']: order
            for order in order_list
            if order['order_status'] not in
            ['Rejected', 'Cancelled', 'Deactivated', 'Filled'] and
            order['stop_loss']
        }
        executions[symbol] = {
            order['order_id']: order
            for order in order_list
            if order['order_status'] == 'Filled'
        }

    account_data['execution'] = executions
    account_data['order'] = orders
    account_data['stop_order'] = stop_orders

    return account_data


def place_order(session: usdt_perpetual.HTTP,
                symbol: str,
                order_type: str,
                side: str,
                qty: int,
                price: float = None,
                stop_loss: float = None,
                take_proft: float = None,
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
    session: usdt_perpetual.HTTP
        active bybit http session
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

    response = session.place_active_order(symbol=symbol,
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


def place_conditional_order(session: usdt_perpetual.HTTP,
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
    session: usdt_perpetual.HTTP
        active bybit http session
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

    response = session.place_conditional_order(
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
