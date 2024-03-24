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
        event_timestamp TEXT,           
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
    query = f"SELECT start_time, close, symbol FROM market_data WHERE symbol = '{symbol}' ORDER BY id ASC"
    df = pd.read_sql(query, conn, parse_dates=['start_time'], index_col='start_time')
    conn.close()
    return df  

def fetch_daily_data(symbol='BTCUSDT'):
    # Connect to the SQLite database
    conn = connect_db()
    # Fetch data for the specified symbol
    query = f"""
        SELECT 
            t1.*
        FROM 
            market_data t1
        INNER JOIN 
            (
                SELECT 
                    DATE(start_time) as date,
                    MAX(id) as max_id
                FROM 
                    market_data
                GROUP BY 
                    DATE(start_time)
            ) t2 ON t1.id = t2.max_id
        ORDER BY 
            t1.start_time DESC;
        """
    df = pd.read_sql(query, conn, parse_dates=['start_time'], index_col='start_time')
    conn.close()
    return df  

def insert_data(event_timestamp,start_time, end_time, open, high, low, close, volume,symbol):
    try:
        conn = connect_db()
        c = conn.cursor()
        c.execute('''INSERT INTO market_data (event_timestamp, start_time, end_time, open, high, low, close, volume, symbol) 
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''', 
                  (event_timestamp, start_time, end_time, open, high, low, close, volume, symbol))
        conn.commit()
    except sqlite3.IntegrityError as e:
        print("SQLite integrity error:", e)
        # Handle integrity errors (e.g., constraint violation)
    except sqlite3.OperationalError as e:
        print("SQLite operational error:", e)
        # Handle operational errors (e.g., unexpected disconnect, cannot find table)
    except Exception as e:
        # Catch-all for any other database exceptions
        print("General database error:", e)
    finally:
        # Ensure the connection is closed properly in any case
        if conn:
            conn.close()