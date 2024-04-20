
from configuration.email_config import google
from notifications.email import send_email
from configuration.telegram_config import config
from notifications.telegram import send_telegram_message
import asyncio

def send_signal(signal, symbol, channel):
    if channel == 'EMAIL':
        email(signal, symbol)
    else:
        telegram(signal, symbol)    
    
def email(signal, symbol):
    config = google()
    body = f'You have a signal to {signal} {symbol}'
    send_email('d4pano@gmail.com','jimmypano@hotmail.com','New signal','',config['smtp_server'],config['port'],config['email_password'])

def telegram(signal, symbol):
    telegram_config = config()
    message = f'New {signal} signal for {symbol}'
    asyncio.run(send_telegram_message(telegram_config['token'], telegram_config['chat_id'], message))     