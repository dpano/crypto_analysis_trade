import asyncio
import pandas as pd
import ta
import time
from binance.client import Client
from binance.enums import *
from configuration.binance_config import config as binance_config
from db.database import log_trade, setup_database
from configuration.telegram_config import config as telegram_config
from notifications.telegram import send_telegram_message

# Set up Binance API
binance_config = binance_config()
api_key = binance_config['api_key']
api_secret = binance_config['api_secret']

client = Client(api_key, api_secret)

symbol = 'ETHUSDT'  # Example symbol
timeframe = '4h'    # Example timeframe
fast_length = 12
slow_length = 26
signal_smoothing = 9
rsi_length = 14
rsi_overbought = 70
rsi_oversold = 30
rsi_entry_min = 40
rsi_entry_max = 60
investment_percentage = 0.1  # 10% of equity

def fetch_ohlcv(symbol, timeframe):
    klines = client.get_klines(symbol=symbol, interval=timeframe)
    df = pd.DataFrame(klines, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_asset_volume', 'number_of_trades', 'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df['close'] = df['close'].astype(float)
    return df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]

def calculate_indicators(df):
    macd = ta.trend.MACD(df['close'], window_slow=slow_length, window_fast=fast_length, window_sign=signal_smoothing)
    df['macd'] = macd.macd()
    df['signal'] = macd.macd_signal()
    df['rsi'] = ta.momentum.RSIIndicator(df['close'], window=rsi_length).rsi()
    return df

def generate_signals(df):
    df['buy_signal'] = ((df['macd'] > df['signal']) & 
                        (df['macd'].shift() <= df['signal'].shift()) &
                        (df['rsi'] > rsi_entry_min) & 
                        (df['rsi'] < rsi_entry_max))
    
    df['sell_signal'] = ((df['macd'] < df['signal']) & 
                         (df['macd'].shift() >= df['signal'].shift()) &
                         (df['rsi'] > rsi_overbought))
    
    df['short_signal'] = ((df['macd'] < df['signal']) & 
                          (df['macd'].shift() >= df['signal'].shift()) &
                          (df['rsi'] > rsi_entry_min) & 
                          (df['rsi'] < rsi_entry_max))
    
    df['cover_signal'] = ((df['macd'] > df['signal']) & 
                          (df['macd'].shift() <= df['signal'].shift()) &
                          (df['rsi'] < rsi_oversold))
    return df

def execute_trade(signal, symbol, side, quantity):
    if signal:
        price = client.get_symbol_ticker(symbol=symbol)['price']
        price = float(price)
        if side == 'buy':
            telegram(f"Executing buy order for {quantity} {symbol}")
            #order = client.order_market_buy(symbol=symbol, quantity=quantity)
        elif side == 'sell':
            telegram(f"Executing sell order for {quantity} {symbol}")
            #order = client.order_market_sell(symbol=symbol, quantity=quantity)
        
        # Log the trade
        log_trade(symbol, side, price, quantity)

def run_bot():
    df = fetch_ohlcv(symbol, timeframe)
    df = calculate_indicators(df)
    df = generate_signals(df)
    
    balance = client.get_asset_balance(asset='USDT')
    equity = float(balance['free'])
    investment_amount = equity * investment_percentage

    last_row = df.iloc[-1]
    
    if last_row['buy_signal']:
        execute_trade(True, symbol, 'buy', investment_amount / last_row['close'])
    elif last_row['sell_signal']:
        execute_trade(True, symbol, 'sell', investment_amount / last_row['close'])
    elif last_row['short_signal']:
        execute_trade(True, symbol, 'sell', investment_amount / last_row['close'])
    elif last_row['cover_signal']:
        execute_trade(True, symbol, 'buy', investment_amount / last_row['close'])

def telegram(message):
    config = telegram_config()
    asyncio.run(send_telegram_message(config['token'], config['chat_id'], message))     

if __name__ == "__main__":
    setup_database()
    telegram('Trading bot started')
    while True:
        run_bot()
        time.sleep(60 * 60)  # Run every hour (timeframe = 1h)
