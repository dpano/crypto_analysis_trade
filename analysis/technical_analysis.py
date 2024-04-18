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
    # Initialize the 'last_signal' column with empty strings
    df['last_signal'] = 'HOLD'

    # Create SELL signal conditions
    sell_conditions = [
        (df['death_cross'] & df['overbought']),  # Death cross and overbought: likely a strong sell
        (df['golden_cross'] & df['overbought'])  # Golden cross but overbought: consider selling if too high too quickly
    ]
    # Combine sell conditions using any()
    df.loc[df[sell_conditions].any(axis=1), 'last_signal'] = 'SELL'

    # Create BUY signal conditions
    buy_conditions = [
        (df['golden_cross'] & df['oversold']),  # Golden cross and oversold: strong buy signal
        (df['death_cross'] & df['oversold'])    # Death cross but oversold: might be an overreaction, consider buying
    ]
    # Combine buy conditions using any()
    df.loc[df[buy_conditions].any(axis=1), 'last_signal'] = 'BUY'

    # HOLD signals could be considered explicitly or implicitly by the absence of buy/sell conditions
    # For example, you might explicitly want to set HOLD under specific conditions
    hold_conditions = [
        (df['golden_cross'] & ~df['oversold'] & ~df['overbought']),  # Golden cross but not overbought or oversold
        (df['death_cross'] & ~df['oversold'] & ~df['overbought'])    # Death cross but not overbought or oversold
    ]
    # Combine hold conditions using any()
    df.loc[df[hold_conditions].any(axis=1), 'last_signal'] = 'HOLD'

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
            #if last_signal_row['last_signal'] == 'SELL' or last_signal_row['last_signal'] == 'BUY':
                #send_signal(last_signal_row['last_signal'],symbol)
        time.sleep(sleep)        

