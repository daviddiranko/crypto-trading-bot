import warnings

warnings.simplefilter(action='ignore', category=FutureWarning)
import pandas as pd
from typing import List, Dict, Any, Tuple
from trading_ig import IGService
import requests_cache
import json
from pybit import usdt_perpetual
from binance.helpers import date_to_milliseconds
from dotenv import load_dotenv
import os
import itertools

import time
from datetime import datetime
import src.endpoints.bybit_ws as bb

load_dotenv()

PRIVATE_TOPICS = eval(os.getenv('PRIVATE_TOPICS'))

IGM_USER = os.getenv('IGM_USER')
IGM_KEY = os.getenv('IGM_KEY')
IGM_PW = os.getenv('IGM_PW')
IGM_ACC_TYPE = os.getenv('IGM_ACC_TYPE')
IGM_ACC = os.getenv('IGM_ACC')
IGM_RES_MAPPING = eval(os.getenv('IGM_RES_MAPPING'))
BASE_CUR = os.getenv('BASE_CUR')
CONTRACT_CUR = os.getenv('CONTRACT_CUR')


def get_historical_klines(symbol: str,
                          interval: str,
                          start_str: str,
                          end_str: str = None) -> List[Dict[str, Any]]:
    '''Get Historical Klines from IGM

    Parameter
    ----------
    symbol: str
        Name of symbol pair -- BTCUSD, ETCUSD, EOSUSD, XRPUSD 
    interval: str
        Bybit Kline interval -- 1 2 3 5 "M"
    start_str: str
        Start date string in UTC format
    end_str: str
        optional - end date string in UTC format
    
    Return
    --------
    output_data: List[Dict[str, Any]] list of OHLCV values
    '''

    # instantiate igm session object
    ig_service = IGService(IGM_USER, IGM_PW, IGM_KEY, IGM_ACC_TYPE)
    ig_service.create_session()

    # start_ts = int(date_to_milliseconds(start_str))
    start_ts = pd.to_datetime(start_str)
    end_ts = None
    if end_str:
        # end_ts = int(date_to_milliseconds(end_str)/1000)
        end_ts = pd.to_datetime(end_str)
    else:
        # end_ts = int(date_to_milliseconds('now')/1000)
        end_ts = pd.to_datetime(date_to_milliseconds('now'))

    # fetch the klines from start_ts up to max 200 entries
    klines = ig_service.fetch_historical_prices_by_epic_and_date_range(
        symbol, IGM_RES_MAPPING[interval], start_ts, end_ts)

    # calculate prices as mean between bid and ask
    klines = klines['prices'][[
        'bid', 'ask'
    ]].transpose().groupby(level=1).mean().transpose()

    # format dataframe to list of dict
    keys = list(klines.columns)

    output_data = list(
        map(lambda x: {key: x[keys.index(key)] for key in keys},
            get_historical_klines.values))

    return output_data


def format_message(message: json) -> json:
    '''
    Format message from IG Markets Websocket Stream to fit the trading api.
    '''
    # msg = json.loads(message)
    msg = message

    if 'name' in msg.keys():
        topic = msg['name'][:6]

        if topic == "TRADE:":
            new_msg = format_trade_message(msg)
            return new_msg
        elif topic == "CHART:":
            # only forward full candles
            if msg['values']['CONS_END'] == '1':
                new_msg = format_kline_message(msg)
                return new_msg
        elif topic == "ACCOUN":
            new_msg = format_account_message(msg)
            return new_msg



def format_kline_message(msg: Dict[str, Any]) -> json:
    '''
    Format candlestick message from IG Markets Websocket Stream to fit the trading api.
    '''

    increment = msg['name'].split(':')[-1]
    epic = msg['name'].split(':')[1]
    time_increment = ''.join(list(map(lambda x: x if x.isnumeric() else '', increment)))
    topic = f'candle.{time_increment}.{epic}'
    new_msg = {
        'topic':
            topic,
        'data': [{
            'start':
                int(msg['values']['UTM']),
            'end':
                int(int(msg['values']['UTM']) +
                pd.Timedelta(increment).total_seconds()),
            'interval':
                ''.join(
                    list(map((lambda x: x if x.isdigit() else ''), increment))),
            'volume':
                int(msg['values']['TTV']) if msg['values']['TTV'] else 0,
            'turnover':
                0,
            'confirm':
                bool(msg['values']['CONS_END'] == '1'),
            'timestamp':
                int(msg['values']['UTM'])
        }]
    }

    for price in ['open', 'close', 'high', 'low']:
        new_msg['data'][0][price] = (
            float(msg['values']['BID_' + price.upper()]) +
            float(msg['values']['OFR_' + price.upper()])) / 2

    return json.dumps(new_msg)


def format_account_message(msg: Dict[str, Any]) -> json:
    '''
    Format account message from IG Markets Websocket Stream to fit the trading api.
    '''

    new_msg = {
        'topic': 'wallet',
        'data': {
            BASE_CUR: {
                'wallet_balance': msg['values']['EQUITY'],
                'available_balance': msg['values']['AVAILABLE_TO_DEAL'],
            }
        }
    }

    return json.dumps(new_msg)


def format_trade_message(msg: Dict[str, Any]) -> json:
    '''
    Format trade message from IG Markets Websocket Stream to fit the trading api.
    Receives single trade execution message.
    Returns triple of execution, position and order updates
    '''

    if 'CONFIRMS' in msg['values'].keys():
        if msg['values']['CONFIRMS']:
            exec = json.loads(msg['values']['CONFIRMS'])

            if not exec['dealStatus'] == 'ACCEPTED':
                return None

            execution = {'topic': 'execution'}
            execution['data'] = []
            execution['data'].append({})
            execution['data'][0]['symbol'] = exec['epic']
            execution['data'][0][
                'side'] = exec['direction'][0] + exec['direction'][1:].lower()
            execution['data'][0]['order_id'] = exec['dealId']
            execution['data'][0]['exec_id'] = exec['dealId']
            execution['data'][0]['order_link_id'] = exec['dealReference']
            execution['data'][0]['price'] = float(exec['level'])
            execution['data'][0]['order_qty'] = float(exec['size'])
            execution['data'][0]['exec_qty'] = float(exec['size'])
            execution['data'][0]['exec_fee'] = 0.0
            execution['data'][0]['leaves_qty'] = 0.0
            execution['data'][0]['trade_time'] = pd.to_datetime(
                exec['date']).value

            return json.dumps(execution)

    if 'OPU' in msg['values'].keys():
        if msg['values']['OPU']:

            pos = json.loads(msg['values']['OPU'])

            position = {'topic': 'position'}
            position['data'] = []
            position['data'].append({})
            position['data'][0]['symbol'] = pos['epic']
            position['data'][0][
                'side'] = pos['direction'][0] + pos['direction'][1:].lower()
            position['data'][0]['position_id'] = pos['dealId']
            position['data'][0]['position_value'] = float(pos['level']) * float(
                pos['size'])
            position['data'][0]['size'] = float(pos['size'])
            position['data'][0]['take_profit'] = float(
                pos['limitLevel']) if pos['limitLevel'] else None
            position['data'][0]['stop_loss'] = float(
                pos['stopLevel']) if pos['stopLevel'] else None
            position['data'][0]['position_idx'] = 0

            return json.dumps(position)

    if 'WOU' in msg['values'].keys():

        if msg['values']['WOU']:

            ord = json.loads(msg['values']['WOU'])

            order = {'topic': 'stop_order'}
            order['data'] = []
            order['data'].append({})

            order['data'][0]['symbol'] = ord['epic']
            order['data'][0][
                'side'] = ord['direction'][0] + ord['direction'][1:].lower()
            order['data'][0]['stop_order_id'] = ord['dealId']
            order['data'][0]['order_link_id'] = ord['dealReference']
            order['data'][0]['price'] = float(ord['level'])
            order['data'][0]['qty'] = float(ord['size'])
            order['data'][0]['stop_order_type'] = ord['orderType']
            order['data'][0]['order_type'] = ord['orderType']
            order['data'][0]['order_statzs'] = ord['status']
            order['data'][0]['stop_loss'] = float(
                ord['stopLevel']) if ord['stopLevel'] else None
            order['data'][0]['take_profit'] = float(
                ord['limitLevel']) if ord['limitLevel'] else None
            order['data'][0]['position_idx'] = 0
            order['data'][0]['reduce_only'] = True
            order['data'][0]['update_time'] = int(ord['timestamp'])
            order['data'][0]['time_in_force'] = ord['timeInForce']

            return json.dumps(order)

    return None

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

    # instantiate igm session object
    ig_service = IGService(IGM_USER, IGM_PW, IGM_KEY, IGM_ACC_TYPE)
    ig_service.create_session()

    start_ts = int(date_to_milliseconds(start_str))
    end_ts = None
    if end_str:
        # end_ts = int(date_to_milliseconds(end_str)/1000)
        end_ts = pd.to_datetime(end_str)
    else:
        # end_ts = int(date_to_milliseconds('now')/1000)
        end_ts = pd.to_datetime(date_to_milliseconds('now'))

    # fetch the klines from start_ts up to max 200 entries
    klines = ig_service.fetch_historical_prices_by_epic_and_date_range(
        symbol, IGM_RES_MAPPING(interval), start_ts, end_ts)

    # calculate prices as mean between bid and ask
    df = klines['prices'][['bid', 'ask'
                          ]].transpose().groupby(level=1).mean().transpose()

    return df


def format_klines(msg: Dict[str, Any]) -> Dict[str, Any]:
    '''
    Format candlestick data received by igm websocket

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
    data['start'] = pd.to_datetime(data['start'], unit='ms')
    data['end'] = pd.to_datetime(data['end'], unit='ms')
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


def initialize_account_data(
        session: IGService,
        symbols: List[str],
        account_id: str = IGM_ACC) -> Dict[str, Dict[str, Any]]:
    '''
    Initialize account data by pulling current values from igm via http request.

    Parameters
    ---------
    session: IGService
        active igm http session
    symbols: List[str]
            list of symbols to incorporate.
    account_id: str
        id of igm subaccount that is traded in
    Returns
    -------
    account_data: Dict[str, Dict[str, Any]]
        received account data
        index of first dictionary is the endpoint, e.g. "wallet" and the value is the extracted data
    '''
    # initialize account data
    account_data = {topic: None for topic in PRIVATE_TOPICS}

    # pull current position data
    position = session.fetch_open_positions()

    # pull current wallet data
    accounts = session.fetch_accounts()

    wallet = accounts.loc[accounts['accountId'] == account_id].iloc[0]

    # build all possible tuples from symbols
    # symbol_tuples = [
    #     list(s)[0] + list(s)[1]
    #     for s in list(itertools.product(symbols, repeat=2))
    # ]

    account_data['position'] = {}

    for index in position.index:
        if position.loc[index]['epic'] in symbols:

            account_data['position'][position.loc[index]['epic']] = json.loads(
                format_trade_message(msg={
                    'values': {
                        'OPU': json.dumps(position.loc[index].to_dict())
                    }
                }))['data'][0]

    account_data['wallet'] = {
        BASE_CUR: {
            'wallet_balance': wallet['balance'],
            'available_balance': wallet['available']
        }
    }

    # pull current order, stop order and execution data for every symbol
    orders = {symbol: None for symbol in account_data['position'].keys()}
    stop_orders = {symbol: None for symbol in account_data['position'].keys()}
    executions = {symbol: None for symbol in account_data['position'].keys()}

    # organize orders, stop orders and executions in a 3 layer dict.
    # The first layer is indexed by the symbol and holds all orders or executions per symbol
    # These orders or executions are organized as dictionaries, indexed by the order id and hold another dictionary with the order information
    all_orders = session.fetch_working_orders()
    for symbol in orders.keys():
        order_list = all_orders.loc[all_orders['epic'] == symbol]
        orders[symbol] = {
            order_list.loc[index]['dealId']: order_list.loc[index]
            for index in order_list.index
            if order_list.loc[index]['marketStatus'] not in ['REJECTED'] and
            not order_list.loc[index]['stopDistance']
        }
        stop_orders[symbol] = {
            order_list.loc[index]['dealId']: order_list.loc[index]
            for index in order_list.index
            if order_list.loc[index]['marketStatus'] not in ['REJECTED'] and
            order_list.loc[index]['stopDistance']
        }
        executions[symbol] = {
            order_list.loc[index]['dealId']: order_list.loc[index]
            for index in order_list.index
            if order_list.loc[index]['marketStatus'] == 'ACCEPTED'
        }

    account_data['execution'] = executions
    account_data['order'] = orders
    account_data['stop_order'] = stop_orders

    return account_data


def place_order(session: IGService,
                symbol: str,
                order_type: str,
                side: str,
                qty: int,
                price: float = None,
                stop_loss: float = None,
                stop_distance: float = None,
                take_profit: float = None,
                limit_distance: float = None,
                currency_code: str = CONTRACT_CUR,
                time_in_force: str = "FillOrKill",
                sl_trigger_by: str = "LastPrice",
                tp_trigger_by: str = "LastPrice",
                order_link_id: str = None,
                guaranteed_stop: bool = False,
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
    stop_distance: float
        distance between price and stop loss
    take_profit: float
        stop price to take profits
    limit_distance: float
        distance between price and take profit
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

    if not reduce_only:
        response = session.create_open_position(currency_code=currency_code,
                                                direction=side,
                                                order_type=order_type,
                                                epic=symbol,
                                                expiry='JUN-23',
                                                force_open=True,
                                                size=qty,
                                                stop_distance=stop_distance,
                                                guaranteed_stop=guaranteed_stop,
                                                level=price,
                                                limit_distance=limit_distance,
                                                limit_level=take_profit,
                                                quote_id=order_link_id,
                                                stop_level=stop_loss,
                                                trailing_stop=None,
                                                trailing_stop_increment=None)
    else:
        response = session.close_open_position(direction=side,
                                               epic=symbol,
                                               expiry='JUN-23',
                                               order_type=order_type,
                                               size=qty,
                                               deal_id=order_link_id,
                                               level=price,
                                               quote_id=order_link_id)
    return response


def set_stop_loss(session: IGService,
                  position_id: str,
                  stop_loss: float,
                  symbol: str = None,
                  side: str = None):
    '''
    Set stop loss of open position.

    Parameters
    ----------
    session: IGService
        active ig markets http session
    position_id: str
        ig markets deal id linked to the position
    stop_loss: float
        stop loss to set
    symbol: str
        symbol of position to set stop loss in (NOT USED)
    side: str
        side of open position to set stop loss in (NOT USED)
    '''

    limit_level = session.fetch_open_position_by_deal_id(
        deal_id=position_id)['position']['limitLevel']
    response = session.update_open_position(limit_level=limit_level,
                                            stop_level=stop_loss,
                                            deal_id=position_id)

    return response


def set_take_profit(session: IGService,
                    position_id: str,
                    take_profit: float,
                    symbol: str = None,
                    side: str = None):
    '''
    Set take profit of open position.

    Parameters
    ----------
    session: IGService
        active ig markets http session
    position_id: str
        ig markets deal id linked to the position
    take_profit: float
        take profit to set
    symbol: str
        symbol of position to set stop loss in (NOT USED)
    side: str
        side of open position to set stop loss in (NOT USED)
    '''

    stop_level = session.fetch_open_position_by_deal_id(
        deal_id=position_id)['position']['stopLevel']
    response = session.update_open_position(limit_level=take_profit,
                                            stop_level=stop_level,
                                            deal_id=position_id)

    return response
