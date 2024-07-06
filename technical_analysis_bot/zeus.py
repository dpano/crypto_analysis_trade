import ta
import time
from binance.client import Client
from configuration.binance_config import config as binance_config
from db.database import fetch_data, store_last_signal
from analysis.send_signal import send_signal
from notifications.telegram import send_telegram_message
from configuration.telegram_config import config as telegram_config
import asyncio
import pandas as pd

# Load Binance API configuration
binance_config = binance_config()
api_key = binance_config['api_key']
api_secret = binance_config['api_secret']
client = Client(api_key, api_secret)

def calculate_indicators(df):
    # Symbol
    df['symbol'] = df['symbol']
    # Calculate the 14-period RSI
    df['rsi'] = ta.momentum.RSIIndicator(df['close'], window=14).rsi()
    
    # Calculate the 50-period SMA
    df['sma_50'] = ta.trend.SMAIndicator(df['close'], window=50).sma_indicator()
    
    # Calculate the 200-period SMA
    df['sma_200'] = ta.trend.SMAIndicator(df['close'], window=200).sma_indicator()
    
    # Calculate Bollinger Bands
    df['bb_high'], df['bb_mid'], df['bb_low'] = ta.volatility.bollinger_hband_indicator(df['close']), ta.volatility.bollinger_mavg(df['close']), ta.volatility.bollinger_lband_indicator(df['close'])
    
    return df

def get_historical_data(symbol, interval, lookback):
    klines = client.get_historical_klines(symbol, interval, lookback)
    data = pd.DataFrame(klines, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 
                                         'quote_asset_volume', 'number_of_trades', 'taker_buy_base_asset_volume', 
                                         'taker_buy_quote_asset_volume', 'ignore'])
    data['timestamp'] = pd.to_datetime(data['timestamp'], unit='ms')
    data.set_index('timestamp', inplace=True)
    data = data[['open', 'high', 'low', 'close', 'volume']]
    data = data.astype(float)
    data['symbol'] = symbol
    return data

def generate_signals(data):
    signals = pd.DataFrame(index=data.index)
    signals['signal'] = 0

    # Buy signal: RSI below 30 and price crosses above the lower Bollinger Band
    signals.loc[(data['rsi'] < 30) & (data['close'] > data['bb_low']), 'signal'] = 1

    # Sell signal: RSI above 70 and price crosses below the upper Bollinger Band
    signals.loc[(data['rsi'] > 70) & (data['close'] < data['bb_high']), 'signal'] = -1
    
    # Golden cross signal: 50 SMA crosses above 200 SMA
    signals.loc[(data['sma_50'].shift(1) < data['sma_200'].shift(1)) & (data['sma_50'] > data['sma_200']), 'signal'] = 2
    
    # Death cross signal: 50 SMA crosses below 200 SMA
    signals.loc[(data['sma_50'].shift(1) > data['sma_200'].shift(1)) & (data['sma_50'] < data['sma_200']), 'signal'] = -2

    return signals

def get_last_signal(signals, data, symbol):
    
    last_signal = signals['signal'].iloc[-1]
    print(last_signal)
    if last_signal == 1:
        telegram(f"Buy signal generated for {symbol} at {signals.index[-1]}.\nPrice: {data['close'].iloc[-1]}")
    elif last_signal == -1:
        telegram(f"Sell signal generated for {symbol} at {signals.index[-1]}.\nPrice: {data['close'].iloc[-1]}")
    elif last_signal == 2:
        telegram(f"Golden cross detected for {symbol} at {signals.index[-1]}.\nPrice: {data['close'].iloc[-1]}")
    elif last_signal == -2:
        telegram(f"Death cross detected for {symbol} at {signals.index[-1]}.\nPrice: {data['close'].iloc[-1]}")

def telegram(message):
    config = telegram_config()
    asyncio.run(send_telegram_message(config['token'], config['chat_id'], message))

def zeus_main(symbols=['BTCUSDT', 'ETHUSDT', 'TRXUSDT', 'SOLUSDT'], sleep=3600):
    heartbeat = 0
    while True:
        for symbol in symbols:
            df = get_historical_data(symbol, '1h', '1 month ago UTC')
            df = calculate_indicators(df)
            signals = generate_signals(df)
            get_last_signal(signals, df, symbol)
        time.sleep(sleep)
        heartbeat += 1
        if heartbeat % 24 == 0:
            telegram('Heartbeat - ZEUS is alive')
