# coding: utf-8
import os
import sqlite3
import argparse
import datetime


MESSAGE_TEXT="""
***** Nagios *****

Notification Type: {NOTIFICATIONTYPE}
Host: {HOSTNAME}
State: {HOSTSTATE}
Address: {HOSTADDRESS}
Info: {HOSTOUTPUT}

Date/Time: {LONGDATETIME}
"""

def insert_new_entry(service_alert):
    current_time = datetime.datetime.now() # Get the current time for insertion
    current_time_str = current_time.strftime('%m/%d/%Y %H:%M:%S')

    # Determine how to format the string
    string_to_insert = None
    env = os.environ
    print env
    if service_alert:
        print "Service called"
        string_to_insert = MESSAGE_TEXT.format(NOTIFICATIONTYPE=env.get('NAGIOS_NOTIFICATIONTYPE'), HOSTNAME=env.get('NAGIOS_HOSTNAME'), HOSTSTATE=env.get('NAGIOS_HOSTSTATE'),
                                                        HOSTADDRESS=env.get('NAGIOS_HOSTADDRESS'), HOSTOUTPUT=env.get('NAGIOS_SERVICEOUTPUT'), LONGDATETIME=env.get('NAGIOS_LONGDATETIME'))
    else:
        # Host alert
        print "Host alert"
        string_to_insert = MESSAGE_TEXT.format(NOTIFICATIONTYPE=env.get('NAGIOS_NOTIFICATIONTYPE'), HOSTNAME=env.get('NAGIOS_HOSTNAME'), HOSTSTATE=env.get('NAGIOS_HOSTSTATE'),
                                                        HOSTADDRESS=env.get('NAGIOS_HOSTADDRESS'), HOSTOUTPUT=env.get('NAGIOS_HOSTOUTPUT'), LONGDATETIME=env.get('NAGIOS_LONGDATETIME'))

    conn = sqlite3.connect('alerts.db')
    c = conn.cursor()
    c.execute('''INSERT INTO NAGIOS_ALERTS(date_inserted,message_text, status) VALUES (?, ?, 'UNSENT')''', (current_time_str, string_to_insert) )
    conn.commit()
    conn.close()

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--service', action='store_true', help="This is a service alert")
    args = parser.parse_args()
    service_alert = False # Default is that this is a service alert
    if args.service:
        service_alert = True
    insert_new_entry(service_alert)
    # parse args here

