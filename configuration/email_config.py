import os


def google():
    return {
        'smtp_server': 'smtp.google.com',
        'port': 587,
        'email_password': os.environ.get('GMAIL_PASSWORD')
    }