# telegram-bot
This bot uses `python-telegram-bot` to implement a simple bot that provides access to the following functions:

    * control garages via a REST API
    * provide crypto prices via the Cryptowatch API
    * access to temperatures via REST API
    * config stored in S3 for parameters
 
### Running ###
 * `pip install -r requirements.txt`
 * `pip install .`
 * entrypoint is `telegram_bot.webhook.webhook`

