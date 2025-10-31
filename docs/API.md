# API Documentation

This document outlines the API endpoints for the WD NAS systems supported by this module.

## Version 2 Systems (V2)

| Function | HTTP Method | Endpoint | Parameters / Body | Notes |
| --- | --- | --- | --- | --- |
| Login | `POST` | `/cgi-bin/login_mgr.cgi` | `cmd=wd_login&username=user1&pwd=alisdh2309oas` | `application/x-www-form-urlencoded` body |
| System Info | `GET` | `/xml/sysinfo.xml` | *None* | |
| Share Names | `POST` | `/web/get_share_name_list.php` | *None* | |
| System Status | `POST` | `/cgi-bin/status_mgr.cgi` | `cmd=resource` | `application/x-www-form-urlencoded` body |
| Network Info | `GET` | `/cgi-bin/network_mgr.cgi` | `cmd=cgi_get_lan_xml` | Query Parameter |
| Device Info | `POST` | `/cgi-bin/system_mgr.cgi` | `cmd=cgi_get_device_info` | `application/x-www-form-urlencoded` body |
| System Version | `POST` | `/cgi-bin/system_mgr.cgi` | `cmd=get_firm_v_xml` | `application/x-www-form-urlencoded` body |
| Latest Version | `POST` | `/cgi-bin/system_mgr.cgi` | `get_auto_fw_version` | `application/x-www-form-urlencoded` body |
| Accounts | `POST` | `/xml/account.xml` | *None* | |
| Alerts | `POST` | `/cgi-bin/system_mgr.cgi` | `cmd=cgi_get_alert` | `application/x-www-form-urlencoded` body |

## Version 5 Systems (V5)

| Function | HTTP Method | Endpoint | Parameters / Body | Notes |
| --- | --- | --- | --- | --- |
| Login | `POST` | `/nas/v1/auth` | `{"username":"user1","password":"alisdh2309oas"}` | `application/json` body |
| System Info | `GET` | `/xml/sysinfo.xml` | *None* | |
| Share Names | `POST` | `/web/get_share_name_list.php` | *None* | |
| System Status | `POST` | `/cgi-bin/status_mgr.cgi` | `cmd=cgi_get_general` | `application/x-www-form-urlencoded` body |
| Network Info | `GET` | `/cgi-bin/network_mgr.cgi` | `cmd=cgi_get_lan_xml` | Query Parameter |
| Device Info | `POST` | `/cgi-bin/system_mgr.cgi` | `cmd=cgi_get_device_info` | `application/x-www-form-urlencoded` body |
| System Version | `POST` | `/cgi-bin/system_mgr.cgi` | `cmd=get_firm_v_xml` | `application/x-www-form-urlencoded` body |
| Accounts | `POST` | `/xml/account.xml` | *None* | |
| Alerts | `POST` | `/cgi-bin/system_mgr.cgi` | `cmd=cgi_get_alert` | `application/x-www-form-urlencoded` body |
| Cloud Access | `POST` | `/web/restSDK/cloudAccess.php` | `cmd=getCloudAccess` | `application/x-www-form-urlencoded` body |
| USE Info | `POST` | `/web/get_usb_info.php` | *None* | |