import datetime
import sqlite3

import pandas as pd

def connect_db(db_file='trading_bot.db'):
    return sqlite3.connect(db_file)

def setup_database():
    conn = connect_db()
    cursor = conn.cursor()
    # Create tables
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS market_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        start_time TEXT,
        end_time TEXT,
        open REAL,
        high REAL,
        low REAL,
        close REAL,
        volume REAL,
        symbol)''')
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY,
        type TEXT NOT NULL,
        status TEXT NOT NULL,
        price REAL,
        quantity REAL,
        symbol TEXT NOT NULL,
        creation_timestamp TEXT NOT NULL,
        execution_timestamp TEXT,
        profit_loss REAL
    );
    """)
    conn.commit()
    conn.close()
    
    
def fetch_data(symbol='BTCUSDT'):
    # Connect to the SQLite database
    conn = connect_db()
    # Fetch data for the specified symbol
    query = f"SELECT start_time, last_price FROM market_data WHERE symbol = '{symbol}' ORDER BY start_time ASC"
    df = pd.read_sql(query, conn, parse_dates=['start_time'], index_col='start_time')
    conn.close()
    return df  
  
def insert_data(start_time, end_time, open, high, low, close, volume,symbol):
    conn = connect_db()
    c = conn.cursor()
    c.execute('''INSERT INTO market_data (start_time, end_time, open, high, low, close, volume,symbol) 
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?)''', (start_time, end_time, open, high, low, close, volume,symbol))
    conn.commit()
    conn.close()