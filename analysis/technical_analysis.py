import ta
import time

from db.database import fetch_data, store_last_signal
from analysis.send_signal import send_signal

def calculate_indicators(df):
    # Symbol
    df['symbol'] = df['symbol']
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

def signal_type(df):
    # Ensure columns exist
    for column in ['death_cross', 'golden_cross', 'overbought', 'oversold']:
        if column not in df.columns:
            raise KeyError(f"Column {column} not found in DataFrame.")

    # Initialize the 'last_signal' column with empty strings
    df['last_signal'] = 'HOLD'

    # Apply SELL signals
    df.loc[(df['death_cross'] & df['overbought']) | (df['golden_cross'] & df['overbought']), 'last_signal'] = 'SELL'

    # Apply BUY signals
    df.loc[(df['golden_cross'] & df['oversold']) | (df['death_cross'] & df['oversold']), 'last_signal'] = 'BUY'

    # Apply HOLD signals
    df.loc[(df['golden_cross'] & ~df['oversold'] & ~df['overbought']) | (df['death_cross'] & ~df['oversold'] & ~df['overbought']), 'last_signal'] = 'HOLD'

    return df


def start_market_pair_analysis(symbols=['BTCUSDT'], sleep=86400):
    while True:
        for symbol in symbols:
            df = fetch_data(symbol)
            df = calculate_indicators(df)  # Calculate technical indicators
            df = analyze_signals(df)  # Analyze for trading signals
            df = signal_type(df) # set signal type

            # Assuming analyze_signals returns a DataFrame with a 'last_signal' column
            last_signal_row = df.iloc[-1]  # Get the last row which should have the latest signal

            store_last_signal(symbol, last_signal_row['start_time'], 
                              last_signal_row['last_signal'], 
                              last_signal_row['rsi'], 
                              last_signal_row['sma_50'],
                              last_signal_row['sma_200'],
                              int(last_signal_row['golden_cross']),
                              int(last_signal_row['death_cross']),
                              int(last_signal_row['overbought']),
                              int(last_signal_row['oversold'])
                              )

            # Optional: Print or log the analysis
            print(f"Last signal for {symbol}: {last_signal_row['last_signal']} at {last_signal_row['start_time']}")
            if last_signal_row['last_signal'] == 'SELL' or last_signal_row['last_signal'] == 'BUY':
                send_signal(last_signal_row['last_signal'],symbol,'TELEGRAM')
        time.sleep(sleep)        

