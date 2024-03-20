import ta

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

