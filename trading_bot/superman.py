import asyncio
import pandas as pd
import ta
from binance.client import Client
from binance.enums import *
import time
import sqlite3
from configuration import telegram_config
from configuration.binance_config import config as binance_config
import numpy as np

from notifications.telegram import send_telegram_message

# Load Binance API configuration
binance_config = binance_config()
api_key = binance_config['api_key']
api_secret = binance_config['api_secret']
client = Client(api_key, api_secret)

symbols = ['ETHUSDT', 'TRXUSDT', 'BTCUSDT', 'SOLUSDT', 'FTMUSDT', 'NEARUSDT']
timeframe = Client.KLINE_INTERVAL_1HOUR
fast_length = 12
slow_length = 26
signal_smoothing = 9
rsi_length = 14
rsi_overbought = 70
rsi_oversold = 30
rsi_entry_min = 50
rsi_entry_max = 70
investment_percentage = 0.15
stop_loss_percentage = 0.05

# SQLite database setup
conn = sqlite3.connect('trades.db')
cursor = conn.cursor()

# Create trades table if it doesn't exist
cursor.execute('''
    CREATE TABLE IF NOT EXISTS trades (
        id INTEGER PRIMARY KEY,
        symbol TEXT,
        side TEXT,
        price REAL,
        quantity REAL,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
''')
conn.commit()

def telegram(message):
    config = telegram_config()
    asyncio.run(send_telegram_message(config['token'], config['chat_id'], message))

# Fetch historical data
def fetch_historical_data(symbol, interval, limit=100):
    klines = client.get_klines(symbol=symbol, interval=interval, limit=limit)
    df = pd.DataFrame(klines, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_asset_volume', 'number_of_trades', 'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'])
    df['close'] = df['close'].astype(float)
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    return df

# Calculate indicators
def calculate_indicators(df):
    macd = ta.trend.MACD(df['close'], window_slow=slow_length, window_fast=fast_length, window_sign=signal_smoothing)
    df['macd'] = macd.macd()
    df['signal'] = macd.macd_signal()
    df['rsi'] = ta.momentum.RSIIndicator(df['close'], window=rsi_length).rsi()
    return df

# Generate signals
def generate_signals(df):
    df['buy_signal'] = ((df['macd'] > df['signal']) & 
                        (df['macd'].shift() <= df['signal'].shift()) &
                        (df['rsi'] > rsi_entry_min) & 
                        (df['rsi'] < rsi_entry_max))
    return df

# Execute buy order
def place_buy_order(symbol, amount):
    try:
        order = client.order_market_buy(
            symbol=symbol,
            quantity=amount
        )
        if order:
            cursor.execute('''
                INSERT INTO trades (symbol, side, price, quantity)
                VALUES (?, ?, ?, ?)
            ''', (symbol, 'BUY', float(order['fills'][0]['price']), amount))
            conn.commit()
        return order
    except Exception as e:
        message = f"Error placing buy order: {e}"
        telegram(message)
        print(message)
        return None

# Execute sell order
def place_sell_order(symbol, amount):
    try:
        order = client.order_market_sell(
            symbol=symbol,
            quantity=amount
        )
        if order:
            cursor.execute('''
                INSERT INTO trades (symbol, side, price, quantity)
                VALUES (?, ?, ?, ?)
            ''', (symbol, 'SELL', float(order['fills'][0]['price']), amount))
            conn.commit()
        return order
    except Exception as e:
        message = f"Error placing sell order: {e}"
        telegram(message)
        print(message)
        return None

# Update trailing stop loss
def update_trailing_stop_loss(order_id, symbol, current_stop_loss_price, new_stop_price):
    try:
        if new_stop_price <= current_stop_loss_price:
            return order_id  # Do not update if new stop price is not higher

        order = client.get_order(symbol=symbol, orderId=order_id)
        if order['status'] == 'FILLED':
            return None  # Order already filled

        client.cancel_order(symbol=symbol, orderId=order_id)
        new_order = client.create_order(
            symbol=symbol,
            side=SIDE_SELL,
            type=ORDER_TYPE_STOP_LOSS_LIMIT,
            timeInForce=TIME_IN_FORCE_GTC,
            quantity=order['origQty'],
            price=str(round(new_stop_price, 2)),
            stopPrice=str(round(new_stop_price, 2))
        )
        return new_order['orderId']
    except Exception as e:
        message = f"Error updating trailing stop loss: {e}"
        telegram(message)
        print(message)
        return None

# Trading logic
def trade(symbol, initial_balance):
    df = fetch_historical_data(symbol, timeframe)
    df = calculate_indicators(df)
    df = generate_signals(df)
    
    # Get the current price
    current_price = df['close'].iloc[-1]
    
    # Check if there is a buy signal
    if df['buy_signal'].iloc[-1]:
        balance = client.get_asset_balance(asset='USDT')
        usdt_balance = float(balance['free'])
        if usdt_balance > 10:  # Ensure there's enough balance to trade
            investment_amount = usdt_balance * investment_percentage
            quantity = investment_amount / current_price
            buy_order = place_buy_order(symbol, round(quantity, 6))  # Buy with available USDT balance
            
            if buy_order:
                # Place initial stop loss order
                stop_loss_price = current_price * (1 - stop_loss_percentage)
                stop_loss_order = client.create_order(
                    symbol=symbol,
                    side=SIDE_SELL,
                    type=ORDER_TYPE_STOP_LOSS_LIMIT,
                    timeInForce=TIME_IN_FORCE_GTC,
                    quantity=round(quantity, 6),
                    price=str(round(stop_loss_price, 2)),
                    stopPrice=str(round(stop_loss_price, 2))
                )
                stop_loss_order_id = stop_loss_order['orderId']
                message = f"Buy order placed for {symbol} at {current_price}, stop loss at {stop_loss_price}"
                print(message)
                telegram(message)
                
                # Monitor and update trailing stop loss
                while True:
                    df = fetch_historical_data(symbol, timeframe)
                    current_price = df['close'].iloc[-1]
                    
                    new_stop_loss_price = current_price * (1 - stop_loss_percentage)
                    stop_loss_order_id = update_trailing_stop_loss(stop_loss_order_id, symbol, stop_loss_price, new_stop_loss_price)
                    
                    if stop_loss_order_id is None:
                        break

                    # Update the current stop loss price if the trailing stop loss is successfully updated
                    if new_stop_loss_price > stop_loss_price:
                        stop_loss_price = new_stop_loss_price
                    
                    time.sleep(60)  # Check every minute

# Main trading loop
def main():
    heartbeat = 0
    telegram('Superman BOT started')
    initial_balance = float(client.get_asset_balance(asset='USDT')['free'])
    
    while True:
        for symbol in symbols:
            trade(symbol, initial_balance)
        
        # Wait for the next candle
        time.sleep(3600)
        heartbeat += 1
        if heartbeat % 24 == 0:
            telegram('Heartbeat - bot is alive')

if __name__ == "__main__":
    main()
