# WD-NAS-Client

## About
This module allows users to connect to their local WD NAS and view system info (Storage capacity, Disk temp, volumes etc..)
Its heavily a WIP and is my first public python module

My end goal with this is to link into Home Assistant so I can monitor my WD NAS


## Setup
At this time there is a small bit of configuration required to start.

It seems that the website for the NAS sends passwords encoded using RC4 (Which I dont fully understand..)

I have got a basic RC4 module however it does not work yet and spits out wrongly encoded passwords.

So as a work around, we will be using the RC4 encoded password instead of the actual user password.

How to obtain encoded (RC4) password:
- Open web browser
- Go to NAS site (Something like: wdmycloud.local or 192.168.1.XX)
- Inspect element
  - This is done by right clicking and pressing 'Inspect' (Chrome, Firefox or Edge are recommended)
- Go to network tab
![image](https://github.com/user-attachments/assets/404196e0-e09d-48f5-84ef-e49552d3d0ec)

- Login with the network tab open
  - Lots of request will now appear in the network tab
- Scroll to the top and find a POST request for 'http://wdmycloudmirror.local/cgi-bin/login_mgr.cgi'
  - replace 'wdmycloudmirror.local' with the connection you are using!
- ![image](https://github.com/user-attachments/assets/a766a4e0-a5a9-4c53-8a20-4744bc3e977a)
- Find the 'Request' tab and copy the 'pwd' value (This is the encoded password)
 ![image](https://github.com/user-attachments/assets/5530a1dd-ced3-4dd8-8894-9260fc9dce11)


Thats it!

## Code

At this time I only have a session and system_info
First create the client with the username, encoded password and the host (Be that host name or IP address)

Then call system_info to grab the system info! - This returns the data in JSON format (The NAS API returns it in XML)
```
from wdnas_client import client

username = input("Username: ").lower()
enc_password = input("RC4 Password: ")

wdNAS = client(username, enc_password, 'wdmycloudmirror.local')

print(wdNAS.system_info())
```

## Important Info

I have only tested this on my WD NAS which is a wdmycloud mirror running version 2.13.108

Its an old one and so I cannot say if this system works for any newer WD NAS drives
