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
            open_price REAL,
            close_price REAL,
            profit_loss_percentage REAL,
            open_datetime DATETIME,
            close_datetime DATETIME,
            quantity REAL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()
    logging.info('Database setup complete')

setup_database()

def log_trade(symbol, side, open_price, close_price, profit_loss_percentage, open_datetime, close_datetime, quantity):
    with sqlite3.connect('trades.db') as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO trades (symbol, side, open_price, close_price, profit_loss_percentage, open_datetime, close_datetime, quantity)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (symbol, side, open_price, close_price, profit_loss_percentage, open_datetime, close_datetime, quantity))
        conn.commit()
    logging.info(f"Trade logged: {symbol} {side} at {open_price}/{close_price} for {quantity} with P/L {profit_loss_percentage}%")

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

def get_lot_size(symbol):
    info = client.get_symbol_info(symbol)
    for filt in info['filters']:
        if filt['filterType'] == 'LOT_SIZE':
            return {
                'minQty': float(filt['minQty']),
                'maxQty': float(filt['maxQty']),
                'stepSize': float(filt['stepSize'])
            }
    return None

def adjust_amount(amount, step_size):
    return round(amount - (amount % step_size), 8)

def place_buy_order(symbol, amount):
    try:
        lot_size = get_lot_size(symbol)
        if not lot_size:
            raise Exception("LOT_SIZE filter not found for the symbol")

        # Ensure the amount is within the allowed range
        if amount < lot_size['minQty']:
            raise Exception(f"Amount {amount} is less than the minimum allowed quantity {lot_size['minQty']}")
        if amount > lot_size['maxQty']:
            raise Exception(f"Amount {amount} is greater than the maximum allowed quantity {lot_size['maxQty']}")

        # Adjust the amount to be a multiple of stepSize
        amount = adjust_amount(amount, lot_size['stepSize'])

        order = client.create_order(
            symbol=symbol,
            side=Client.SIDE_BUY,
            type=Client.ORDER_TYPE_MARKET,
            quantity=amount
        )
        if order:
            logging.info(f"Buy order placed for {symbol} amount {amount}")
            return order, amount
        else:
            return None, amount
    except Exception as e:
        message = f"Error placing buy order: {e}"
        telegram(message)
        logging.error(message)
        return None, None

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
            unformatted_quantity = investment_amount / current_price
            buy_order, amount = place_buy_order(symbol, unformatted_quantity)  # Buy with available USDT balance
            
            if buy_order:
                # Place initial stop loss order
                stop_loss_price = current_price * (1 - stop_loss_percentage)
                stop_loss_order = client.create_order(
                    symbol=symbol,
                    side=SIDE_SELL,
                    type=ORDER_TYPE_STOP_LOSS_LIMIT,
                    timeInForce=TIME_IN_FORCE_GTC,
                    quantity=amount,
                    price=str(round(stop_loss_price, 2)),
                    stopPrice=str(round(stop_loss_price, 2))
                )
                stop_loss_order_id = stop_loss_order['orderId']
                message = f"Sell order placed for {symbol} at {current_price}, stop loss at {stop_loss_price}"
                logging.info(message)
                telegram(message)
                
                # Log the buy trade
                open_datetime = pd.to_datetime('now')

                # Monitor and update trailing stop loss
                while True:
                    logging.info("--- UPDATE TRAILING STOP LOSS LOOP START ---")
                    df = fetch_historical_data(symbol,  Client.KLINE_INTERVAL_1MINUTE, 5)
                    close_price = df['close'].iloc[-1]
                    
                    new_stop_loss_price = close_price * (1 - stop_loss_percentage)
                    stop_loss_order_id = update_trailing_stop_loss(stop_loss_order_id, symbol, stop_loss_price, new_stop_loss_price)
                    
                    if stop_loss_order_id is None:
                        sell_message = f"Order is filled for order with ID: {stop_loss_order['orderId']}"
                        logging.info(sell_message)
                        telegram(sell_message)
                        close_datetime = pd.to_datetime('now')
                        profit_loss_percentage = (current_price - stop_loss_price) / stop_loss_price * 100
                        log_trade(symbol, 'SELL', current_price, stop_loss_price, profit_loss_percentage, open_datetime, close_datetime, amount)
                        break

                    # Update the current stop loss price if the trailing stop loss is successfully updated
                    if new_stop_loss_price > stop_loss_price:
                        stop_loss_price = new_stop_loss_price
                        logging.info(f"Stop-loss price updated from {stop_loss_price} to {new_stop_loss_price}")
                    logging.info(f"Stop loss order is not updated and remains at: {stop_loss_price}. ")
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
