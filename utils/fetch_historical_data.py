
import os
from configuration.binance_config import config 
from db.database import setup_database
from utils.ticker_client import binance_client, fetch_and_process_historical_data, process_trading_pairs, trading_pairs
from binance.client import Client

def get_data():
    setup_database()
    conf = config()
    client = binance_client(conf)
    pairs = trading_pairs()
    process_trading_pairs(client, pairs, fetch_and_process_historical_data)