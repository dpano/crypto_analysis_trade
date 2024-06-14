from binance.client import Client
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from configuration.binance_config import config as binance_config
# Initialize the Binance client
binance_config = binance_config()
api_key = binance_config['api_key']
api_secret = binance_config['api_secret']
client = Client(api_key, api_secret)

symbol = 'BTCUSDT'
timeframe = '1h'
sma_period = 50
lma_period = 200
macd_short = 12
macd_long = 26
macd_signal = 9
rsi_period = 14

def fetch_data(symbol, interval):
    klines = client.get_klines(symbol=symbol, interval=interval, limit=1000)
    df = pd.DataFrame(klines, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_asset_volume', 'number_of_trades', 'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'])
    df['close'] = df['close'].astype(float)
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)
    return df

def calculate_indicators(df):
    df['SMA'] = df['close'].rolling(sma_period).mean()
    df['LMA'] = df['close'].rolling(lma_period).mean()
    df['MACD'] = df['close'].ewm(span=macd_short, adjust=False).mean() - df['close'].ewm(span=macd_long, adjust=False).mean()
    df['MACD_Signal'] = df['MACD'].ewm(span=macd_signal, adjust=False).mean()
    df['RSI'] = 100 - (100 / (1 + df['close'].diff(1).clip(lower=0).ewm(com=rsi_period-1, adjust=False).mean() / df['close'].diff(1).clip(upper=0).abs().ewm(com=rsi_period-1, adjust=False).mean()))
    return df

def backtest(df):
    df['Signal'] = 0
    df['Signal'][sma_period:] = np.where(
        (df['SMA'][sma_period:] > df['LMA'][sma_period:]) & 
        (df['MACD'][sma_period:] > df['MACD_Signal'][sma_period:]) & 
        (df['RSI'][sma_period:] > 50) & (df['RSI'][sma_period:] < 70), 1, 0)
    
    df['Signal'][sma_period:] = np.where(
        (df['SMA'][sma_period:] < df['LMA'][sma_period:]) & 
        (df['MACD'][sma_period:] < df['MACD_Signal'][sma_period:]) & 
        (df['RSI'][sma_period:] < 50) & (df['RSI'][sma_period:] > 30), -1, df['Signal'][sma_period:])

    df['Position'] = df['Signal'].shift()
    df['Daily_Return'] = df['close'].pct_change()
    df['Strategy_Return'] = df['Daily_Return'] * df['Position']

    df['Cumulative_Market_Return'] = (1 + df['Daily_Return']).cumprod()
    df['Cumulative_Strategy_Return'] = (1 + df['Strategy_Return']).cumprod()

    return df

def plot_results(df):
    plt.figure(figsize=(12, 8))
    plt.plot(df['Cumulative_Market_Return'], label='Market Return')
    plt.plot(df['Cumulative_Strategy_Return'], label='Strategy Return')
    plt.legend()
    plt.title(f"{symbol} {timeframe}")
    plt.show()

def main():
    df = fetch_data(symbol, timeframe)
    df = calculate_indicators(df)
    df = backtest(df)
    plot_results(df)
    print(f"Final Market Return: {df['Cumulative_Market_Return'].iloc[-1]:.2f}")
    print(f"Final Strategy Return: {df['Cumulative_Strategy_Return'].iloc[-1]:.2f}")

if __name__ == "__main__":
    main()
