import requests
import rc4

RAW_DATA_STRING = 'cmd=wd_login&username={username}&pwd={enc_password}'
HOST = "wdmycloudmirror.local"
SCHEME =  "http://"

username = input('Username: ').lower()
# password = input('Password: ')
enc_password = input('RC4 Password: ')


# This needs reviewing for username / password use - Encrypted password is sent to WD not normal password 
# enc_password = rc4.encRC4(username, password)
# print(enc_password)
url = f"{SCHEME}{HOST}/cgi-bin/login_mgr.cgi"
contentLength = len(RAW_DATA_STRING)
headers = {"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8", "Host": "wdmycloudmirror.local", "Content-Length": str(contentLength)}

response = requests.post(url, data=RAW_DATA_STRING.format(username=username, enc_password=enc_password), headers=headers)
print(response)
cookies = response.cookies
print(cookies)


if response.status_code == 200:
    cookies = response.cookies
    PHPSESSID = cookies.get("PHPSESSID")
    PHPWD_CSRF_TOKENSESSID = cookies.get("WD-CSRF-TOKEN")
    print(PHPSESSID, PHPWD_CSRF_TOKENSESSID)
else:
    print("Request failed:", response.status_code)