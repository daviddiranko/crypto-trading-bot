# !/usr/bin/env python
# coding: utf-8
import warnings

warnings.simplefilter(action='ignore', category=FutureWarning)
import pandas as pd
from typing import Any, Dict, List
from dotenv import load_dotenv
import os
from binance.client import Client
from src.endpoints import binance_functions, bybit_functions
from src.backtest.BacktestAccountData import BacktestAccountData
from src.backtest.BacktestMarketData import BacktestMarketData
from src.backtest.BacktestTradingModel import BacktestTradingModel
import itertools
import unittest

load_dotenv()

BINANCE_KEY = os.getenv('BINANCE_KEY')
BINANCE_SECRET = os.getenv('BINANCE_SECRET')

PUBLIC_TOPICS = eval(os.getenv('PUBLIC_TOPICS'))
PRIVATE_TOPICS = eval(os.getenv('PRIVATE_TOPICS'))


class TestBacktestAccountData(unittest.TestCase):

    def setUp(self):
        self.client = Client(BINANCE_KEY, BINANCE_SECRET)
        self.account = BacktestAccountData(binance_client=self.client,
                                           symbols=['BTC', 'USDT'],
                                           budget={
                                               'USDT': 1000,
                                               'BTC': 0
                                           })
        self.market_data = BacktestMarketData(account=self.account,
                                              client=self.client,
                                              topics=PUBLIC_TOPICS)

        self.order_time = pd.Timestamp('2022-10-01 09:33:12')

        # order time + 1 minute
        self.order_time_1 = pd.Timestamp(self.order_time.value + 60000000000)

    def test_place_order(self):

        # pull historical kline
        msg = self.client.get_historical_klines('BTCUSDT',
                                                start_str=str(self.order_time),
                                                end_str=str(self.order_time_1),
                                                interval='1m')

        # format klines and extract high and low
        quotes = binance_functions.format_historical_klines(msg)

        # spread = quotes.iloc[0]['high'] - quotes.iloc[0]['low']

        self.account.timestamp = self.order_time
        open = self.account.place_order(symbol='BTCUSDT',
                                        side='Buy',
                                        qty=0.01,
                                        order_type='Market',
                                        stop_loss=18000,
                                        take_profit=20000)

        last_trade_1 = self.account.executions['BTCUSDT'][1]

        balance_1 = self.account.wallet['USDT'][
            'available_balance'] + last_trade_1[
                'exec_fee'] + last_trade_1['exec_qty'] * last_trade_1['price']
        position_1 = self.account.positions.copy()

        close = self.account.place_order(symbol='BTCUSDT',
                                         side='Sell',
                                         qty=0.02,
                                         order_type='Market',
                                         stop_loss=18000,
                                         take_profit=20000,
                                         reduce_only=True)

        last_trade_2 = self.account.executions['BTCUSDT'][2]

        balance_2 = self.account.wallet['USDT'][
            'available_balance'] + last_trade_1['exec_fee'] + last_trade_2[
                'exec_fee']

        self.assertAlmostEqual(balance_1, 1000.0)
        self.assertAlmostEqual(balance_2, 1000.0)
        self.assertEqual(open['trade_time'], self.order_time_1)
        self.assertEqual(close['trade_time'], self.order_time_1)
        self.assertEqual(position_1['BTCUSDT']['size'], 0.01)
        self.assertAlmostEqual(position_1['BTCUSDT']['position_value'],
                               193.1234)
        self.assertEqual(position_1['BTCUSDT']['stop_loss'], 18000)
        self.assertEqual(position_1['BTCUSDT']['take_profit'], 20000)
        self.assertEqual(position_1['BTCUSDT']['side'], 'Buy')
        self.assertEqual(self.account.positions['BTCUSDT']['size'], 0)
        self.assertEqual(self.account.positions['BTCUSDT']['position_value'], 0)

    def test_execute(self):

        open = self.account.execute(symbol='BTCUSDT',
                                    side='Buy',
                                    qty=0.01,
                                    execution_time=self.order_time_1,
                                    trade_price=19000,
                                    stop_loss=18000,
                                    take_profit=20000)

        last_trade_1 = self.account.executions['BTCUSDT'][1]

        balance_1 = self.account.wallet['USDT'][
            'available_balance'] + last_trade_1[
                'exec_fee'] + last_trade_1['exec_qty'] * last_trade_1['price']

        position_1 = self.account.positions.copy()
        close = self.account.execute(symbol='BTCUSDT',
                                     side='Sell',
                                     qty=0.02,
                                     execution_time=self.order_time_1,
                                     trade_price=19000,
                                     stop_loss=18000,
                                     take_profit=20000)

        last_trade_2 = self.account.executions['BTCUSDT'][2]

        balance_2 = self.account.wallet['USDT'][
            'available_balance'] + last_trade_1['exec_fee'] + last_trade_2[
                'exec_fee']

        self.assertEqual(balance_1, 1000.0)
        self.assertEqual(balance_2, 1190.0)
        self.assertEqual(open['trade_time'], self.order_time_1)
        self.assertEqual(close['trade_time'], self.order_time_1)
        self.assertEqual(position_1['BTCUSDT']['size'], 0.01)
        self.assertEqual(position_1['BTCUSDT']['position_value'], 190.0)
        self.assertEqual(position_1['BTCUSDT']['stop_loss'], 18000)
        self.assertEqual(position_1['BTCUSDT']['take_profit'], 20000)
        self.assertEqual(position_1['BTCUSDT']['side'], 'Buy')
        self.assertEqual(self.account.positions['BTCUSDT']['size'], 0.01)
        self.assertEqual(self.account.positions['BTCUSDT']['side'], 'Sell')
        self.assertEqual(self.account.positions['BTCUSDT']['position_value'],
                         190.0)

    def test_new_market_data(self):
        self.account.execute(symbol='BTCUSDT',
                             side='Buy',
                             qty=0.01,
                             execution_time=self.order_time,
                             trade_price=19000,
                             stop_loss=18000,
                             take_profit=20000)

        market_data_1 = {
            'start': self.order_time,
            'end': self.order_time_1,
            'open': 19000,
            'close': 19500,
            'high': 19800,
            'low': 18500,
            'volume': 10,
            'turnover': 192000
        }
        pos_1 = self.account.new_market_data(topic=PUBLIC_TOPICS[0],
                                             data=market_data_1)

        self.assertEqual(pos_1['size'], 0.01)
        self.assertAlmostEqual(pos_1['position_value'], 195.0)
        self.assertEqual(
            self.account.wallet['USDT']['available_balance'],
            810.0 - self.account.executions['BTCUSDT'][1]['exec_fee'])

        market_data_2 = {
            'start': self.order_time,
            'end': self.order_time_1,
            'open': 19000,
            'close': 19500,
            'high': 20100,
            'low': 18900,
            'volume': 10,
            'turnover': 192000
        }
        pos_2 = self.account.new_market_data(topic=PUBLIC_TOPICS[0],
                                             data=market_data_2)
        fees_2 = self.account.executions['BTCUSDT'][1][
            'exec_fee'] + self.account.executions['BTCUSDT'][2]['exec_fee']
        self.assertEqual(pos_2['size'], 0)
        self.assertEqual(self.account.wallet['USDT']['available_balance'],
                         1010 - fees_2)

        self.account.execute(symbol='BTCUSDT',
                             side='Sell',
                             qty=0.01,
                             execution_time=self.order_time,
                             trade_price=19000,
                             stop_loss=20000,
                             take_profit=18000)

        market_data_3 = {
            'start': self.order_time,
            'end': self.order_time_1,
            'open': 19500,
            'close': 19100,
            'high': 20100,
            'low': 18500,
            'volume': 10,
            'turnover': 192000
        }
        pos_3 = self.account.new_market_data(topic=PUBLIC_TOPICS[0],
                                             data=market_data_3)
        fees_3 = fees_2 + self.account.executions['BTCUSDT'][3][
            'exec_fee'] + self.account.executions['BTCUSDT'][4]['exec_fee']
        self.assertEqual(pos_3['size'], 0)
        self.assertAlmostEqual(pos_3['position_value'], 0.0)
        self.assertEqual(self.account.wallet['USDT']['available_balance'],
                         1000 - fees_3)
