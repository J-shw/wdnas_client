import requests
# import rc4

RAW_LOGIN_STRING = 'cmd=wd_login&username={username}&pwd={enc_password}'
HOST = "wdmycloudmirror.local"
SCHEME = "http://"

class WDAPI:
    def __init__(self, username, enc_password):
        self.username = username
        self.enc_password = enc_password
        self.session = requests.Session()
        self.login()

    def login(self):
        url = f"{SCHEME}{HOST}/cgi-bin/login_mgr.cgi"
        content_length = 1
        headers = {
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Host": HOST,
            "Content-Length": str(content_length),
        }
        data = RAW_LOGIN_STRING.format(username=self.username, enc_password=self.enc_password)
        response = self.session.post(url, data=data, headers=headers)

        if response.status_code == 200:
            if "PHPSESSID" in response.cookies and "WD-CSRF-TOKEN" in response.cookies:
                print("Login successful!")
            else:
                print("Invalid Username/Password or missing cookies")
        else:
            print(f"Request failed: {response.status_code}")

if __name__ == "__main__":
    username = input("Username: ").lower()
    enc_password = input("RC4 Password: ")

    mycloud_api = WDAPI(username, enc_password)