import os

def config():
    return {
        'token': os.environ.get('TELEGRAM_TOKEN'),
        'chat_id': os.environ.get('TELEGRAM_CHAT_ID')
    }
