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

BASE_CUR = os.getenv('BASE_CUR')

# pull historical data from binance and add to market data history
binance_client = Client(BINANCE_KEY, BINANCE_SECRET)
# binance_client = None


def main():

    # parse arguments
    parser = argparse.ArgumentParser(description="Run backtest for trading.")

    parser.add_argument('--tickers', type=str, default="RTYUSD")
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
    trading_freqs = args['trading_freqs'].split()
    tickers = args['tickers'].split()

    model_args = eval(args['model_args'])

    model_args['tickers'] = tickers
    model_args['expiries'] = {ticker: 'None' for ticker in tickers}
    model_args['trading_freqs'] = trading_freqs

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
                                     'entry_body_1_long': None,
                                     'entry_close_1_long': None,
                                     'entry_open_1_long': None,
                                     'entry_body_1_short': None,
                                     'entry_close_1_short': None,
                                     'entry_open_1_short': None,
                                     'exit_long_higher_lows': [],
                                     'exit_short_lower_highs': [],
                                     'entry_bar_time': pd.Timestamp(0),
                                     'action_bar_time': pd.Timestamp(0)
                                 })

    # create performance report
    model.run_backtest(symbols=BACKTEST_SYMBOLS,
                       start_history=args['start_history'],
                       start_str=args['start_str'],
                       end_str=args['end_str'],
                       save_output=True)


if __name__ == "__main__":
    main()
