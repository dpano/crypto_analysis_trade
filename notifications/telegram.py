from telegram import Bot

async def send_telegram_message(token, chat_id, message):
    bot = Bot(token=token)
    await bot.send_message(chat_id=chat_id, text=message)

# Replace 'YOUR_TOKEN_HERE' with your bot's token and 'CHAT_ID' with the recipient's chat ID
# token = 'YOUR_TOKEN_HERE'
# chat_id = 'CHAT_ID'
# message = 'Hello from your bot!'

