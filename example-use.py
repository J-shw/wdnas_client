import asyncio
from wdnas_client import client

async def main():
    username = input("Username: ").lower()
    password = input("Password: ")
    host = '192.168.86.41'
    version = 2 # Can be 2 or 5
    
    async with client(username, password, host, version) as wdNAS:
        # V2 and V5 systems
        print("System Info:", await wdNAS.system_info())
        print("Share Names:", await wdNAS.share_names())
        print("System Status:", await wdNAS.system_status())
        print("Network Info:", await wdNAS.network_info())
        print("Device Info:", await wdNAS.device_info())
        print("System Version:", await wdNAS.system_version())
        print("Latest Version:", await wdNAS.latest_version())
        print("Accounts:", await wdNAS.accounts())
        print("Alerts:", await wdNAS.alerts())

        # V5 systems only
        if version == 5:
            print("Cloud Access:", await wdNAS.cloud_access())
            print("USB Info:", await wdNAS.usb_info())

if __name__ == "__main__":
    asyncio.run(main())