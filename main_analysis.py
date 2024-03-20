from analysis.technical_analysis import analyze_signals, calculate_indicators
from db.database import fetch_daily_data, fetch_data


def main():
    df = fetch_data()
    df = calculate_indicators(df)  # Calculate technical indicators
    df = analyze_signals(df)  # Analyze for trading signals
    print(df.tail(10))

if __name__ == "__main__":
    main()
