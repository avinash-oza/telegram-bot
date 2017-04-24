#!/bin/bash
source /home/telegram-bot/telegram-virtual-env/bin/activate
cd /home/telegram-bot/telegram-bot
python insert_alert.py
deactivate
