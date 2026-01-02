import arrow
import requests
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

# maps action to the list of commands to be run
NAGIOS_COMMAND_MAPPING = {
    # host commands
    # service commands
    ("service", "acknowledge"): [
        "ACKNOWLEDGE_SVC_PROBLEM;{host_name};{service_desc};1;1;0;telegram-bot;Acknowledged by telegram"
    ],
    ("service", "downtime"): [
        "SCHEDULE_SVC_DOWNTIME;{host_name};{service_desc};{start_time};{end_time};1;0;{downtime_duration};telegram-bot;Scheduled by telegram"
    ],
}

SUPPORTED_ACTIONS = {
    "downtime": "Schedule Downtime",
    "acknowledge": "Acknowledge an Alert",
}

# pattern is to :
# get the action to do ( if needed ask duration time)
# get the message to do the action on
# determine the command to complete the action
# POST the command


def setup_handlers(dispatcher):
    # setup all the handlers required for this
    pass


def get_action_keyboard(bot, update):
    # returns back a keyboard of actions that can be taken
    # TODO: there should be no callbackquery to answer here
    keyboard_options = []
    for action, key_text in SUPPORTED_ACTIONS.items():
        callback_data = f"nagios action {action}"
        keyboard_options.append(
            InlineKeyboardButton(key_text, callback_data=callback_data)
        )

    return InlineKeyboardMarkup(keyboard_options)


def process_menu_option(bot, update):
    if update.callback_query is None:
        # no action yet so sent keyboard
        return get_action_keyboard(bot, update)

    update.callback_query.answer()
    callback_data = update.callback_query.data
    if callback_data in ("nagios action downtime", "nagios action acknowledge"):
        # TODO: how to convert to text box?
        update.callback_query.edit_message_text(
            "Please send the alert that you would like to action"
        )
        return


# TODO: check sender admin and pass update here
def parse_alert_message(bot, msg_txt):
    # TODO: how to select the action to be done?
    # TODO: How to get downtime window?
    downtime_window = 86400  # 1 day
    action = "downtime"
    # takes the input and parses it to a nagios command
    host, service_name = parse_ack_data(msg_txt)
    ack_type = "service"
    if not service_name:
        ack_type = "host"

    key = (ack_type, action)
    try:
        cmds = NAGIOS_COMMAND_MAPPING[key]
    except KeyError:
        print(f"Could not find key {key} in list of commands. Not doing anything")
        return

    # create all possible params for commands
    start_timestamp = arrow.get().timestamp
    end_timestamp = start_timestamp + downtime_window
    kwargs = {
        "host_name": host,
        "service_desc": service_name,
        "start_time": start_timestamp,
        "end_time": end_timestamp,
        "downtime_duration": downtime_window,
    }

    formatted_cmds = [c.format(**kwargs) for c in cmds]
    print(formatted_cmds)


def parse_ack_data(msg_txt):
    # extracts host/service or host information from the passed in string
    if "ACK_DATA" not in msg_txt:
        raise ValueError("Could not find ACK_DATA in string")

    s = test_msg.split("ACK_DATA:", maxsplit=2)[1].rstrip()
    host, service = s.split("|", maxsplit=2)

    return host, service


def get_unsent_messages(endpoint_url):
    results = requests.get(endpoint_url)
    results.raise_for_status()

    alerts_to_send = results.json()["alerts"]

    message_to_send = """"""
    return_keyboard = []
    for alert_number, one_alert in enumerate(alerts_to_send):
        alert_id = one_alert["id"]

        # construct the text message
        message_to_send += "Message ID: {}\n".format(alert_number)
        message_to_send += one_alert["message_text"] + "\n"

        if one_alert["can_acknowledge"]:
            return_keyboard.append(
                [
                    InlineKeyboardButton(
                        "Acknowledge alert {}".format(alert_number),
                        callback_data="nagios_ack {}".format(alert_id),
                    )
                ]
            )

        message_to_send += "--------------------\n"
        # mark the alert as sent
        update_resp = requests.post(
            endpoint_url + "{}".format(str(alert_id)), params={"status": "SENT"}
        )
        update_resp.raise_for_status()

    if message_to_send:
        message_to_send += "{0} messages sent".format(len(alerts_to_send))
    return message_to_send, return_keyboard


if __name__ == "__main__":
    test_msg = """
    *****Nagios*****
Notification Type: ${NAGIOS_NOTIFICATIONTYPE}
Host: ${NAGIOS_HOSTDISPLAYNAME}
State: ${NAGIOS_HOSTSTATE}
Address: ${NAGIOS_HOSTADDRESS}
Info: ${NAGIOS_SERVICEOUTPUT}
Date/Time: ${NAGIOS_LONGDATETIME}
ACK_DATA:localhost|SSH
    """

    test_msg2 = """
        *****Nagios*****
    Notification Type: ${NAGIOS_NOTIFICATIONTYPE}
    Host: ${NAGIOS_HOSTDISPLAYNAME}
    State: ${NAGIOS_HOSTSTATE}
    Address: ${NAGIOS_HOSTADDRESS}
    Info: ${NAGIOS_SERVICEOUTPUT}
    Date/Time: ${NAGIOS_LONGDATETIME}
    ACK_DATA:HOST|
        """
    parse_alert_message(None, test_msg)
