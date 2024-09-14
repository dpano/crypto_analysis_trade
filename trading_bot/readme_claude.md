# Cryptocurrency Trading Bot

This repository contains a Python-based cryptocurrency trading bot that automates trading on the Binance exchange using technical indicators and predefined strategies.

## Features

- Automated trading on Binance exchange
- Uses MACD and RSI indicators for buy signals
- Implements a take-profit strategy
- Supports multiple trading pairs
- Stores trading positions in a SQLite database
- Sends notifications via Telegram
- Implements error handling and logging

## Prerequisites

- Python 3.7+
- Binance account with API access
- Telegram bot for notifications (optional)

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/yourusername/crypto-trading-bot.git
   cd crypto-trading-bot
   ```

2. Install required packages:
   ```
   pip install -r requirements.txt
   ```

3. Set up configuration files:
   - Create `configuration/binance_config.py` with your Binance API credentials
   - Create `configuration/telegram_config.py` with your Telegram bot token and chat ID (optional)

## Configuration

1. Binance API Configuration (`configuration/binance_config.py`):
   ```python
   def config():
       return {
           'api_key': 'YOUR_BINANCE_API_KEY',
           'api_secret': 'YOUR_BINANCE_API_SECRET'
       }
   ```

2. Telegram Configuration (`configuration/telegram_config.py`):
   ```python
   def config():
       return {
           'token': 'YOUR_TELEGRAM_BOT_TOKEN',
           'chat_id': 'YOUR_TELEGRAM_CHAT_ID'
       }
   ```

3. Trading Pairs Configuration:
   Modify the `trading_pairs_config` dictionary in the main script to include the trading pairs you want to monitor and their respective settings.

## Usage

Run the bot using the following command:

```
python main.py
```

The bot will start monitoring the configured trading pairs, execute trades based on the defined strategy, and send notifications via Telegram.

## How it Works

1. The bot fetches market data for each configured trading pair.
2. It calculates technical indicators (MACD and RSI) on the fetched data.
3. Buy signals are generated based on MACD crossovers and RSI values.
4. When a buy signal is detected, the bot places a market buy order.
5. After a successful buy, a limit sell order is placed at the take-profit price.
6. The bot continuously monitors open positions and updates their status upon completion.
7. All trading activities are logged and notifications are sent via Telegram.

## Customization

You can customize the bot's behavior by modifying the following parameters in the `CryptoTradingBot` class:

- `fast_length`, `slow_length`, `signal_smoothing`: MACD parameters
- `rsi_length`, `rsi_entry_min`, `rsi_entry_max`: RSI parameters

## Disclaimer

This bot is for educational purposes only. Use it at your own risk. The authors are not responsible for any financial losses incurred from using this bot.

## License

This project is licensed under the MIT License.