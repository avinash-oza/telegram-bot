#!/bin/bash
source /home/telegram_bot/telegram-virtual-env/bin/activate
cd /home/telegram_bot/telegram-bot
python insert_alert.py
deactivate
