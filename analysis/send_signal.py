from configuration.email_config import google
from notifications.email import send_email


def send_signal(signal, symbol):
    config = google()
    body = f'You have a signal to {signal} {symbol}'
    send_email('d4pano@gmail.com','jimmypano@hotmail.com','New signal','',config.smtp_server,config.port,config.email_password)