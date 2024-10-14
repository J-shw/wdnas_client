import requests, json
# import rc4
from .exceptions import InvalidLoginError, RequestFailedError
from xml.etree import ElementTree

RAW_LOGIN_STRING = 'cmd=wd_login&username={username}&pwd={enc_password}'
SCHEME = "http://"


class client:
    def __init__(self, username, enc_password, host):
        self.host = host
        self.username = username
        self.enc_password = enc_password
        self.session = requests.Session()
        self.login()

    def login(self):
        url = f"{SCHEME}{self.host}/cgi-bin/login_mgr.cgi"
        content_length = 1
        headers = {
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Host": self.host,
            "Content-Length": str(content_length),
        }
        data = RAW_LOGIN_STRING.format(username=self.username, enc_password=self.enc_password)
        response = self.session.post(url, data=data, headers=headers)

        if response.status_code == 200:
            if "PHPSESSID" in response.cookies and "WD-CSRF-TOKEN" in response.cookies:
                print("Login successful!")
            else:
                raise InvalidLoginError("Invalid Username/Password or missing cookies")
        else:
            raise RequestFailedError(response.status_code)
        
    def system_info(self):
        url = f"{SCHEME}{self.host}/xml/sysinfo.xml"
        wd_csrf_token = self.session.cookies['WD-CSRF-TOKEN']
        phpsessid = self.session.cookies['PHPSESSID']
        headers = {
            "Host": self.host,
            "X-CSRF-Token": wd_csrf_token,
            "Cookie": f"PHPSESSID={phpsessid}; WD-CSRF-TOKEN={wd_csrf_token};"
        }

        response = self.session.get(url, headers=headers)

        if response.status_code == 200:
            device_info = ElementTree.fromstring(response.content)
            device_info_json = {"disks": {}, "volumes": {"size":{}}}

            for disk in device_info.iter('disk'):
                device_info_json['disks'][disk.attrib['id']] = {
                    "name":  disk.findtext('name'),
                    "connected":  bool(int(disk.findtext('connected'))),
                    "vendor":  disk.findtext('vendor'),
                    "model":  disk.findtext('model'),
                    "rev":  disk.findtext('rev'),
                    "sn":  disk.findtext('sn'),
                    "size":  int(disk.findtext('size')),
                    "failed":  bool(int(disk.findtext('failed'))),
                    "healthy":  bool(int(disk.findtext('healthy'))),
                    "removable":  bool(int(disk.findtext('removable'))),
                    "over_temp":  bool(int(disk.findtext('over_temp'))),
                    "temp": int(disk.findtext('temp')),
                    "sleep":  bool(int(disk.findtext('sleep')))
                }
            
            for disk in device_info.iter('vol'):
                device_info_json['volumes'][disk.attrib['id']] = {
                    "name":  disk.findtext('name'),
                    "label":  disk.findtext('label'),
                    "encrypted":  bool(int(disk.findtext('encrypted'))),
                    "unlocked":  bool(int(disk.findtext('unlocked'))),
                    "mounted":  bool(int(disk.findtext('mounted'))),
                    "size":  int(disk.findtext('size')),
                }
            
            device_info_json['volumes']['size']['total'] =int(device_info.find('.//total_size').text)
            device_info_json['volumes']['size']['used'] = int(device_info.find('.//total_used_size').text)
            device_info_json['volumes']['size']['unused'] = int(device_info.find('.//total_unused_size').text)
            
            return device_info_json
        else:
            raise RequestFailedError(response.status_code)
    
    def share_names(self):
        url = f"{SCHEME}{self.host}/web/get_share_name_list.php"
        wd_csrf_token = self.session.cookies['WD-CSRF-TOKEN']
        phpsessid = self.session.cookies['PHPSESSID']
        headers = {
            "Host": self.host,
            "X-CSRF-Token": wd_csrf_token,
            "Cookie": f"PHPSESSID={phpsessid}; WD-CSRF-TOKEN={wd_csrf_token};"
        }

        response = self.session.post(url, headers=headers)

        if response.status_code == 200:
            json_content = json.loads(response.content)
            if json_content['success']:
                return json_content['item']
            else:
                raise RequestFailedError(response.status_code)
        else:
            raise RequestFailedError(response.status_code)
    
    def system_status(self):
        url = f"{SCHEME}{self.host}/cgi-bin/status_mgr.cgi"
        wd_csrf_token = self.session.cookies['WD-CSRF-TOKEN']
        phpsessid = self.session.cookies['PHPSESSID']
        headers = {
            "Host": self.host,
            "X-CSRF-Token": wd_csrf_token,
            "Cookie": f"PHPSESSID={phpsessid}; WD-CSRF-TOKEN={wd_csrf_token};",
            "Content-Length": str(1),
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        }

        data = 'cmd=resource'
        response = self.session.post(url, data=data, headers=headers)

        if response.status_code == 200:
            device_status = ElementTree.fromstring(response.content)
            json_device_status = {"memory": {}, "cpu": None}

            # cpu
            json_device_status['cpu'] = int(device_status.find('.//cpu').text.strip('%'))

            # Memory
            json_device_status['memory']['total'] = int(device_status.find('.//mem_total').text)
            json_device_status['memory']['unused'] = int(device_status.find('.//mem_free').text)
            json_device_status['memory']['simple'] = device_status.find('.//mem2_total').text

            return json_device_status
        else:
            raise RequestFailedError(response.status_code)

    def system_version(self):
        url = f"{SCHEME}{self.host}/cgi-bin/system_mgr.cgi"
        wd_csrf_token = self.session.cookies['WD-CSRF-TOKEN']
        phpsessid = self.session.cookies['PHPSESSID']
        headers = {
            "Host": self.host,
            "X-CSRF-Token": wd_csrf_token,
            "Cookie": f"PHPSESSID={phpsessid}; WD-CSRF-TOKEN={wd_csrf_token};",
            "Content-Length": str(1),
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        }

        data = 'cmd=get_firm_v_xml'
        response = self.session.post(url, data=data, headers=headers)

        if response.status_code == 200:
            device_version = ElementTree.fromstring(response.content)

            json_device_version = {"firmware": None, "oled": None}

            json_device_version['firmware'] = device_version.find('.//fw').text
            json_device_version['oled'] = device_version.find('.//oled').text.strip('\n')

            return json_device_version
        else:
            raise RequestFailedError(response.status_code)
    
    def latest_version(self):
        url = f"{SCHEME}{self.host}/cgi-bin/system_mgr.cgi"
        wd_csrf_token = self.session.cookies['WD-CSRF-TOKEN']
        phpsessid = self.session.cookies['PHPSESSID']
        headers = {
            "Host": self.host,
            "X-CSRF-Token": wd_csrf_token,
            "Cookie": f"PHPSESSID={phpsessid}; WD-CSRF-TOKEN={wd_csrf_token};",
            "Content-Length": str(1),
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        }

        data = 'cmd=get_auto_fw_version'
        response = self.session.post(url, data=data, headers=headers)

        if response.status_code == 200:
            latest_version = ElementTree.fromstring(response.content)

            json_latest_version = {"new": None, "details": {}}

            json_latest_version['new'] = bool(int(latest_version.find('.//new').text))
            
            json_latest_version['details']['version'] = latest_version.find('.//version').text
            json_latest_version['details']['path'] = latest_version.find('.//path').text
            json_latest_version['details']['releasenote'] = latest_version.find('.//releasenote').text

            return json_latest_version
        else:
            raise RequestFailedError(response.status_code)
    
    def accounts(self):
        url = f"{SCHEME}{self.host}/xml/account.xml"
        wd_csrf_token = self.session.cookies['WD-CSRF-TOKEN']
        phpsessid = self.session.cookies['PHPSESSID']
        headers = {
            "Host": self.host,
            "X-CSRF-Token": wd_csrf_token,
            "Cookie": f"PHPSESSID={phpsessid}; WD-CSRF-TOKEN={wd_csrf_token};",
        }

        response = self.session.post(url, headers=headers)

        if response.status_code == 200:
            accounts = ElementTree.fromstring(response.content)

            json_accounts = {"users": {}, "groups": {}}

            for user in accounts.iter('item'):
                json_accounts['users'][user.findtext('uid')] = {
                    "name": user.findtext('name'),
                    "email": user.findtext('email'),
                    "pwd": user.findtext('pwd'),
                    "gid": user.findtext('gid'),
                    "first_name": user.findtext('first_name'),
                    "hint": user.findtext('hint'),
                }

            
            for group in accounts.iter('item'):
                gid = group.findtext('gid')
                json_accounts['groups'][gid] = {
                    "name": group.findtext('name'),
                    "user_cnt": user.findtext('user_cnt'),
                }

                json_accounts['groups'][gid]['users'] = []
                for user in group.iter('users'):
                    json_accounts['groups'][gid]['users'].append(user.findtext('user'))
            
            return json_accounts
        else:
            raise RequestFailedError(response.status_code)