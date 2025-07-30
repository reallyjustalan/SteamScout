from telethon import TelegramClient, events, Button
from dotenv import load_dotenv
from os import getenv
import requests
from datetime import datetime
from collections import defaultdict
load_dotenv()

api_id = getenv('TELEGRAM_API_ID')
api_hash = getenv('TELEGRAM_API_HASH')
bot_token = getenv('TELEGRAM_API_KEY')

url = "http://localhost:8000"


client = TelegramClient('bot', api_id, api_hash).start(bot_token=bot_token)

def get_users():
    response = requests.get(f"{url}/people/")
    if response.status_code == 200:
        return response.json().get('all_users', [])
    return []


def build_message_and_buttons(users):
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    
    if not users:
        text = f"No users are currently being tracked.\n\n_Last updated: {now}_"
        buttons = [[Button.inline("Update Status", b"update_status")]]
        return text, buttons

    games = defaultdict(lambda: defaultdict(list))
    not_in_game = []

    for user in users:
        app_id = user.get('game_played_app_id')
        rp = user.get('rich_presence', {})
        group_id = rp.get('steam_player_group')
        if not app_id:
            not_in_game.append(user['name'])
            continue

        games[app_id][group_id].append(user)

    lines = []
    for app_id, groupings in games.items():
        game_name = "CS2" if app_id == 730 else ("CS2 Danger Zone" if app_id == 740 else f"App {app_id}")
        lines.append(f"🎮 **{game_name}**:")

        for group_id, userlist in groupings.items():
            # Let's extract shared map, score, mode info for the group
            first_rp = userlist[0]['rich_presence'] if userlist[0].get('rich_presence') else {}
            map_name = first_rp.get('game:map')
            score = first_rp.get('game:score') or ""
            mode = first_rp.get('game:mode', '')
            act = first_rp.get('game:act', '')
            # Handle group display
            if group_id:
                # Party/Lobby
                names = ", ".join(u['name'] for u in userlist)
                # Build a display string
                desc_parts = []
                if mode and mode != 'custom':
                    desc_parts.append(mode.capitalize())
                if map_name:
                    desc_parts.append(map_name)
                if score:
                    desc_parts.append(f"Score {score}")
                elif act == 'offline':
                    desc_parts.append("Offline Map")
                # Final description
                group_desc = " | ".join(desc_parts)
                lines.append(f"    • Lobby [{group_id}]: {names} ({group_desc})")
            else:
                # Solo, show what they're doing
                for u in userlist:
                    rp = u.get('rich_presence', {})
                    map_name = rp.get('game:map')
                    mode = rp.get('game:mode')
                    act = rp.get('game:act')
                    score = rp.get('game:score')
                    solo_desc = []
                    if mode and mode != 'custom':
                        solo_desc.append(mode.capitalize())
                    if map_name:
                        solo_desc.append(map_name)
                    if score:
                        solo_desc.append(f"Score {score}")
                    elif act == 'offline':
                        solo_desc.append("Offline Map")
                    solo_string = " | ".join(solo_desc) if solo_desc else ""
                    lines.append(f"    • {u['name']} (solo){f' ({solo_string})' if solo_string else ''}")

    if not_in_game:
        lines.append("\n❌ Not in-game:\n" + ", ".join(not_in_game))

    text = "\n".join(lines) + f"\n\n__Last updated: {now}__"
    buttons = [[Button.inline("Update Status", b"update_status")]]
    return text, buttons


@client.on(events.NewMessage)
async def my_event_handler(event):
    if 'status' in event.raw_text:
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
