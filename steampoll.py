import logging
from steam.client import SteamClient, builtins, user
from steam.steamid import SteamID
from steam.enums import EResult, EPersonaState
import requests
from dotenv import load_dotenv
import os
import time
import gevent
import datetime
import pprint

load_dotenv()

# setup logging
logging.basicConfig(format="%(asctime)s | %(message)s", level=logging.INFO)
LOG = logging.getLogger()

client = SteamClient()

#set up requests
url = "http://localhost:8000"


@client.on("error")
def handle_error(result):
    LOG.info("Logon result: %s", repr(result))

@client.on("channel_secured")
def send_login():
    if client.relogin_available:
        client.relogin()

@client.on("connected")
def handle_connected():
    LOG.info("Connected to %s", client.current_server_addr)

@client.on("reconnect")
def handle_reconnect(delay):
    LOG.info("Reconnect in %ds...", delay)

@client.on("disconnected")
def handle_disconnect():
    LOG.info("Disconnected.")

    if client.relogin_available:
        LOG.info("Reconnecting...")
        client.reconnect(maxdelay=5)
    else:
        login_and_run()
        

@client.on("logged_on")
def handle_after_logon():
    LOG.info("-"*30)
    LOG.info("Logged on as: %s", client.user.name)
    LOG.info("Community profile: %s", client.steam_id.community_url)
    LOG.info("Last logon: %s", client.user.last_logon)
    LOG.info("Last logoff: %s", client.user.last_logoff)
    LOG.info("-"*30)
    LOG.info("Press ^C to exit")
    

@client.on("chat_message")
def handle_chat_message(steamuser, message):
    """Handle incoming chat messages."""
    LOG.info("Chat message from %s:/ %s", steamuser.name, message)
    steamuser.send_message(f"Received your message, {steamuser.name}!")


last_played = {}
presence_greenlets = {}
already_posted = set()

def poll_rich_presence(friend):
    """Poll and print rich presence every 5 seconds while the friend is in game."""
    last_rp = None
    while True:
        app_id = friend.get_ps("game_played_app_id")
        if not app_id:
            LOG.info(f"{friend.name} is not in game. Stopping rich presence poller.")
            break  # Stop if friend is no longer in game
        rp = friend.rich_presence
        if rp != last_rp:
            LOG.info(f" {friend.name} rich presence: {rp}")
            # Send rich presence to web server
            payload = {
                "steam_id": friend.steam_id,
                "name": friend.name,
                "game_played_app_id": app_id,
                "rich_presence": friend.rich_presence
            }
            requests.post(f"{url}/people/{friend.steam_id}", json=payload)
            last_rp = rp
        gevent.sleep(5)

def poll_friends_games():
    while True:
        LOG.info(f"Polling friends' games: {[f.name for f in client.friends]}")
        for friend in client.friends:
            #send all players once
            if friend.steam_id not in already_posted:
                payload = {
                            "steam_id": friend.steam_id,
                            "name": friend.name,
                            "game_played_app_id": None,
                            "rich_presence": {},
                        }
                requests.post(f"{url}/people/{friend.steam_id}", json=payload)
                already_posted.add(friend.steam_id)
        
            current_app = friend.get_ps("game_played_app_id")
            previous_app = last_played.get(friend.steam_id)
            if current_app != previous_app:
                if current_app and current_app != previous_app:
                    LOG.info(f"{friend.name} started playing {current_app}.")
                    # Start polling rich presence in a new greenlet
                    if friend.steam_id not in presence_greenlets:
                        g = gevent.spawn(poll_rich_presence, friend)
                        presence_greenlets[friend.steam_id] = g
                elif not current_app and previous_app:
                    payload = {
                        "steam_id": friend.steam_id,
                        "name": friend.name,
                        "game_played_app_id": None,
                        "rich_presence": {},
                    }
                    requests.post(f"{url}/people/{friend.steam_id}", json=payload)
                    LOG.info(f"{friend.name} stopped playing {previous_app}")
                    # Stop polling rich presence (the poller exits automatically)
                    if friend.steam_id in presence_greenlets:
                        # We can't force kill the greenlet, but it will exit on its own
                        del presence_greenlets[friend.steam_id]
            last_played[friend.steam_id] = current_app
        gevent.sleep(5)


@client.friends.on('ready')
def when_friendlist_ready():
    LOG.info("Friendlist ready, starting presence poller")
    gevent.spawn(poll_friends_games)  # Start poller as a greenlet


def login_and_run():
    try:
        result = client.cli_login(username=os.getenv("STEAM_USERNAME"), 
                                  password=os.getenv("STEAM_PASSWORD"))
        if result != EResult.OK:
            LOG.info("Failed to login: %s" % repr(result))
            raise SystemExit
        LOG.info("Login successful")
        client.run_forever()
    except KeyboardInterrupt:
        if client.connected:
            LOG.info("Logout")
            client.logout()
    finally:
        LOG.info("-" * 30)

LOG.info("-"*30)
try:
    login_and_run()

except KeyboardInterrupt:
    if client.connected:
        LOG.info("Logout")
        client.logout()
