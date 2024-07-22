import requests
import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Define a function to get the data from CoinGecko API
def get_crypto_data():
    url = 'https://api.coingecko.com/api/v3/coins/markets'
    parameters = {
        'vs_currency': 'usd',
        'order': 'market_cap_desc',
        'per_page': 250,
        'page': 1,
        'sparkline': False
    }
    
    try:
        response = requests.get(url, params=parameters)
        response.raise_for_status()
        data = response.json()
        return pd.DataFrame(data)
    except requests.exceptions.HTTPError as http_err:
        logging.error(f"HTTP error occurred: {http_err}")
    except requests.exceptions.ConnectionError as conn_err:
        logging.error(f"Connection error occurred: {conn_err}")
    except requests.exceptions.Timeout as timeout_err:
        logging.error(f"Timeout error occurred: {timeout_err}")
    except requests.exceptions.RequestException as req_err:
        logging.error(f"An error occurred: {req_err}")
    return pd.DataFrame()  # Return an empty DataFrame in case of error

# Function to filter coins based on certain criteria
def filter_potential_coins(df):
    if df.empty:
        logging.warning("Empty DataFrame provided to filter_potential_coins function.")
        return df
    
    # Ensure necessary columns are present
    required_columns = ['market_cap', 'total_volume', 'price_change_percentage_24h', 'circulating_supply', 'ath_change_percentage']
    for col in required_columns:
        if col not in df.columns:
            logging.warning(f"Missing required column: {col}")
            return pd.DataFrame()  # Return an empty DataFrame if required column is missing
    
    # Convert columns to numeric if they are not
    df[required_columns] = df[required_columns].apply(pd.to_numeric, errors='coerce')
    
    # Drop rows with NaN values in required columns
    df.dropna(subset=required_columns, inplace=True)
    
    # Example criteria:
    # 1. Market Cap less than $1 billion (considered small to mid-cap)
    # 2. Volume/Market Cap ratio (liquidity) greater than 0.1
    # 3. 24h price change positive (indicating upward momentum)
    filtered_df = df[(df['market_cap'] < 1e9) &
                     (df['total_volume'] / df['market_cap'] > 0.1) &
                     (df['price_change_percentage_24h'] > 0)]
    
    # Additional custom criteria for potential 10x growth
    # e.g., exclude very high supply coins, consider recent performance, etc.
    filtered_df = filtered_df[(filtered_df['circulating_supply'] < 1e10) & 
                              (filtered_df['ath_change_percentage'] < -50)]
    
    return filtered_df

# Function to get historical data for a specific coin
def get_historical_data(coin_id, days=30):
    url = f'https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart'
    parameters = {
        'vs_currency': 'usd',
        'days': days
    }
    
    try:
        response = requests.get(url, params=parameters)
        response.raise_for_status()
        data = response.json()
        prices = data['prices']
        return pd.DataFrame(prices, columns=['timestamp', 'price'])
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to fetch historical data for {coin_id}: {e}")
        return pd.DataFrame()

# Function to analyze historical trends
def analyze_historical_trends(coin_id):
    df = get_historical_data(coin_id)
    if df.empty:
        return None
    
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)
    
    # Calculate daily returns
    df['returns'] = df['price'].pct_change()
    
    # Calculate volatility (standard deviation of returns)
    volatility = df['returns'].std()
    
    return volatility

# Main function
def main():
    # Get crypto data
    df = get_crypto_data()
    
    # Filter the data to find potential coins
    potential_coins = filter_potential_coins(df)
    
    if not potential_coins.empty:
        # Analyze historical trends and add to the DataFrame
        potential_coins['volatility'] = potential_coins['id'].apply(analyze_historical_trends)
        
        # Sort by market cap for better readability
        potential_coins = potential_coins.sort_values(by='market_cap', ascending=True)
        
        # Display the potential coins
        pd.set_option('display.max_columns', None)  # Show all columns
        print(potential_coins[['id', 'symbol', 'name', 'current_price', 'market_cap', 'price_change_percentage_24h', 'ath_change_percentage', 'volatility']])
    else:
        logging.info("No potential coins found.")

if __name__ == '__main__':
    main()
