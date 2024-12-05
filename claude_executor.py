import asyncio
import argparse
from configuration.telegram_config import config as telegram_config
from notifications.telegram import send_telegram_message
from trading_bot.claude import CryptoTradingBot
import logging

logging.basicConfig(filename='trading_bot.log', level=logging.INFO, 
                    format='%(asctime)s %(message)s')

def telegram(message):
    config = telegram_config()
    asyncio.run(send_telegram_message(config['token'], config['chat_id'], message))
    logging.info(f"Telegram message sent: {message}")

if __name__ == "__main__":
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Set percentage_investment_amount for all trading pairs.")
    parser.add_argument(
        "--percentage",
        type=float,
        required=True,
        help="Percentage investment amount to set for all trading pairs (e.g., 0.1 for 10%)."
    )
    args = parser.parse_args()
    
    # Command-line argument for percentage_investment_amount
    percentage_investment_amount = args.percentage

    telegram('Claude BOT started')
    logging.info('Claude BOT started')

    # Define trading pairs with their individual take-profit and diversification percentages
    trading_pairs_config = {
        'BTCUSDT': {
            'take_profit_percentage': 0.03,  # 3% take profit for BTC
            'fixed_investment_amount': 20,
            'percentage_investment_amount': percentage_investment_amount
        },
        'SOLUSDT': {
            'take_profit_percentage': 0.05, 
            'fixed_investment_amount': 20,  
            'percentage_investment_amount': percentage_investment_amount
        },
        'TRXUSDT': {
            'take_profit_percentage': 0.05, 
            'fixed_investment_amount': 20,
            'percentage_investment_amount': percentage_investment_amount
        },
        'ETHUSDT': {
            'take_profit_percentage': 0.02, 
            'fixed_investment_amount': 20,
            'percentage_investment_amount': percentage_investment_amount
        },
        'XRPUSDT': {
            'take_profit_percentage': 0.03,  
            'fixed_investment_amount': 20,
            'percentage_investment_amount': percentage_investment_amount
        },
        'ADAUSDT': {
            'take_profit_percentage': 0.03,
            'fixed_investment_amount': 20,
            'percentage_investment_amount': percentage_investment_amount
        }
    }

    bot = CryptoTradingBot(trading_pairs_config)
    try:
        bot.run()
    except Exception as e: 
        telegram("CLAUDE has STOPPED with error! " + str(e))
        raise
