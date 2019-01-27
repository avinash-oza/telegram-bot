FROM python:latest
ARG TELEGRAM_BOT_RELEASE=v0.2b7
VOLUME ["/root/.aws"]

RUN mkdir -p /tmp/telegram-bot \
    && curl -SL https://github.com/avinash-oza/telegram-bot/archive/${TELEGRAM_BOT_RELEASE}.tar.gz | tar xvzf - --strip-components=1 -C /tmp/telegram-bot \
    && ls -al /tmp/telegram-bot \
    && pip install -r /tmp/telegram-bot/requirements.txt \
    && pip install /tmp/telegram-bot

CMD ["run-telegram-bot"]