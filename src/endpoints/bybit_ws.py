import hashlib
import hmac
import json
import time
import urllib.parse
from threading import Thread
from collections import deque

from requests import Request, Session
from requests.exceptions import HTTPError
from websocket import WebSocketApp
import pandas as pd
from dotenv import load_dotenv
import os

load_dotenv()

BYBIT_TEST_ENDPOINT = os.getenv('BYBIT_TEST_ENDPOINT')
BYBIT_ENDPOINT = os.getenv('BYBIT_ENDPOINT')

WS_PUBLIC_URL = os.getenv('WS_PUBLIC_URL')
WS_PUBLIC_TEST_URL = os.getenv('WS_PUBLIC_TEST_URL')


class Bybit():
    url_main = BYBIT_ENDPOINT
    url_test = BYBIT_TEST_ENDPOINT
    ws_url_main = WS_PUBLIC_URL
    ws_url_test = WS_PUBLIC_TEST_URL
    headers = {'Content-Type': 'application/json'}

    def __init__(self, api_key, secret, symbol, ws=False, test=True):
        self.api_key = api_key
        self.secret = secret

        self.symbol = symbol
        self.s = Session()
        self.s.headers.update(self.headers)

        self.url = self.url_main if not test else self.url_test
        self.ws_url = self.ws_url_main if not test else self.ws_url_test

        self.ws = ws
        if ws:
            self._connect()

    #
    # WebSocket
    #

    def _connect(self):
        self.ws = WebSocketApp(url=self.ws_url,
                               on_open=self._on_open,
                               on_message=self._on_message)

        self.ws_data = {
            'trade.' + str(self.symbol): deque(maxlen=200),
            'instrument.' + str(self.symbol): {},
            'order_book_25L1.' + str(self.symbol): pd.DataFrame(),
            'position': {},
            'execution': deque(maxlen=200),
            'order': deque(maxlen=200)
        }

        # 初期ポジション取得
        positions = self.get_position_http()['result']
        for p in positions:
            if p['symbol'] == self.symbol:
                self.ws_data['position'].update(p)
                break

        # WS接続
        Thread(target=self.ws.run_forever, daemon=True).start()

    def _on_open(self):
        timestamp = int(time.time() * 1000)
        param_str = 'GET/realtime' + str(timestamp)
        sign = hmac.new(self.secret.encode('utf-8'), param_str.encode('utf-8'),
                        hashlib.sha256).hexdigest()

        self.ws.send(
            json.dumps({
                'op': 'auth',
                'args': [self.api_key, timestamp, sign]
            }))
        self.ws.send(
            json.dumps({
                'op':
                    'subscribe',
                'args': [
                    'trade.' + str(self.symbol),
                    'instrument.' + str(self.symbol),
                    'order_book_25L1.' + str(self.symbol), 'position',
                    'execution', 'order'
                ]
            }))

    def _on_message(self, message):
        message = json.loads(message)
        topic = message.get('topic')
        # 各トピックごとの処理
        if topic == 'order_book_25L1.' + str(self.symbol):
            if message['type'] == 'snapshot':
                self.ws_data[topic] = pd.io.json.json_normalize(
                    message['data']).set_index('id').sort_index(ascending=False)
            else:  # message['type'] == 'delta'
                # delete or update or insert
                if len(message['data']['delete']) != 0:
                    drop_list = [x['id'] for x in message['data']['delete']]
                    self.ws_data[topic].drop(index=drop_list)
                elif len(message['data']['update']) != 0:
                    update_list = pd.io.json.json_normalize(
                        message['data']['update']).set_index('id')
                    self.ws_data[topic].update(update_list)
                    self.ws_data[topic] = self.ws_data[topic].sort_index(
                        ascending=False)
                elif len(message['data']['insert']) != 0:
                    insert_list = pd.io.json.json_normalize(
                        message['data']['insert']).set_index('id')
                    self.ws_data[topic].update(insert_list)
                    self.ws_data[topic] = self.ws_data[topic].sort_index(
                        ascending=False)

        elif topic in ['trade.' + str(self.symbol), 'execution', 'order']:
            # dequeにappendするだけ
            self.ws_data[topic].append(message['data'][0])

        elif topic in ['instrument.' + str(self.symbol), 'position']:
            # 辞書を上書きするだけ
            self.ws_data[topic].update(message['data'][0])

    def get_trade(self):
        """
        約定履歴を取得
        """
        if not self.ws:
            return None

        return self.ws_data['trade.' + str(self.symbol)]

    def get_instrument(self):
        """
        ティッカー情報を取得
        """
        if not self.ws:
            return None

        # データ待ち
        while len(self.ws_data['instrument.' + str(self.symbol)]) != 4:
            time.sleep(1.0)

        return self.ws_data['instrument.' + str(self.symbol)]

    def get_orderbook(self, side=None):
        """
        板情報を取得する
        sideに'Sell'または'Buy'を指定可能
        ※データ型: Pandas DataFrame形式
        """
        if not self.ws:
            return None

        # データ待ち
        while self.ws_data['order_book_25L1.' + str(self.symbol)].empty:
            time.sleep(1.0)

        if side == 'Sell':
            orderbook = self.ws_data['order_book_25L1.' +
                                     str(self.symbol)].query(
                                         'side.str.contains("Sell")',
                                         engine='python')
        elif side == 'Buy':
            orderbook = self.ws_data['order_book_25L1.' +
                                     str(self.symbol)].query(
                                         'side.str.contains("Buy")',
                                         engine='python')
        else:
            orderbook = self.ws_data['order_book_25L1.' + str(self.symbol)]
        return orderbook

    def get_position(self):
        """
        ポジションを取得
        """
        if not self.ws:
            return None

        return self.ws_data['position']

    def get_my_executions(self):
        """
        アカウントの約定履歴を取得
        """
        if not self.ws:
            return None

        return self.ws_data['execution']

    def get_order(self):
        """
        オーダー情報を取得
        """
        if not self.ws:
            return None

        return self.ws_data['order']

    #
    # Http Apis
    #

    def _request(self, method, path, payload):
        payload['api_key'] = self.api_key
        payload['timestamp'] = int(time.time() * 1000)
        payload = dict(sorted(payload.items()))
        for k, v in list(payload.items()):
            if v is None:
                del payload[k]

        param_str = urllib.parse.urlencode(payload)
        sign = hmac.new(self.secret.encode('utf-8'), param_str.encode('utf-8'),
                        hashlib.sha256).hexdigest()
        payload['sign'] = sign

        if method == 'GET':
            query = payload
            body = None
        else:
            query = None
            body = json.dumps(payload)

        req = Request(method, self.url + path, data=body, params=query)
        prepped = self.s.prepare_request(req)

        resp = None
        try:
            resp = self.s.send(prepped)
            resp.raise_for_status()
        except HTTPError as e:
            print(e)

        try:
            return resp.json()
        except json.decoder.JSONDecodeError as e:
            print('json.decoder.JSONDecodeError: ' + str(e))
            return resp.text

    def place_active_order(self,
                           side=None,
                           symbol=None,
                           order_type=None,
                           qty=None,
                           price=None,
                           time_in_force='GoodTillCancel',
                           take_profit=None,
                           stop_loss=None,
                           order_link_id=None):
        """
        オーダーを送信
        """
        payload = {
            'side': side,
            'symbol': symbol if symbol else self.symbol,
            'order_type': order_type,
            'qty': qty,
            'price': price,
            'time_in_force': time_in_force,
            'take_profit': take_profit,
            'stop_loss': stop_loss,
            'order_link_id': order_link_id
        }
        return self._request('POST', '/open-api/order/create', payload=payload)

    def get_active_order(self,
                         order_id=None,
                         order_link_id=None,
                         symbol=None,
                         sort=None,
                         order=None,
                         page=None,
                         limit=None,
                         order_status=None):
        """
        オーダーを取得
        """
        payload = {
            'order_id': order_id,
            'order_link_id': order_link_id,
            'symbol': symbol if symbol else self.symbol,
            'sort': sort,
            'order': order,
            'page': page,
            'limit': limit,
            'order_status': order_status
        }
        return self._request('GET', '/open-api/order/list', payload=payload)

    def cancel_active_order(self, order_id=None):
        """
        オーダーをキャンセル
        """
        payload = {'order_id': order_id}
        return self._request('POST', '/open-api/order/cancel', payload=payload)

    def place_conditional_order(self,
                                side=None,
                                symbol=None,
                                order_type=None,
                                qty=None,
                                price=None,
                                base_price=None,
                                stop_px=None,
                                time_in_force='GoodTillCancel',
                                close_on_trigger=None,
                                reduce_only=None,
                                order_link_id=None):
        """
        条件付きオーダーを送信
        """
        payload = {
            'side': side,
            'symbol': symbol if symbol else self.symbol,
            'order_type': order_type,
            'qty': qty,
            'price': price,
            'base_price': base_price,
            'stop_px': stop_px,
            'time_in_force': time_in_force,
            'close_on_trigger': close_on_trigger,
            'reduce_only': reduce_only,
            'order_link_id': order_link_id
        }
        return self._request('POST',
                             '/open-api/stop-order/create',
                             payload=payload)

    def get_conditional_order(self,
                              stop_order_id=None,
                              order_link_id=None,
                              symbol=None,
                              sort=None,
                              order=None,
                              page=None,
                              limit=None):
        """
        条件付きオーダーを取得
        """
        payload = {
            'stop_order_id': stop_order_id,
            'order_link_id': order_link_id,
            'symbol': symbol if symbol else self.symbol,
            'sort': sort,
            'order': order,
            'page': page,
            'limit': limit
        }
        return self._request('GET',
                             '/open-api/stop-order/list',
                             payload=payload)

    def cancel_conditional_order(self, order_id=None):
        """
        条件付きオーダーをキャンセル
        """
        payload = {'order_id': order_id}
        return self._request('POST',
                             '/open-api/stop-order/cancel',
                             payload=payload)

    def get_leverage(self):
        """
        レバレッジを取得
        """
        payload = {}
        return self._request('GET', '/user/leverage', payload=payload)

    def change_leverage(self, symbol=None, leverage=None):
        """
        レバレッジを変更
        """
        payload = {
            'symbol': symbol if symbol else self.symbol,
            'leverage': leverage
        }
        return self._request('POST', '/user/leverage/save', payload=payload)

    def get_position_http(self):
        """
        ポジションを取得(HTTP版)
        """
        payload = {}
        return self._request('GET', '/position/list', payload=payload)

    def change_position_margin(self, symbol=None, margin=None):
        """
        ポジションマージンを変更
        """
        payload = {
            'symbol': symbol if symbol else self.symbol,
            'margin': margin
        }
        return self._request('POST',
                             '/position/change-position-margin',
                             payload=payload)

    def get_prev_funding_rate(self, symbol=None):
        """
        ファンディングレートを取得
        """
        payload = {
            'symbol': symbol if symbol else self.symbol,
        }
        return self._request('GET',
                             '/open-api/funding/prev-funding-rate',
                             payload=payload)

    def get_prev_funding(self, symbol=None):
        """
        アカウントのファンディングレートを取得
        """
        payload = {
            'symbol': symbol if symbol else self.symbol,
        }
        return self._request('GET',
                             '/open-api/funding/prev-funding',
                             payload=payload)

    def get_predicted_funding(self, symbol=None):
        """
        予測資金調達レートと資金調達手数料を取得
        """
        payload = {
            'symbol': symbol if symbol else self.symbol,
        }
        return self._request('GET',
                             '/open-api/funding/predicted-funding',
                             payload=payload)

    def get_my_execution(self, order_id=None):
        """
        アカウントの約定情報を取得
        """
        payload = {'order_id': order_id}
        return self._request('GET',
                             '/v2/private/execution/list',
                             payload=payload)

    #
    # New Http Apis (developing)
    #

    def symbols(self):
        """
        シンボル情報を取得
        """
        payload = {}
        return self._request('GET', '/v2/public/symbols', payload=payload)

    # def kline(self, symbol=None, interval=None, _from=None, limit=None):
    #     """
    #     ローソク足を取得 (developing)
    #     """
    #     payload = {
    #         'symbol': symbol if symbol else self.symbol,
    #         'interval': interval,
    #         'from': _from,
    #         'limit': limit
    #     }
    #     return self._request('GET', '/v2/public/kline/list', payload=payload)

    def kline(self,
              category='linear',
              symbol=None,
              interval=None,
              _start=None,
              _end=None,
              limit=200):
        """
        ローソク足を取得 (developing)
        """
        payload = {
            'category': category,
            'symbol': symbol if symbol else self.symbol,
            'interval': interval,
            'start': _start,
            'end': _end,
            'limit': limit
        }
        return self._request('GET', '/v5/market/kline', payload=payload)

    def place_active_order_v2(self,
                              symbol=None,
                              side=None,
                              order_type=None,
                              qty=None,
                              price=None,
                              time_in_force='GoodTillCancel',
                              order_link_id=None):
        """
        オーダーを送信 v2 (developing)
        """
        payload = {
            'symbol': symbol if symbol else self.symbol,
            'side': side,
            'order_type': order_type,
            'qty': qty,
            'price': price,
            'time_in_force': time_in_force,
            'order_link_id': order_link_id
        }
        return self._request('POST',
                             '/v2/private/order/create',
                             payload=payload)

    def cancel_active_order_v2(self, order_id=None):
        """
        オーダーをキャンセル v2 (developing)
        """
        payload = {'order_id': order_id}
        return self._request('POST',
                             '/v2/private/order/cancel',
                             payload=payload)

    #
    # New Http Apis added by ST
    #

    def get_ticker(self, symbol=None):
        """
        ティッカー情報を取得
        """
        payload = {
            'symbol': symbol if symbol else self.symbol,
        }
        return self._request('GET', '/v2/public/tickers', payload=payload)

    def get_orderbook_http(self, symbol=None):
        """
        order book 情報を取得(HTTP版)
        """
        payload = {
            'symbol': symbol if symbol else self.symbol,
        }
        return self._request('GET', '/v2/public/orderBook/L2', payload=payload)


# if __name__ == '__main__':
#     bybit = Bybit(api_key=BYBIT_TEST_KEY,
#                   secret=BYBIT_TEST_SECRET, symbol='BTCUSD', test=True, ws=True)

#     # ポジションを取得
#     position = bybit.get_position()
#     print('Position ----------------------------------------------------------')
#     print(json.dumps(position, indent=2))

#     # 板情報を取得
#     orderbook_buy = bybit.get_orderbook(side='Buy')
#     print('Orderbook (Buy) ---------------------------------------------------')
#     print(orderbook_buy.head(5))
#     best_buy = float(orderbook_buy.iloc[0]['price'])

#     # オーダーを送信
#     print('Sending Order... --------------------------------------------------')
#     ### NOTE: price needs to be converted to STRING! (float will give you signature error)
#     order_resp = bybit.place_active_order(side='Buy', order_type='Limit', qty=100, price=str(best_buy - 100), time_in_force='PostOnly')
#     print(json.dumps(order_resp, indent=2))
#     order_id = order_resp['result']['order_id'] if order_resp['result'] else None

#     time.sleep(5.0)

#     # オーダーをキャンセル
#     print('Cancel Order... ---------------------------------------------------')
#     cancel_resp = bybit.cancel_active_order(order_id=order_id)
#     print(json.dumps(cancel_resp, indent=2))
