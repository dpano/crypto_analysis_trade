from db.database import setup_database
from utils.websocket_client import start_websocket

def main():
    setup_database()
    start_websocket()

if __name__ == "__main__":
    main()
