import sys

sys.path.append('../')

from src.backtest.BacktestTradingModel import BacktestTradingModel
from src.models.checklist_model import checklist_model
import os
import pandas as pd
from src.helper_functions.statistics import sma
import argparse
from dotenv import load_dotenv

load_dotenv()

BASE_CUR = os.getenv('BASE_CUR')

binance_client = None


def main():

    # parse arguments
    parser = argparse.ArgumentParser(
        description="Run backtest for futures trading.")

    parser.add_argument('--ticker', type=str, default="RTYUSD")
    parser.add_argument(
        '--freqs',
        type=str,
        default="1 5 15",
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
    model_args = eval(args['model_args'])
    model_args['ticker'] = args['ticker']

    ticker = args['ticker']
    BACKTEST_SYMBOLS = {
        '{}.{}m'.format(ticker, freq): 'candle.{}.{}'.format(freq, ticker)
        for freq in freqs
    }
    BINANCE_BYBIT_MAPPING = {
        'candle.{}.{}'.format(freq, ticker): '{}'.format(ticker)
        for freq in freqs
    }

    PUBLIC_TOPICS = ["candle.{}.{}".format(freq, ticker) for freq in freqs]

    # instantiate model
    model = BacktestTradingModel(
        model=checklist_model,
        http_session=binance_client,
        symbols=[ticker[:-len(BASE_CUR)], ticker[-len(BASE_CUR):]],
        budget={
            ticker[-len(BASE_CUR):]: 1000,
            ticker[:-len(BASE_CUR)]: 0
        },
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
