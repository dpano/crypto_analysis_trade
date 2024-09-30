
import asyncio
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
    heartbeat = 0
    telegram('Claude BOT started')
    logging.info('Claude BOT started')
        # Define trading pairs with their individual take-profit and diversification percentages
    trading_pairs_config = {
        'BTCUSDT': {
            'take_profit_percentage': 0.03,  # 3% take profit for BTC
            'fixed_investment_amount': 10
        },
        'SOLUSDT': {
            'take_profit_percentage': 0.03,  # 4% take profit for ETH
            'fixed_investment_amount': 10  # 3% of available balance for ETH
        },
        'TRXUSDT': {
            'take_profit_percentage': 0.03,  # 5% take profit for ADA
            'fixed_investment_amount': 10  # 2% of available balance for ADA
        },
        'ETHUSDT': {
            'take_profit_percentage': 0.03,  # 5% take profit for ADA
            'fixed_investment_amount': 10  # 2% of available balance for ADA
        }
    }

    bot = CryptoTradingBot(trading_pairs_config)
    bot.run()