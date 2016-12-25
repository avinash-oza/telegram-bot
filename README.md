# telegram-bot
There are 2 goals in here: Create a bot to communicate with at home, provide a way for nagios to send email alerts via telegram.

 * start_telegram_bot.py : The script which will house the bot to provide different commands
 * send_alert.sh : Wrapper script for nagios to set up the alert and call the script
 * send_nagios_alert.py : Main script to use the telegram API in order to send out the alert
