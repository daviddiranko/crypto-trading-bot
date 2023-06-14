import warnings

warnings.simplefilter(action='ignore', category=FutureWarning)
import pandas as pd
import numpy as np
import unittest
import json
from src.endpoints.igm_functions import *

from trading_ig import IGService, IGStreamService
from trading_ig.lightstreamer import Subscription

from dotenv import load_dotenv
import os
import time

load_dotenv()

BYBIT_TEST_KEY = os.getenv('BYBIT_TEST_KEY')
BYBIT_TEST_SECRET = os.getenv('BYBIT_TEST_SECRET')

BYBIT_TEST_ENDPOINT = os.getenv('BYBIT_TEST_ENDPOINT')

IGM_USER = os.getenv('IGM_USER')
IGM_KEY = os.getenv('IGM_KEY')
IGM_PW = os.getenv('IGM_PW')
IGM_ACC = os.getenv('IGM_ACC')
IGM_ACC_TYPE = os.getenv('IGM_ACC_TYPE')


class TestIGMFunctions(unittest.TestCase):

    def setUp(self):

        self.success_message_chart = '{"pos": 1, "name": "CHART:IX.D.SPTRD.FWM1.IP:5MINUTE", "values": {"UTM": "1683611700000", "TTV": null, "BID_OPEN": "4150.38", "BID_HIGH": "4150.63", "BID_LOW": "4150.13", "BID_CLOSE": "4150.38", "OFR_OPEN": "4151.38", "OFR_HIGH": "4151.63", "OFR_LOW": "4151.13", "OFR_CLOSE": "4151.38", "CONS_END": "0"}}'
        self.success_message_account = '{"pos": 1, "name": "ACCOUNT:Z55I7A", "values": {"AVAILABLE_CASH": "22033.56", "PNL_LR": "0", "PNL_NLR": "109.39", "FUNDS": "29945.03", "MARGIN": "8020.86", "MARGIN_LR": "0.00", "MARGIN_NLR": "8020.86", "AVAILABLE_TO_DEAL": "22033.56", "EQUITY": "30054.42", "EQUITY_USED": "26.69"}}'
        self.success_message_trade_1 = '{"pos": 1, "name": "TRADE:Z55I7A", "values": {"CONFIRMS": "{\\"direction\\":\\"BUY\\",\\"epic\\":\\"IX.D.RUSSELL.FWS2.IP\\",\\"stopLevel\\":1747.3,\\"limitLevel\\":null,\\"dealReference\\":\\"WB4MZCERL5GTYPH\\",\\"dealId\\":\\"DIAAAAMDJ45YEBB\\",\\"limitDistance\\":null,\\"stopDistance\\":null,\\"expiry\\":\\"JUN-23\\",\\"affectedDeals\\":[{\\"dealId\\":\\"DIAAAAMDJ45YEBB\\",\\"status\\":\\"OPENED\\"}],\\"dealStatus\\":\\"ACCEPTED\\",\\"guaranteedStop\\":false,\\"trailingStop\\":false,\\"level\\":1757.3,\\"reason\\":\\"SUCCESS\\",\\"status\\":\\"OPEN\\",\\"size\\":1,\\"profit\\":null,\\"profitCurrency\\":null,\\"date\\":\\"2023-05-10T05:39:38.277\\",\\"channel\\":\\"PublicRestOTC\\"}", "OPU": null, "WOU": null}}'
        self.success_message_trade_2 = '{"pos": 1, "name": "TRADE:Z55I7A", "values": {"CONFIRMS": null, "OPU": "{\\"dealReference\\":\\"WB4MZCERL5GTYPH\\",\\"dealId\\":\\"DIAAAAMDJ45YEBB\\",\\"direction\\":\\"BUY\\",\\"epic\\":\\"IX.D.RUSSELL.FWS2.IP\\",\\"status\\":\\"UPDATED\\",\\"dealStatus\\":\\"ACCEPTED\\",\\"level\\":1757.3,\\"size\\":1,\\"timestamp\\":\\"2023-05-10T05:40:56.235\\",\\"channel\\":\\"PublicRestOTC\\",\\"dealIdOrigin\\":\\"DIAAAAMDJ45YEBB\\",\\"expiry\\":\\"JUN-23\\",\\"stopLevel\\":1740,\\"limitLevel\\":null,\\"guaranteedStop\\":false}", "WOU": null}}'

        self.success_response_chart = '{"topic": "CHART:IX.D.SPTRD.FWM1.IP:5MINUTE", "data": [{"start": 1683611700000000000, "end": 1683612000000000000, "interval": "5", "volume": 0, "turnover": 0, "confirm": false, "timestamp": 1683611700000000000, "open": 4150.88, "close": 4150.88, "high": 4151.13, "low": 4150.63}]}'
        self.success_response_account = '{"topic": "wallet", "data": {"USD": {"wallet_balance": "30054.42", "available_balance": "22033.56"}}}'
        self.success_response_trade_1 = '{"topic": "execution", "data": [{"symbol": "IX.D.RUSSELL.FWS2.IP", "side": "Buy", "order_id": "DIAAAAMDJ45YEBB", "exec_id": "DIAAAAMDJ45YEBB", "order_link_id": "WB4MZCERL5GTYPH", "price": 1757.3, "order_qty": 1.0, "exec_qty": 1.0, "exec_fee": 0.0, "leaves_qty": 0.0, "trade_time": 1683697178277000000}]}'
        self.success_response_trade_2 = '{"topic": "position", "data": [{"symbol": "IX.D.RUSSELL.FWS2.IP", "side": "Buy", "position_id": "DIAAAAMDJ45YEBB", "position_value": 1757.3, "size": 1.0, "take_profit": null, "stop_loss": 1740.0, "position_idx": 0}]}'

        self.session = IGService(IGM_USER, IGM_PW, IGM_KEY, IGM_ACC_TYPE)
        self.session.create_session()

    def tearDown(self):
        try:
            place_order(session=self.session,
                        symbol='IX.D.SPTRD.FWM1.IP',
                        order_type='MARKET',
                        expiry='JUN-23',
                        side='SELL',
                        qty=1,
                        reduce_only=True)

        except:
            pass

    def test_format_message(self):

        extraction_chart = format_message(self.success_message_chart)
        extraction_account = format_message(self.success_message_account)
        extraction_trade_1 = format_message(self.success_message_trade_1)
        extraction_trade_2 = format_message(self.success_message_trade_2)

        self.assertEqual(extraction_chart, self.success_response_chart)
        self.assertEqual(extraction_account, self.success_response_account)
        self.assertEqual(extraction_trade_1, self.success_response_trade_1)
        self.assertEqual(extraction_trade_2, self.success_response_trade_2)

    def test_place_order(self):

        response_buy = place_order(session=self.session,
                                   symbol='IX.D.SPTRD.FWM1.IP',
                                   order_type='MARKET',
                                   expiry='JUN-23',
                                   side='BUY',
                                   qty=1)

        balance_1 = initialize_account_data(session=self.session,
                                            symbols=['IX.D.SPTRD.FWM1.IP'],
                                            account_id=IGM_ACC).copy()

        wallet_diff_usd = balance_1['wallet']['USD'][
            'wallet_balance'] - balance_1['wallet']['USD']['available_balance']

        self.assertEqual(response_buy['dealStatus'], 'ACCEPTED')
        self.assertEqual(response_buy['reason'], 'SUCCESS')
        self.assertEqual(response_buy['status'], 'OPEN')
        # self.assertAlmostEqual(
        #     balance_1['position']['IX.D.SPTRD.FWM1.IP']['position_value'],
        #     wallet_diff_usd,
        #     places=1)
        self.assertGreater(
            balance_1['position']['IX.D.SPTRD.FWM1.IP']['position_value'], 0)
        response_sell = place_order(session=self.session,
                                    symbol='IX.D.SPTRD.FWM1.IP',
                                    expiry='JUN-23',
                                    order_type='MARKET',
                                    side='SELL',
                                    qty=1,
                                    reduce_only=True)

        self.assertEqual(response_sell['dealStatus'], 'ACCEPTED')
        self.assertEqual(response_sell['reason'], 'SUCCESS')
        self.assertEqual(response_sell['status'], 'CLOSED')

    def test_stop_loss(self):

        response_buy = place_order(session=self.session,
                                   symbol='IX.D.SPTRD.FWM1.IP',
                                   expiry='JUN-23',
                                   order_type='MARKET',
                                   side='BUY',
                                   qty=1)

        open_positions = self.session.fetch_open_positions()
        open_pos = open_positions.loc[open_positions['epic'] ==
                                      'IX.D.SPTRD.FWM1.IP']

        stop_loss = np.floor(open_pos['level'][0] * 0.9)

        response = set_stop_loss(session=self.session,
                                 position_id=open_pos['dealId'][0],
                                 stop_loss=stop_loss)

        new_open_positions = self.session.fetch_open_positions()
        new_open_pos = new_open_positions.loc[new_open_positions['epic'] ==
                                              'IX.D.SPTRD.FWM1.IP']

        new_stop_loss = new_open_pos['stopLevel'][0]

        self.assertEqual(response['status'], "AMENDED")
        self.assertEqual(response['reason'], "SUCCESS")
        self.assertEqual(response['dealStatus'], "ACCEPTED")

        self.assertAlmostEqual(stop_loss, new_stop_loss)

    def test_take_profit(self):

        response_buy = place_order(session=self.session,
                                   symbol='IX.D.SPTRD.FWM1.IP',
                                   expiry='JUN-23',
                                   order_type='MARKET',
                                   side='BUY',
                                   qty=1)

        open_positions = self.session.fetch_open_positions()
        open_pos = open_positions.loc[open_positions['epic'] ==
                                      'IX.D.SPTRD.FWM1.IP']

        take_profit = np.ceil(open_pos['level'][0] * 1.01)

        response = set_take_profit(session=self.session,
                                   position_id=open_pos['dealId'][0],
                                   take_profit=take_profit)

        new_open_positions = self.session.fetch_open_positions()
        new_open_pos = new_open_positions.loc[new_open_positions['epic'] ==
                                              'IX.D.SPTRD.FWM1.IP']

        new_take_profif = new_open_pos['limitLevel'][0]

        self.assertEqual(response['status'], "AMENDED")
        self.assertEqual(response['reason'], "SUCCESS")
        self.assertEqual(response['dealStatus'], "ACCEPTED")

        self.assertAlmostEqual(take_profit, new_take_profif)
