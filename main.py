from db.database import setup_database
from utils import ticker_client
from utils.websocket_client import start_websocket

def main():
    setup_database()
    #start_websocket()
    #ticker_client.start_ticker()

if __name__ == "__main__":
    main()
