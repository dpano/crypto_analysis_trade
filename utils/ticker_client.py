import datetime
import os
import time
from binance.client import Client
import pprint

from db.database import insert_data
from helpers.data_manipulation import transform_timestamp_to_date

# Configuration function
def config():
    return {
        'api_key': os.environ.get('BINANCE_API_KEY'),
        'api_secret': os.environ.get('BINANCE_API_SECRET')
    }

# Functional approach to create a Binance client
def binance_client(config):
    return Client(config['api_key'], config['api_secret'])

def trading_pairs():
    return ['BTCUSDT', 'ETHUSDT', 'BNBUSDT']

# High-order function to process trading pairs
def process_trading_pairs(client, pairs, process_fn):
    return [process_fn(client, pair) for pair in pairs]

# Function to fetch and process candlesticks data
def fetch_and_process_candlesticks(client, symbol, interval=Client.KLINE_INTERVAL_1MINUTE):
    klines = client.get_klines(symbol=symbol, interval=interval, limit=1)
    pprint.pprint(klines)
    # Data processing (functional approach)
    data = {
        'start_time': transform_timestamp_to_date(klines[0][0]),
        'end_time': transform_timestamp_to_date(klines[0][6]),
        'event_timestamp': datetime.datetime.today().strftime('%Y-%m-%d %H:%M:%S'),
        'open': klines[0][1],
        'high': klines[0][2],
        'low': klines[0][3],
        'close': klines[0][4],
        'volume': klines[0][5],
        'symbol': symbol
    }
    insert_data(**data)

def start_ticker():
    conf = config()
    client = binance_client(conf)
    pairs = trading_pairs()
    while True:
        process_trading_pairs(client, pairs, fetch_and_process_candlesticks)
        time.sleep(60)  # Functional approach avoids explicit loop control inside processing

