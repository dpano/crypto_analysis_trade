import sqlite3
from binance.client import Client
import pandas as pd
import asyncio
import time
from configuration.binance_config import config as binance_config
from configuration.telegram_config import config as telegram_config
from notifications.telegram import send_telegram_message
import ta
from binance.enums import *
import logging

# Configure logging
logging.basicConfig(filename='trading_bot.log', level=logging.INFO, 
                    format='%(asctime)s %(levelname)s:%(message)s')

# Load Binance API configuration
binance_config = binance_config()
api_key = binance_config['api_key']
api_secret = binance_config['api_secret']
client = Client(api_key, api_secret)

symbols = ['TRXUSDT', 'BTCUSDT']
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
def setup_database():
    conn = sqlite3.connect('trades.db')
    cursor = conn.cursor()
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
    conn.close()
    logging.info('Database setup complete')

setup_database()

def log_trade(symbol, side, price, quantity):
    with sqlite3.connect('trades.db') as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO trades (symbol, side, price, quantity)
            VALUES (?, ?, ?, ?)
        ''', (symbol, side, price, quantity))
        conn.commit()
    logging.info(f"Trade logged: {symbol} {side} at {price} for {quantity}")

def telegram(message):
    config = telegram_config()
    asyncio.run(send_telegram_message(config['token'], config['chat_id'], message))
    logging.info(f"Telegram message sent: {message}")

# Fetch historical data
def fetch_historical_data(symbol, interval, limit=300):
    klines = client.get_klines(symbol=symbol, interval=interval, limit=limit)
    df = pd.DataFrame(klines, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_asset_volume', 'number_of_trades', 'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'])
    df['close'] = df['close'].astype(float)
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    logging.info(f"Fetched historical data for {symbol}")
    return df

# Calculate indicators
def calculate_indicators(df):
    macd = ta.trend.MACD(df['close'], window_slow=slow_length, window_fast=fast_length, window_sign=signal_smoothing)
    df['macd'] = macd.macd()
    df['signal'] = macd.macd_signal()
    df['rsi'] = ta.momentum.RSIIndicator(df['close'], window=rsi_length).rsi()
    logging.info("Indicators calculated")
    return df

# Generate signals
def generate_signals(df):
    df['buy_signal'] = ((df['macd'] > df['signal']) & 
                        (df['macd'].shift() <= df['signal'].shift()) &
                        (df['rsi'] > rsi_entry_min) & 
                        (df['rsi'] < rsi_entry_max))
    logging.info("Signals generated")
    return df

# Execute buy order
def place_buy_order(symbol, amount):
    try:
        order = client.order_market_buy(
            symbol=symbol,
            quantity=amount
        )
        if order:
            log_trade(symbol, 'BUY', float(order['fills'][0]['price']), amount)
        logging.info(f"Buy order placed for {symbol} amount {amount}")
        return order
    except Exception as e:
        message = f"Error placing buy order: {e}"
        telegram(message)
        logging.error(message)
        return None

# Execute sell order
def place_sell_order(symbol, amount):
    try:
        order = client.order_market_sell(
            symbol=symbol,
            quantity=amount
        )
        if order:
            log_trade(symbol, 'SELL', float(order['fills'][0]['price']), amount)
        logging.info(f"Sell order placed for {symbol} amount {amount}")
        return order
    except Exception as e:
        message = f"Error placing sell order: {e}"
        telegram(message)
        logging.error(message)
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
        logging.info(f"Trailing stop loss updated for {symbol}")
        return new_order['orderId']
    except Exception as e:
        message = f"Error updating trailing stop loss: {e}"
        telegram(message)
        logging.error(message)
        return None

# Trading logic
def trade(symbol):
    logging.info(f"--- SYMBOL LOOP START ---")
    df = fetch_historical_data(symbol, timeframe)
    df = calculate_indicators(df)
    df = generate_signals(df)
    
    # Get the current price
    current_price = df['close'].iloc[-1]
    logging.info(f"Current price ({symbol}) : {current_price}")
    logging.info(f"buy_signal FOUND: {df['buy_signal'].iloc[-1]}")
    # Check if there is a buy signal
    if df['buy_signal'].iloc[-1]:
        logging.info(f"TRADE BUY SIGNAL at {current_price}")
        balance = client.get_asset_balance(asset='USDT')
        usdt_balance = float(balance['free'])
        if usdt_balance > 10:  # Ensure there's enough balance to trade
            logging.info(f"USDT Balance is sufficient")
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
                logging.info(message)
                telegram(message)
                
                # Monitor and update trailing stop loss
                while True:
                    logging.info("--- UPDATE TRAILING STOP LOSS LOOP START ---")
                    df = fetch_historical_data(symbol,  Client.KLINE_INTERVAL_1MINUTE,5)
                    current_price = df['close'].iloc[-1]
                    
                    new_stop_loss_price = current_price * (1 - stop_loss_percentage)
                    stop_loss_order_id = update_trailing_stop_loss(stop_loss_order_id, symbol, stop_loss_price, new_stop_loss_price)
                    
                    if stop_loss_order_id is None:
                        logging.info(f"stop_loss_order_id not found")
                        break

                    # Update the current stop loss price if the trailing stop loss is successfully updated
                    if new_stop_loss_price > stop_loss_price:
                        stop_loss_price = new_stop_loss_price
                        logging.info(f"Stop-loss price updated from {stop_loss_price} to {new_stop_loss_price}")
                    logging.info("Stop loss order is not updated")
                    time.sleep(60)  # Check every minute

# Main trading loop
def main():
    heartbeat = 0
    telegram('Superman BOT started')
    logging.info('Superman BOT started')
    
    while True:
        logging.info(f"Iteration ({heartbeat + 1})")
        for symbol in symbols:
            trade(symbol)
        
        # Wait for the next candle
        time.sleep(3600)
        heartbeat += 1
        if heartbeat % 24 == 0:
            telegram('Heartbeat - bot is alive')
            logging.info('Heartbeat - bot is alive')

