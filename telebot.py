from telethon import TelegramClient, events
from dotenv import load_dotenv
from os import getenv
import requests

load_dotenv()

api_id = getenv('TELEGRAM_API_ID')
api_hash = getenv('TELEGRAM_API_HASH')
bot_token = getenv('TELEGRAM_API_KEY')

url = "http://localhost:8000"

client = TelegramClient('bot', api_id, api_hash).start(bot_token=bot_token)

@client.on(events.NewMessage)
async def my_event_handler(event):
    if 'hello' in event.raw_text:
        await event.reply('Hello! I am your Steam Stalker bot. How can I assist you today?')
    elif 'status' in event.raw_text:
        response = requests.get(f"{url}/people/")
        if response.status_code == 200:
            users = response.json().get('all_users', [])
            if users:
                users_list = []
                for user in users:
                    # Format the user information
                    user_info = f"{user['name']}: {user['game_played_app_id'] or 'None'}"
                    if user['rich_presence']:
                        user_info += f"\nRich Presence: {user['rich_presence']}"
                    users_list.append(user_info)
                await event.reply("\n".join(users_list))
            else:
                await event.reply("No users are currently being tracked.")
        else:
            await event.reply("Failed to retrieve user status.")

client.start()
client.run_until_disconnected()
