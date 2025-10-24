# WDNAS-Client

## About
This module allows users to connect to their local WD NAS and view system info (Storage capacity, Disk temp, volumes etc..)
Its heavily a WIP and is my first public python module

My end goal with this is to link into Home Assistant so I can monitor my WD NAS

## Code

First create the client with the username, password, the host (Be that hostname or IP address)n and the system version number (2 or 5)

__Admin account is requred!__

Now call the functions to obtain wanted data - Thats it!

'''python
import asyncio
from wdnas_client import client

async def main():
    username = input("Username: ").lower()
    password = input("Password: ")
    host = '192.168.1.42'
    version = 2 # Can be 2 or 5
    
    async with client(username, password, host, version) as wdNAS:
        # V2 and V5 systems
        print("System Info:", await wdNAS.system_info())
        print("Share Names:", await wdNAS.share_names())
        print("System Status:", await wdNAS.system_status())
        print("Network Info:", await wdNAS.network_info())
        print("Device Info:", await wdNAS.device_info())
        print("System Version:", await wdNAS.system_version())
        print("Accounts:", await wdNAS.accounts())
        print("Alerts:", await wdNAS.alerts())

        # V2 systems only
        if version == 2:
            print("Latest Version:", await wdNAS.latest_version())

        # V5 systems only
        if version == 5:
            print("Cloud Access:", await wdNAS.cloud_access())
            print("USB Info:", await wdNAS.usb_info())

if __name__ == "__main__":
    asyncio.run(main())
'''
## Important Info

Currently supports V2 and V5 systems
