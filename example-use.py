import asyncio
import getpass

from wdnas_client import client
from wdnas_client.exceptions import UptimeUnavailableError


async def main():
    username = input("Username: ").lower()
    password = getpass.getpass("Password: ")
    host = input("NAS IP address: ").strip()
    version = int(input("API version (2, 4 or 5): ").strip())

    async with client(username, password, host, version) as wdNAS:
        # V2, V4 and V5 systems
        print("System Info:", await wdNAS.system_info())
        print("System Status:", await wdNAS.system_status())
        print("Device Info:", await wdNAS.device_info())
        print("System Version:", await wdNAS.system_version())

        # V2 and V5 systems
        if version in (2, 5):
            print("Share Names:", await wdNAS.share_names())
            print("Network Info:", await wdNAS.network_info())
            print("Accounts:", await wdNAS.accounts())
            print("Alerts:", await wdNAS.alerts())

        if version == 4:
            print("System Information:", await wdNAS.system_information())
            print("Firmware Info:", await wdNAS.firmware_info())
            print("System State:", await wdNAS.system_state())

        # V2 systems only
        if version == 2:
            print("Latest Version:", await wdNAS.latest_version())

        # V5 systems only
        if version == 5:
            print("Diagnostics:", await wdNAS.diagnostics())
            print("Capacity Usage:", await wdNAS.capacity_usage())
            print("Volume Status:", await wdNAS.volume_status())
            print("System Warning:", await wdNAS.system_warning())
            print("Internet Access (reported by NAS):", await wdNAS.internet_access())
            # Avoid printing sensitive commands, users, and PIDs by default.
            processes = await wdNAS.process_info()
            print("Process Count:", len(processes))
            print("USB Info:", await wdNAS.usb_info())
            try:
                print("Uptime:", await wdNAS.uptime())
            except UptimeUnavailableError as error:
                print("Uptime unavailable:", error)

            print("Cloud Access:", await wdNAS.cloud_access())


if __name__ == "__main__":
    asyncio.run(main())
