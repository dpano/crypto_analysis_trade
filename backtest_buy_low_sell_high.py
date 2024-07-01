import pandas as pd
import ta
from binance.client import Client
import matplotlib.pyplot as plt
from configuration.binance_config import config as binance_config
import numpy as np

binance_config = binance_config()
api_key = binance_config['api_key']
api_secret = binance_config['api_secret']
client = Client(api_key, api_secret)

symbol = 'ETHUSDT'  # Example symbol
timeframe = Client.KLINE_INTERVAL_1HOUR  
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
def backtest_strategy(df, initial_balance, investment_percentage, stop_loss_percentage, commission_percentage):
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

    return df, trades, equity_curve

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

# Main function to run the backtest
def main():
    df = fetch_historical_data(symbol, timeframe, '2023-07-01')
    df = calculate_indicators(df)
    df = generate_signals(df)
    df, trades, equity_curve = backtest_strategy(df, initial_balance, investment_percentage, stop_loss_percentage, commission_percentage)
    df.set_index('timestamp', inplace=True)
    
    # Calculate performance metrics
    metrics = calculate_performance_metrics(trades, equity_curve, initial_balance)
    print("\nPerformance Metrics:")
    for key, value in metrics.items():
        print(f"{key}: {value:.2f}")
    
    # Print trades
    # print("\nTrades:")
    # for trade in trades:
    #     print(f"Entry Index: {trade['entry_index']}, Entry Price: {trade['entry_price']}, Exit Index: {trade['exit_index']}, Exit Price: {trade['exit_price']}, Amount: {trade['amount']:.6f}, Profit/Loss: {trade['profit_loss']:.2f} USDT, Percent Profit/Loss: {trade['percent_profit_loss']:.2f}%")


    # Prepare data for buy and sell markers
    buy_signals = df[df['buy_signal']].index
    sell_signals = [df.index[trade['exit_index']] for trade in trades]
    sell_prices = [trade['exit_price'] for trade in trades]
    buy_prices = df.loc[buy_signals]['close']
    
    # Plotting
    plt.figure(figsize=(14, 7))
    
    # Plot market close price
    plt.subplot(2, 1, 1)
    plt.plot(df.index, df['close'], label='Market Price')
    plt.scatter(buy_signals, buy_prices, marker='^', color='green', label='Buy Signal', alpha=1)
    plt.scatter(sell_signals, sell_prices, marker='v', color='red', label='Sell Signal', alpha=1)
    plt.title('Market Price with Buy and Sell Signals')
    plt.legend()
    
    # Plot strategy equity curve
    plt.subplot(2, 1, 2)
    plt.plot(df.index, df['equity_curve'], label='Strategy Equity Curve', color='orange')
    plt.title('Strategy Equity Curve')
    plt.legend()
    
    plt.tight_layout()
    plt.show()
    
    #print(df[['equity_curve']])

if __name__ == "__main__":
    main()
