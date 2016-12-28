# telegram-bot
There are 2 goals in here: Create a bot to communicate with at home, provide a way for nagios to send email alerts via telegram.

### Requirements ###
* requirements.txt provides all the requirements. This script is based on the python-telegram-bot API written in python.
* Make sure to chmod 0777 the directory so that all scripts are executable and the sql lite DB can be read

#### Description ####

 * start_telegram_bot.py : Script that holds the bot and will respond to requests and send out alerts. It periodically reads from the SQLLite database to see if there are any unsent alerts.
 * insert_[service|host]_alert.sh : Wrapper script for `insert_alert.py` which uses python in order to insert the entry into the SQLLite db.
 
### Running ###
 Currently this requires a lot of packages as it is in python 2.7:
 * Create a virtualenv (strongly reccomended)
 * pip install -r requirements.txt
 * `python start_telegram_bot.py & ` (this will start the bot and background it. You may see some warnings)
