import pandas as pd
from binance.client import Client
from datetime import datetime
import matplotlib.pyplot as plt

# Initialize the Binance client
from configuration.binance_config import config as binance_config
from main_new_bot import calculate_indicators
binance_config = binance_config()
api_key = binance_config['api_key']
api_secret = binance_config['api_secret']
client = Client(api_key, api_secret)

symbol = 'ETHUSDT'
timeframe = '1h'
sma_period = 50
lma_period = 200
macd_short = 12
macd_long = 26
macd_signal = 9
rsi_period = 14
trade_percentage = 0.20  # 10% of equity for each trade
initial_balance = 1000  # Initial balance in USDT

def fetch_historical_data(symbol, interval, start_str, end_str=None):
    klines = client.get_historical_klines(symbol, interval, start_str, end_str)
    df = pd.DataFrame(klines, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_asset_volume', 'number_of_trades', 'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'])
    df['close'] = df['close'].astype(float)
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)
    return df

def calculate_indicators_old(df):
    df['SMA'] = df['close'].rolling(sma_period).mean()
    df['LMA'] = df['close'].rolling(lma_period).mean()
    df['MACD'] = df['close'].ewm(span=macd_short, adjust=False).mean() - df['close'].ewm(span=macd_long, adjust=False).mean()
    df['MACD_Signal'] = df['MACD'].ewm(span=macd_signal, adjust=False).mean()
    df['RSI'] = 100 - (100 / (1 + df['close'].diff(1).clip(lower=0).ewm(com=rsi_period-1, adjust=False).mean() / df['close'].diff(1).clip(upper=0).abs().ewm(com=rsi_period-1, adjust=False).mean()))
    return df

def backtest(df, initial_balance, trade_percentage):
    balance = initial_balance
    eth_balance = 0
    trades = []

    for i in range(1, len(df)):
        if df['SMA'].iloc[i-1] < df['LMA'].iloc[i-1] and df['SMA'].iloc[i] > df['LMA'].iloc[i] and df['MACD'].iloc[i] > df['MACD_Signal'].iloc[i] and df['RSI'].iloc[i] > 50 and df['RSI'].iloc[i] < 70:
            # Buy Signal
            trade_amount_in_usdt = balance * trade_percentage
            trade_amount_in_eth = trade_amount_in_usdt / df['close'].iloc[i]
            balance -= trade_amount_in_usdt
            eth_balance += trade_amount_in_eth
            trades.append({'timestamp': df.index[i], 'type': 'buy', 'price': df['close'].iloc[i], 'amount': trade_amount_in_eth, 'amount(USDT)':trade_amount_in_usdt})

        if df['SMA'].iloc[i-1] > df['LMA'].iloc[i-1] and df['SMA'].iloc[i] < df['LMA'].iloc[i] and df['MACD'].iloc[i] < df['MACD_Signal'].iloc[i] and df['RSI'].iloc[i] < 50 and df['RSI'].iloc[i] > 30:
            # Sell Signal
            trade_amount_in_eth = eth_balance * trade_percentage
            trade_amount_in_usdt = trade_amount_in_eth * df['close'].iloc[i]
            balance += trade_amount_in_usdt
            eth_balance -= trade_amount_in_eth
            trades.append({'timestamp': df.index[i], 'type': 'sell', 'price': df['close'].iloc[i], 'amount': trade_amount_in_eth, 'amount(USDT)':trade_amount_in_usdt})

    final_balance = balance + (eth_balance * df['close'].iloc[-1])
    return trades, final_balance

def plot_trades(df, trades):
    plt.figure(figsize=(14, 7))
    plt.plot(df['close'], label='Price')
    buys = [trade for trade in trades if trade['type'] == 'buy']
    sells = [trade for trade in trades if trade['type'] == 'sell']
    plt.scatter([trade['timestamp'] for trade in buys], [trade['price'] for trade in buys], color='green', label='Buy', marker='^', alpha=1)
    plt.scatter([trade['timestamp'] for trade in sells], [trade['price'] for trade in sells], color='red', label='Sell', marker='v', alpha=1)
    plt.xlabel('Date')
    plt.ylabel('Price')
    plt.legend()
    plt.show()

# Fetch historical data
df = fetch_historical_data(symbol, Client.KLINE_INTERVAL_1HOUR, '1 Jan 2024', '20 Jun 2024')
df = calculate_indicators(df.dropna())

# Run backtest
trades, final_balance = backtest(df, initial_balance, trade_percentage)

# Calculate percentage change
percentage_change = ((final_balance - initial_balance) / initial_balance) * 100

# Print results
print(f"Initial Balance: {initial_balance} USDT")
print(f"Final Balance: {final_balance:.2f} USDT")
print(f"Total Trades: {len(trades)}")
print(f"Percentage Profit/Loss: {percentage_change:.2f}%")
# List trades with details
trades_df = pd.DataFrame(trades)
print(trades_df)

# Plot trades on price chart
plot_trades(df, trades)
