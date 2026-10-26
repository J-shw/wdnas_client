# Supported Devices Documentation

<!-- 
&#10003; for supported
- for not sure
&#10005; for not supported
-->

This document outlines the supported WD NAS systems.

## Version 2 Systems (V2)

| Model | Firmware Version | Supported |
| --- | --- | --- |
| WD My Cloud Mirror | 2.13.108 | &#10003; |

## Version 5 Systems (V5)

| Model | Firmware Version | Supported | Validation |
| --- | --- | --- | --- |
| My Cloud Home | 5.31.108 | - | Existing project listing; not verified by this change |
| My Cloud EX2 Ultra | 5.31.108 | &#10003; | Existing project listing; not re-tested by this change |
| WD My Cloud PR2100 | 5.31.108 | - | Existing project listing; not verified by this change |
| WD My Cloud Mirror | 5.33.102 | &#10003; (uptime unavailable) | Tested on real hardware |

For the WD My Cloud Mirror, login, `system_version()`, `device_info()`,
`system_info()`, `system_status()`, `network_info()`, `share_names()`,
`accounts()`, `alerts()`, `diagnostics()`, `capacity_usage()`, `volume_status()`,
`system_warning()`, `internet_access()`, `process_info()`, and the extended
`system_status()` response were tested on the physical device. `usb_info()` was
tested without a connected USB device and
returned `{"success": false}`. The documented RAID failure/rebuild variants and
multi-volume parsing are covered by automated fixtures rather than live fault
injection. The device returned HTTP 500 with an empty body for `uptime()` and
HTTP 404 for the state-dependent `/xml/dm_read_state.xml` resource. Compatibility
of the new monitoring methods is asserted only for Mirror firmware 5.33.102;
other listed OS 5 models retain their existing support status.

The Mirror dashboard source for firmware 5.33.102 confirms the safety-check,
restart, and shutdown CGI commands implemented by `reboot()` and `shutdown()`.
Restart was successfully tested on the physical NAS. Shutdown is implemented
with the same safety flow but has not been executed on hardware.

## Version 4 Systems (V4 identifier)

V4 is this integration's identifier for original WD My Cloud devices in the OS
3 family; it is not a claim that WD released a product named My Cloud OS 4.

| Model | Model number | Firmware | Support status | Validation |
| --- | --- | --- | --- | --- |
| WD My Cloud | `sq` | `04.06.00-111` | &#10003; | Login, monitoring, storage, internet status, logout, and restart tested on real hardware; shutdown implemented but not live-tested |

The verified read endpoints include `/api/2.1/rest/system_information`,
`firmware_info`, `system_state`, `storage_usage`, and `internet_access`.
Storage values remain byte-accurate and qualitative health strings are not
presented as numeric measurements. No CPU, memory, detailed disk list, or
detailed volume list has been established, so the client does not fabricate
them.

The login endpoint is `/api/2.1/rest/local_login`; server cleanup uses
`GET /api/2.1/rest/logout`. Restart and shutdown use the source-confirmed
`PUT /api/2.1/rest/shutdown` request with `state=reboot` or `state=halt`.
HTTP does not encrypt the login query parameters. Restart is hardware-tested;
shutdown remains intentionally untested on hardware.
