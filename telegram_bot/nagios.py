import requests
from telegram import InlineKeyboardButton


def get_unsent_nagios_alerts(endpoint_url):
    results = requests.get(endpoint_url)
    results.raise_for_status()

    alerts_to_send = results.json()['alerts']

    message_to_send = """"""
    return_keyboard = []
    for alert_number, one_alert in enumerate(alerts_to_send):
        alert_id = one_alert['id']

        # construct the text message
        message_to_send += "Alert ID: {}".format(alert_number)
        message_to_send += one_alert['message_text']
        acknowledge_alert = one_alert['notification_type'].upper() == 'PROBLEM'
        if acknowledge_alert:
            return_keyboard.append([InlineKeyboardButton('Acknowledge alert {}'.format(alert_number), callback_data='nagios_ack {}'.format(alert_id))])

        message_to_send += "--------------------\n"
        # mark the alert as sent
        update_resp = requests.post(endpoint_url + 'alerts/{}'.format(str(alert_id)), params={'status': 'SENT'})
        update_resp.raise_for_status()

    if message_to_send:
        message_to_send += "{0} messages sent".format(len(alerts_to_send))
    return message_to_send, return_keyboard


if __name__ == '__main__':
    print(get_unsent_nagios_alerts("http://localhost:5000/nagios/"))
