# !/usr/bin/env python
# coding: utf-8
import warnings

warnings.simplefilter(action='ignore', category=FutureWarning)
import pandas as pd
from dotenv import load_dotenv
import os
from src.backtest.BacktestTradingModel import BacktestTradingModel
from src.models.mock_model import mock_model
import unittest
from binance.client import Client

load_dotenv()

BINANCE_KEY = os.getenv('BINANCE_KEY')
BINANCE_SECRET = os.getenv('BINANCE_SECRET')

PUBLIC_TOPICS = ["candle.1.BTCUSDT", "candle.15.BTCUSDT"]
BINANCE_BYBIT_MAPPING = {
    'candle.1.BTCUSDT': 'BTCUSDT',
    'candle.15.BTCUSDT': 'BTCUSDT'
}

BACKTEST_SYMBOLS = {
    'BTCUSDT.1m': 'candle.1.BTCUSDT',
    'BTCUSDT.5m': 'candle.5.BTCUSDT'
}


class TestBacktestTradingModel(unittest.TestCase):

    def setUp(self):
        self.client = Client(BINANCE_KEY, BINANCE_SECRET)
        self.model = BacktestTradingModel(model=mock_model,
                                          http_session=self.client,
                                          symbols=['BTC', 'USDT'],
                                          budget={
                                              'USDT': 1000,
                                              'BTC': 0
                                          },
                                          topics=PUBLIC_TOPICS,
                                          topic_mapping=BINANCE_BYBIT_MAPPING,
                                          backtest_symbols=BACKTEST_SYMBOLS,
                                          model_args={
                                              'open': True,
                                              'reduce_only': True
                                          },
                                          model_storage={
                                              'open': False,
                                              'close': False
                                          })
        self.symbols = {
            'BTCUSDT.1m': 'candle.1.BTCUSDT',
            'BTCUSDT.15m': 'candle.15.BTCUSDT'
        }

    def test_run_backtest(self):

        report = self.model.run_backtest(symbols=self.symbols,
                                         start_history='2022-11-21 23:59:00',
                                         start_str='2022-11-22 00:00:00',
                                         end_str='2022-11-22 00:03:00',
                                         slice_length=3)

        positions = {
            'BTCBTC': {
                'symbol': 'BTCBTC',
                'size': 0.0,
                'side': 'Buy',
                'position_value': 0.0,
                'take_profit': 0.0,
                'stop_loss': 0.0
            },
            'BTCUSDT': {
                'symbol': 'BTCUSDT',
                'size': 0.0,
                'side': 'Sell',
                'position_value': 0.0,
                'take_profit': None,
                'stop_loss': None
            },
            'USDTBTC': {
                'symbol': 'USDTBTC',
                'size': 0.0,
                'side': 'Buy',
                'position_value': 0.0,
                'take_profit': 0.0,
                'stop_loss': 0.0
            },
            'USDTUSDT': {
                'symbol': 'USDTUSDT',
                'size': 0.0,
                'side': 'Buy',
                'position_value': 0.0,
                'take_profit': 0.0,
                'stop_loss': 0.0
            }
        }

        executions = {
            'BTCBTC': {},
            'BTCUSDT': {
                1: {
                    'symbol': 'BTCUSDT',
                    'side': 'Buy',
                    'open': True,
                    'order_id': 1,
                    'exec_id': 1,
                    'price': 15773.47,
                    'order_qty': 0.001,
                    'exec_type': 'Trade',
                    'exec_qty': 0.001,
                    'exec_fee': 0.009464081999999999,
                    'trade_time': pd.Timestamp('2022-11-22 00:02:00')
                },
                2: {
                    'symbol': 'BTCUSDT',
                    'side': 'Sell',
                    'open': False,
                    'order_id': 2,
                    'exec_id': 2,
                    'price': 15773.47,
                    'order_qty': 0.001,
                    'exec_type': 'Trade',
                    'exec_qty': 0.001,
                    'exec_fee': 0.009464081999999999,
                    'trade_time': pd.Timestamp('2022-11-22 00:02:00')
                }
            },
            'USDTBTC': {},
            'USDTUSDT': {}
        }

        new_executions = {
            'BTCBTC': {},
            'BTCUSDT': {
                1: {
                    'symbol': 'BTCUSDT',
                    'side': 'Buy',
                    'open': True,
                    'order_id': 1,
                    'exec_id': 1,
                    'price': 15773.47,
                    'order_qty': 0.001,
                    'exec_type': 'Trade',
                    'exec_qty': 0.001,
                    'exec_fee': 0.009464081999999999,
                    'trade_time': pd.Timestamp('2022-11-22 00:02:00')
                },
                2: {
                    'symbol': 'BTCUSDT',
                    'side': 'Sell',
                    'open': True,
                    'order_id': 2,
                    'exec_id': 2,
                    'price': 15773.47,
                    'order_qty': 10.0,
                    'exec_type': 'Trade',
                    'exec_qty': 10.0,
                    'exec_fee': 94.64081999999999,
                    'trade_time': pd.Timestamp('2022-11-22 00:02:00')
                },
                3: {
                    'symbol': 'BTCUSDT',
                    'side': 'Buy',
                    'open': False,
                    'order_id': 3,
                    'exec_id': 3,
                    'price': 15805.58,
                    'order_qty': 9.999,
                    'exec_type': 'Trade',
                    'exec_qty': 9.999,
                    'exec_fee': 94.823996652,
                    'trade_time': pd.Timestamp('2022-11-22 00:05:00')
                }
            },
            'USDTBTC': {},
            'USDTUSDT': {}
        }

        # print(self.model.account.executions)
        self.assertDictEqual(self.model.account.executions, executions)
        self.assertDictEqual(self.model.account.positions, positions)

        new_model = BacktestTradingModel(model=mock_model,
                                         http_session=self.client,
                                         symbols=['BTC', 'USDT'],
                                         budget={
                                             'USDT': 1000,
                                             'BTC': 0
                                         },
                                         topics=PUBLIC_TOPICS,
                                         topic_mapping=BINANCE_BYBIT_MAPPING,
                                         backtest_symbols=BACKTEST_SYMBOLS,
                                         model_args={
                                             'open': True,
                                             'reduce_only': False
                                         },
                                         model_storage={
                                             'open': False,
                                             'close': False
                                         })
        new_report = new_model.run_backtest(symbols=self.symbols,
                                            start_history='2022-11-21 23:59:00',
                                            start_str='2022-11-22 00:00:00',
                                            end_str='2022-11-22 00:03:00',
                                            slice_length=3)

        print(new_model.account.executions)
        self.assertDictEqual(new_model.account.positions, positions)
        self.assertDictEqual(new_model.account.executions, new_executions)

        trades = pd.DataFrame(
            self.model.account.executions['BTCUSDT']).transpose()
        trades['trading_value'] = -2 * (
            (trades['side'] == 'Buy') -
            0.5) * trades['exec_qty'] * trades['price'] - trades['exec_fee']

        new_trades = pd.DataFrame(
            new_model.account.executions['BTCUSDT']).transpose()
        new_trades['trading_value'] = -2 * (
            (new_trades['side'] == 'Buy') - 0.5) * new_trades[
                'exec_qty'] * new_trades['price'] - new_trades['exec_fee']

        self.assertAlmostEqual(report['BTCUSDT']['trading_return'],
                               trades['trading_value'].sum())
        self.assertEqual(
            report['BTCUSDT']['total_trades'],
            len(self.model.account.executions['BTCUSDT'].keys()) / 2)

        self.assertAlmostEqual(new_report['BTCUSDT']['trading_return'],
                               new_trades['trading_value'].sum())
