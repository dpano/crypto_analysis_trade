import datetime
from binance.client import Client
import pprint
from db.database import insert_data
from helpers.data_manipulation import transform_timestamp_to_date


def binance_client(config):
    return Client(config['api_key'], config['api_secret'])

def trading_pairs():
    return ['BTCUSDT', 'ETHUSDT', 'BNBUSDT','SOLUSDT','ADAUSDT','DOGEUSDT','AVAXUSDT','DOTUSDT','LINKUSDT','TRXUSDT','ICPUSDT','MATICUSDT','NEARUSDT','UNIUSDT']

# High-order function to process trading pairs
def process_trading_pairs(client, pairs, process_fn):
    return [process_fn(client, pair) for pair in pairs]

# Function to fetch and process candlesticks data
def fetch_and_process_candlesticks(client, symbol, interval=Client.KLINE_INTERVAL_1DAY):
    klines = client.get_klines(symbol=symbol, interval=interval, limit=1)
    pprint.pprint(klines)
    # Data processing (functional approach)
    data = process_kline(klines[0],symbol)
    insert_data(**data)

# Function to fetch and process historical data    
def fetch_and_process_historical_data(client, symbol,start_str = "1 Jan, 2021", interval=Client.KLINE_INTERVAL_1DAY):
    klines = client.get_historical_klines(symbol, interval, start_str)
    for kline in klines:
        data = process_kline(kline,symbol)
        insert_data(**data)

def process_kline(kline, symbol):
    return {
        'start_time': transform_timestamp_to_date(kline[0]),
        'end_time': transform_timestamp_to_date(kline[6]),
        'event_timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'open': kline[1],
        'high': kline[2],
        'low': kline[3],
        'close': kline[4],
        'volume': kline[5],
        'symbol': symbol
    }