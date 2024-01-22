import sys

sys.path.append('../')

from binance.client import Client
from dotenv import load_dotenv
from src.backtest.BacktestTradingModel import BacktestTradingModel
from src.models.checklist_model import checklist_model
import os
import pandas as pd
from src.helper_functions.statistics import sma
import argparse

load_dotenv()

BINANCE_KEY = os.getenv('BINANCE_KEY')
BINANCE_SECRET = os.getenv('BINANCE_SECRET')

import yaml
from dotenv import load_dotenv
import os

load_dotenv()

CONFIG_DIR = os.getenv('CONFIG_DIR')

# Load variables from the YAML file
with open(CONFIG_DIR, 'r') as file:
    config = yaml.safe_load(file)

# Access variables from the loaded data
BASE_CUR = config.get('base_cur', 'USDT')

# pull historical data from binance and add to market data history
binance_client = Client(BINANCE_KEY, BINANCE_SECRET)
# binance_client = None


def main():

    # parse arguments
    parser = argparse.ArgumentParser(description="Run backtest for trading.")

    parser.add_argument('--tickers', type=str, default="RTYUSD")
    parser.add_argument('--tick_sizes',
                        type=str,
                        default="0.1",
                        help="Tick size for each ticker")
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

    parser.add_argument('--model_args',
                        type=str,
                        default=str({'param': 1}),
                        help="optional arguments for trading model")
    parser.add_argument(
        '--start_history',
        type=str,
        help=" start for historical data for modelformat yyyy-mm-dd hh:mm:ss")
    parser.add_argument('--start_str',
                        type=str,
                        help="start for backtest format yyyy-mm-dd hh:mm:ss")
    parser.add_argument('--end_str',
                        type=str,
                        help="end for backtest format yyyy-mm-dd hh:mm:ss")

    args = parser.parse_args()
    args = vars(args)

    freqs = args['freqs'].split()
    tick_sizes_raw = args['tick_sizes'].split()
    trading_freqs = args['trading_freqs'].split()
    tickers = args['tickers'].split()

    model_args = eval(args['model_args'])

    tick_sizes = {
        ticker: float(tick_size)
        for ticker, tick_size in zip(tickers, tick_sizes_raw)
    }

    model_args['tickers'] = tickers
    model_args['tick_sizes'] = tick_sizes
    model_args['expiries'] = {ticker: 'None' for ticker in tickers}
    model_args['trading_freqs'] = trading_freqs
    model_args['open'] = None
    model_args['reduce_only'] = True

    BACKTEST_SYMBOLS = {
        '{}.{}m'.format(ticker, freq): 'candle.{}.{}'.format(freq, ticker)
        for freq in freqs for ticker in tickers
    }
    BINANCE_BYBIT_MAPPING = {
        'candle.{}.{}'.format(freq, ticker): '{}'.format(ticker)
        for freq in freqs for ticker in tickers
    }

    PUBLIC_TOPICS = [
        "candle.{}.{}".format(freq, ticker)
        for freq in freqs
        for ticker in tickers
    ]

    symbols = [ticker[:-len(BASE_CUR)] for ticker in tickers]
    symbols.extend([ticker[-len(BASE_CUR):] for ticker in tickers])

    budget = {}
    for ticker in tickers:
        budget[ticker[-len(BASE_CUR):]] = 1000
        budget[ticker[:-len(BASE_CUR)]] = 0

    # instantiate model
    model = BacktestTradingModel(model=checklist_model,
                                 http_session=binance_client,
                                 symbols=symbols,
                                 budget=budget,
                                 topics=PUBLIC_TOPICS,
                                 topic_mapping=BINANCE_BYBIT_MAPPING,
                                 backtest_symbols=BACKTEST_SYMBOLS,
                                 model_args=model_args,
                                 model_storage={
                                     'open': None,
                                     'close': None,
                                     'entry_bar_time': pd.Timestamp(0)
                                 })

    # create performance report
    model.run_backtest(symbols=BACKTEST_SYMBOLS,
                       start_history=args['start_history'],
                       start_str=args['start_str'],
                       end_str=args['end_str'],
                       save_output=True)


if __name__ == "__main__":
    main()
