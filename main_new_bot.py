from binance.client import Client
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from configuration.binance_config import config as binance_config
from configuration.telegram_config import config as telegram_config
from notifications.telegram import send_telegram_message
import time
import asyncio
# Initialize the Binance client
binance_config = binance_config()
api_key = binance_config['api_key']
api_secret = binance_config['api_secret']
symbol = 'ETHUSDT'
timeframe = '1h'
sma_period = 50
lma_period = 200
macd_short = 12
macd_long = 26
macd_signal = 9
rsi_period = 14

def fetch_data(symbol, interval):
    klines = Client.get_klines(symbol=symbol, interval=interval)
    df = pd.DataFrame(klines, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_asset_volume', 'number_of_trades', 'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'])
    df['close'] = df['close'].astype(float)
    return df

def calculate_indicators(df):
    df['SMA'] = df['close'].rolling(sma_period).mean()
    df['LMA'] = df['close'].rolling(lma_period).mean()
    df['MACD'] = df['close'].ewm(span=macd_short, adjust=False).mean() - df['close'].ewm(span=macd_long, adjust=False).mean()
    df['MACD_Signal'] = df['MACD'].ewm(span=macd_signal, adjust=False).mean()
    df['RSI'] = 100 - (100 / (1 + df['close'].diff(1).clip(lower=0).ewm(com=rsi_period-1, adjust=False).mean() / df['close'].diff(1).clip(upper=0).abs().ewm(com=rsi_period-1, adjust=False).mean()))
    return df

def place_order(symbol, side, quantity, order_type=Client.ORDER_TYPE_MARKET):
    try:
        order = Client.create_order(
            symbol=symbol,
            side=side,
            type=order_type,
            quantity=quantity
        )
        print(f"Order placed: {order}")
        telegram(f"Executing {side} order for {quantity} {symbol}")
    except Exception as e:
        telegram(f"Error Executing {side} order for {quantity} {symbol}")
        print(f"An error occurred: {e}")

def telegram(message):
    config = telegram_config()
    asyncio.run(send_telegram_message(config['token'], config['chat_id'], message))     

def main():
    quantity = 0.0015  # Adjust this to your desired trade amount
    while True:
        df = fetch_data(symbol, timeframe)
        df = calculate_indicators(df)

        if df['SMA'].iloc[-2] < df['LMA'].iloc[-2] and df['SMA'].iloc[-1] > df['LMA'].iloc[-1] and df['MACD'].iloc[-1] > df['MACD_Signal'].iloc[-1] and df['RSI'].iloc[-1] > 50 and df['RSI'].iloc[-1] < 70:
            print("Buy Signal")
            # Implement your buy logic here
            place_order(symbol, Client.SIDE_BUY, quantity)
        if df['SMA'].iloc[-2] > df['LMA'].iloc[-2] and df['SMA'].iloc[-1] < df['LMA'].iloc[-1] and df['MACD'].iloc[-1] < df['MACD_Signal'].iloc[-1] and df['RSI'].iloc[-1] < 50 and df['RSI'].iloc[-1] > 30:
            print("Sell Signal")
            # Implement your sell logic here
            place_order(symbol, Client.SIDE_SELL, quantity)
        time.sleep(60 * 60)  # Wait for 1 hour before the next iteration

if __name__ == "__main__":
    main()