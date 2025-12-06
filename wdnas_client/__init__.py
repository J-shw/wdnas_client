import aiohttp, json, base64
import re
from datetime import timedelta
from .exceptions import InvalidLoginError, RequestFailedError
from .const import V2_RAW_LOGIN_STRING, SCHEME, ENDPOINTS
from xml.etree import ElementTree
import http.cookies

class client:
    """
    A client class for interacting with the WD NAS device API's (Versions 2 or 5).

    :host: The hostname or IP address of the device.
    :username: The username used for authentication (stored in lowercase).
    :password: The password used for authentication.
    :version: The API version being used (2 or 5).
    :session: An aiohttp.ClientSession object for making async requests (initially None).
    :phpsessid: The PHP session ID token (initially None; set after login).
    :wd_csrf_token: The CSRF token required for v2 requests (initially None; set after login).
    """
    def __init__(self, username: str, password: str, host: str, version: int):
        if version not in [2, 5]:
            raise ValueError("Unsupported/invalid version. Must be 2 or 5.")
        
        self.host = host
        self.username = username.lower()
        self.password = password
        self.version = version
        self.session = None
        self.phpsessid = None
        self.wd_csrf_token = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        await self.login()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.session.close()
        
    async def login(self) -> None:
        """Login to device"""
        url = f"{SCHEME}{self.host}{ENDPOINTS[self.version]['login']}"

        enc_password = base64.b64encode(self.password.encode('utf-8')).decode("utf-8")

        if self.version == 2:
            data = V2_RAW_LOGIN_STRING.format(username=self.username, enc_password=enc_password)
            headers = {
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                "Host": self.host,
            }
            async with self.session.post(url, data=data, headers=headers) as response:
                pass
        elif self.version == 5:
            json_payload = {
                "username": self.username,
                "password": enc_password
            }
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Host": self.host,
            }
            async with self.session.post(url, json=json_payload, headers=headers) as response:
                pass

        
        if response.status == 200:

            set_cookies = response.headers.getall('Set-Cookie', [])
            for cookie_str in set_cookies:
                cookie = http.cookies.SimpleCookie(cookie_str)
                for key, morsel in cookie.items():
                    self.session.cookie_jar.update_cookies({key: morsel.value})

            cookies = response.cookies

            if self.version == 2:
                if "PHPSESSID" in cookies and "WD-CSRF-TOKEN" in cookies:
                    self.phpsessid = cookies["PHPSESSID"].value
                    self.wd_csrf_token = cookies["WD-CSRF-TOKEN"].value
                else:
                    raise InvalidLoginError("Invalid Username/Password or missing cookies")
            elif self.version == 5:
                if "PHPSESSID" in cookies:
                    self.phpsessid = cookies["PHPSESSID"].value
        else:
            raise RequestFailedError(response.status)
    
    async def system_info(self) -> dict:
        """
        Fetches system information from the device.

        This includes data about physical **disks**, logical **volumes**, and overall
        storage **size** (total, used, and unused).
        """
        url = f"{SCHEME}{self.host}{ENDPOINTS[self.version]['system_info']}"
        if self.version == 2:     
            headers = {
                "Host": self.host,
                "X-CSRF-Token": self.wd_csrf_token,
            }
        elif self.version == 5:
            headers = {
                "Host": self.host
            }
        else:
            raise ValueError("Unsupported/invalid version.")
            
        async with self.session.get(url, headers=headers) as response:
            if response.status == 200:
                content = await response.text()
                device_info = ElementTree.fromstring(content)
                device_info_json = {"disks": [], "volumes": [], "size": {}}
                for disk in device_info.iter('disk'):
                    device_info_json['disks'].append({
                        "id": disk.attrib['id'],
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
                    })
                for disk in device_info.iter('vol'):
                    device_info_json['volumes'].append({
                        "id": disk.attrib['id'],
                        "name":  disk.findtext('name'),
                        "label":  disk.findtext('label'),
                        "encrypted":  bool(int(disk.findtext('encrypted'))),
                        "unlocked":  bool(int(disk.findtext('unlocked'))),
                        "mounted":  bool(int(disk.findtext('mounted'))),
                        "size":  int(disk.findtext('size')),
                    })
                device_info_json['size']['total'] =int(device_info.find('.//total_size').text)
                device_info_json['size']['used'] = int(device_info.find('.//total_used_size').text)
                device_info_json['size']['unused'] = int(device_info.find('.//total_unused_size').text)
                return device_info_json
            else:
                raise RequestFailedError(response.status)
    
    async def share_names(self) -> list:
        """Fetches a list of all share names configured on the device."""
        url = f"{SCHEME}{self.host}{ENDPOINTS[self.version]['share_names']}"

        if self.version == 2:     
            headers = {
                "Host": self.host,
                "X-CSRF-Token": self.wd_csrf_token,
            }
        elif self.version == 5:
            headers = {
                "Host": self.host
            }
        else:
            raise ValueError("Unsupported/invalid version.")

        async with self.session.post(url, headers=headers) as response:
            if response.status == 200:
                content = await response.text()
                json_content = json.loads(content)
                if json_content['success']:
                    return json_content['item']
                else:
                    raise RequestFailedError(response.status)
            else:
                raise RequestFailedError(response.status)
    
    async def system_status(self) -> dict:
        """
        Fetches system status from the device.

        This includes data about **CPU** and **memory** usage.
        """
        url = f"{SCHEME}{self.host}{ENDPOINTS[self.version]['system_status']}"

        if self.version == 2:     
            headers = {
                "Host": self.host,
                "X-CSRF-Token": self.wd_csrf_token,
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            }
            data = 'cmd=resource'
        elif self.version == 5:
            headers = {
                "Host": self.host,
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            }
            data = 'cmd=resource'
        else:
            raise ValueError("Unsupported/invalid version.")

        async with self.session.post(url, data=data, headers=headers) as response:
            if response.status == 200:
                content = await response.text()
                device_status = ElementTree.fromstring(content)
                json_device_status = {"memory": {}, "cpu": None}
                json_device_status['cpu'] = int(device_status.find('.//cpu').text.strip('%'))
                json_device_status['memory']['total'] = int(device_status.find('.//mem_total').text)
                json_device_status['memory']['unused'] = int(device_status.find('.//mem_free').text)
                json_device_status['memory']['simple'] = device_status.find('.//mem2_total').text
                return json_device_status
            else:
                raise RequestFailedError(response.status)
    
    async def network_info(self) -> dict:
        """
        Fetches network information from the device.

        This includes device **IP**, **MAC Address** and **Speed**.
        """
        url = f"{SCHEME}{self.host}{ENDPOINTS[self.version]['network_info']}"

        if self.version == 2:
            headers = {
                "Host": self.host,
                "X-CSRF-Token": self.wd_csrf_token,
            }
        elif self.version == 5:
            headers = {
                "Host": self.host
            }
        else:
            raise ValueError("Unsupported/invalid version.")

        async with self.session.get(url, headers=headers) as response:
            if response.status == 200:
                content = await response.text()
                network_info = ElementTree.fromstring(content)
                json_network_info = {}
                for lan in network_info.iter('lan'):
                    mac = lan.findtext('mac')
                    if mac != 'No found.':
                        json_network_info[mac] = {
                            "speed": lan.findtext('speed'),
                            "dhcp_enable": bool(int(lan.findtext('dhcp_enable'))),
                            "dns_manual": bool(int(lan.findtext('dns_manual'))),
                            "ip": lan.findtext('ip'),
                            "netmask": lan.findtext('netmask'),
                            "gateway": lan.findtext('gateway'),
                            "lan_speed": lan.findtext('lan_speed'),
                            "lan_enabled": bool(int(lan.findtext('lan_status'))),
                            "dns1": lan.findtext('dns1'),
                            "dns2": lan.findtext('dns2'),
                            "dns3": lan.findtext('dns3')
                        }
                return json_network_info
            else:
                raise RequestFailedError(response.status)

    async def device_info(self) -> dict:
        """
        Fetches device information from the device.

        Data such as **Serial Number**, **Name** and **Description** are returned.
        """
        url = f"{SCHEME}{self.host}{ENDPOINTS[self.version]['device_info']}"
        if self.version == 2:
            data = 'cmd=cgi_get_device_info'
            headers = {
                "Host": self.host,
                "X-CSRF-Token": self.wd_csrf_token,
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            }
        elif self.version == 5:
            data = 'cmd=cgi_get_device_info'
            headers = {
                "Host": self.host,
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            }
        else:
            raise ValueError("Unsupported/invalid version.")

        async with self.session.post(url, data=data, headers=headers) as response:
            if response.status == 200:
                content = await response.text()
                device_info = ElementTree.fromstring(content)

                json_device_info = {"serial_number": None, "name": None, "description": None}

                serial_number_node = device_info.find('.//serial_number')
                name_node = device_info.find('.//name')
                description_node = device_info.find('.//description')

                if serial_number_node is not None:
                    json_device_info["serial_number"] = serial_number_node.text
                if name_node is not None:
                    json_device_info["name"] = name_node.text
                if description_node is not None:
                    json_device_info["description"] = description_node.text

                return json_device_info
            else:
                raise RequestFailedError(response.status)

    async def system_version(self) -> dict:
        """Fetches system firmware version from the device."""
        url = f"{SCHEME}{self.host}{ENDPOINTS[self.version]['system_version']}"
        if self.version == 2:
            data = 'cmd=get_firm_v_xml'
            headers = {
                "Host": self.host,
                "X-CSRF-Token": self.wd_csrf_token,
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            }
        elif self.version == 5:
            data = 'cmd=get_firm_v_xml'
            headers = {
                "Host": self.host,
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            }
        else:
            raise ValueError("Unsupported/invalid version.")

        async with self.session.post(url, data=data, headers=headers) as response:
            if response.status == 200:
                content = await response.text()
                device_version = ElementTree.fromstring(content)
                json_device_version = {"firmware": None, "oled": None}

                firmware_node = device_version.find('.//fw')
                oled_node = device_version.find('.//oled')

                if firmware_node is not None:
                    json_device_version["firmware"] = firmware_node.text
                if oled_node is not None:
                    json_device_version["oled"] = oled_node.text.strip('\n')

                return json_device_version
            else:
                raise RequestFailedError(response.status)
                     
    async def latest_version(self) -> dict:
        """
        Fetches the latest firmware version from the device.

        Only devices with **V2** OS are supported.
        """
        if self.version != 2:
            raise ValueError("Unsupported/invalid version. Must be 2.")
        
        url = f"{SCHEME}{self.host}{ENDPOINTS[self.version]['device_info']}"
        data = 'cmd=get_auto_fw_version'
        headers = {
            "Host": self.host,
            "X-CSRF-Token": self.wd_csrf_token,
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        }

        async with self.session.post(url, data=data, headers=headers) as response:
            if response.status == 200:
                content = await response.text()
                latest_version = ElementTree.fromstring(content)
                json_latest_version = {"new": None, "details": {}}

                new_node = latest_version.find('.//new')
                version_node = latest_version.find('.//version')
                path_node = latest_version.find('.//path')
                releasenote_node = latest_version.find('.//releasenote')


                if new_node is not None:
                    json_latest_version["new"] = bool(int(new_node.text))
                if version_node is not None:
                    json_latest_version["details"]["version"] = version_node.text
                if path_node is not None:
                    json_latest_version["details"]["path"] = path_node.text
                if releasenote_node is not None:
                    json_latest_version["details"]["releasenote"] = releasenote_node.text
                
                return json_latest_version
            else:
                raise RequestFailedError(response.status)
    
    async def accounts(self) -> dict:
        """Fetches account information from the device."""
        url = f"{SCHEME}{self.host}{ENDPOINTS[self.version]['accounts']}"
        if self.version == 2:
            headers = {
                "Host": self.host,
                "X-CSRF-Token": self.wd_csrf_token,
            }
        elif self.version == 5:
            headers = {
                "Host": self.host,
            }
        else:
            raise ValueError("Unsupported/invalid version.")
        
        async with self.session.post(url, headers=headers) as response:
            if response.status == 200:
                content = await response.text()
                accounts = ElementTree.fromstring(content)
                json_accounts = {"users": [], "groups": {}}
                for user in accounts.iter('item'):
                    uid = user.findtext('uid')
                    if user.findtext('pwd') is not None:
                        password_bool = bool(int(user.findtext('pwd')))
                    else:
                        password_bool = False
                    last_name_list = []
                    for lastName in user.iter('last_name'):
                        last_name_list.append(lastName.text)
                    json_accounts['users'].append({
                        "uid": uid,
                        "name": user.findtext('name'),
                        "email": user.findtext('email'),
                        "pwd": password_bool,
                        "gid": user.findtext('gid'),
                        "first_name": user.findtext('first_name'),
                        "last_name": last_name_list,
                        "hint": user.findtext('hint'),
                    })
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
                raise RequestFailedError(response.status)
    
    async def alerts(self) -> tuple:
        """Retrieves the current system alerts and notifications from the device."""
        url = f"{SCHEME}{self.host}{ENDPOINTS[self.version]['alerts']}"
        data = 'cmd=cgi_get_alert'
        if self.version == 2:
            headers = {
                "Host": self.host,
                "X-CSRF-Token": self.wd_csrf_token,
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            }
        elif self.version == 5:
            headers = {
                "Host": self.host,
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            }
        else:
            raise ValueError("Unsupported/invalid version.")
        
        async with self.session.post(url, data=data, headers=headers) as response:
            if response.status == 200:
                content = await response.text()
                alerts_xml = ElementTree.fromstring(content)
                alerts_list = []
                for entry in alerts_xml.iter("alerts"):
                    alerts_list.append({
                        "code": entry.findtext("code"),
                        "seq_num": entry.findtext("seq_num"),
                        "level": entry.findtext("level"),
                        "msg": entry.findtext("msg"),
                        "desc": entry.findtext("desc"),
                        "time": entry.findtext("time")
                    })
        
                return len(alerts_list), alerts_list
            else:
                raise RequestFailedError(response.status)
    
    async def cloud_access(self) -> dict:
        """
        Fetches cloud access information from the device.

        Only devices with **V5** OS are supported.
        """
        if self.version != 5:
            raise ValueError("Unsupported/invalid version. Must be 5.")
        
        url = f"{SCHEME}{self.host}/web/restSDK/cloudAccess.php"

        data = 'cmd=getCloudAccess'
        headers = {
            "Host": self.host,
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        }

        async with self.session.post(url, data=data, headers=headers) as response:
            if response.status == 200:
                content = await response.text()
                json_content = json.loads(content)
                return json_content
            else:
                raise RequestFailedError(response.status)

    async def usb_info(self) -> dict:
        """
        Fetches connected USB devices from the device.

        Only devices with **V5** OS are supported.
        """
        if self.version != 5:
            raise ValueError("Unsupported/invalid version. Must be 5.")
        
        url = f"{SCHEME}{self.host}/web/get_usb_info.php"

        headers = {
            "Host": self.host
        }

        async with self.session.post(url, headers=headers) as response:
            if response.status == 200:
                content = await response.text()
                json_content = json.loads(content)
                return json_content
            else:
                raise RequestFailedError(response.status)
    
    async def uptime(self) -> int:
        """
        Returns the device uptime in seconds (parsed).

        Only devices with **V5** OS are supported.
        """
        if self.version != 5:
            raise ValueError("Unsupported/invalid version. Must be 5.")
    
        url = f"{SCHEME}{self.host}/cgi-bin/status_mgr.cgi"
    
        headers = {
            "Host": self.host,
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        }
    
        data = "cmd=cgi_get_uptime"
    
        async with self.session.post(url, data=data, headers=headers) as response:
            if response.status != 200:
                raise RequestFailedError(response.status)
    
            text = await response.text()
    
            match = re.search(r"<uptime>(.*?)</uptime>", text, re.S)
            if not match:
                raise RequestFailedError("Uptime not found in XML response.")
    
            uptime_raw = match.group(1).strip()
    
            match = re.search(
                r"(\d+)\s*days?\s*(\d+)\s*hour[s]?\s*(\d+)\s*minute[s]?",
                uptime_raw,
                re.I,
            )
    
            if not match:
                raise RequestFailedError(f"Unexpected uptime format: {uptime_raw}")
    
            d, h, m = map(int, match.groups())
            return int(timedelta(days=d, hours=h, minutes=m).total_seconds())
