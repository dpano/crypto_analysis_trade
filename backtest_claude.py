import os
import pandas as pd
import numpy as np
from binance.client import Client
import ta
from ta.momentum import RSIIndicator
from ta.volatility import BollingerBands
from ta.trend import SMAIndicator
import math

class CryptoTradingBotBacktest:
    def __init__(self, symbol, start_date, end_date, initial_balance=10000):
        self.symbol = symbol
        self.start_date = start_date
        self.end_date = end_date
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.positions = []
        self.trades = []
        self.fast_length = 12
        self.slow_length = 26
        self.signal_smoothing = 9
        self.rsi_length = 14
        self.rsi_entry_min = 50
        self.rsi_entry_max = 70
        self.trade_profit_percentage = 0.05
        self.diversification_percentage = 0.1

    def get_historical_data(self):
        client = Client()
        klines = client.get_historical_klines(self.symbol, Client.KLINE_INTERVAL_1HOUR, self.start_date, self.end_date)
        df = pd.DataFrame(klines, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_asset_volume', 'number_of_trades', 'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df['close'] = df['close'].astype(float)
        return df
    
    def calculate_indicators(self, df):
        macd = ta.trend.MACD(df['close'], window_slow=self.slow_length, window_fast=self.fast_length, window_sign=self.signal_smoothing)
        df['macd'] = macd.macd()
        df['signal'] = macd.macd_signal()
        df['rsi'] = ta.momentum.RSIIndicator(df['close'], window=self.rsi_length).rsi()
        return df

    def generate_buy_signal(self, row, prev_row):
        # rsi_condition = row['rsi'] < 30
        # bb_condition = prev_row['close'] <= prev_row['bb_lower'] and row['close'] > row['bb_lower']
        # sma_condition = prev_row['sma50'] <= prev_row['sma200'] and row['sma50'] > row['sma200']
        buysignal = ((row['macd'] > row['signal']) & 
                        (prev_row['macd'] <= prev_row['signal']) &
                        (row['rsi'] > self.rsi_entry_min) & 
                        (row['rsi'] < self.rsi_entry_max))

        return buysignal

    def simulate_trading(self, df, take_profit_percentage=0.03, diversification_percentage=0.1):
        for i in range(1, len(df)):
            current_row = df.iloc[i]
            prev_row = df.iloc[i-1]

            if self.generate_buy_signal(current_row, prev_row):
                investment_amount = math.ceil(self.balance * diversification_percentage)
                if investment_amount > 10:
                    quantity = investment_amount / float(current_row['close'])
                    entry_price = float(current_row['close'])
                    take_profit_price = entry_price * (1 + take_profit_percentage)

                    self.balance -= investment_amount
                    self.positions.append({
                        'entry_price': entry_price,
                        'quantity': quantity,
                        'take_profit_price': take_profit_price
                    })

            # Check for take profit
            for position in self.positions[:]:
                if float(current_row['high']) >= position['take_profit_price']:
                    profit = (position['take_profit_price'] - position['entry_price']) * position['quantity']
                    self.balance += position['quantity'] * position['take_profit_price']
                    self.trades.append({
                        'entry_price': position['entry_price'],
                        'exit_price': position['take_profit_price'],
                        'quantity': position['quantity'],
                        'profit': profit
                    })
                    self.positions.remove(position)
        # Calculate the value of remaining open positions
        open_positions_value = sum(position['quantity'] * df.iloc[-1]['close'] for position in self.positions)
        return open_positions_value             

    def run_backtest(self):
        df = self.get_historical_data()
        df = self.calculate_indicators(df)
        open_positions_value = self.simulate_trading(df, self.trade_profit_percentage)

        total_profit = sum(trade['profit'] for trade in self.trades)
        final_balance = self.balance + open_positions_value
        profit_percentage = (final_balance - self.initial_balance) / self.initial_balance * 100
        num_trades = len(self.trades)

        return {
            'symbol': self.symbol,
            'take_profit_percentage_foreach_trade': self.trade_profit_percentage,
            'diversification_percentage': self.diversification_percentage,
            'fast_length': self.fast_length,
            'slow_length': self.slow_length,
            'signal_smoothing': self.signal_smoothing,
            'rsi_length': self.rsi_length,
            'rsi_entry_min': self.rsi_entry_min,
            'rsi_entry_max': self.rsi_entry_max,
            'start_date': self.start_date,
            'end_date': self.end_date,
            'initial_balance': self.initial_balance,
            'total_profit': total_profit,
            'profit_percentage': profit_percentage,
            'num_trades': num_trades,
            'final_balance': final_balance,
            'open_positions_value': open_positions_value
        }

# Run the backtest
symbols = ['TRXUSDT', 'BTCUSDT','ETHUSDT', 'SOLUSDT', 'XRPUSDT', 'ADAUSDT'] 
start_date = "1 Jan, 2024"
end_date = "5 Dec, 2024"
initial_balance = 3000

# Define file name
file_name = 'claude_backtest_results.csv'

# Prepare a list to store results
results_list = []

for symbol in symbols:
    backtest = CryptoTradingBotBacktest(symbol, start_date, end_date, initial_balance)
    results = backtest.run_backtest()
    results_list.append(results)

    print(f"Backtest Results for {symbol} from {start_date} to {end_date}")
    print(f"Initial Balance: ${initial_balance}")
    print(f"Final Balance: ${results['final_balance']:.2f}")
    print(f"Open Positions Value: ${results['open_positions_value']:.2f}")
    print(f"Total Profit: ${results['total_profit']:.2f}")
    print(f"Profit Percentage: {results['profit_percentage']:.2f}%")
    print(f"Number of Trades: {results['num_trades']}")
    print(f"Open positions: {len(backtest.positions)}")

# Save results to a CSV file, appending if the file already exists
results_df = pd.DataFrame(results_list)

if os.path.exists(file_name):
    existing_df = pd.read_csv(file_name)
    combined_df = pd.concat([existing_df, results_df], ignore_index=True)
    combined_df.to_csv(file_name, index=False)
else:
    results_df.to_csv(file_name, index=False)

print(f"Backtest results have been {'appended to' if os.path.exists(file_name) else 'saved to'} '{file_name}'.")
