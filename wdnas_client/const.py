V2_RAW_LOGIN_STRING = 'cmd=wd_login&username={username}&pwd={enc_password}'

SCHEME = "http://"

ENDPOINTS = {
    2: {
        "login": "/cgi-bin/login_mgr.cgi",
        "system_info": "/xml/sysinfo.xml",
        "share_names": "/web/get_share_name_list.php",
        "system_status": "/cgi-bin/status_mgr.cgi",
        "network_info": "/cgi-bin/network_mgr.cgi?cmd=cgi_get_lan_xml",
        "device_info": "/cgi-bin/system_mgr.cgi",
        "system_version": "/cgi-bin/system_mgr.cgi",
        "latest_version": "/cgi-bin/system_mgr.cgi",
        "accounts": "/xml/account.xml",
        "alerts": "/cgi-bin/system_mgr.cgi"
    },
    5: {
        "login": "/nas/v1/auth",
        "system_info": "/xml/sysinfo.xml",
        "share_names": "/web/get_share_name_list.php",
        "system_status": "/cgi-bin/status_mgr.cgi",
        "network_info": "/cgi-bin/network_mgr.cgi?cmd=cgi_get_lan_xml",
        "device_info": "/cgi-bin/system_mgr.cgi",
        "system_version": "/cgi-bin/system_mgr.cgi",
        "latest_version": "/cgi-bin/system_mgr.cgi",
        "accounts": "/xml/account.xml",
        "alerts": "/cgi-bin/system_mgr.cgi"
    }
}