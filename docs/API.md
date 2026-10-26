# API Documentation

This document outlines the API endpoints for the WD NAS systems supported by this module.

## Version 2 Systems (V2)

| Function | HTTP Method | Endpoint | Parameters / Body | Notes |
| --- | --- | --- | --- | --- |
| Login | `POST` | `/cgi-bin/login_mgr.cgi` | `cmd=wd_login&username=user1&pwd=alisdh2309oas` | `application/x-www-form-urlencoded` body |
| System Info | `GET` | `/xml/sysinfo.xml` | *None* | |
| Share Names | `POST` | `/web/get_share_name_list.php` | *None* | |
| System Status | `POST` | `/cgi-bin/status_mgr.cgi` | `cmd=resource` | `application/x-www-form-urlencoded` body |
| Network Info | `GET` | `/cgi-bin/network_mgr.cgi` | `cmd=cgi_get_lan_xml` | Query Parameter |
| Device Info | `POST` | `/cgi-bin/system_mgr.cgi` | `cmd=cgi_get_device_info` | `application/x-www-form-urlencoded` body |
| System Version | `POST` | `/cgi-bin/system_mgr.cgi` | `cmd=get_firm_v_xml` | `application/x-www-form-urlencoded` body |
| Latest Version | `POST` | `/cgi-bin/system_mgr.cgi` | `get_auto_fw_version` | `application/x-www-form-urlencoded` body |
| Accounts | `POST` | `/xml/account.xml` | *None* | |
| Alerts | `POST` | `/cgi-bin/system_mgr.cgi` | `cmd=cgi_get_alert` | `application/x-www-form-urlencoded` body |

## Version 4 Systems (V4 integration identifier)

These original WD My Cloud devices belong to the OS 3 family. V4 identifies
their REST 2.1 XML API inside this project.

| Function | HTTP Method | Endpoint | Parameters | Notes |
| --- | --- | --- | --- | --- |
| Login | `GET` | `/api/2.1/rest/local_login` | `username`, `password` query parameters | Hardware-tested on model `sq`, firmware `04.06.00-111` |
| System Information | `GET` | `/api/2.1/rest/system_information` | *None* | Identity and capacity label |
| Firmware Info | `GET` | `/api/2.1/rest/firmware_info` | *None* | Current package name, version, and description |
| System State | `GET` | `/api/2.1/rest/system_state` | *None* | Qualitative readiness and health strings |
| Storage Usage | `GET` | `/api/2.1/rest/storage_usage` | *None* | Total, used, free, percentage, and optional media byte counters |
| Internet Access | `GET` | `/api/2.1/rest/internet_access` | *None* | Boolean `connectivity` value |
| Restart / Shutdown | `PUT` | `/api/2.1/rest/shutdown` | `state=reboot` or `state=halt` | Restart hardware-tested; shutdown not live-tested |
| Logout | `GET` | `/api/2.1/rest/logout` | *None* | Exactly one server cleanup attempt |

`system_information()`, `firmware_info()`, and `system_state()` expose the
verified XML resources directly. The established `system_info()`,
`device_info()`, `system_version()`, and `system_status()` methods adapt those
responses for existing consumers. A capacity label such as `2TB` is converted
to decimal bytes; exact `storage_usage` counters take precedence when
available. CPU, memory, numeric temperature, disk topology, and volume topology
remain unavailable.

V4 login maintains cookies in the existing `aiohttp.ClientSession`. HTTP 401
and 403 responses become `InvalidLoginError`, including expired-session reads.
The client sanitizes login transport exceptions because the firmware sends the
credentials in URL query parameters. Plain HTTP provides no confidentiality;
use only on a trusted local network and avoid HTTP request logging.

V4 cleanup calls the source-confirmed logout endpoint once and closes local
resources even when logout fails. Restart and shutdown reuse the authenticated
session and issue exactly one `PUT` request without retry or method fallback.

## Version 5 Systems (V5)

| Function | HTTP Method | Endpoint | Parameters / Body | Notes |
| --- | --- | --- | --- | --- |
| Login | `POST` | `/nas/v1/auth` | `{"username":"user1","password":"alisdh2309oas"}` | `application/json` body |
| Logout | `DELETE` | `/nas/v1/auth` | *None* | Reuses the existing authenticated session; never retried |
| System Info | `GET` | `/xml/sysinfo.xml` | *None* | |
| Share Names | `POST` | `/web/get_share_name_list.php` | *None* | |
| System Status | `POST` | `/cgi-bin/status_mgr.cgi` | `cmd=resource` | `application/x-www-form-urlencoded` body |
| Network Info | `GET` | `/cgi-bin/network_mgr.cgi` | `cmd=cgi_get_lan_xml` | Query Parameter |
| Device Info | `POST` | `/cgi-bin/system_mgr.cgi` | `cmd=cgi_get_device_info` | `application/x-www-form-urlencoded` body |
| System Version | `POST` | `/cgi-bin/system_mgr.cgi` | `cmd=get_firm_v_xml` | `application/x-www-form-urlencoded` body |
| Accounts | `POST` | `/xml/account.xml` | *None* | |
| Alerts | `POST` | `/cgi-bin/system_mgr.cgi` | `cmd=cgi_get_alert` | `application/x-www-form-urlencoded` body |
| Cloud Access | `POST` | `/web/restSDK/cloudAccess.php` | `cmd=getCloudAccess` | `application/x-www-form-urlencoded` body |
| USB Info | `GET` | `/web/get_usb_info.php` | *None* | `success: false` can mean that no USB device is attached |
| Diagnostics | `POST` | `/cgi-bin/home_mgr.cgi` | `cmd=2` | Disk, fan, board, and RAID data |
| Capacity Usage | `POST` | `/cgi-bin/hd_config.cgi` | `cmd=cgi_Status_CapacityUsage` | Raw capacity/media counters and percentage |
| Volume Status | `GET` | `/xml/used_volume_info.xml` | *None* | Detailed volume, filesystem, mount, encryption, and RAID values |
| System Warning | `POST` | `/cgi-bin/home_mgr.cgi` | `cmd=8` | Temperature/busy warning code |
| Internet Access | `GET` | `/cgi-bin/network_mgr.cgi?cmd=cgi_get_internet_access` | *None* | Connectivity assessment made by the NAS |
| Process Info | `POST` | `/cgi-bin/status_mgr.cgi` | `cmd=cgi_process` | Diagnostic process list |
| Uptime | `POST` | `/cgi-bin/status_mgr.cgi` | `cmd=cgi_get_uptime` | Not available on all OS 5 models |
| Power safety check | `POST` | `/cgi-bin/hd_config.cgi` | `cmd=cgi_Detect_Dangerous` | Required before restart/shutdown; non-zero blocks the action |
| Restart | `POST` | `/cgi-bin/system_mgr.cgi` | `cmd=cgi_restart` | Authenticated OS 5 action; may disconnect HTTP immediately |
| Shutdown | `POST` | `/cgi-bin/system_mgr.cgi` | `cmd=cgi_shutdown` | Authenticated OS 5 action; may disconnect HTTP immediately |

## Method responses and compatibility

### `await nas.logout()` / `await nas.close()`

For V4, `logout()` sends the source-confirmed `GET /api/2.1/rest/logout`
request using the existing session. `close()` makes at most one logout attempt
and always closes the local `aiohttp.ClientSession`; a logout HTTP, timeout, or
transport failure remains visible to the caller.

For OS 5, `logout()` sends the WD JavaScript-confirmed
`DELETE /nas/v1/auth` request through the existing HTTP session. It does not
require the legacy `phpsessid` attribute and never creates a session or logs in.
Concurrent or repeated cleanup sends at most one request. `close()` always
closes local resources and still reports HTTP, timeout, or connection failures.
For safety, an open HTTP session alone is not treated as ownership. The DELETE
is permitted only after the login response issued a `PHPSESSID` or a protected
OS 5 system/device response was successfully parsed. Ambiguous login cleanup is
local-only. Server-side invalidation on config-entry disable was successfully
tested on a My Cloud Mirror Gen 2 running firmware 5.33.102.

No equivalent OS 2 server endpoint has been established from the available WD
sources. OS 2 `close()` therefore closes only the local HTTP session, while an
explicit OS 2 `logout()` raises `ValueError` rather than claiming that the NAS
session was released.

### `await nas.reboot()` / `await nas.shutdown()`

For OS 5, both methods first call the dashboard's read-only
`cgi_Detect_Dangerous` check. A non-zero result raises
`PowerActionBlockedError` and the action request is not sent. Only a specific
`aiohttp.ServerDisconnectedError` after the action request is treated as the
expected device transition; timeouts, HTTP failures, malformed safety replies,
and other exceptions remain errors. These methods use the existing authenticated
session and do not use SSH.

For V4, the methods send one authenticated `PUT /api/2.1/rest/shutdown` with
`state=reboot` or `state=halt`. They do not retry an ambiguous result.

### `await nas.diagnostics()`

OS 5 only. The method returns a dictionary with this shape:

```python
{
    "board_temperature": 0,
    "fan_rpm": 0,
    "disk_statuses": ["healthy", "healthy"],
    "disk_status_extra": {},
    "raid": {
        "volume_count": 1,
        "result": 1,
        "disk_count": 2,
        "volumes": [
            {
                "id": "1",
                "number": 1,
                "volume": "Volume_1",
                "mode": "raid1",
                "state": "clean",
                "extra": {},
            }
        ],
        "extra": {},
    },
    "extra": {},
}
```

`board_temperature` is a WD diagnostic code, not a Celsius temperature.
`fan_rpm` is the RPM value reported by the firmware; zero is not interpreted as
healthy or unhealthy. RAID states are returned verbatim. Known values include
`clean`, `degraded`, `damaged`, `resync`, `resync5` (parity verification),
`recovery`, `migrate`, `reshape`, and `expansion`. Missing known elements become
`None` (or an empty list), while
additional XML values are retained in the nearest `extra` mapping.

The WD My Cloud Mirror response shown above was verified on real firmware
5.33.102. Failure/rebuild states, missing fields, unknown fields, and multiple
RAID volumes are verified with automated response fixtures.

### `await nas.capacity_usage()`

OS 5 only. Returns a list so that devices with multiple volumes are represented
without loss:

```python
[
    {
        "volume": 1,
        "total_size": 1918590988,
        "used_size": 1918589500,
        "free_size": 1488,
        "used_rate": 100,
        "shared_pictures": 0,
        "shared_music": 0,
        "shared_videos": 0,
        "extra": {},
    }
]
```

The WD web-interface code treats `use_size` and `free_size` as KiB block counts.
`total_size` is inferred to use the same unit from its live magnitude and field
relationship. `Shared_Pictures`, `Shared_Music`, and `Shared_Videos` appear to
already be byte values because the WD code does not multiply them by 1024 before
combining them with capacity values. These unit conclusions are derived from WD
code and are not a published protocol contract. The client returns every raw
integer unchanged; it does not convert or reconcile values with `system_info()`,
whose endpoint may report different storage figures. `used_rate` is an integer
percentage. Missing values become `None`, and additional item fields are kept in
`extra`. One-volume behavior was verified on real Mirror firmware 5.33.102;
multi-volume parsing is fixture-tested.

### `await nas.volume_status()`

OS 5 only. Performs the read-only `GET /xml/used_volume_info.xml` request and
returns one dictionary per volume. Known fields include `volume`, `raid_mode`,
`raid_status`, `file_type`, `size`, `used_size`, `free_size`, `percentage`,
`device`, `dev_num`, `mount`, `mount_status`, `volume_encrypt`,
`is_roaming_volume`, `scsi_mapping`, `spare`, `to_be_sync`, and `web_cmd`.
Numerical text is converted to integers where appropriate; missing fields become
`None`, and unknown fields are retained in `extra`. RAID status codes are raw
values and are not interpreted. The live values for `size`, `used_size`, and
`free_size` are consistent with KiB block counts, but this remains an
implementation-derived interpretation rather than a published contract.

```python
[
    {
        "volume": 1,
        "raid_mode": "raid1",
        "raid_status": 0,
        "file_type": "ext4",
        "size": 1918590988,
        "used_size": 1918484104,
        "free_size": 106884,
        "percentage": 0,
        "device": "sdasdb",
        "dev_num": 2,
        "mount": "...",
        "mount_status": "...",
        "volume_encrypt": 0,
        "is_roaming_volume": 0,
        "scsi_mapping": 3,
        "spare": None,
        "to_be_sync": None,
        "web_cmd": 9,
        "sdx3_flag": 0,
        "used_device": "...",
        "raid_uuid": "...",
        "scsi0_serial": "...",
        "scsi1_serial": "...",
        "extra": {},
    }
]
```

On the tested, almost-full Mirror volume, `percentage` was still `0`. It is
therefore an uninterpreted firmware value and must not be presented as storage
utilization without further evidence. Use neither this field nor an inferred
formula as a substitute for the separately reported capacity values.

`volume_status().free_size` and `capacity_usage().free_size` differed in the
same live test. They come from separate WD endpoints
(`/xml/used_volume_info.xml` and `/cgi-bin/hd_config.cgi` respectively), and the
client deliberately preserves both raw values without reconciling them.

The response can also expose `mount`, device identifiers, `raid_uuid`, and SCSI
serial numbers. They remain available for diagnostics but should be redacted
from logs and issue reports. The client does not log them. This method performs
no RAID or configuration operation.

### `await nas.system_warning()`

OS 5 only. Returns `{"code": 0, "status": "normal"}` for warning code 0.
Known statuses are `normal`, `over_temperature`, and `system_busy_hotplug` for
codes 0, 1, and 2. Any other value is returned unchanged in `code` with status
`unknown`; it is never treated as normal.

### `await nas.internet_access()`

OS 5 only. Returns `True` or `False` from the NAS-reported `connectivity` value.
It does not contact any external service or perform its own DNS/HTTP test.
Missing or unexpected values raise `ValueError` instead of being collapsed to
`False`; HTTP failures raise `RequestFailedError`.

### `await nas.process_info()`

OS 5 only. Returns a list containing `command`, `user`, `pid`, `cpu`, `mem`, and
`extra`. Integer/decimal values are typed where possible; malformed values are
preserved to avoid data loss. WD JavaScript sorts and displays `cpu` directly
but does not establish a protocol-level unit, and no reliable unit for `mem` was
found, so both remain raw measurements. Commands, usernames, and PIDs are
potentially sensitive and the library does not log the list. The method is for
diagnostics and does not control processes.

```python
[
    {
        "command": "...",
        "user": "...",
        "pid": 1234,
        "cpu": 2.1,
        "mem": 1580,
        "extra": {},
    }
]
```

### `await nas.system_status()` additions

The original `cpu` and `memory.total`, `memory.unused`, and `memory.simple`
keys and types remain unchanged. When supplied by the firmware, the result also
contains `memory.buffers`, `memory.cached`, `bonding`, `now_time`,
`process_count`, and raw interface values under `network.lan` and
`network.lan2`. The memory counters are treated as raw KiB values based on the
WD UI calculations. `now_time` is a Unix sample timestamp, not uptime.

The WD UI divides each LAN value by 1024 twice and displays MB/s without taking
a counter difference. Because the underlying API semantics are not formally
documented, the client exposes them as `received_raw`/`transmitted_raw`, does not
add duplicate-looking interfaces, and does not promise bytes per second.
Unknown top-level resource fields are retained in `extra`. `process_count` is
derived only when actual `process_main` records are present.

```python
{
    "memory": {
        "total": 509780,
        "unused": 20500,
        "simple": "512MB",
        "buffers": 31360,
        "cached": 220544,
    },
    "cpu": 4,
    "bonding": 0,
    "now_time": 1792870243,
    "process_count": 51,
    "network": {
        "lan": {"received_raw": 13191338173, "transmitted_raw": 11278793837},
        "lan2": {"received_raw": 13191338173, "transmitted_raw": 11278793837},
    },
    "extra": {},
}
```

### Disk Manager progress limitation

`GET /xml/dm_read_state.xml` returned HTTP 404 on the tested Mirror firmware
5.33.102. It may be firmware- or operation-state-dependent, so no public method
or polling behavior is provided and no RAID operation is initiated to expose it.

### `await nas.usb_info()`

OS 5 only. This uses the same `GET` request as the original WD web interface.
The JSON response is returned unchanged. In particular, `{"success": false}`
without an attached USB device is not converted into a communication error.

### `await nas.uptime()`

OS 5 only. Existing successful uptime parsing remains available. If the endpoint
returns the observed empty HTTP 500 response or no supported `<uptime>` value,
the method raises `UptimeUnavailableError`. This exception subclasses
`RequestFailedError` for backward-compatible exception handling. Other HTTP
errors remain `RequestFailedError`, while transport errors continue to propagate
from `aiohttp`. It never derives uptime from `resource`'s `now_time` value. WD My
Cloud Mirror firmware 5.33.102 returns an empty HTTP 500 response for both
`cgi_get_uptime` and `cgi_get_general`; uptime therefore remains unavailable on
that tested device. The client has no cached model/firmware identity at this
point, so it deliberately does not attempt speculative model detection.
