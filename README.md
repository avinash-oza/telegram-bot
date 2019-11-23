# telegram-bot
This bot uses `python-telegram-bot` to implement a simple bot that provides access to the following functions:

* control garages via AWS SNS
* provide crypto prices via the GDAX and Gemini API
 
### Running ###
 * `pip install -r requirements.txt`
 * `pip install .`
 * Setup AWS credentials to access the response queue
 * use `run-telegram-bot` to start up

### Docker ###
This project can be run via Docker. AWS credentials need to be mounted from the local machine:

`docker run -d --env-file bot.env -v /home/my_dir/.aws:/root/.aws avinashoza/telegram-bot:v0.2b7`
