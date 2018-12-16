import requests

class GarageDoorHandler:
    def __init__(self, config):
        hostname = config.get('GARAGE', 'hostname')
        port = config.get('GARAGE', 'port')

        user = config.get('GARAGE', 'username')
        password = config.get('GARAGE', 'password')

        self.garage_door_base_url = 'http://{0}:{1}'.format(hostname, port)
        self.garage_door_user_pass = (user, password)

    def _get_garage_position(self, garage_name='all'):
        # Returns whether the garage is open or closed
        request_url = '{0}/garage/status/{1}'.format(self.garage_door_base_url, garage_name)
        r = requests.get(request_url, auth=self.garage_door_user_pass)
        if r.status_code == 200:
            return r.json()

        return []

    def _control_garage(self, garage_name, action):
        request_url = '{0}/garage/control/{1}/{2}'.format(self.garage_door_base_url, garage_name, action)

        r = requests.get(request_url, auth=self.garage_door_user_pass)

        return r
