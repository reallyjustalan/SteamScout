from telethon import TelegramClient, events, Button
from dotenv import load_dotenv
from os import getenv
import requests
from datetime import datetime, timedelta, timezone

load_dotenv()

api_id = getenv('TELEGRAM_API_ID')
api_hash = getenv('TELEGRAM_API_HASH')
bot_token = getenv('TELEGRAM_API_KEY')

url = "http://localhost:8000"

# Singapore is UTC+8
SGT = timezone(timedelta(hours=8))

client = TelegramClient('bot', api_id, api_hash).start(bot_token=bot_token)

def get_users():
    response = requests.get(f"{url}/people/")
    if response.status_code == 200:
        return response.json().get('all_users', [])
    return []

def build_message_and_buttons(users):
    now = datetime.now(SGT).strftime('%Y-%m-%d %H:%M:%S')
    if not users:
        text = f"No users are currently being tracked.\n\n_Last updated: {now}_"
        buttons = [[Button.inline("Update Status", b"update_status")]]
        return text, buttons
    messages = []
    for user in users:
        user_text = f"**{user['name']}**: {user['game_played_app_id'] or 'None'}"
        if user['rich_presence']:
            user_text += f"\nRich Presence: {user['rich_presence']}"
        messages.append(user_text)
    text = "\n\n".join(messages) + f"\n\n__Last updated: {now}__"
    buttons = [[Button.inline("Update Status", b"update_status")]]
    return text, buttons

@client.on(events.NewMessage)
async def my_event_handler(event):
    if 'hello' in event.raw_text:
        await event.reply('Hello! I am your Steam Stalker bot. How can I assist you today?')
    elif 'status' in event.raw_text:
        users = get_users()
        text, buttons = build_message_and_buttons(users)
        await event.reply(text, buttons=buttons)

@client.on(events.CallbackQuery(data=b"update_status"))
async def handler(event):
    users = get_users()
    text, buttons = build_message_and_buttons(users)
    await event.edit(text, buttons=buttons)

client.start()
client.run_until_disconnected()
