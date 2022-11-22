# !/usr/bin/env python
# coding: utf-8

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
                                              topics=PUBLIC_TOPICS)

    def test_place_order(self):

        order_time = pd.Timestamp('2022-10-01 09:33:12')

        # order time + 1 minute
        order_time_1 = pd.Timestamp(order_time.value + 60000000000)

        # pull historical kline
        msg = self.client.get_historical_klines('BTCUSDT',
                                                start_str=str(order_time),
                                                end_str=str(order_time_1),
                                                interval='1m')

        # format klines and extract high and low
        quotes = binance_functions.format_historical_klines(msg)

        spread = quotes.iloc[0]['high'] - quotes.iloc[0]['low']

        open = self.account.place_order(symbol='BTCUSDT',
                                        side='Buy',
                                        qty=0.01,
                                        order_time=order_time,
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
                                         order_time=order_time,
                                         order_type='Market',
                                         stop_loss=18000,
                                         take_profit=20000,
                                         reduce_only=True)

        last_trade_2 = self.account.executions['BTCUSDT'][2]

        balance_2 = self.account.wallet['USDT'][
            'available_balance'] + last_trade_1['exec_fee'] + last_trade_2[
                'exec_fee'] + 0.01 * spread

        self.assertAlmostEqual(balance_1, 1000.0)
        self.assertAlmostEqual(balance_2, 1000.0)
        self.assertEqual(open['trade_time'], order_time_1)
        self.assertEqual(close['trade_time'], order_time_1)
        self.assertEqual(position_1['BTCUSDT']['size'], 0.01)
        self.assertAlmostEqual(position_1['BTCUSDT']['position_value'],
                               193.2393)
        self.assertEqual(position_1['BTCUSDT']['stop_loss'], 18000)
        self.assertEqual(position_1['BTCUSDT']['take_profit'], 20000)
        self.assertEqual(position_1['BTCUSDT']['side'], 'Buy')
        self.assertEqual(self.account.positions['BTCUSDT']['size'], 0)
        self.assertEqual(self.account.positions['BTCUSDT']['position_value'], 0)

    def test_execute(self):

        order_time = pd.Timestamp('2022-10-01 09:33:12')

        # order time + 1 minute
        order_time_1 = pd.Timestamp(order_time.value + 60000000000)

        open = self.account.execute(symbol='BTCUSDT',
                                    side='Buy',
                                    qty=0.01,
                                    execution_time=order_time_1,
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
                                     execution_time=order_time_1,
                                     trade_price=19000,
                                     stop_loss=18000,
                                     take_profit=20000)

        last_trade_2 = self.account.executions['BTCUSDT'][2]

        balance_2 = self.account.wallet['USDT'][
            'available_balance'] + last_trade_1['exec_fee'] + last_trade_2[
                'exec_fee']

        self.assertEqual(balance_1, 1000.0)
        self.assertEqual(balance_2, 1190.0)
        self.assertEqual(open['trade_time'], order_time_1)
        self.assertEqual(close['trade_time'], order_time_1)
        self.assertEqual(position_1['BTCUSDT']['size'], 0.01)
        self.assertEqual(position_1['BTCUSDT']['position_value'], 190.0)
        self.assertEqual(position_1['BTCUSDT']['stop_loss'], 18000)
        self.assertEqual(position_1['BTCUSDT']['take_profit'], 20000)
        self.assertEqual(position_1['BTCUSDT']['side'], 'Buy')
        self.assertEqual(self.account.positions['BTCUSDT']['size'], 0.01)
        self.assertEqual(self.account.positions['BTCUSDT']['side'], 'Sell')
        self.assertEqual(self.account.positions['BTCUSDT']['position_value'],
                         190.0)
