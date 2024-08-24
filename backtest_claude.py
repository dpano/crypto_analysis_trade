import pandas as pd
import numpy as np
from binance.client import Client
import ta
from datetime import datetime, timedelta

# Initialize Binance client (use testnet if available)
client = Client()

# Strategy parameters
symbols = ['TRXUSDT', 'BTCUSDT']
timeframe = Client.KLINE_INTERVAL_1HOUR
fast_length = 12
slow_length = 26
signal_smoothing = 9
rsi_length = 14
rsi_entry_min = 50
rsi_entry_max = 70
investment_percentage = 0.15
stop_loss_percentage = 0.05
initial_balance = 10000  # Starting balance in USDT

def fetch_historical_data(symbol, interval, start_str, end_str):
    klines = client.get_historical_klines(symbol, interval, start_str, end_str)
    df = pd.DataFrame(klines, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_asset_volume', 'number_of_trades', 'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df['close'] = df['close'].astype(float)
    df['high'] = df['high'].astype(float)
    df['low'] = df['low'].astype(float)
    return df

def calculate_indicators(df):
    macd = ta.trend.MACD(df['close'], window_slow=slow_length, window_fast=fast_length, window_sign=signal_smoothing)
    df['macd'] = macd.macd()
    df['signal'] = macd.macd_signal()
    df['rsi'] = ta.momentum.RSIIndicator(df['close'], window=rsi_length).rsi()
    return df

def generate_signals(df):
    df['buy_signal'] = ((df['macd'] > df['signal']) & 
                        (df['macd'].shift() <= df['signal'].shift()) &
                        (df['rsi'] > rsi_entry_min) & 
                        (df['rsi'] < rsi_entry_max))
    return df

def simulate_trades(df, initial_balance):
    balance = initial_balance
    position = None
    trades = []
    
    for i, row in df.iterrows():
        if position is None and row['buy_signal']:
            # Open a new position
            entry_price = row['close']
            position_size = balance * investment_percentage / entry_price
            stop_loss = entry_price * (1 - stop_loss_percentage)
            position = {
                'entry_price': entry_price,
                'size': position_size,
                'stop_loss': stop_loss,
                'entry_date': row['timestamp']
            }
            balance -= position_size * entry_price
        elif position is not None:
            # Check for stop loss
            if row['low'] <= position['stop_loss']:
                # Stop loss triggered
                exit_price = position['stop_loss']
                profit_loss = (exit_price - position['entry_price']) * position['size']
                balance += (position['size'] * exit_price)
                trades.append({
                    'entry_date': position['entry_date'],
                    'exit_date': row['timestamp'],
                    'entry_price': position['entry_price'],
                    'exit_price': exit_price,
                    'size': position['size'],
                    'profit_loss': profit_loss
                })
                position = None
            else:
                # Update trailing stop loss
                new_stop_loss = row['close'] * (1 - stop_loss_percentage)
                if new_stop_loss > position['stop_loss']:
                    position['stop_loss'] = new_stop_loss
    
    # Close any open position at the end of the period
    if position is not None:
        exit_price = df.iloc[-1]['close']
        profit_loss = (exit_price - position['entry_price']) * position['size']
        balance += (position['size'] * exit_price)
        trades.append({
            'entry_date': position['entry_date'],
            'exit_date': df.iloc[-1]['timestamp'],
            'entry_price': position['entry_price'],
            'exit_price': exit_price,
            'size': position['size'],
            'profit_loss': profit_loss
        })
    
    return balance, trades

def backtest_strategy(symbol, start_date, end_date, initial_balance):
    # Fetch historical data
    df = fetch_historical_data(symbol, timeframe, start_date, end_date)
    
    # Calculate indicators and generate signals
    df = calculate_indicators(df)
    df = generate_signals(df)
    
    # Simulate trades
    final_balance, trades = simulate_trades(df, initial_balance)
    
    # Calculate performance metrics
    total_profit_loss = sum(trade['profit_loss'] for trade in trades)
    num_trades = len(trades)
    win_rate = sum(1 for trade in trades if trade['profit_loss'] > 0) / num_trades if num_trades > 0 else 0
    
    return {
        'symbol': symbol,
        'initial_balance': initial_balance,
        'final_balance': final_balance,
        'total_profit_loss': total_profit_loss,
        'num_trades': num_trades,
        'win_rate': win_rate,
        'trades': trades
    }

def run_backtest():
    start_date = "1 Jun, 2024"
    end_date = "1 Aug, 2024"
    
    results = {}
    for symbol in symbols:
        print(f"Backtesting {symbol}...")
        result = backtest_strategy(symbol, start_date, end_date, initial_balance)
        results[symbol] = result
        
        print(f"Results for {symbol}:")
        print(f"Initial Balance: ${result['initial_balance']:.2f}")
        print(f"Final Balance: ${result['final_balance']:.2f}")
        print(f"Total Profit/Loss: ${result['total_profit_loss']:.2f}")
        print(f"Number of Trades: {result['num_trades']}")
        print(f"Win Rate: {result['win_rate']:.2%}")
        print("\n")
    
    return results

if __name__ == "__main__":
    backtest_results = run_backtest()
    
    # You can further analyze or visualize the results here
    # For example, you could plot the equity curve, calculate drawdowns, etc.