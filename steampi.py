import logging
from steam.client import SteamClient, builtins, user
from steam.enums import EResult, EPersonaState
from dotenv import load_dotenv
import os
import time
import gevent
import datetime
import pprint

print = pprint.pp
  # Good practice with gevent

load_dotenv()

# setup logging
logging.basicConfig(format="%(asctime)s | %(message)s", level=logging.INFO)
LOG = logging.getLogger()

client = SteamClient()
client.set_credential_location(".")  # where to store sentry files and other stuff


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
        client.reconnect(maxdelay=30)

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
    LOG.info("Chat message from %s: %s", steamuser.name, message)
    steamuser.send_message(f"Received your message, {steamuser.name}!")

last_played = {}
presence_greenlets = {}

def nowstr():
    return datetime.datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")


def poll_rich_presence(friend):
    """Poll and print rich presence every 5 seconds while the friend is in game."""
    last_rp = None
    while True:
        app_id = friend.get_ps("game_played_app_id")
        if not app_id:
            break  # Stop if friend is no longer in game
        rp = friend.rich_presence
        if rp != last_rp:
            print(f"{nowstr()} {friend.name} rich presence: {rp}")
            friend.send_message(f"Rich presence update: {rp}")
            last_rp = rp
        gevent.sleep(5)

def poll_friends_games():
    while True:
        # Print all friend names in one line, with timestamp
        names = [f.name for f in client.friends]
        print(f"{nowstr()} Checking games for: {', '.join(names)}")
        for friend in client.friends:
            current_app = friend.get_ps("game_played_app_id")
            previous_app = last_played.get(friend.steam_id)
            if current_app != previous_app:
                if current_app:
                    print(f"{nowstr()} {friend.name} started playing {current_app}")
                    # Start polling rich presence in a new greenlet
                    if friend.steam_id not in presence_greenlets:
                        g = gevent.spawn(poll_rich_presence, friend)
                        presence_greenlets[friend.steam_id] = g
                elif previous_app:
                    print(f"{nowstr()} {friend.name} stopped playing {previous_app}")
                    # Stop polling rich presence (the poller exits automatically)
                    if friend.steam_id in presence_greenlets:
                        # We can't force kill the greenlet, but it will exit on its own
                        del presence_greenlets[friend.steam_id]
            last_played[friend.steam_id] = current_app
        gevent.sleep(5)

@client.friends.on('ready')
def when_friendlist_ready():
    print("Friendlist ready, starting presence poller")
    gevent.spawn(poll_friends_games)  # Start poller as a greenlet


# main bit
LOG.info("-"*30)

try:
    result = client.cli_login(username=os.getenv("STEAM_USERNAME"), 
                              password=os.getenv("STEAM_PASSWORD"))
    if result != EResult.OK:
        LOG.info("Failed to login: %s" % repr(result))
        raise SystemExit
    LOG.info("Login successful")
    client.change_status(persona_state = EPersonaState.Online)
    client.run_forever()


except KeyboardInterrupt:
    if client.connected:
        LOG.info("Logout")
        client.logout()
