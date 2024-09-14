import pandas as pd
import ta
from binance.client import Client
import matplotlib.pyplot as plt
from configuration.binance_config import config as binance_config
import numpy as np
import os
import csv

binance_config = binance_config()
api_key = binance_config['api_key']
api_secret = binance_config['api_secret']
client = Client(api_key, api_secret)

symbols = ['TRXUSDT', 'BTCUSDT','ETHUSDT']  # Example symbol
timeframe = Client.KLINE_INTERVAL_4HOUR  
fast_length = 12
slow_length = 26
signal_smoothing = 9
rsi_length = 14
rsi_overbought = 70
rsi_oversold = 30
rsi_entry_min = 50
rsi_entry_max = 70
initial_balance = 1180  # Initial balance in USDT
investment_percentage = 0.15  # equity per trade
stop_loss_percentage = 0.05  # 2% stop los5
commission_percentage = 0.001  # 0.1% commission
metrics_file = 'backtest_metrics.csv'

# Fetch historical data (you may need to replace this with your data source)
def fetch_historical_data(symbol, interval, start_str, end_str=None):
    klines = client.get_historical_klines(symbol, interval, start_str, end_str)
    df = pd.DataFrame(klines, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_asset_volume', 'number_of_trades', 'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'])
    df['close'] = df['close'].astype(float)
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    return df

# Calculate indicators
def calculate_indicators(df):
    macd = ta.trend.MACD(df['close'], window_slow=slow_length, window_fast=fast_length, window_sign=signal_smoothing)
    df['macd'] = macd.macd()
    df['signal'] = macd.macd_signal()
    df['rsi'] = ta.momentum.RSIIndicator(df['close'], window=rsi_length).rsi()
    return df

# Generate signals
def generate_signals(df):
    df['buy_signal'] = ((df['macd'] > df['signal']) & 
                        (df['macd'].shift() <= df['signal'].shift()) &
                        (df['rsi'] > rsi_entry_min) & 
                        (df['rsi'] < rsi_entry_max))
    
    return df

# Simulate trades
def backtest_strategy(df, initial_balance, investment_percentage, stop_loss_percentage, commission_percentage, symbol):
    balance = initial_balance
    positions = []  # List to hold open positions
    equity_curve = []
    trades = []
    trade_count = 0

    for index, row in df.iterrows():
        price = row['close']
        if row['buy_signal'] and balance > 0:
            investment_amount = balance * investment_percentage
            balance -= investment_amount
            balance -= investment_amount * commission_percentage  # Commission fee for buying
            positions.append({
                'amount': investment_amount / price,
                'buy_price': price,
                'stop_loss_price': price * (1 - stop_loss_percentage),
                'entry_index': index,
                'entry_price': price,
            })
            trade_count += 1
            #print(f"Buy: {(investment_amount / price):.6f} {symbol.replace('USDT','')} for {investment_amount:.2f} USDT at {price} {symbol}")
        
        for position in positions[:]:  # Iterate over a copy of the list to allow removal
            position['stop_loss_price'] = max(position['stop_loss_price'], price * (1 - stop_loss_percentage))
            # Check stop loss condition
            if price <= position['stop_loss_price']:
                balance += position['amount'] * price
                balance -= position['amount'] * price * commission_percentage  # Commission fee for selling
                trades.append({
                    'entry_index': position['entry_index'],
                    'entry_price': position['entry_price'],
                    'exit_index': index,
                    'exit_price': price,
                    'amount': position['amount'],
                    'profit_loss': (price - position['entry_price']) * position['amount'],
                    'percent_profit_loss': ((price - position['entry_price']) / position['entry_price']) * 100,
                })
                positions.remove(position)
                trade_count += 1
                #print(f"Sell: {position['amount']:.6f} {symbol.replace('USDT','')} at {price} {symbol} (Stop Loss)")

        equity_curve.append(balance + sum(pos['amount'] * price for pos in positions))

    df['equity_curve'] = equity_curve
    final_balance = equity_curve[-1]
    profit_loss_percentage = ((final_balance - initial_balance) / initial_balance) * 100

    print(f'Symbol: {symbol}')
    print(f"Initial Balance: {initial_balance} USDT")
    print(f"Final Balance: {final_balance} USDT")
    print(f'Investment Percentage: {investment_percentage:.2f}')
    print(f'Stop Loss: {stop_loss_percentage:.2f}')
    print(f"Total Trades: {trade_count}")
    print(f"Percentage Profit/Loss: {profit_loss_percentage:.2f}%")
    print(f"Open positions: {len(positions)}")

    return df, trades, equity_curve, positions

# Calculate key performance metrics
def calculate_performance_metrics(trades, equity_curve, initial_balance):
    trade_profits = [trade['profit_loss'] for trade in trades]
    win_rate = sum(1 for profit in trade_profits if profit > 0) / len(trade_profits) if trade_profits else 0
    avg_profit_loss = np.mean(trade_profits) if trade_profits else 0
    max_drawdown = np.max(np.maximum.accumulate(equity_curve) - equity_curve)
    returns = np.diff(equity_curve) / equity_curve[:-1]
    sharpe_ratio = np.mean(returns) / np.std(returns) * np.sqrt(252) if returns.any() else 0
    
    return {
        'win_rate': win_rate,
        'avg_profit_loss': avg_profit_loss,
        'max_drawdown': max_drawdown,
        'sharpe_ratio': sharpe_ratio
    }

# Function to write metrics to a CSV file
def write_metrics_to_file(metrics, positions, symbol):
    file_exists = os.path.isfile(metrics_file)
    
    with open(metrics_file, 'a', newline='') as file:
        writer = csv.writer(file)
        if not file_exists:
            writer.writerow(['symbol', 'timeframe', 'fast_length', 'slow_length', 'signal_smoothing', 'rsi_length',
                              'rsi_entry_min', 'rsi_entry_max', 'initial_balance',
                             'investment_percentage', 'stop_loss_percentage', 'commission_percentage', 'win_rate',
                             'avg_profit_loss', 'max_drawdown', 'sharpe_ratio','open_positions'])
        
        writer.writerow([symbol, timeframe, fast_length, slow_length, signal_smoothing, rsi_length, 
                         rsi_entry_min, rsi_entry_max, initial_balance, investment_percentage,
                         stop_loss_percentage, commission_percentage, metrics['win_rate'], metrics['avg_profit_loss'],
                         metrics['max_drawdown'], metrics['sharpe_ratio'], len(positions)])


def plot_graphs(df, trades):
    # Prepare data for buy and sell markers
    buy_signals = df[df['buy_signal']].index
    sell_signals = [df.index[trade['exit_index']] for trade in trades]
    sell_prices = [trade['exit_price'] for trade in trades]
    buy_prices = df.loc[buy_signals]['close']
    
    # Plotting
    plt.figure(figsize=(14, 10))
    
    # Plot market close price
    plt.subplot(4, 1, 1)
    plt.plot(df.index, df['close'], label='Market Price')
    plt.scatter(buy_signals, buy_prices, marker='^', color='green', label='Buy Signal', alpha=1)
    plt.scatter(sell_signals, sell_prices, marker='v', color='red', label='Sell Signal', alpha=1)
    plt.title('Market Price with Buy and Sell Signals')
    plt.legend()
    
    # Plot MACD and signal line
    plt.subplot(4, 1, 2)
    plt.plot(df.index, df['macd'], label='MACD', color='blue')
    plt.plot(df.index, df['signal'], label='Signal Line', color='red')
    plt.title('MACD and Signal Line')
    plt.legend()
    
    # Plot RSI
    plt.subplot(4, 1, 3)
    plt.plot(df.index, df['rsi'], label='RSI', color='purple')
    plt.axhline(y=rsi_overbought, color='red', linestyle='--', label='Overbought')
    plt.axhline(y=rsi_oversold, color='green', linestyle='--', label='Oversold')
    plt.axhline(y=rsi_entry_min, color='blue', linestyle='--', label='Entry Min')
    plt.axhline(y=rsi_entry_max, color='orange', linestyle='--', label='Entry Max')
    plt.title('RSI')
    plt.legend()
    
    # Plot strategy equity curve
    plt.subplot(4, 1, 4)
    plt.plot(df.index, df['equity_curve'], label='Strategy Equity Curve', color='orange')
    plt.title('Strategy Equity Curve')
    plt.legend()
    
    plt.tight_layout()
    plt.show()


# Main function to run the backtest
def main(symbol):
    df = fetch_historical_data(symbol, timeframe, '2024-07-01')
    df = calculate_indicators(df)
    df = generate_signals(df)
    df, trades, equity_curve , positions = backtest_strategy(df, initial_balance, investment_percentage, stop_loss_percentage, commission_percentage, symbol)
    df.set_index('timestamp', inplace=True)
    
    # Calculate performance metrics
    metrics = calculate_performance_metrics(trades, equity_curve, initial_balance)
    print("\nPerformance Metrics:")
    for key, value in metrics.items():
        print(f"{key}: {value:.2f}")
    
    # Write metrics to file
    write_metrics_to_file(metrics, positions, symbol)
    plot_graphs(df, trades)   
    

if __name__ == "__main__":
    for symbol in symbols:
        print(f'### {symbol} ### \n')
        main(symbol)