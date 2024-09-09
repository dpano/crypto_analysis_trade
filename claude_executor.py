import ccxt

from trading_bot.claude import CryptoTradingBot


if __name__ == "__main__":
    exchange = ccxt.binance()  # Use Binance as an example, replace with your preferred exchange
        
        # Define trading pairs with their individual take-profit and diversification percentages
    trading_pairs_config = {
        'BTC/USDT': {
            'take_profit_percentage': 0.03,  # 3% take profit for BTC
            'diversification_percentage': 0.05  # 5% of available balance for BTC
        },
        'ETH/USDT': {
            'take_profit_percentage': 0.04,  # 4% take profit for ETH
            'diversification_percentage': 0.03  # 3% of available balance for ETH
        },
        'ADA/USDT': {
            'take_profit_percentage': 0.05,  # 5% take profit for ADA
            'diversification_percentage': 0.02  # 2% of available balance for ADA
        },
    }

    bot = CryptoTradingBot(exchange, trading_pairs_config)
    bot.run()