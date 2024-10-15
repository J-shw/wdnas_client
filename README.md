# WDNAS-Client

## About
This module allows users to connect to their local WD NAS and view system info (Storage capacity, Disk temp, volumes etc..)
Its heavily a WIP and is my first public python module

My end goal with this is to link into Home Assistant so I can monitor my WD NAS

## Code

First create the client with the username, password and the host (Be that hostname or IP address)

__Admin account is requred!__

Now call the functions to obtain wanted data - Thats it!

```
from wdnas_client import client

username = input("Username: ").lower()
password = input("Password: ")

wdNAS = client(username, password, 'wdmycloudmirror.local')

print(wdNAS.system_info())

print(wdNAS.share_names())

print(wdNAS.system_status())

print(wdNAS.system_version())

print(wdNAS.latest_version())

print(wdNAS.accounts())

print(wdNAS.alerts)
```

## Important Info

I have only tested this on my WD NAS which is a wdmycloud mirror running version 2.13.108

Its an old one and so I cannot say if this system works for any newer WD NAS drives
