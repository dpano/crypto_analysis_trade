import asyncio
import logging
import time
import pandas as pd
import sqlite3
from binance.client import Client
from binance.exceptions import BinanceAPIException
import ta
from ta.momentum import RSIIndicator
from ta.volatility import BollingerBands
from ta.trend import SMAIndicator
from configuration.binance_config import config as binance_config
from configuration.telegram_config import config as telegram_config
from notifications.telegram import send_telegram_message
# Configure logging
logging.basicConfig(filename='trading_bot.log', level=logging.INFO, 
                    format='%(asctime)s %(message)s')
class CryptoTradingBot:
    heartbeat = 0
    def __init__(self, trading_pairs_config):
        bnc = binance_config()
        self.client = Client(bnc['api_key'], bnc['api_secret'])
        self.trading_pairs_config = trading_pairs_config
        self.conn = sqlite3.connect('trading_positions.db')
        self.create_positions_table()
        self.fast_length = 12
        self.slow_length = 26
        self.signal_smoothing = 9
        self.rsi_length = 14
        self.rsi_entry_min = 50
        self.rsi_entry_max = 70

    def telegram(self, message):
        config = telegram_config()
        asyncio.run(send_telegram_message(config['token'], config['chat_id'], message))
        logging.info(f"Telegram message sent: {message}")
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
                actual_profit_percentage REAL,
                created TEXT, 
                updated TEXT             
            )
        ''')
        self.conn.commit()

    def get_market_data(self, symbol, interval=Client.KLINE_INTERVAL_1HOUR, limit=210):
        klines = self.client.get_klines(symbol=symbol, interval=interval, limit=limit)
        df = pd.DataFrame(klines, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_asset_volume', 'number_of_trades', 'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df['close'] = df['close'].astype(float)
        df['symbol'] = symbol
        # message = f"---Get data for symbol---: {symbol}"
        # logging.info(message)
        # print(message)
        return df

    def calculate_indicators(self, df):
        macd = ta.trend.MACD(df['close'], window_slow=self.slow_length, window_fast=self.fast_length, window_sign=self.signal_smoothing)
        df['macd'] = macd.macd()
        df['signal'] = macd.macd_signal()
        df['rsi'] = ta.momentum.RSIIndicator(df['close'], window=self.rsi_length).rsi()
        # message = f"Indicators: madc: {df['macd'].iloc[-1]}, signal: {df['signal'].iloc[-1]}, rsi: {df['rsi'].iloc[-1]}"
        # logging.info(message)
        # print(message)
        return df

    def generate_buy_signal(self, df):
        df['buy_signal'] = ((df['macd'] > df['signal']) & 
                        (df['macd'].shift() <= df['signal'].shift()) &
                        (df['rsi'] > self.rsi_entry_min) & 
                        (df['rsi'] < self.rsi_entry_max))
        has_signal = df['buy_signal'].iloc[-1]
        if has_signal:
            message = f"Buy signal generated({df['symbol'].iloc[-1]}): {has_signal}"
            logging.info(message)
            print(message)
        return df

    def place_buy_order(self, symbol, quantity):
        try:

            # Place the buy order if it meets the criteria
            order = self.client.create_order(
                symbol=symbol,
                side=Client.SIDE_BUY,
                type=Client.ORDER_TYPE_MARKET,
                quoteOrderQty=quantity
            )
            return order
        except BinanceAPIException as e:
            message = f"Error placing buy order: {e}"
            print(message)
            logging.error(message)
            return None


    def place_sell_order(self, symbol, quantity, price):
        try:
            price_filter = self.get_price_filter(symbol)
            if not price_filter:
                raise Exception("PRICE_FILTER not found for the symbol")
            
            # Adjust the price to be within the allowed limits
            price = max(price_filter['minPrice'], min(price, price_filter['maxPrice']))
            price = round(price - (price % price_filter['tickSize']), 8)
            
            order = self.client.create_order(
                symbol=symbol,
                side=Client.SIDE_SELL,
                type=Client.ORDER_TYPE_LIMIT,
                timeInForce=Client.TIME_IN_FORCE_GTC,
                quantity=quantity,
                price=str(price)
            )
            return order
        except BinanceAPIException as e:
            message = f"Error placing sell order: {e}"
            print(message)
            logging.error(message)
            send_telegram_message(message)
            return None

    def store_position(self, trading_pair, entry_price, quantity, take_profit_price, buy_order_id, sell_order_id):
        cursor = self.conn.cursor()
        current_time = "datetime('now', 'localtime')"
        cursor.execute(f'''
            INSERT INTO positions (trading_pair, entry_price, quantity, take_profit_price, status, buy_order_id, sell_order_id, created, updated)
            VALUES (?, ?, ?, ?, ?, ?, ?, {current_time}, {current_time})
        ''', (trading_pair, entry_price, quantity, take_profit_price, 'open', buy_order_id, sell_order_id))
        self.conn.commit()

    def update_position(self, position_id, actual_profit, actual_profit_percentage):
        cursor = self.conn.cursor()
        current_time = "datetime('now', 'localtime')"
        cursor.execute('''
            UPDATE positions
            SET status = ?, actual_profit = ?, actual_profit_percentage = ?, updated = ?
            WHERE id = ?
        ''', ('closed', actual_profit, actual_profit_percentage, position_id, current_time))
        self.conn.commit()
    
    def adjust_amount(self, amount, step_size):
        # Convert step_size to a string and check if it has a decimal part
        step_size_str = str(step_size)
        if '.' in step_size_str:
            # If there's a decimal part, calculate the number of decimal places
            decimal_places = len(step_size_str.split('.')[1])
        else:
            # If there's no decimal part, set decimal_places to 0
            decimal_places = 0

        # Ensure the quantity is rounded down to the nearest stepSize
        adjusted_amount = round(amount - (amount % step_size), decimal_places)

        # Check if adjusted amount is 0 or less, which would be invalid
        if adjusted_amount <= 0:
            raise ValueError(f"Adjusted amount is zero or negative after rounding: {adjusted_amount}. Check the input values.")
        
        return adjusted_amount


    
    def get_lot_size(self, symbol):
        """ Refers to quantity """
        info = self.client.get_symbol_info(symbol)
        for filt in info['filters']:
            if filt['filterType'] == 'LOT_SIZE':
                return {
                    'minQty': float(filt['minQty']),
                    'maxQty': float(filt['maxQty']),
                    'stepSize': float(filt['stepSize'])
                }
        return None

    def get_price_filter(self, symbol):
        """ Refers to price """
        info = self.client.get_symbol_info(symbol)
        for filt in info['filters']:
            if filt['filterType'] == 'PRICE_FILTER':
                return {
                    'minPrice': float(filt['minPrice']),
                    'maxPrice': float(filt['maxPrice']),
                    'tickSize': float(filt['tickSize'])
                }
        return None

    def get_notional_filter(self, symbol):
        """Refers to quantity for limit_stop_loss"""
        info = self.client.get_symbol_info(symbol)
        for filt in info['filters']:
            if filt['filterType'] == 'MIN_NOTIONAL':
                return float(filt['minNotional'])
        return None

    def run(self):
        while True:
            for trading_pair, config in self.trading_pairs_config.items():
                df = self.get_market_data(trading_pair)
                df = self.calculate_indicators(df)
                df = self.generate_buy_signal(df)
                if True or df['buy_signal'].iloc[-1]:
                    # Specify the fixed amount of USDT to invest for each trading pair
                    fixed_investment_amount = config.get('fixed_investment_amount', None)

                    if not fixed_investment_amount:
                        message = f"Fixed investment amount not set for {trading_pair}. Skipping..."
                        logging.info(message)
                        print(message)
                        continue

                    # Get the current balance in USDT
                    account = self.client.get_account()
                    usdt_balance = float(next(asset['free'] for asset in account['balances'] if asset['asset'] == 'USDT'))

                    # Ensure that the USDT balance is enough for the fixed investment
                    if fixed_investment_amount > usdt_balance:
                        message = f"Not enough USDT balance to place the trade for {trading_pair}. Required: {fixed_investment_amount}, Available: {usdt_balance}"
                        logging.info(message)
                        print(message)
                        continue

                    # Calculate the amount of crypto to buy using the fixed USDT amount
                    amount = fixed_investment_amount / float(df['close'].iloc[-1])
                    
                    # Retrieve the lot size (minimum and maximum order size) for the trading pair
                    lot_size = self.get_lot_size(trading_pair)
                    
                    if not lot_size:
                        raise Exception("LOT_SIZE filter not found for the symbol")
                    
                    # Ensure the amount is within the allowed range
                    if amount < lot_size['minQty']:
                        message = f"Amount {amount} is less than the minimum allowed quantity {lot_size['minQty']}"
                        logging.info(message)
                        print(message)
                        continue
                        
                    if amount > lot_size['maxQty']:
                        message = f"Amount {amount} is greater than the maximum allowed quantity {lot_size['maxQty']}"
                        logging.info(message)
                        print(message)
                        continue
                    
                    # Adjust the amount to be within the allowed step size
                    quantity = fixed_investment_amount #self.adjust_amount(amount, float(lot_size['stepSize']))
                    
                    # Place the buy order
                    buy_order = self.place_buy_order(trading_pair, quantity)

                    if buy_order:
                        message = f"Buy order placed for: {trading_pair}, amount: {quantity}"
                        print(message)
                        self.telegram(message)
                        logging.info(message)
                        entry_price = float(buy_order['fills'][0]['price'])
                        quantity = float(buy_order['executedQty'])
                        take_profit_price = entry_price * (1 + config['take_profit_percentage'])

                        # Place the sell order
                        sell_order = self.place_sell_order(trading_pair, quantity, take_profit_price)

                        if sell_order:            
                            message = f"Sell order placed for {trading_pair}"
                            print(message)
                            logging.info(message)
                            self.telegram(message)
                            self.store_position(trading_pair, entry_price, quantity, take_profit_price, buy_order['orderId'], sell_order['orderId'])

            self.check_completed_orders()
            self.heartbeat += 1
            if self.heartbeat % 1440 == 0:
                self.telegram('Heartbeat - Claude is alive')
                logging.info('Heartbeat - Claude is alive')
            break 
            time.sleep(60)  # Wait for 1 minute before next iteration


    def check_completed_orders(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, trading_pair, entry_price, quantity, sell_order_id FROM positions WHERE status = 'open'")
        open_positions = cursor.fetchall()

        for position in open_positions:
            position_id, trading_pair, entry_price, quantity, sell_order_id = position
            try:
                order = self.client.get_order(symbol=trading_pair, orderId=sell_order_id)

                if order['status'] == Client.ORDER_STATUS_FILLED:
                    actual_profit = (float(order['price']) - entry_price) * quantity
                    actual_profit_percentage = ((float(order['price']) - entry_price) / entry_price) * 100
                    self.update_position(position_id, actual_profit, actual_profit_percentage)
                    
                    message = f"Position closed for {trading_pair}. Profit: {actual_profit} USDT ({actual_profit_percentage}%)"
                    print(message)
                    self.telegram(message)
                    logging.info(message)
            except BinanceAPIException as e:
                message = f"Error checking order status for position {position_id}: {e}"
                print(message)
                self.telegram(message)
                logging.error(message)
