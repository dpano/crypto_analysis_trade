import sqlite3

import pandas as pd

def connect_db(db_file='trading_bot.db'):
    return sqlite3.connect(db_file)

def get_db_cursor():
    conn = connect_db()
    conn.row_factory = sqlite3.Row
    return conn

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
        symbol,
        UNIQUE(start_time,end_time,symbol)
    )''')
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY,
        position_id INTEGER,
        type TEXT NOT NULL,
        status TEXT NOT NULL,
        price REAL,
        quantity REAL,
        symbol TEXT NOT NULL,
        creation_timestamp TEXT NOT NULL,
        execution_timestamp TEXT,
        FOREIGN KEY (position_id) REFERENCES positions(id)
    );
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS positions (
        id INTEGER PRIMARY KEY,
        status TEXT NOT NULL,
        quantity REAL,
        entry_price REAL,
        exit_price REAL,       
        symbol TEXT NOT NULL,
        create_timestamp TEXT NOT NULL,
        entry_timestamp TEXT,
        exit_timestamp TEXT,
        profit_loss REAL
    );
    """)

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS trading_signals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT,           
        signal_time TEXT,
        signal_type TEXT,
        rsi REAL,
        sma_50 REAL,
        sma_200 REAL,
        golden_cross INTEGER,
        death_cross INTEGER,
        overbought INTEGER,
        oversold INTEGER,           
        UNIQUE(symbol,signal_time));
    ''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY,
                    timestamp TEXT,
                    symbol TEXT,
                    side TEXT,
                    price REAL,
                    quantity REAL,
                    total REAL
                 )''')
    conn.commit()
    conn.close()
    
    
def fetch_data(symbol='BTCUSDT', limit=500):
    # Connect to the SQLite database
    conn = connect_db()
    # Fetch data for the specified symbol
    query = f"""SELECT id, start_time, end_time, close, symbol 
                FROM (
                    SELECT id, start_time, end_time, close, symbol
                    FROM market_data 
                    WHERE symbol = '{symbol}'
                    ORDER BY id DESC
                    LIMIT '{limit}'
                ) AS last_records
                ORDER BY id ASC"""
    df = pd.read_sql(query, conn, parse_dates=['start_time'], index_col='id')
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

def store_last_signal(symbol, signal_time, signal_type, rsi, sma_50, sma_200, golden_cross, death_cross, overbought, oversold):
    conn = connect_db()
    cursor = conn.cursor()
    # INSERT OR REPLACE based on the uniqueness of (symbol, signal_time)
    query = '''INSERT OR REPLACE INTO trading_signals (symbol, signal_time, signal_type, rsi, sma_50, sma_200, golden_cross, death_cross, overbought, oversold) 
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'''
    cursor.execute(query, (symbol, signal_time.isoformat(), signal_type, rsi, sma_50, sma_200, golden_cross, death_cross, overbought, oversold))
    conn.commit()
    conn.close()     

def log_trade(symbol, side, price, quantity):
    conn = connect_db()
    c = conn.cursor()
    total = price * quantity
    c.execute("INSERT INTO trades (timestamp, symbol, side, price, quantity, total) VALUES (datetime('now'), ?, ?, ?, ?, ?)",
              (symbol, side, price, quantity, total))
    conn.commit()
    conn.close()       