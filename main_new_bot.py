from binance.client import Client
import pandas as pd
import asyncio
import time
from configuration.binance_config import config as binance_config
from configuration.telegram_config import config as telegram_config
from db.database import log_trade, setup_database
from notifications.telegram import send_telegram_message
import pandas_ta as ta

# Initialize the Binance client
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
trade_percentage = 0.10  # 10% of equity for each trade

def fetch_data(symbol, interval):
    klines = client.get_klines(symbol=symbol, interval=interval)
    df = pd.DataFrame(klines, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_asset_volume', 'number_of_trades', 'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'])
    df['close'] = df['close'].astype(float)
    return df

def fetch_historical_data(symbol, interval, start_str, end_str=None):
    klines = client.get_historical_klines(symbol, interval, start_str, end_str)
    df = pd.DataFrame(klines, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_asset_volume', 'number_of_trades', 'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'])
    df['close'] = df['close'].astype(float)
    return df

def calculate_indicators(df):
    df['SMA'] = ta.sma(df['close'], length=sma_period)
    df['LMA'] = ta.sma(df['close'], length=lma_period)
    
    # Calculate MACD and MACD Signal separately
    df['MACD'] = ta.ema(df['close'], length=macd_short) - ta.ema(df['close'], length=macd_long)
    df['MACD_Signal'] = ta.ema(df['MACD'], length=macd_signal)
    
    df['RSI'] = ta.rsi(df['close'], length=rsi_period)
    return df

def get_balance(asset):
    balance = client.get_asset_balance(asset=asset)
    return float(balance['free'])

def calculate_trade_quantity(symbol, trade_percentage, side):
    asset = symbol.replace('USDT', '')
    if side == Client.SIDE_BUY:
        equity = get_balance('USDT')
        trade_amount_in_usdt = equity * trade_percentage
        price = float(client.get_symbol_ticker(symbol=symbol)['price'])
        quantity = trade_amount_in_usdt / price
    else:  # side == Client.SIDE_SELL
        equity = get_balance(asset)
        quantity = equity * trade_percentage
    return round(quantity, 6)  # rounding to 6 decimal places for precision

def place_order(symbol, side, quantity, order_type=Client.ORDER_TYPE_MARKET):
    try:
        order = client.create_order(
            symbol=symbol,
            side=side,
            type=order_type,
            quantity=quantity
        )
        print(f"Order placed: {order}")
        telegram(f"Executing {side} order for {quantity} {symbol}")
        
        # Log trade in SQLite database
        price = float(order['fills'][0]['price'])
        log_trade(symbol,side,price,quantity)
    except Exception as e:
        telegram(f"Error Executing {side} order for {quantity} {symbol}")
        print(f"An error occurred: {e}")

def telegram(message):
    config = telegram_config()
    asyncio.run(send_telegram_message(config['token'], config['chat_id'], message))

def main():
    telegram('New BOT Started')
    setup_database()
    heartbeat = 0
    while True:
        df = fetch_data(symbol, timeframe)
        df = calculate_indicators(df)        

        if df['SMA'].iloc[-2] < df['LMA'].iloc[-2] and df['SMA'].iloc[-1] > df['LMA'].iloc[-1] and df['MACD'].iloc[-1] > df['MACD_Signal'].iloc[-1] and df['RSI'].iloc[-1] > 50 and df['RSI'].iloc[-1] < 70:
            print("Buy Signal")
            quantity = calculate_trade_quantity(symbol, trade_percentage,Client.SIDE_BUY)
            place_order(symbol, Client.SIDE_BUY, quantity)
        if df['SMA'].iloc[-2] > df['LMA'].iloc[-2] and df['SMA'].iloc[-1] < df['LMA'].iloc[-1] and df['MACD'].iloc[-1] < df['MACD_Signal'].iloc[-1] and df['RSI'].iloc[-1] < 50 and df['RSI'].iloc[-1] > 30:
            print("Sell Signal")
            quantity = calculate_trade_quantity(symbol, trade_percentage,Client.SIDE_SELL)
            place_order(symbol, Client.SIDE_SELL, quantity)
        time.sleep(60 * 60)  # Wait for 1 hour before the next iteration
        heartbeat += 1
        if heartbeat % 24 == 0:
            telegram('Heartbeat - bot is alive')

if __name__ == "__main__":
    main()
