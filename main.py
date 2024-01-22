import sys

sys.path.append('../')

import pandas as pd
from src.endpoints.igm_functions import format_message, MessageAggregator
from datetime import datetime
from dotenv import load_dotenv
import os
from src.TradingModel import TradingModel
from src.models.checklist_model import checklist_model
import argparse
from trading_ig import IGService, IGStreamService
from trading_ig.lightstreamer import Subscription
import json
import boto3
import time 

# load environment variables
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
IGM_CHART_FIELDS = eval(os.getenv('IGM_CHART_FIELDS'))


def main():

    # parse arguments
    parser = argparse.ArgumentParser(
        description="Run Live Trading Model for bybit trading.")

    parser.add_argument('--tickers', type=str, default="[BTCUSDT]")
    parser.add_argument(
        '--freqs',
        type=str,
        default="1 5 15",
        help="List of candle frequencies in minutes required by the model")

    parser.add_argument(
        '--trading_freqs',
        type=str,
        default="5",
        help="List of candle frequencies in minutes required by the model")
    
    parser.add_argument(
        '--tick_sizes',
        type=str,
        default="0.1",
        help="Tick size for each ticker")

    parser.add_argument('--model_args',
                        type=str,
                        default=str({'param': 1}),
                        help="optional arguments for trading model")

    args = parser.parse_args()
    args = vars(args)

    print('Establish IGM HTTP session...')

    # instantiate igm session object
    session = IGService(IGM_USER, IGM_PW, IGM_KEY, IGM_ACC_TYPE)
    session.create_session()

    print('Done!')

    print('Extract hyperparameters and tickers...')

    freqs = args['freqs'].split()
    trading_freqs = args['trading_freqs'].split()
    tick_sizes_raw = args['tick_sizes'].split()
    tickers_raw = args['tickers'].split()

    markets = [
        session.fetch_sub_nodes_by_node(ticker)['markets']
        for ticker in tickers_raw
    ]
    futures_market_indices = [market['expiry'] != '-' for market in markets]
    tickers = [
        market['epic'].loc[id].iloc[0]
        for market, id in zip(markets, futures_market_indices)
    ]
    expiries = {
        market['epic'].loc[id].iloc[0]: market['expiry'].loc[id].iloc[0]
        for market, id in zip(markets, futures_market_indices)
    }

    tick_sizes = {
        ticker: float(tick_size)
        for ticker, tick_size in zip(tickers, tick_sizes_raw)
    }

    model_args = eval(args['model_args'])

    model_args['tickers'] = tickers
    model_args['tick_sizes'] = tick_sizes
    model_args['trading_freqs'] = trading_freqs
    model_args['expiries'] = expiries

    BACKTEST_SYMBOLS = {
        '{}.{}m'.format(ticker, freq): 'candle.{}.{}'.format(freq, ticker)
        for freq in freqs for ticker in tickers
    }

    HIST_TICKERS = tickers
    PUBLIC_TOPICS = [
        "candle.{}.{}".format(freq, ticker)
        for freq in freqs
        for ticker in tickers
    ]

    BACKTEST_SYMBOLS = {
        '{}:{}MINUTE'.format(ticker, freq): 'candle.{}.{}'.format(freq, ticker)
        for freq in freqs for ticker in tickers
    }

    HIST_TICKERS = tickers

    PUBLIC_TOPICS = list(BACKTEST_SYMBOLS.values())

    # generate parameters for historical data
    start = 10
    start_unit = 'h'

    # symbol_list = [symbol[:-4] for symbol in HIST_TICKERS]
    # symbol_list.extend([symbol[-4:] for symbol in HIST_TICKERS])

    symbol_list = HIST_TICKERS

    print('Done!')

    print('Initialize Trading Model...')
    # initialize message aggregation
    aggregated_messages = {}
    for ticker in tickers:
        for freq in freqs:
            if freq not in ['1', '2', '5']:
                aggregated_messages["candle.{}.{}".format(
                    freq, ticker)] = MessageAggregator(
                        msg_topic="candle.1.{}".format(ticker),
                        aggregated_topic="candle.{}.{}".format(freq, ticker),
                        msg_interval=1,
                        aggregated_interval=int(freq))

    # initialize TradingModel object
    model = TradingModel(
        client=None,
        http_session=session,
        symbols=symbol_list,
        topics=PUBLIC_TOPICS,
        model=checklist_model,
        model_args=model_args,
        model_storage={
            'entry_body_1_long':
                None,
            'entry_close_1_long':
                None,
            'entry_open_1_long':
                None,
            'entry_body_1_short':
                None,
            'entry_close_1_short':
                None,
            'entry_open_1_short':
                None,
            'exit_long_higher_lows': [],
            'exit_short_lower_highs': [],
            'entry_bar_time':
                pd.Timestamp(pd.Timestamp.now(tz='UTC').to_datetime64()),
            'action_bar_time':
                pd.Timestamp(pd.Timestamp.now(tz='UTC').to_datetime64())
        })
    
    print('Done!')

    print('Closing potentially open trades...')
    
    # close potential open positions upfront
    for pos in model.account.positions.values():
        for ticker in tickers:
            if (pos['size'] > 0) and (pos['symbol'] == ticker):
                if pos['side'].upper() == 'BUY':
                    side = 'SELL'
                else:
                    side = 'BUY'
                model.account.place_order(symbol=pos['symbol'],
                                          expiry=model.model_args['expiries'][pos['symbol']],
                                          side=side,
                                          order_type='MARKET',
                                          qty=pos['size'],
                                          reduce_only=True)

    # construct start string
    now = pd.Timestamp(pd.Timestamp.now(tz='UTC').to_datetime64())
    start_str = str(
         now -
        pd.Timedelta(start, start_unit))
    end_str = str(now)

    print('Load trading history for trading model...')
    # model.market_data.build_history(symbols=BACKTEST_SYMBOLS,
    #                                 start_str=start_str,
    #                                 end_str=end_str)

    print('Done!')

    print('Log into aws s3')
    # initialie s3 client and timestamp reference to log market data 
    s3_client = boto3.client('s3')
    ref_timestamp = pd.Timestamp(year=now.year, month=now.month+1, day=1)

    print('Done!')

    def pass_msg(msg: dict):
        '''
        Pass a Lightstreamer message to the trading model.
        '''
        msg = format_message(msg)
        if msg:
            print(msg)
            model.on_message(msg)
                
            if json.loads(msg)['topic'].startswith('candle'):
                for aggregated_msg in aggregated_messages.keys():
                    new_msg = aggregated_messages[aggregated_msg].update(
                        msg=msg)
                    if new_msg:
                        print(new_msg)
                        model.on_message(new_msg)

    
    print('Connect to IGM Lightstreamer...')

    # initialize streaming service
    ig_stream_service = IGStreamService(session)
    ig_stream_service.create_session()

    # Create Subscriptions
    subscription_prices = Subscription(
        mode="MERGE",
        items=['CHART:' + key for key in BACKTEST_SYMBOLS.keys()],
        fields=IGM_CHART_FIELDS,
    )

    subscription_account = Subscription(
        mode="MERGE",
        items=["ACCOUNT:" + IGM_ACC],
        fields=[
            "AVAILABLE_CASH", "PNL_LR", "PNL_NLR", "FUNDS", "MARGIN",
            "MARGIN_LR", "MARGIN_NLR", "AVAILABLE_TO_DEAL", "EQUITY",
            "EQUITY_USED"
        ],
    )

    subscription_trades = Subscription(mode="DISTINCT",
                                    items=["TRADE:" + IGM_ACC],
                                    fields=["CONFIRMS", "OPU", "WOU"])

    # Adding listeners
    subscription_prices.addlistener(pass_msg)
    subscription_account.addlistener(pass_msg)
    subscription_trades.addlistener(pass_msg)

    # Registering the Subscriptions
    sub_key_prices = ig_stream_service.ls_client.subscribe(subscription_prices)
    sub_key_account = ig_stream_service.ls_client.subscribe(
        subscription_account)
    sub_key_trades = ig_stream_service.ls_client.subscribe(subscription_trades)

    print('Done!')

    print('Start trading...')

    while True:
        try:
            if ig_stream_service.ls_client._stream_connection_thread.is_alive():
                
                # log market data every month
                now = pd.Timestamp(pd.Timestamp.now(tz='UTC').to_datetime64())
                if now.day==1 and now.hour==0 and now.minute==0 and now.second==0:
                    for key in model.market_data.history.keys():
                        history = model.market_data.history[key].loc[model.market_data.history[key]['start']>now-pd.offsets.MonthBegin(1)]
                        s3_client.put_object(Body=history.to_json(), Bucket='igm-data-log',Key=key+'{}.json'.format(now))

                continue
            else:
                print('Connection lost!')
                print('Connect to IGM Lightstreamer...')
                ig_stream_service.create_session()

                # Registering the Subscriptions
                sub_key_prices = ig_stream_service.ls_client.subscribe(subscription_prices)
                sub_key_account = ig_stream_service.ls_client.subscribe(
                    subscription_account)
                sub_key_trades = ig_stream_service.ls_client.subscribe(subscription_trades)

                print('Done!')

                print('Start trading...')

                # # close potential open positions
                # for pos in model.account.positions.values():
                #     for ticker in tickers:
                #         if (pos['size'] > 0) and (pos['symbol'] == ticker):
                #             if pos['side'].upper() == 'BUY':
                #                 side = 'SELL'
                #             else:
                #                 side = 'BUY'
                #             model.account.place_order(symbol=pos['symbol'],
                #                                     expiry=model.model_args['expiries'][pos['symbol']],
                #                                     side=side,
                #                                     order_type='MARKET',
                #                                     qty=pos['size'],
                #                                     reduce_only=True)

                # # Disconnecting
                # ig_stream_service.disconnect()
        except:
            print('Connection lost!')
            print('Connect to IGM Lightstreamer...')
            ig_stream_service.create_session()

            # Registering the Subscriptions
            sub_key_prices = ig_stream_service.ls_client.subscribe(subscription_prices)
            sub_key_account = ig_stream_service.ls_client.subscribe(
                subscription_account)
            sub_key_trades = ig_stream_service.ls_client.subscribe(subscription_trades)

            print('Done!')

            print('Start trading...')


if __name__ == "__main__":
    main()
