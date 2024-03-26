from analysis.technical_analysis import start_market_pair_analysis
from brokers.binance import trading_pairs

def main():
    start_market_pair_analysis(trading_pairs())

if __name__ == "__main__":
    main()
