import ta
import time

from db.database import fetch_daily_data, fetch_data
from signal.signals import should_send_oportunity_signal

def calculate_indicators(df):
    # Calculate the 14-period RSI
    df['rsi'] = ta.momentum.RSIIndicator(df['close'], window=14).rsi()
    
    # Calculate the 50-period SMA
    df['sma_50'] = ta.trend.SMAIndicator(df['close'], window=50).sma_indicator()
    
    # Calculate the 200-period SMA
    df['sma_200'] = ta.trend.SMAIndicator(df['close'], window=200).sma_indicator()
    
    return df

def analyze_signals(df):
    # Golden Cross
    df['golden_cross'] = df['sma_50'] > df['sma_200']
    # Death Cross
    df['death_cross'] = df['sma_50'] < df['sma_200']
    # Overbought condition (RSI > 70)
    df['overbought'] = df['rsi'] > 70
    # Oversold condition (RSI < 30)
    df['oversold'] = df['rsi'] < 30
    
    return df

def start_analysis(sleep = 60):
    while True:
        df = fetch_data()
        df = calculate_indicators(df)  # Calculate technical indicators
        df = analyze_signals(df)  # Analyze for trading signals
        for index, row in df.iterrows():
            if should_send_oportunity_signal(row['rsi'], row['golden_cross'], row['death_cross']):
                # Here is where you would send an email
                print(f"Adjust purchase for data at {index}. Conditions met.")
        print(df.info(verbose=True))
        print(df.tail(10))
        time.sleep(sleep)

