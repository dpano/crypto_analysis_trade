import time
from brokers.binance import binance_client, fetch_and_process_candlesticks, process_trading_pairs, trading_pairs
from configuration.binance_config import config 

def start_ticker():
    conf = config()
    client = binance_client(conf)
    pairs = trading_pairs()
    while True:
        process_trading_pairs(client, pairs, fetch_and_process_candlesticks)
        time.sleep(86400)  # Functional approach avoids explicit loop control inside processing

