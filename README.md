# WDNAS-Client

[![PyPI Version](https://img.shields.io/pypi/v/wdnas-client.svg)](https://pypi.org/project/wdnas-client/)

This module allows users to connect to their local WD NAS and view system info (storage capacity, disk temp, volumes, etc.). It is a work-in-progress and my first public Python module.

Initially built for my Home Assistant integration [ha-mycloud](https://github.com/J-shw/ha-mycloud). I thought I would make it into a python module for a bit of fun and to share the API systems for others to use.

## Features
* Fetches system info, share names, network status, and more.
* Asynchronous library using `asyncio` and `client`.
* Supports V2 and V5 WD NAS firmware and original WD My Cloud OS 3 devices
  through the V4 REST 2.1 XML API.
* Reports OS 5 RAID diagnostics, detailed volume state, resource monitoring,
  process diagnostics, warning state, and NAS-reported internet connectivity.
* Reuses authenticated V4 and supported OS 5 sessions for explicit restart and
  shutdown actions without automatic retries.

---

## Installation

```bash
pip install wdnas-client
```

---

## Usage

> **Note:** An **admin account** is required for the client to log in.

Here is a basic example of how to connect and pull data:

```python
import asyncio
import getpass
from wdnas_client import client
from wdnas_client.exceptions import UptimeUnavailableError

async def main():
    username = input("Username: ").lower()
    password = getpass.getpass("Password: ")
    host = '192.168.1.42'
    version = 2 # Can be 2, 4 or 5
    
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

        # V4 systems only
        if version == 4:
            print("System Information:", await wdNAS.system_information())
            print("Firmware Info:", await wdNAS.firmware_info())
            print("System State:", await wdNAS.system_state())
            print("Storage Usage:", await wdNAS.storage_usage())
            print("Internet Access:", await wdNAS.internet_access())

            # Explicit device actions; never retry an uncertain result.
            # await wdNAS.reboot()
            # await wdNAS.shutdown()

        # V2 systems only
        if version == 2:
            print("Latest Version:", await wdNAS.latest_version())

        # V5 systems only
        if version == 5:
            print("Diagnostics:", await wdNAS.diagnostics())
            print("Capacity Usage:", await wdNAS.capacity_usage())
            print("Volume Status:", await wdNAS.volume_status())
            print("System Warning:", await wdNAS.system_warning())
            print("Internet Access:", await wdNAS.internet_access())
            # Avoid printing sensitive commands, users, and PIDs by default.
            processes = await wdNAS.process_info()
            print("Process Count:", len(processes))
            print("USB Info:", await wdNAS.usb_info())

            # Explicit device actions. Each performs the dashboard safety check.
            # await wdNAS.reboot()
            # await wdNAS.shutdown()

            # Not every OS 5 model exposes uptime through the WD API.
            try:
                print("Uptime:", await wdNAS.uptime())
            except UptimeUnavailableError as error:
                print("Uptime unavailable:", error)

            print("Cloud Access:", await wdNAS.cloud_access())

if __name__ == "__main__":
    asyncio.run(main())
```

---

## Documentation

For more detailed information, please see the `docs` folder:

* **[Supported Models](./docs/SUPPORTED_MODELS.md)**
    * A list of all tested and compatible NAS models and firmware versions.

* **[API Reference](./docs/API.md)**
    * A detailed breakdown of the V2, V4, and V5 API endpoints.

## WD My Cloud Mirror (OS 5)

WD My Cloud Mirror firmware 5.33.102 has been tested on real hardware. Login,
system/device/status/network information, shares, accounts, alerts, diagnostics,
capacity usage, detailed volume state, warning state, NAS-reported internet
connectivity, and process diagnostics work. With no USB device connected, the
NAS returns
`{"success": false}`; this is returned as data and is not treated as a transport
error. The tested firmware returns HTTP 500 for the uptime endpoint, so callers
should catch `UptimeUnavailableError` (which remains a subclass of
`RequestFailedError`). See the API reference for response shapes and limits.
Restart was successfully exercised on the physical Mirror. Shutdown uses the
same WD JavaScript-derived safety flow but has not been executed on hardware.
Cleanup uses the WD JavaScript-confirmed `DELETE /nas/v1/auth` endpoint before
closing local HTTP resources. Releasing the administrator session when the
Home Assistant config entry is disabled was successfully tested on the Mirror
Gen 2 with firmware 5.33.102.
The client sends that request only after the current login issued a session
cookie or a protected OS 5 response was successfully parsed. A failed or
ambiguous login therefore closes local resources without risking another
administrator's browser session.

## Original WD My Cloud V4 (OS 3 family)

Model number `sq` with firmware `04.06.00-111` is hardware-tested for client
login, monitoring, storage usage, internet status, session reuse, logout, and
restart. Shutdown uses the same source-confirmed endpoint with `state=halt`, but
has not been executed on hardware. V4 login uses unencrypted HTTP query
parameters, so it must be limited to a trusted local network.
