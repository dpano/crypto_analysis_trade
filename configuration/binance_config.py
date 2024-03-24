# Configuration function
import os


def config():
    return {
        'api_key': os.environ.get('BINANCE_API_KEY'),
        'api_secret': os.environ.get('BINANCE_API_SECRET')
    }