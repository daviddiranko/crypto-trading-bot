import warnings

warnings.simplefilter(action='ignore', category=FutureWarning)
import pandas as pd
import numpy as np
import unittest
import json
from src.endpoints.bybit_functions import *
from pybit import usdt_perpetual
from dotenv import load_dotenv
import os
import time

load_dotenv()

BYBIT_TEST_KEY = os.getenv('BYBIT_TEST_KEY')
BYBIT_TEST_SECRET = os.getenv('BYBIT_TEST_SECRET')

BYBIT_TEST_ENDPOINT = os.getenv('BYBIT_TEST_ENDPOINT')


class TestBybitFunctions(unittest.TestCase):

    def setUp(self):

        self.success_message = json.loads(
            '{"topic":"candle.1.BTCUSDT","data":[{"start":1667461800,"end":1667461860,"period":"1","open":20282,"close":20280.5,"high":20282.5,"low":20280,"volume":"20.753","turnover":"420912.939","confirm":false,"cross_seq":19909786084,"timestamp":1667461837466318}],"timestamp_e6":1667461837466318}'
        )
        self.failure_message = '{"success":true,"ret_msg":"","conn_id":"0645af2a-2a34-476e-bcc6-40baa771c0bf","request":{"op":"subscribe","args":["candle.1.BTCUSDT"]}}'
        self.success = {
            "topic": "candle.1.BTCUSDT",
            "data": [{
                "start": pd.Timestamp('2022-11-03 07:50:00'),
                "end": pd.Timestamp('2022-11-03 07:51:00'),
                "period": "1",
                "open": 20282,
                "close": 20280.5,
                "high": 20282.5,
                "low": 20280,
                "volume": 20.753,
                "turnover": 420912.939,
                "confirm": False,
                "cross_seq": 19909786084,
                "timestamp": 1667461837466318
            }],
            "timestamp_e6": 1667461837466318
        }

        self.session = usdt_perpetual.HTTP(endpoint=BYBIT_TEST_ENDPOINT,
                                           api_key=BYBIT_TEST_KEY,
                                           api_secret=BYBIT_TEST_SECRET)

    def tearDown(self):
        try:
            place_order(session=self.session,
                        symbol='BTCUSDT',
                        order_type='Market',
                        side='Sell',
                        qty=10,
                        reduce_only=True)
            while self.session.get_active_order(
                    symbol='BTCUSDT'
            )['result']['data'][-1]['order_status'] != 'Filled':
                time.sleep(1)
        except:
            pass

        try:
            self.session.cancel_all_conditional_orders(symbol='BTCUSDT')
        except:
            pass

    def test_format_klines(self):

        extraction = format_klines(self.success_message)

        self.assertEqual(extraction, self.success['data'][0])

    def test_place_order(self):
        try:
            self.session.set_leverage(symbol='BTCUSDT',
                                      sell_leverage=1,
                                      buy_leverage=1)
        except:
            pass
        response_buy = place_order(session=self.session,
                                   symbol='BTCUSDT',
                                   order_type='Market',
                                   side='Buy',
                                   qty=0.001)

        while self.session.query_active_order(
                symbol='BTCUSDT', order_id=response_buy['result']
            ['order_id'])['result']['order_status'] != 'Filled':
            time.sleep(1)

        balance_1 = initialize_account_data(session=self.session,
                                            symbols=['BTC', 'USDT']).copy()

        wallet_diff_usdt = balance_1['wallet']['USDT']['equity'] - balance_1[
            'wallet']['USDT']['available_balance']

        self.assertEqual(response_buy['ret_code'], 0)
        self.assertEqual(response_buy['ret_msg'], "OK")
        self.assertAlmostEqual(
            balance_1['position']['BTCUSDT']['position_value'],
            wallet_diff_usdt,
            places=1)
        self.assertGreater(balance_1['position']['BTCUSDT']['position_value'],
                           0)
        response_sell = place_order(session=self.session,
                                    symbol='BTCUSDT',
                                    order_type='Market',
                                    side='Sell',
                                    qty=1,
                                    reduce_only=True)
        while self.session.query_active_order(
                symbol='BTCUSDT', order_id=response_buy['result']
            ['order_id'])['result']['order_status'] != 'Filled':
            time.sleep(1)

        balance_2 = initialize_account_data(session=self.session,
                                            symbols=['BTC', 'USDT']).copy()
        self.assertEqual(response_sell['ret_code'], 0)
        self.assertEqual(response_sell['ret_msg'], "OK")
        self.assertEqual(balance_2['position']['BTCUSDT']['position_value'], 0)

    # def test_place_conditional_order(self):
    #     try:
    #         self.session.set_leverage(symbol='BTCUSDT',
    #                                   sell_leverage=1,
    #                                   buy_leverage=1)
    #     except:
    #         pass
    #     response_buy = place_conditional_order(session=self.session,
    #                                            symbol='BTCUSDT',
    #                                            order_type='Market',
    #                                            side='Buy',
    #                                            qty=0.001)

    #     self.assertEqual(response_buy['ret_code'], 0)
    #     self.assertEqual(response_buy['ret_msg'], "OK")

    #     self.session.cancel_all_conditional_orders(symbol='BTCUSDT')

    def test_stop_loss(self):
        try:
            self.session.set_leverage(symbol='BTCUSDT',
                                      sell_leverage=1,
                                      buy_leverage=1)
        except:
            pass
        response_buy = place_order(session=self.session,
                                   symbol='BTCUSDT',
                                   order_type='Market',
                                   side='Buy',
                                   qty=0.001)

        while self.session.query_active_order(
                symbol='BTCUSDT', order_id=response_buy['result']
            ['order_id'])['result']['order_status'] != 'Filled':
            time.sleep(1)

        stop_loss = np.floor(
            self.session.my_position(
                symbol="BTCUSDT")['result'][0]['entry_price'] * 0.5)

        response = set_stop_loss(session=self.session,
                                 symbol="BTCUSDT",
                                 side='Buy',
                                 stop_loss=stop_loss)

        new_stop_loss = self.session.my_position(
            symbol="BTCUSDT")['result'][0]['stop_loss']

        self.assertEqual(response['ret_msg'], "OK")
        self.assertAlmostEqual(stop_loss, new_stop_loss)

    def test_take_profit(self):
        try:
            self.session.set_leverage(symbol='BTCUSDT',
                                      sell_leverage=1,
                                      buy_leverage=1)
        except:
            pass
        response_buy = place_order(session=self.session,
                                   symbol='BTCUSDT',
                                   order_type='Market',
                                   side='Buy',
                                   qty=0.001)

        while self.session.query_active_order(
                symbol='BTCUSDT', order_id=response_buy['result']
            ['order_id'])['result']['order_status'] != 'Filled':
            time.sleep(1)

        take_profit = np.floor(
            self.session.my_position(
                symbol="BTCUSDT")['result'][0]['entry_price'] * 1.5)

        response = set_take_profit(session=self.session,
                                   symbol="BTCUSDT",
                                   side='Buy',
                                   take_profit=take_profit)

        new_take_profit = self.session.my_position(
            symbol="BTCUSDT")['result'][0]['take_profit']

        self.assertEqual(response['ret_msg'], "OK")
        self.assertAlmostEqual(take_profit, new_take_profit)
