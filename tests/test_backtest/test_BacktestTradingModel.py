# !/usr/bin/env python
# coding: utf-8

import pandas as pd
import json
from dotenv import load_dotenv
import os
from typing import Any, Dict
from src.backtest.BacktestMarketData import BacktestMarketData
from src.backtest.BacktestAccountData import BacktestAccountData
from src.TradingModel import TradingModel
import unittest

load_dotenv()

PUBLIC_TOPICS = eval(os.getenv('PUBLIC_TOPICS'))
PRIVATE_TOPICS = eval(os.getenv('PRIVATE_TOPICS'))

HIST_TICKERS = eval(os.getenv('HIST_TICKERS'))


class TestBacktestTradingModel(unittest.TestCase):

    def setUp(self):
        pass
