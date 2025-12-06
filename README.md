# WDNAS-Client

[![PyPI Version](https://img.shields.io/pypi/v/wdnas-client.svg)](https://pypi.org/project/wdnas-client/)

This module allows users to connect to their local WD NAS and view system info (storage capacity, disk temp, volumes, etc.). It is a work-in-progress and my first public Python module.

Initially built for my Home Assistant integration [ha-mycloud](https://github.com/J-shw/ha-mycloud). I thought I would make it into a python module for a bit of fun and to share the API systems for others to use.

## Features
* Fetches system info, share names, network status, and more.
* Asynchronous library using `asyncio` and `client`.
* Supports V2 and V5 WD NAS firmware.

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
            print("Uptime:", await wdNAS.uptime())

if __name__ == "__main__":
    asyncio.run(main())
```

---

## Documentation

For more detailed information, please see the `docs` folder:

* **[Supported Models](./docs/SUPPORTED_MODELS.md)**
    * A list of all tested and compatible NAS models and firmware versions.

* **[API Reference](./docs/API.md)**
    * A detailed breakdown of the V2 and V5 API endpoints this integration uses.