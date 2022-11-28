# !/usr/bin/env python
# coding: utf-8
import warnings

warnings.simplefilter(action='ignore', category=FutureWarning)
import json
import os
import unittest
from src.AccountData import AccountData
from pybit import usdt_perpetual
from dotenv import load_dotenv

PUBLIC_TOPICS = ["candle.1.BTCUSDT"]
PUBLIC_TOPICS_COLUMNS = [
    "start", "end", "period", "open", "close", "high", "low", "volume",
    "turnover", "confirm", "cross_seq", "timestamp"
]

load_dotenv()
BYBIT_TEST_KEY = os.getenv('BYBIT_TEST_KEY')
BYBIT_TEST_SECRET = os.getenv('BYBIT_TEST_SECRET')
BYBIT_TEST_ENDPOINT = os.getenv('BYBIT_TEST_ENDPOINT')


class TestAccountData(unittest.TestCase):

    def setUp(self):
        # initialize new http session
        self.session = usdt_perpetual.HTTP(endpoint=BYBIT_TEST_ENDPOINT,
                                           api_key=BYBIT_TEST_KEY,
                                           api_secret=BYBIT_TEST_SECRET)
        # create new account data object
        self.account_data = AccountData(http_session=self.session,
                                        symbols=['BTC', 'USDT'])

        # reset attributes for testing purposes
        self.account_data.positions = {'BTCUSDT': None}
        self.account_data.executions = {'BTCUSDT': {}}
        self.account_data.orders = {'BTCUSDT': {}}
        self.account_data.stop_orders = {'BTCUSDT': {}}
        self.account_data.wallet = {'USDT': {}, 'BTC': {}}

        self.position_response = json.dumps({
            "topic":
                "position",
            "action":
                "update",
            "data": [{
                "user_id": "533285",
                "symbol": "BTCUSDT",
                "size": 0.01,
                "side": "Buy",
                "position_value": 202.195,
                "entry_price": 20219.5,
                "liq_price": 0.5,
                "bust_price": 0.5,
                "leverage": 99,
                "order_margin": 0,
                "position_margin": 1959.6383,
                "occ_closing_fee": 3e-06,
                "take_profit": 25000,
                "tp_trigger_by": "LastPrice",
                "stop_loss": 18000,
                "sl_trigger_by": "LastPrice",
                "trailing_stop": 0,
                "realised_pnl": -4.189762,
                "auto_add_margin": "0",
                "cum_realised_pnl": -13.640625,
                "position_status": "Normal",
                "position_id": "0",
                "position_seq": "92962",
                "adl_rank_indicator": "2",
                "free_qty": 0.01,
                "tp_sl_mode": "Full",
                "risk_id": "1",
                "isolated": False,
                "mode": "BothSide",
                "position_idx": "1"
            }]
        })
        self.position_success = {
            'BTCUSDT': {
                "user_id": "533285",
                "symbol": "BTCUSDT",
                "size": 0.01,
                "side": "Buy",
                "position_value": 202.195,
                "entry_price": 20219.5,
                "liq_price": 0.5,
                "bust_price": 0.5,
                "leverage": 99,
                "order_margin": 0,
                "position_margin": 1959.6383,
                "occ_closing_fee": 3e-06,
                "take_profit": 25000,
                "tp_trigger_by": "LastPrice",
                "stop_loss": 18000,
                "sl_trigger_by": "LastPrice",
                "trailing_stop": 0,
                "realised_pnl": -4.189762,
                "auto_add_margin": "0",
                "cum_realised_pnl": -13.640625,
                "position_status": "Normal",
                "position_id": "0",
                "position_seq": "92962",
                "adl_rank_indicator": "2",
                "free_qty": 0.01,
                "tp_sl_mode": "Full",
                "risk_id": "1",
                "isolated": False,
                "mode": "BothSide",
                "position_idx": "1"
            }
        }
        self.execution_response = json.dumps({
            "topic":
                "execution",
            "data": [{
                "symbol": "BTCUSDT",
                "side": "Sell",
                "order_id": "xxxxxxxx-xxxx-xxxx-9a8f-4a973eb5c418",
                "exec_id": "xxxxxxxx-xxxx-xxxx-8b66-c3d2fcd352f6",
                "order_link_id": "",
                "price": 11527.5,
                "order_qty": 0.001,
                "exec_type": "Trade",
                "exec_qty": 0.001,
                "exec_fee": 0.00864563,
                "leaves_qty": 0,
                "is_maker": False,
                "trade_time": "2020-08-12T21:16:18.142746Z"
            }]
        })

        self.execution_success = {
            "BTCUSDT": {
                "xxxxxxxx-xxxx-xxxx-9a8f-4a973eb5c418": {
                    "symbol": "BTCUSDT",
                    "side": "Sell",
                    "order_id": "xxxxxxxx-xxxx-xxxx-9a8f-4a973eb5c418",
                    "exec_id": "xxxxxxxx-xxxx-xxxx-8b66-c3d2fcd352f6",
                    "order_link_id": "",
                    "price": 11527.5,
                    "order_qty": 0.001,
                    "exec_type": "Trade",
                    "exec_qty": 0.001,
                    "exec_fee": 0.00864563,
                    "leaves_qty": 0,
                    "is_maker": False,
                    "trade_time": "2020-08-12T21:16:18.142746Z"
                }
            }
        }
        self.order_response = json.dumps({
            "topic":
                "order",
            "action":
                "",
            "data": [{
                "order_id": "19a8cbbe-e077-42c7-bdba-505c76619ea5",
                "order_link_id": "Bactive004",
                "symbol": "BTCUSDT",
                "side": "Sell",
                "order_type": "Market",
                "price": 19185.5,
                "qty": 0.01,
                "leaves_qty": 0,
                "last_exec_price": 20196,
                "cum_exec_qty": 0.01,
                "cum_exec_value": 201.95999,
                "cum_exec_fee": 0.121176,
                "time_in_force": "ImmediateOrCancel",
                "create_type": "CreateByUser",
                "cancel_type": "UNKNOWN",
                "order_status": "Filled",
                "take_profit": 0,
                "stop_loss": 0,
                "trailing_stop": 0,
                "create_time": "2022-06-23T04:08:47.956636888Z",
                "update_time": "2022-06-23T04:08:47.960908408Z",
                "reduce_only": True,
                "close_on_trigger": False,
                "position_idx": "1"
            }]
        })
        self.order_success = {
            "BTCUSDT": {
                "19a8cbbe-e077-42c7-bdba-505c76619ea5": {
                    "order_id": "19a8cbbe-e077-42c7-bdba-505c76619ea5",
                    "order_link_id": "Bactive004",
                    "symbol": "BTCUSDT",
                    "side": "Sell",
                    "order_type": "Market",
                    "price": 19185.5,
                    "qty": 0.01,
                    "leaves_qty": 0,
                    "last_exec_price": 20196,
                    "cum_exec_qty": 0.01,
                    "cum_exec_value": 201.95999,
                    "cum_exec_fee": 0.121176,
                    "time_in_force": "ImmediateOrCancel",
                    "create_type": "CreateByUser",
                    "cancel_type": "UNKNOWN",
                    "order_status": "Filled",
                    "take_profit": 0,
                    "stop_loss": 0,
                    "trailing_stop": 0,
                    "create_time": "2022-06-23T04:08:47.956636888Z",
                    "update_time": "2022-06-23T04:08:47.960908408Z",
                    "reduce_only": True,
                    "close_on_trigger": False,
                    "position_idx": "1"
                }
            }
        }
        self.stop_order_response = json.dumps({
            "topic":
                "stop_order",
            "data": [{
                "stop_order_id": "559bba2c-0152-4557-84f6-63dc6ab78463",
                "order_link_id": "",
                "user_id": "533285",
                "symbol": "BTCUSDT",
                "side": "Sell",
                "order_type": "Market",
                "price": 0,
                "qty": 0.01,
                "time_in_force": "ImmediateOrCancel",
                "create_type": "CreateByTakeProfit",
                "cancel_type": "UNKNOWN",
                "order_status": "Untriggered",
                "stop_order_type": "TakeProfit",
                "tp_trigger_by": "UNKNOWN",
                "trigger_price": 25000,
                "create_time": "2022-06-23T04:06:55.402188346Z",
                "update_time": "2022-06-23T04:08:47.960950878Z",
                "reduce_only": True,
                "close_on_trigger": True,
                "position_idx": "1",
                "take_profit": 0.65,
                "stop_loss": 0.25
            }]
        })
        self.stop_order_success = {
            "BTCUSDT": {
                "559bba2c-0152-4557-84f6-63dc6ab78463": {
                    "stop_order_id": "559bba2c-0152-4557-84f6-63dc6ab78463",
                    "order_link_id": "",
                    "user_id": "533285",
                    "symbol": "BTCUSDT",
                    "side": "Sell",
                    "order_type": "Market",
                    "price": 0,
                    "qty": 0.01,
                    "time_in_force": "ImmediateOrCancel",
                    "create_type": "CreateByTakeProfit",
                    "cancel_type": "UNKNOWN",
                    "order_status": "Untriggered",
                    "stop_order_type": "TakeProfit",
                    "tp_trigger_by": "UNKNOWN",
                    "trigger_price": 25000,
                    "create_time": "2022-06-23T04:06:55.402188346Z",
                    "update_time": "2022-06-23T04:08:47.960950878Z",
                    "reduce_only": True,
                    "close_on_trigger": True,
                    "position_idx": "1",
                    "take_profit": 0.65,
                    "stop_loss": 0.25
                }
            }
        }
        self.wallet_response_1 = json.dumps({
            "topic":
                "wallet",
            "data": [{
                "user_id": 738713,
                "coin": "BTC",
                "available_balance": "1.50121026",
                "wallet_balance": "1.50121261"
            }]
        })
        self.wallet_success_1 = {
            "USDT": {},
            "BTC": {
                "user_id": 738713,
                "coin": "BTC",
                "available_balance": "1.50121026",
                "wallet_balance": "1.50121261"
            }
        }
        self.wallet_response_2 = json.dumps({
            "topic":
                "wallet",
            "data": [{
                "wallet_balance": 429.80713,
                "available_balance": 429.67322
            }]
        })
        self.wallet_success_2 = {
            "USDT": {
                "wallet_balance": 429.80713,
                "available_balance": 429.67322
            },
            "BTC": {}
        }

        self.failure_1 = json.dumps({"topic": "no_topic", "data": [1]})
        self.failure_2 = json.dumps({"no_topic": "no_topic", "data": [1]})

    def test_on_message(self):

        self.assertDictEqual(
            self.account_data.on_message(self.position_response),
            self.position_success)
        self.assertDictEqual(
            self.account_data.on_message(self.execution_response),
            self.execution_success)
        self.assertDictEqual(self.account_data.on_message(self.order_response),
                             self.order_success)
        self.assertDictEqual(
            self.account_data.on_message(self.stop_order_response),
            self.stop_order_success)
        self.assertDictEqual(
            self.account_data.on_message(self.wallet_response_2),
            self.wallet_success_2)
        self.assertFalse(self.account_data.on_message(self.failure_1))
        self.assertFalse(self.account_data.on_message(self.failure_2))

    def test_update_positions(self):
        self.account_data.update_positions(
            json.loads(self.position_response)['data'])
        self.assertDictEqual(self.account_data.positions, self.position_success)

    def test_update_executions(self):
        self.account_data.update_executions(
            json.loads(self.execution_response)['data'])
        self.assertDictEqual(self.account_data.executions,
                             self.execution_success)

    def test_update_orders(self):
        self.account_data.update_orders(json.loads(self.order_response)['data'])
        self.assertDictEqual(self.account_data.orders, self.order_success)

    def test_update_stop_orders(self):
        self.account_data.update_stop_orders(
            json.loads(self.stop_order_response)['data'])
        self.assertDictEqual(self.account_data.stop_orders,
                             self.stop_order_success)

    def test_update_wallet(self):
        self.account_data.update_wallet(
            json.loads(self.wallet_response_1)['data'])
        self.assertDictEqual(self.account_data.wallet, self.wallet_success_1)
