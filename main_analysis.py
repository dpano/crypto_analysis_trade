from db.database import fetch_daily_data


def main():
    #setup_database()
    #start_websocket()
    df = fetch_daily_data()
    print(df)

if __name__ == "__main__":
    main()
