# coding: utf-8
import os
import argparse
import datetime
import urllib
import urllib2
import json
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
    env = os.environ
    # Parameters for alerts
    notification_type = env.get('NAGIOS_NOTIFICATIONTYPE')
    host_name = env.get('NAGIOS_HOSTNAME')
    host_state = env.get('NAGIOS_HOSTSTATE')
    host_address = env.get('NAGIOS_HOSTADDRESS')
    service_output = env.get('NAGIOS_SERVICEOUTPUT')
    host_output = env.get('NAGIOS_HOSTOUTPUT')
    nagios_date_time = env.get('NAGIOS_LONGDATETIME')
    service_name = env.get('NAGIOS_SERVICEDISPLAYNAME') # The display name of the service

    url = config.get('ALERTS', 'api_endpoint')

    data_dict = {'host_name' : host_name,
                'host_state': host_state,
                'host_address': host_address,
                'n_datetime' : nagios_date_time,
                'service_name' : service_name,
                'notification_type' : notification_type}

    if service_alert:
        print "Service called"
        data_dict['alert_type'] = 'SERVICE'
        data_dict['output_text'] = service_output
    else:
        # Host alert
        print "Host alert"
        data_dict['alert_type'] = 'HOST'
        data_dict['output_text'] = host_output

    req = urllib2.Request(url)
    req.add_header('Content-Type', 'application/json')
    content = urllib2.urlopen(req, data=json.dumps(data_dict)).read()

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--service', action='store_true', help="This is a service alert")
    args = parser.parse_args()
    service_alert = False # Default is that this is a service alert
    if args.service:
        service_alert = True

    insert_new_entry(service_alert)
