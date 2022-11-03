from dotenv import load_dotenv
import os

load_dotenv()

BYBIT_KEY = os.getenv('BYBIT_KEY')
BYBIT_SECRET = os.getenv('BYBIT_SECRET')

BINANCE_KEY = os.getenv('BINANCE_KEY')
BINANCE_SECRET = os.getenv('BINANCE_SECRET')


def main():
    return None


if __name__ == "__main__":
    main()
