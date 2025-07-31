#!/bin/sh
trap "kill 0" SIGINT SIGTERM
uv run steampoll.py &
uv run uvicorn webserver:app &
uv run telebot.py &
wait
