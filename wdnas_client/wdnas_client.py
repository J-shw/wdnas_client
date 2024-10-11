import requests
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
                    "size":  disk.findtext('size'),
                    "failed":  bool(int(disk.findtext('failed'))),
                    "healthy":  bool(int(disk.findtext('healthy'))),
                    "removable":  bool(int(disk.findtext('removable'))),
                    "over_temp":  bool(int(disk.findtext('over_temp'))),
                    "temp": disk.findtext('temp'),
                    "sleep":  bool(int(disk.findtext('sleep')))
                }
            
            for disk in device_info.iter('vol'):
                device_info_json['volumes'][disk.attrib['id']] = {
                    "name":  disk.findtext('name'),
                    "label":  disk.findtext('label'),
                    "encrypted":  bool(int(disk.findtext('encrypted'))),
                    "unlocked":  bool(int(disk.findtext('unlocked'))),
                    "mounted":  bool(int(disk.findtext('mounted'))),
                    "size":  disk.findtext('size'),
                }
            
            device_info_json['volumes']['size']['total'] = device_info.find('.//total_size').text
            device_info_json['volumes']['size']['used'] = device_info.find('.//total_used_size').text
            device_info_json['volumes']['size']['unused'] = device_info.find('.//total_unused_size').text
            
            return device_info_json
        else:
            raise RequestFailedError(response.status_code)
