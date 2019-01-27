# telegram-bot
There are 2 goals in here: Create a bot to communicate with at home, provide a way for nagios to send email alerts via telegram.

`sudo docker run -d --env-file /etc/telegram-bot/bot.env -v /home/my_dir/.aws:/root/.aws telegram-bot:v0.2b7`

### Requirements ###
* requirements.txt provides all the requirements. This script is based on the `python-telegram-bot` API written in python.
* Make sure to chmod 0777 the directory so that all scripts are executable and the sql lite DB can be read

#### Description ####

 * start_telegram_bot.py : Holds logic for the telegram bot
  * `powerstatus` : holds logic for retrieving the current UPS status
  * `send_nagios_alerts` : periodic job that checks the MySQL db for any alerts to send. It pushes this to the `admin_id` via telegram. The optiuon is given to acknowledge the alert which will schedule downtime on nagios.
 * insert_[service|host]_alert.sh : Wrapper script for `insert_alert.py` which uses python in order to insert the entry into MySQL db.
 
### Running ###
 Currently this requires a lot of packages as it is in python 2.7:
 * Create a virtualenv (strongly reccomended)
 * `pip install -r requirements.txt`
 * `pip install .`
 * use the `run-telegram-bot` to start up
