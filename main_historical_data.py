from db.database import setup_database
from utils import ticker_client
from utils.fetch_historical_data import get_data
from utils.websocket_client import start_websocket

def main():
    get_data()

if __name__ == "__main__":
    main()
