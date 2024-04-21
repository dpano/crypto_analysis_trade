import os

def config():
    return {
        'token': os.environ.get('TELEGRAM_TOKEN'),
        'chat_id': os.environ.get('TELEGRAM_CHAT_ID')
    }
    #'7054122444:AAHitQ3o2zl_TIhqIL86ha4QZWCtLrMUxbY'
    #'7078347828'