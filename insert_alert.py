# coding: utf-8
import os
import sqlite3
import argparse
import datetime
import mysql.connector
import ConfigParser

config = ConfigParser.ConfigParser()
config.read('bot.config')

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

    db_host_name = config.get('DATABASE', 'host')
    db_user_name = config.get('DATABASE', 'user')
    db_password = config.get('DATABASE', 'password')
    database_name = config.get('DATABASE', 'database')

    conn =  mysql.connector.connect(user=db_user_name,password=db_password,host=db_host_name, database=database_name)
    cursor = conn.cursor(buffered=True)

    query =  """INSERT INTO `nagios_alerts`(`message_text`) VALUES ("{0}")""".format(string_to_insert)
    cursor.execute(query )
    # Commit the changes
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

