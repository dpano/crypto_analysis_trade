

from trading_bot.claude import CryptoTradingBot


if __name__ == "__main__":
    
        # Define trading pairs with their individual take-profit and diversification percentages
    trading_pairs_config = {
        'BTCUSDT': {
            'take_profit_percentage': 0.03,  # 3% take profit for BTC
            'diversification_percentage': 0.4
        },
        'SOLUSDT': {
            'take_profit_percentage': 0.04,  # 4% take profit for ETH
            'diversification_percentage': 0.30  # 3% of available balance for ETH
        },
        'TRXUSDT': {
            'take_profit_percentage': 0.05,  # 5% take profit for ADA
            'diversification_percentage': 0.2  # 2% of available balance for ADA
        },
    }

    bot = CryptoTradingBot(trading_pairs_config)
    bot.run()