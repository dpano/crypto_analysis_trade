import websocket
import json
import datetime

from db.database import insert_data

# WebSocket Callbacks
def on_message(ws, message):
    data = json.loads(message)
    # Simplified: Assuming data contains the necessary fields
     # Example data extraction (adjust according to actual message format)
    start_time = transform_timestamp_to_date(data['k']['t'])  # Start Timestamp of the candlestick
    end_time = transform_timestamp_to_date(data['k']['T'])  # End Timestamp of the candlestick
    open_price = data['k']['o']
    high_price = data['k']['h']
    low_price = data['k']['l']
    close_price = data['k']['c']
    volume = data['k']['v']
    symbol = data['s']
    event_timestamp = transform_timestamp_to_date(data['E'])
    
    # Insert extracted data into SQLite database
    insert_data(event_timestamp,start_time, end_time, open_price, high_price, low_price, close_price, volume, symbol)

    print("Received a message")
    print(json.loads(message))

def on_open(ws):
    subscribe_message = json.dumps({
        "method": "SUBSCRIBE",
        "params": ["btcusdt@kline_1d"],
        "id": 1
    })
    ws.send(subscribe_message)
def on_close(ws):
    print("### closed ###")
        
def on_error(ws, error):
    print(error)

def start_websocket():
    ws = websocket.WebSocketApp("wss://stream.binance.com:9443/ws/btcusdt@kline_1d",
                                on_message=on_message,
                                on_error = on_error,
                                on_open=on_open)
    ws.run_forever()    

def transform_timestamp_to_date(timestamp):
    return datetime.datetime.fromtimestamp(timestamp / 1000.0).strftime('%Y-%m-%d %H:%M:%S')