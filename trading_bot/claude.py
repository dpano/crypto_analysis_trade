import ccxt
import pandas as pd
import sqlite3
import time
from ta.momentum import RSIIndicator
from ta.volatility import BollingerBands
from ta.trend import SMAIndicator
from configuration.binance_config import config as binance_config

class CryptoTradingBot:
    def __init__(self, exchange, trading_pairs_config):
        bnc = binance_config()
        self.exchange = ccxt.Exchange({'apiKey': bnc['api_key'], 'secret': bnc['api_secret']})
        self.trading_pairs_config = trading_pairs_config
        self.conn = sqlite3.connect('trading_positions.db')
        self.create_positions_table()

    def create_positions_table(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS positions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trading_pair TEXT,
                entry_price REAL,
                quantity REAL,
                take_profit_price REAL,
                status TEXT,
                buy_order_id TEXT,
                sell_order_id TEXT,
                actual_profit REAL,
                actual_profit_percentage REAL
            )
        ''')
        self.conn.commit()

    def get_market_data(self, symbol, timeframe='1h', limit=100):
        ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        return df

    def calculate_indicators(self, df):
        rsi = RSIIndicator(df['close'], window=14)
        bb = BollingerBands(df['close'], window=20, window_dev=2)
        sma50 = SMAIndicator(df['close'], window=50)
        sma200 = SMAIndicator(df['close'], window=200)

        df['rsi'] = rsi.rsi()
        df['bb_lower'] = bb.bollinger_lband()
        df['sma50'] = sma50.sma_indicator()
        df['sma200'] = sma200.sma_indicator()
        return df

    def generate_buy_signal(self, df):
        last_row = df.iloc[-1]
        prev_row = df.iloc[-2]

        rsi_condition = last_row['rsi'] < 30
        bb_condition = prev_row['close'] <= prev_row['bb_lower'] and last_row['close'] > last_row['bb_lower']
        sma_condition = prev_row['sma50'] <= prev_row['sma200'] and last_row['sma50'] > last_row['sma200']

        return rsi_condition and (bb_condition or sma_condition)

    def place_buy_order(self, symbol, amount):
        try:
            order = self.exchange.create_market_buy_order(symbol, amount)
            return order
        except Exception as e:
            print(f"Error placing buy order: {e}")
            return None

    def place_sell_order(self, symbol, amount, price):
        try:
            order = self.exchange.create_limit_sell_order(symbol, amount, price)
            return order
        except Exception as e:
            print(f"Error placing sell order: {e}")
            return None

    def store_position(self, trading_pair, entry_price, quantity, take_profit_price, buy_order_id, sell_order_id):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO positions (trading_pair, entry_price, quantity, take_profit_price, status, buy_order_id, sell_order_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (trading_pair, entry_price, quantity, take_profit_price, 'open', buy_order_id, sell_order_id))
        self.conn.commit()

    def update_position(self, position_id, actual_profit, actual_profit_percentage):
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE positions
            SET status = ?, actual_profit = ?, actual_profit_percentage = ?
            WHERE id = ?
        ''', ('closed', actual_profit, actual_profit_percentage, position_id))
        self.conn.commit()

    def run(self):
        while True:
            for trading_pair, config in self.trading_pairs_config.items():
                df = self.get_market_data(trading_pair)
                df = self.calculate_indicators(df)

                if self.generate_buy_signal(df):
                    balance = self.exchange.fetch_balance()
                    usdt_balance = balance['USDT']['free']
                    investment_amount = usdt_balance * config['diversification_percentage']

                    if investment_amount > 10:
                        buy_order = self.place_buy_order(trading_pair, investment_amount)
                        if buy_order:
                            entry_price = buy_order['price']
                            quantity = buy_order['amount']
                            take_profit_price = entry_price * (1 + config['take_profit_percentage'])

                            sell_order = self.place_sell_order(trading_pair, quantity, take_profit_price)

                            if sell_order:
                                print(f"Sell order placed for {trading_pair}")
                                self.store_position(trading_pair, entry_price, quantity, take_profit_price, buy_order['id'], sell_order['id'])

            self.check_completed_orders()
            time.sleep(60)  # Wait for 1 minute before next iteration

    def check_completed_orders(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, trading_pair, entry_price, quantity, sell_order_id FROM positions WHERE status = 'open'")
        open_positions = cursor.fetchall()

        for position in open_positions:
            position_id, trading_pair, entry_price, quantity, sell_order_id = position
            try:
                order = self.exchange.fetch_order(sell_order_id, trading_pair)

                if order['status'] == 'closed':
                    actual_profit = (order['price'] - entry_price) * quantity
                    actual_profit_percentage = (order['price'] - entry_price) / entry_price * 100
                    self.update_position(position_id, actual_profit, actual_profit_percentage)
                    print(f"Position closed for {trading_pair}. Profit: {actual_profit} USDT ({actual_profit_percentage}%)")
            except Exception as e:
                print(f"Error checking order status for position {position_id}: {e}")

if __name__ == "__main__":
    exchange = ccxt.binance()  # Use Binance as an example, replace with your preferred exchange
    
    # Define trading pairs with their individual take-profit and diversification percentages
    trading_pairs_config = {
        'BTC/USDT': {
            'take_profit_percentage': 0.03,  # 3% take profit for BTC
            'diversification_percentage': 0.05  # 5% of available balance for BTC
        },
        'ETH/USDT': {
            'take_profit_percentage': 0.04,  # 4% take profit for ETH
            'diversification_percentage': 0.03  # 3% of available balance for ETH
        },
        'ADA/USDT': {
            'take_profit_percentage': 0.05,  # 5% take profit for ADA
            'diversification_percentage': 0.02  # 2% of available balance for ADA
        },
    }

    bot = CryptoTradingBot(exchange, trading_pairs_config)
    bot.run()