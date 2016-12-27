# Python script to create nagios alerts table

import sqlite3
conn = sqlite3.connect('alerts.db')
c = conn.cursor()
c.execute('''CREATE TABLE NAGIOS_ALERTS(id integer primary key AUTOINCREMENT, date_inserted TEXT, date_sent text, message_text text,  status text)''')
c.execute('''CREATE INDEX index_name ON NAGIOS_ALERTS (status)''') # For quick lookup on bot
conn.close()
