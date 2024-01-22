import warnings

warnings.simplefilter(action='ignore', category=FutureWarning)
import pandas as pd
from typing import List, Dict, Any, Tuple
from pybit import usdt_perpetual
from binance.helpers import date_to_milliseconds
from dotenv import load_dotenv
import os
import itertools

import time
from datetime import datetime
import src.endpoints.bybit_ws as bb
import yaml

load_dotenv()

BYBIT_TEST_KEY = os.getenv('BYBIT_TEST_KEY')
BYBIT_TEST_SECRET = os.getenv('BYBIT_TEST_SECRET')
CONFIG_DIR = os.getenv('CONFIG_DIR')

# Load variables from the YAML file
with open(CONFIG_DIR, 'r') as file:
    config = yaml.safe_load(file)

# Access variables from the loaded data
PRIVATE_TOPICS = config.get('private_topics')


def get_historical_klines(symbol: str,
                          interval: str,
                          start_str: str,
                          end_str: str = None) -> List[Dict[str, Any]]:
    '''Get Historical Klines from Bybit

    this code is based on get_historical_data() from python-binance module 
    https://github.com/sammchardy/python-binance
    it also requires pybybit.py available from this page 
    https://note.mu/mtkn1/n/n9ef3460e4085 
    (where pandas & websocket-client are needed) 

    See dateparse docs for valid start and end string formats http://dateparser.readthedocs.io/en/latest/
    If using offset strings for dates add "UTC" to date string e.g. "now UTC", "11 hours ago UTC"
    
    Parameter
    ----------
    symbol: str
        Name of symbol pair -- BTCUSD, ETCUSD, EOSUSD, XRPUSD 
    interval: str
        Bybit Kline interval -- 1 3 5 15 30 60 120 240 360 720 "D" "M" "W" "Y"
    start_str: str
        Start date string in UTC format
    end_str: str
        optional - end date string in UTC format
    
    Return
    --------
    output_data: List[Dict[str, Any]] list of OHLCV values
    '''

    # instantiate bybit object
    bybit = bb.Bybit(api_key=BYBIT_TEST_KEY,
                     secret=BYBIT_TEST_SECRET,
                     symbol=symbol,
                     test=True,
                     ws=False)

    # set parameters for kline()
    if interval[-1] == 'm':
        timeframe = str(interval[:-1])
    else:
        timeframe = str(interval)
    limit = 200
    # start_ts = int(date_to_milliseconds(start_str)/1000)
    start_ts = int(date_to_milliseconds(start_str))
    end_ts = None
    if end_str:
        # end_ts = int(date_to_milliseconds(end_str)/1000)
        end_ts = int(date_to_milliseconds(end_str))
    else:
        # end_ts = int(date_to_milliseconds('now')/1000)
        end_ts = int(date_to_milliseconds('now'))

    # init our list
    output_data = []

    # loop counter
    idx = 0
    # it can be difficult to know when a symbol was listed on Binance so allow start time to be before list date
    symbol_existed = False
    while True:
        # fetch the klines from start_ts up to max 200 entries
        temp_dict = bybit.kline(symbol=symbol,
                                interval=timeframe,
                                _start=start_ts,
                                _end=end_ts,
                                limit=limit)

        # temp_dict = bybit.kline(symbol=symbol, interval=timeframe, _from=start_ts, limit=limit)

        # handle the case where our start date is before the symbol pair listed on Binance
        if not symbol_existed and len(temp_dict):
            symbol_existed = True

        if symbol_existed:
            # extract data and convert to list
            # temp_data = [list(i.values())[2:] for i in temp_dict['result']]
            temp_data = temp_dict['result']['list']
            # temp_data.sort()

            # format temp_data to fit binance format
            # add 4 0s in the end
            list(map(lambda x: x.extend([0, 0, 0, 0]), temp_data))

            # insert end timestamp of candle
            list(
                map(
                    lambda x: x.insert(
                        6,
                        int(x[0]) + int(pd.Timedelta(interval).value / 1000000)
                    ), temp_data))

            # append this loops data to our output data
            output_data += temp_data

            # update our start timestamp using the last value in the array and add the interval timeframe
            # NOTE: current implementation ignores inteval of D/W/M/Y  for now
            # start_ts = temp_data[len(temp_data) - 1][0] + interval*60
            # start_ts = int(temp_data[len(temp_data) - 1][0]) + int(pd.Timedelta('1m').value/1000000)
            end_ts = int(temp_data[len(temp_data) - 1][0]) - int(
                pd.Timedelta('1m').value / 1000000)

        else:
            # it wasn't listed yet, increment our start date
            end_ts -= int(pd.Timedelta(interval).value / 1000000)

        idx += 1

        # check if we received less than the required limit and exit the loop
        if len(temp_data) < limit:
            # exit the while loop
            break

        # sleep after every 3rd call to be kind to the API
        if idx % 3 == 0:
            time.sleep(0.2)

    output_data.sort()

    return output_data


def get_historical_klines_pd(symbol: str,
                             interval: str,
                             start_str: str,
                             end_str: str = None) -> pd.DataFrame:
    '''Get Historical Klines from Bybit

    See dateparse docs for valid start and end string formats 
    http://dateparser.readthedocs.io/en/latest/
    If using offset strings for dates add "UTC" to date string 
    e.g. "now UTC", "11 hours ago UTC"

    Parameter
    ----------
    symbol: str
        Name of symbol pair -- BTCUSD, ETCUSD, EOSUSD, XRPUSD 
    interval: str
        Bybit Kline interval -- 1 3 5 15 30 60 120 240 360 720 "D" "M" "W" "Y"
    start_str: str
        Start date string in UTC format
    end_str: str
        optional - end date string in UTC format
    
    Return
    --------
    df: pandas.DataFrame
        formatted list of OHLCV values

    '''

    # instantiate bybit object
    bybit = bb.Bybit(api_key=BYBIT_TEST_KEY,
                     secret=BYBIT_TEST_SECRET,
                     symbol=symbol,
                     test=True,
                     ws=False)

    # set parameters for kline()
    if interval[-1] == 'm':
        timeframe = str(interval[:-1])
    else:
        timeframe = str(interval)
    limit = 200
    # start_ts = int(date_to_milliseconds(start_str)/1000)
    start_ts = int(date_to_milliseconds(start_str))
    end_ts = None
    if end_str:
        # end_ts = int(date_to_milliseconds(end_str)/1000)
        end_ts = int(date_to_milliseconds(end_str))
    else:
        # end_ts = int(date_to_milliseconds('now')/1000)
        end_ts = int(date_to_milliseconds('now'))

    # init our list
    output_data = []

    # loop counter
    idx = 0
    # it can be difficult to know when a symbol was listed on Binance so allow start time to be before list date
    symbol_existed = False
    while True:

        # fetch the klines from start_ts up to max 200 entries
        temp_dict = bybit.kline(symbol=symbol,
                                interval=timeframe,
                                _start=start_ts,
                                _end=end_ts,
                                limit=limit)
        # temp_dict = bybit.kline(symbol=symbol, interval=timeframe, _from=start_ts, limit=limit)

        # handle the case where our start date is before the symbol pair listed on Binance
        if not symbol_existed and len(temp_dict):
            symbol_existed = True

        if symbol_existed:
            # extract data and convert to list
            # temp_data = [list(i.values())[2:] for i in temp_dict['result']]
            temp_data = temp_dict['result']['list']

            # format temp_data to fit binance format
            # add 4 0s in the end
            list(map(lambda x: x.extend([0, 0, 0, 0]), temp_data))

            # insert end timestamp of candle
            list(
                map(
                    lambda x: x.insert(
                        6,
                        int(x[0]) + int(pd.Timedelta(interval).value / 1000000)
                    ), temp_data))

            # append this loops data to our output data
            output_data += temp_data

            # update our start timestamp using the last value in the array and add the interval timeframe
            # NOTE: current implementation ignores inteval of D/W/M/Y  for now
            # start_ts = temp_data[len(temp_data) - 1][0] + interval*60
            # start_ts = int(temp_data[len(temp_data) - 1][0]) + int(pd.Timedelta('1m').value/1000000)
            end_ts = int(temp_data[len(temp_data) - 1][0]) - int(
                pd.Timedelta('1m').value / 1000000)

        else:
            # it wasn't listed yet, increment our start date
            end_ts -= int(pd.Timedelta(interval).value / 1000000)

        idx += 1
        # check if we received less than the required limit and exit the loop
        if len(temp_data) < limit:
            # exit the while loop
            break

        # sleep after every 3rd call to be kind to the API
        if idx % 3 == 0:
            time.sleep(0.2)

    output_data.sort()

    # convert to data frame
    df = pd.DataFrame(
        output_data,
        columns=['start', 'open', 'high', 'low', 'close', 'volume', 'turnover'])
    df['Date'] = [
        datetime.fromtimestamp(i).strftime('%Y-%m-%d %H:%M:%S.%d')[:-3]
        for i in df['TimeStamp']
    ]

    return df


def format_klines(msg: Dict[str, Any]) -> Dict[str, Any]:
    '''
    Format candlestick data received by bybit websocket

    Parameters
    ----------
    msg: Dict[str, Any]
        extracted json payload

    Returns
    -------
    data: Dict[str, Any]
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
    data['confirm'] = bool(data['confirm'])

    return data


def create_simulation_data(symbols: Dict[str, str], start_str: str,
                           end_str: str) -> Tuple[List[List[Any]], List[str]]:
    '''
    Create simulation data.
    Pull all relevant candles from bybit and add them to a single list.
    for each list index, add the bybit topic in another list

    Parameters
    ----------
    symbols: Dict[str, str]
        dictionary of relevant symbols for backtesting
        symbols for backtesting
        keys have format binance_ticker.binacne_interval and values are coresponding bybit ws topics.
    start_str: str
        start of simulation in format yyyy-mm-dd hh-mm-ss
    end_str: str
        end of simulation in format yyyy-mm-dd hh-mm-ss

    Returns
    --------
    klines: List[List[Any]]
        list of raw klines
    
    topics: List[str]
        list of respective websocket topics
    '''
    klines = []
    topics = []
    for symbol in symbols:
        ticker, interval = symbol.split('.')

        # extend data by one interval to close trades in the last timestamp
        actual_end_str = str(pd.Timestamp(end_str) + pd.Timedelta(interval))

        bybit_data = get_historical_klines(ticker,
                                           start_str=start_str,
                                           end_str=actual_end_str,
                                           interval=interval)
        klines.extend(bybit_data)
        topics.extend([symbols[symbol]] * len(bybit_data))

    return klines, topics


def initialize_account_data(session: usdt_perpetual.HTTP,
                            symbols: List[str]) -> Dict[str, Dict[str, Any]]:
    '''
    Initialize account data by pulling current values from bybit via http request.

    Parameters
    ---------
    session: usdt_perpetual.HTTP
        active bybit http session
    symbols: List[str]
            list of symbols to incorporate.
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
                take_profit: float = None,
                time_in_force: str = "FillOrKill",
                sl_trigger_by: str = "LastPrice",
                tp_trigger_by: str = "LastPrice",
                order_link_id: str = None,
                reduce_only: bool = False,
                close_on_trigger: bool = False,
                position_idx: int = 0) -> Dict[str, Any]:
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
                                          take_profit=take_profit,
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


def set_stop_loss(session: usdt_perpetual.HTTP, symbol: str, side: str,
                  stop_loss: float):
    '''
    Set stop loss of open position.

    Parameters
    ----------
    session: usdt_perpetual.HTTP
        active bybit http session
    symbol: str
        symbol of position to set stop loss in
    side: str
        side of open position to set stop loss in
    stop_loss: float
        stop loss to set
    '''
    response = session.set_trading_stop(symbol=symbol,
                                        side=side,
                                        stop_loss=stop_loss)
    return response


def set_take_profit(session: usdt_perpetual.HTTP, symbol: str, side: str,
                    take_profit: float):
    '''
    Set stop loss of open position.

    Parameters
    ----------
    session: usdt_perpetual.HTTP
        active bybit http session
    symbol: str
        symbol of position to set stop loss in
    side: str
        side of open position to set stop loss in
    take_profit: float
        take profit to set
    '''
    response = session.set_trading_stop(symbol=symbol,
                                        side=side,
                                        take_profit=take_profit)
    return response
