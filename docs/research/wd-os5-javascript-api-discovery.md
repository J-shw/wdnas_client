# WD My Cloud OS 5 JavaScript API discovery

Date: 2026-10-24
Target represented by the captured assets: WD My Cloud Mirror Gen 2 / OS 5.33.102

## Scope and evidence levels

This report is a static analysis of the captured `WD-Mirror/resources` JavaScript
files. No request was sent to the NAS.
The terms used below have deliberately narrow meanings:

- **JS-proven**: endpoint, method, parameters, and consumed fields occur in the
  captured JavaScript.
- **Hardware-confirmed**: supplied live-test results confirm the behavior on the
  WD My Cloud Mirror running 5.33.102.
- **Candidate**: the JavaScript proves a call exists, but its behavior on this
  firmware has not been observed.
- **Inference**: a conclusion drawn from usage in the UI. It is marked as such
  and must not be treated as a verified response contract.

The captured `define.js` identifies the UI build as My Cloud Mirror Gen 2
(`DEV_NAME`, `DEV_ID`, `PROJECT_NAME`) and enables RAID, disk-status, network
UPS, and system-test features (`resources/define.js:7`,
`resources/define.js:59-83`).

## Corpus summary

- 32 JavaScript files, 512,739 bytes in total.
- 20 application files contain requests, one additional file is the AJAX pool
  wrapper, and 11 are UI or helper files with no local API request.
- 50 unique endpoint-like local paths (`.cgi`, `.php`, `.xml`, and `/nas/v1/*`)
  were found lexically. This count includes configuration XML resources and a
  few web workflow pages, not only monitoring APIs.
- 112 direct literal `cmd` values were found, plus two commands selected by a
  ternary expression (`cgi_usb_Storage_umount`, `cgi_usb_mtp_umount`). There are
  also `cgi_name=get_ip_address`, `cgi_name=fw_analytics`, and an unresolved
  dynamic `cgi_name` used for analytics.
- No `fetch()`, `XMLHttpRequest`, `$.get()`, or `$.post()` call occurs. Requests
  use `$.ajax()` directly or `wd_ajax()`. The latter only delegates to
  `$.ajax(options)` and tracks requests for cancellation; it does not alter the
  endpoint, method, body, authentication, or response (`resources/wd_ajax.js:14-17`).

Files with requests are `cloud.js`, `device_active.js`, `diag.js`, `eula.js`,
`function.js`, `fw.js`, `home_usb.js`, `home.js`, `homeDiag.js`, `init.js`,
`language.js`, `notification.js`, `ota.js`, `quota.js`, `raid_diag.js`,
`reg_device.js`, `sms.js`, `system.js`, `users.js`, and `web_idle_timeout.js`
(counting `wd_ajax.js` itself only as the wrapper). The remaining files were
also inspected and contain no NAS API call.

### Complete lexical endpoint inventory

The 50 paths counted above are listed here so that low-priority and unsafe
surfaces are not mistaken for omissions:

- CGI: `/cgi-bin/account_mgr.cgi`, `/cgi-bin/app_mgr.cgi`,
  `/cgi-bin/folder_tree.cgi`, `/cgi-bin/hd_config.cgi`,
  `/cgi-bin/home_mgr.cgi`, `/cgi-bin/network_mgr.cgi`,
  `/cgi-bin/remote_backup.cgi`, `/cgi-bin/share.cgi`,
  `/cgi-bin/status_mgr.cgi`, `/cgi-bin/system_mgr.cgi`,
  `/cgi-bin/usb_device.cgi`.
- NAS REST: `/nas/v1/api/eula`, `/nas/v1/auth`, `/nas/v1/locale`.
- Web/PHP: `/web/auth0/change_password.php`, `/web/auth0/login.php`,
  `/web/cgi_api.php`, `/web/get_share_name_list.php`,
  `/web/get_usb_info.php`, `/web/get_XML_value.php`, `/web/home.php`,
  `/web/ota/ota.php`, `/web/php/getADInfo.php`, `/web/php/modUserName.php`,
  `/web/php/noHDD.php`, `/web/php/reg_device.php`, `/web/php/users.php`,
  `/web/restAPI/device_registration.php`, `/web/restSDK/cloudAccess.php`,
  `/web/storage/raid_cgi.php`.
- XML resources: `/xml/account.xml`, `/xml/apkg_all.xml`,
  `/xml/cgi_fmt_gui_log.xml`, `/xml/check_disk_size_status.xml`,
  `/xml/create_sys_log.xml`, `/xml/current_hd_info.xml`,
  `/xml/dm_read_progress.xml`, `/xml/dm_read_state.xml`,
  `/xml/dm_volume_info.xml`, `/xml/english.xml`,
  `/xml/hd_right_position.xml`, `/xml/hidden_encryption.xml`, `/xml/ip.xml`,
  `/xml/lang.xml`, `/xml/smb.xml`, `/xml/sms_conf.xml`, `/xml/sysinfo.xml`,
  `/xml/unused_volume_info.xml`, `/xml/usb_info.xml`,
  `/xml/used_volume_info.xml`.

`/web/home.php` and `/web/auth0/login.php` are UI/workflow pages rather than
monitoring APIs. `/xml/usb_info.xml` appears only as a commented legacy URL
(`home_usb.js:68`); the active USB endpoint is the JSON PHP endpoint. Language,
SMS, EULA, registration, Auth0, and account-administration resources are in the
inventory but intentionally not recommended for Home Assistant monitoring.

## Known hardware facts

The following facts come from the supplied live tests and are not inferred from
the JavaScript:

- OS 5 login works.
- `diagnostics()` returns two healthy disks and a clean RAID 1.
- `capacity_usage()` works.
- `POST /cgi-bin/status_mgr.cgi`, `cmd=resource`, works.
- `cgi_get_uptime` and `cgi_get_general` return HTTP 500 with an empty body.
- USB GET without an attached device returns `{"success": false}`.

The rejected uptime commands are not recommended again below.

## Monitoring API catalog

### System load and processes

| Source | Request | Consumed response | Safety | Client support / value |
| --- | --- | --- | --- | --- |
| `device_active.js:338-377` | `POST /cgi-bin/status_mgr.cgi`, `cmd=resource` | XML: `bonding`, `mem_total`, `mem2_total`, `mem_free`, `buffers`, `cached`, `cpu`, `lan_r_speed`, `lan_t_speed`, `lan2_r_speed`, `lan2_t_speed`, `now_time`, count of `process_main` | **READ** | `system_status()` uses only CPU, total/free/simple memory. Buffer/cache, bonding, network rates, and process count are unused and valuable. Hardware-confirmed endpoint. |
| `device_active.js:209-225` | `POST /cgi-bin/status_mgr.cgi`, `cmd=cgi_process` | XML `process_main`: `command`, `user`, `pid`, `cpu`, `mem` | **READ** | New. Useful for diagnostics, but high-cardinality process sensors are a poor default for Home Assistant and may expose usernames/commands. |
| `device_active.js:1047-1058` | `POST /cgi-bin/status_mgr.cgi`, `cmd=cgi_clear_resource` | XML not consumed | **UNKNOWN/WRITE** | Called only after repeated `resource` errors. It may reset server-side sampling state. Do not probe or implement as monitoring. |

`now_time` is used only to calculate the interval between samples
(`device_active.js:472-481`). It is not interpreted as time since boot and is no
evidence for uptime.

### Diagnostics, temperatures, fan, S.M.A.R.T., and RAID summary

| Source | Request | Consumed response | Safety | Client support / value |
| --- | --- | --- | --- | --- |
| `homeDiag.js:47-179`, `home.js:135-178` | `POST /cgi-bin/home_mgr.cgi`, `cmd=2` | XML: `board_temperature`, `fan`, `hd_status/disk`, `raid/res`, RAID `item/state`; detailed UI also uses count/mode/volume fields | **READ** | Implemented as `diagnostics()` and hardware-confirmed. |
| `web_idle_timeout.js:141-202` | `POST /cgi-bin/home_mgr.cgi`, `cmd=8` | XML `res`: `0` normal, `1` over-temperature warning, `2` system busy/hotplug handling | **READ** | New compact health-warning signal; strong Home Assistant binary-sensor candidate. |
| `function.js:296-308`, `raid_diag.js:235-263` | `GET` or `POST /xml/current_hd_info.xml` (cache-busting query in UI) | XML items: `allowed`, `device_name`, `scsi`, `vendor`, `model`, `serial`, `size`, `size_in_gbytes`, `sdx2_size`, `part_cnt` | **READ** | New richer physical-disk inventory. Redact `serial` in diagnostics and bug reports. Much overlaps `system_info()`. |
| `web_idle_timeout.js:284-300` | `POST /web/php/noHDD.php`, `cmd=getDiskStatus` | XML `cntDisk`, `res`, `eula` | **READ** | New. Useful chiefly for “no disks / initialization” state; `eula` is not monitoring data. |
| `function.js:355-372` | `POST /cgi-bin/hd_config.cgi`, `cmd=cgi_Volume_Status`, `f_flag` | XML `state` values documented in JS: no volume, OK, SMART test, formatting, scanning, no disk, invalid sequence | **UNKNOWN** | `f_flag=0` is described as “scan disk, check volume”; whether it starts work or only inspects state is unclear. Do not live-test yet. `f_flag=1` is associated with formatting/SMART workflows and must not be probed. |

The JavaScript exposes only a summarized S.M.A.R.T. result (`none`, `healthy`,
`non-healthy`) through `cmd=2` (`homeDiag.js:79-119`). No endpoint for SMART
attributes, test history, or a read-only self-test result was found. No SMART
self-test command is safe to infer from `cgi_Volume_Status`.

`board_temperature` is handled as a diagnostic code: `0` normal, `2` critical,
and other non-zero values elevated (`homeDiag.js:55-64`). Disk Celsius values
come from `/xml/sysinfo.xml`, not from this field (`homeDiag.js:183-267`). The
captured model sets `_MIN_FAN_SPEED = 0` (`define.js:47`); the UI prints the
reported RPM. This does not establish that `0 RPM` is universally healthy.

The UI recognizes one additional RAID state not called out in the current API
documentation: `resync5`, described as RAID parity verification
(`homeDiag.js:139-143`). The Python parser already returns arbitrary state text,
so code behavior is compatible; only the documented known-state list is
incomplete.

### RAID and volume detail/progress

| Source | Request | Consumed response | Safety | Client support / value |
| --- | --- | --- | --- | --- |
| `raid_define.js:7-16`, `raid_diag.js:55-71`, `raid_diag.js:816-846` | `GET /xml/dm_read_state.xml` | XML `dm_state/percent`, `finished`, `describe`, `errcode` | **READ** | New. Safe poll used by the UI. Likely Disk Manager operation progress; do not label it RAID resync until a live response proves that relationship. |
| `raid_define.js:13` | `GET /xml/dm_read_progress.xml` | Not consumed anywhere in this corpus | **READ candidate** | Endpoint constant only; response contract and purpose unverified. Priority B. |
| `raid_diag.js:23-38`, `raid_diag.js:267-281`, `raid_diag.js:1139-1148` | `GET /xml/used_volume_info.xml` | `volume`, `raid_mode`, `file_type`, `is_roaming_volume`, plus `mount_status`, `mount`, `raid_status`, `volume_encrypt` elsewhere | **READ** | New rich volume/RAID detail. Strong live-test candidate. |
| `raid_diag.js:7-21`, `raid_diag.js:1151-1153`, `raid_diag.js:1376-1387` | `GET /xml/unused_volume_info.xml` | `partition` and unused-disk entries | **READ** | New; useful for missing/unassigned disk diagnostics. |
| `raid_diag.js:75-93`, `raid_diag.js:1542-1551` | `POST /web/storage/raid_cgi.php`, `cmd=cgi_Get_SysInfo` | XML `raids/raid`: at least `dev`, `uuid`; full document is retained by UI | **READ** | New, polled every two seconds by RAID UI. UUID must be treated as sensitive diagnostic data. Response needs capture before designing an API. |
| `home.js:306-318`, `fw.js:672-681` | `/xml/sysinfo.xml` | Existing volume fields plus `mnt`, `raid_state`, top-level `roaming`, `skip_roaming` | **READ** | `system_info()` is implemented but drops these useful RAID/mount fields. |
| `system.js:244-260` | `POST /xml/dm_read_state.xml` | Same progress fields | **READ** | Confirms the static XML is used as a polling resource even when requested with POST. GET is preferable for a safe test because RAID code explicitly uses GET. |

Other constants in `raid_define.js` identify `/xml/dm_volume_info.xml`,
`/xml/hd_right_position.xml`, and `/xml/hidden_encryption.xml`. Their schemas are
not meaningfully consumed in the captured monitoring paths. They remain
Priority B and should not be assigned semantics from their names alone.

### Capacity and filesystem data

| Source | Request | Consumed response | Safety | Client support / value |
| --- | --- | --- | --- | --- |
| `homeDiag.js:337-367` | `POST /cgi-bin/hd_config.cgi`, `cmd=cgi_Status_CapacityUsage` | Per item: `volume`, `free_size`, `use_size`, `Shared_Videos`, `Shared_Pictures`, `Shared_Music`; live response also includes `total_size`, `used_rate` | **READ** | Implemented and hardware-confirmed. |
| `home.js:39-54`, `function.js:311-330` | `GET` or `POST /xml/sysinfo.xml` | Disks, volumes, aggregate sizes; UI additionally consumes human-readable `total_unused_size_h` | **READ** | Implemented. Preserve distinction from capacity endpoint. |
| `cloud.js:1425-1438` | `POST /web/restSDK/cloudAccess.php`, `cmd=get_capacity` | JSON passed through without field inspection | **READ candidate** | New but cloud-stack-specific and undocumented; lower value than local capacity CGI. |

The JavaScript clarifies a unit mismatch in current documentation. It multiplies
`free_size` and `use_size` by `1024` before combining them with the media category
values (`homeDiag.js:351-370`). Therefore:

- `free_size` and `use_size` are strongly evidenced as 1-KiB block counts.
- By inference, `total_size` is the same kind of block count because its live
  magnitude and sibling fields match.
- `Shared_Videos`, `Shared_Pictures`, and `Shared_Music` appear to already be
  byte counts; the UI does **not** multiply them before subtraction and passes
  them directly to `size2str()`.

The current `docs/API.md` sentence that groups all three media values with the
KiB counters is therefore inconsistent with the captured WD code. The Python
client correctly preserves raw integers, so this is a documentation/typing issue,
not a conversion bug in `capacity_usage()`.

### Network

| Source | Request | Consumed response | Safety | Client support / value |
| --- | --- | --- | --- | --- |
| `function.js:1995-2015`, `function.js:2065-2079` | `GET /cgi-bin/network_mgr.cgi?cmd=cgi_get_internet_access` | XML `connectivity` (`true`/`false`) | **READ** | New and strong Home Assistant connectivity binary-sensor candidate. |
| `function.js:1510-1523` | `POST /xml/ip.xml` | XML `lan/ip` | **READ** | New alternative source; largely redundant with `network_info()`. |
| `function.js:2082-2091` | `POST /web/cgi_api.php?cgi_name=get_ip_address` | JSON `ip_address` | **READ** | New but redundant. |
| `cloud.js:522-542` | `POST /cgi-bin/network_mgr.cgi`, `cmd=cgi_dashboard_cloud_access_info` | XML `https_port`, `http_port`, `dashboard_cloud_access` | **READ** | New but configuration-oriented, not core monitoring. |
| `device_active.js:338-377` | `POST /cgi-bin/status_mgr.cgi`, `cmd=resource` | Instantaneous LAN1/LAN2 receive/transmit rates and bonding flag | **READ** | Existing `system_status()` leaves these fields unused. Strong enhancement candidate. |

The current `network_info()` uses `cgi_get_lan_xml`. That command is not present
in this captured JavaScript subset, but it is already hardware-confirmed by the
supplied tests; absence from this corpus is not evidence against it.

### USB, MTP, and UPS

| Source | Request | Consumed response | Safety | Client support / value |
| --- | --- | --- | --- | --- |
| `home_usb.js:62-139` | `GET /web/get_usb_info.php` | JSON `success`, `usb`; common `type`, `device_name`. Storage: model/vendor/manufacturer/revision, lock state/hint, IDs, port/speed/connectivity, serial, map device, sizes, partitions (`share_name`, `base_path`, `mounted_date`, `size`, `fs_type`). UPS: `sn`, `manufacturer`, misspelled `barrery_charge`, `status`. MTP: manufacturer/model/serial/revision. | **READ** | `usb_info()` is implemented but returns raw JSON. UPS battery/status and storage capacity are valuable unused data. `success:false` without devices is hardware-confirmed and valid. |
| `home_usb.js:317-344` | `POST /cgi-bin/usb_device.cgi`, `cmd=cgi_usb_storage_unlock` | XML `unlock_status` | **WRITE** | Unlocks storage and can save a password. Never use for monitoring. |
| `home_usb.js:390-408` | `POST /cgi-bin/usb_device.cgi`, dynamic `cgi_usb_Storage_umount` or `cgi_usb_mtp_umount` | Not consumed | **DANGEROUS** | Unmount/eject side effect. Never probe. |
| `home_usb.js:414-429` | `POST /cgi-bin/usb_device.cgi`, `cmd=cgi_usb_check_eject` | XML not inspected | **UNKNOWN** | Name suggests status, but it follows unmount workflow. Do not probe. |

### Alerts, time, firmware, accounts, and low-priority status

| Source | Request | Consumed response | Safety | Client support / value |
| --- | --- | --- | --- | --- |
| `init.js:169-273`, `init.js:401-415` | `POST /cgi-bin/system_mgr.cgi`, `cmd=cgi_get_alert` | XML alerts: `code`, `seq_num`, `level`, `msg`, `desc`, `time` | **READ** | Implemented by `alerts()` and hardware-confirmed. Delete commands nearby are WRITE. |
| `users.js:2224-2239` | `POST /cgi-bin/system_mgr.cgi`, `cmd=cgi_get_time` | Calendar fields `year`, `mon`, `day`, `date_format` | **READ** | New but is wall-clock/configuration data, not uptime. |
| `quota.js:170-187` | `POST /cgi-bin/account_mgr.cgi`, `cmd=cgi_get_quota_info` | XML `hddnum`, `hddsize`, `usernum`, `groupnum`, `v_name` | **READ** | New, low-priority capacity/account metadata. |
| `quota.js:14-40` | Same CGI, `cgi_get_user_quota_maxsize` / `cgi_get_group_quota_minsize`, parameters `name`, `hdd` | XML `quota_info/max_size` | **READ** | New but requires account names; not a default HA sensor. |
| `function.js:1974-1989` | `POST /cgi-bin/app_mgr.cgi`, `cmd=cgi_dlna_get` | XML retained as a whole | **READ** | Low-priority service configuration. |
| `home.js:58-101` | `GET /xml/apkg_all.xml` | App items including `show`, `user_control` | **READ** | Installed-app inventory, low monitoring value. |
| `ota.js:3-13`, `fw.js:851-876` | `POST /web/ota/ota.php`, `cmd=get_fw_update_configuration` | JSON `statusCode`, `updateStatus`, `downloadPercent`, `available`, etc. | **READ with external/cloud caveat** | Firmware/update state candidate, but some call sites pass `forceUpdate=true`, which may contact external services. Do not include in first live-test batch. |
| `function.js:1729-1749` | `POST /cgi-bin/system_mgr.cgi`, `cmd=get_firm_v_xml` | Firmware XML | **READ** | Implemented by `system_version()`. |
| `cloud.js:1425-1438` and other `get*` calls | `/web/restSDK/cloudAccess.php` | JSON | **READ or session-sensitive** | `getCloudAccess` is implemented. Other cloud account/service calls may expose identities or contact remote services and are not recommended for monitoring probes. |

## Uptime investigation

No JavaScript-backed alternative uptime endpoint was found.

- There is no `uptime` token in the WD application code that maps to an API
  request.
- `resource/now_time` is a sample timestamp used to advance charts, not time
  since boot (`device_active.js:472-481`).
- `cgi_get_time` returns calendar components for a date picker
  (`users.js:2224-2239`).
- `/system_ready.html` and `/system_boot.html` are reachability markers used
  during restart workflows (`cloud.js:632-641`, `function.js:1527-1544`); neither
  exposes boot time or elapsed uptime.
- `cgi_process` exposes command/user/PID/CPU/memory but no process start or
  elapsed-time field (`device_active.js:219-225`).
- The already disproven `cgi_get_uptime` and `cgi_get_general` commands do not
  appear in the captured UI JavaScript.

Conclusion: retain the documented `UptimeUnavailableError` for this model and
firmware. Do not derive uptime from `now_time`, NAS wall clock, first-seen time,
PID values, or page readiness. JavaScript analysis provides no safe new uptime
live test.

## Comparison with `wdnas_client`

| Client method | Assessment |
| --- | --- |
| `login()` | OS 5 endpoint matches the UI and is hardware-confirmed. |
| `system_info()` | Core disks/volumes/sizes are implemented. It drops useful `mnt`, `raid_state`, `roaming`, `skip_roaming`, and human-readable capacity fields used by the UI. Parsing remains less defensive than the new diagnostics parser if known nodes are absent. |
| `system_status()` | Correctly uses hardware-confirmed `resource`, but drops `buffers`, `cached`, bonding, LAN rates, `now_time`, and process count. `now_time` must remain a sample timestamp. |
| `network_info()` | Hardware-confirmed. Command is absent from this JS corpus, so no new conclusion about its response contract is possible. |
| `device_info()`, `system_version()` | Corresponding read commands are JS-proven and hardware-confirmed. |
| `share_names()`, `accounts()`, `alerts()` | Corresponding resources/commands occur in the UI. Alerts are fully aligned with the consumed fields. |
| `diagnostics()` | Response shape matches the UI and live result. It correctly preserves unknown state text. `resync5` should be added to documentation in a future implementation task. |
| `capacity_usage()` | Raw-return strategy is correct. The documentation should distinguish KiB block counters from apparently byte-valued media categories. |
| `usb_info()` | Correct GET method and raw JSON behavior. Structured helpers could expose UPS and storage fields without breaking the raw public API. |
| `cloud_access()` | `getCloudAccess` is JS-proven. Cloud identity data is less useful for local monitoring. |
| `uptime()` | No supported JavaScript alternative was found; current unavailable behavior on Mirror 5.33.102 remains justified. |

## Safety classification of the full command inventory

This appendix groups all command values found in request contexts. “READ” means
the UI usage is unambiguously observational. It does not mean the response is
free of sensitive data.

### READ

`2`, `8`, `resource`, `cgi_process`, `cgi_Status_CapacityUsage`,
`cgi_dashboard_cloud_access_info`, `cgi_Detect_Dangerous`, `cgi_dlna_get`,
`cgi_adduser_get_user_quota_maxsize`, `cgi_get_ads_info`, `cgi_get_alert`,
`cgi_get_create_status`,
`cgi_get_device_info`, `cgi_get_firmware_verify`,
`cgi_get_group_quota_minsize`, `cgi_get_HD_Mapping_Info`,
`cgi_get_internet_access`, `cgi_get_mail_addr`, `cgi_get_modify_user_info`,
`cgi_get_percentage`, `cgi_get_quota_info`, `cgi_get_restore_status`,
`cgi_Get_SysInfo`, `cgi_get_time`, `cgi_get_uP_fw`,
`cgi_get_uP_percentage`, `cgi_get_USB_Mapping_Info`, `cgi_get_user_info`,
`cgi_get_user_quota_maxsize`, `cgi_hotplug_status`, `cgi_sms_test_result`,
`cgi_upload_status`, `check_power_sch`, `check_token`, `chk_fw_upload`,
`get_agreement`, `get_capacity`, `get_firm_v_xml`,
`get_fw_update_configuration`, `getAccountXml`,
`getAllUsersAttachedToDevice`, `getCloudAccess`, `getCloudAccountInfo`,
`getCloudServiceURLs`, `getDiskStatus`, `getReleaseNoteURL`, `getSmbXml`.

Some of these are operation-status or cloud/session queries rather than useful
monitoring APIs. Only the Priority A subset below is recommended for live tests.

### WRITE

`analytics`, `logger`, `backup_otaclient_db`, `cgi_clear_resource`,
`cgi_create_sys_log`, `cgi_dashboard_cloud_access`, `cgi_del_alert`,
`cgi_del_alert_all`, `cgi_eula`,
`cgi_mail_addr`, `cgi_mail_del`, `cgi_mail_enable`, `cgi_mail_level`,
`cgi_mail_send_level`, `cgi_modify_account`, `cgi_set_share_access`,
`cgi_sms_add`, `cgi_sms_del`, `cgi_sms_modify`, `set_cloud_access`,
`set_group_permission`, `set_hwTranscoding`, `set_public`,
`set_share_folder`, `set_user_permission`, `setCloudAccess`,
`update_agreement`, `update_device_name`, `update_device_owner`,
`attach_device_owner`, `detach_user`, `invite`, `logout`, `reset_pw`,
`sign_in`.

These modify local configuration, cloud/session state, logs, accounts, shares,
or notification settings. They are excluded from live testing.

### DANGEROUS

`cgi_Disk_Remount`, `cgi_FMT_GUI_Log`, `cgi_FMT_Wipe_DiskMGR`, `cgi_Restart`,
`cgi_RAID_Roaming`, `cgi_RAID_Roaming_Skip`, `cgi_restart`,
`cgi_restart_service`, `cgi_restore`, `cgi_shutdown`, `cgi_usb_storage_unlock`,
`cgi_usb_Storage_umount`, `cgi_usb_mtp_umount`, `cgi_user_add`, `cgi_user_del`,
`device_reset`, `delete_device_owner`, `switch_quick_restore`, `setSataPower`,
`update_fw`, `cgi_upload`, `cgi_firmware_init_upload`, `cgi_email_test`,
`cgi_sms_test`.

Some entries are workflow helpers rather than destructive by themselves, but
they participate directly in restart, restore, disk, firmware, account, eject,
or outbound-message workflows. Conservative classification is intentional.

### UNKNOWN — do not probe

`5`, `6`, `cgi_Check_Disk_Remount_State`, `cgi_chk_restore`,
`cgi_firmware_init_upload_chk`, `cgi_FMT_Disk_DiskMGR_ps`,
`cgi_usb_check_eject`, `cgi_Volume_Status`.

Names suggest that several are status checks, but the code does not establish
that they are side-effect-free in isolation. The dynamic `/web/cgi_api.php`
analytics route is also UNKNOWN because `cgi_name` may be supplied by callers.

## Priorities

### Priority A — safe and valuable live-test candidates

1. `GET /xml/used_volume_info.xml`: richer volume, RAID mode/state, filesystem,
   mount, encryption, and roaming details.
2. `GET /xml/dm_read_state.xml`: Disk Manager operation progress. Record the
   response while idle and, only during a naturally occurring rebuild, compare
   it with `diagnostics().raid.volumes[].state`; do not start an operation.
3. `POST /cgi-bin/home_mgr.cgi`, `cmd=8`: compact over-temperature/system-busy
   warning state.
4. `GET /cgi-bin/network_mgr.cgi?cmd=cgi_get_internet_access`: connectivity
   boolean.
5. `POST /cgi-bin/status_mgr.cgi`, `cmd=cgi_process`: process snapshot. Sanitize
   commands/usernames before sharing captures.
6. Expand observation of the already confirmed `resource` response to record
   `buffers`, `cached`, bonding, LAN rates, and process count.
7. Re-run the already implemented USB GET only when an UPS or USB disk is
   naturally attached, to validate the documented JSON fields. Do not attach or
   eject hardware solely for the test.

### Priority B — useful but contract or semantics need clarification

- `POST /web/storage/raid_cgi.php`, `cmd=cgi_Get_SysInfo` (full schema unknown,
  contains UUIDs).
- `GET /xml/current_hd_info.xml` (mostly overlap, contains serial numbers).
- `GET /xml/unused_volume_info.xml`, `/xml/dm_read_progress.xml`,
  `/xml/dm_volume_info.xml`, `/xml/hd_right_position.xml`.
- `POST /web/php/noHDD.php`, `cmd=getDiskStatus` and
  `POST /cgi-bin/hd_config.cgi`, `cmd=cgi_hotplug_status` (mainly initialization
  and hotplug workflow signals).
- Firmware/cloud status getters, because they can contact external WD services
  or expose account data.

### Priority C — do not pursue for monitoring

All WRITE, DANGEROUS, and UNKNOWN commands listed above. In particular, never
probe restart/shutdown/restore, RAID roaming/format/remount, firmware upload or
update, USB unlock/unmount/eject, user/share/account modifications, alert
deletion, email/SMS tests, or system-log creation.

## Safe example probes (not executed)

These examples assume an already authenticated OS 5 `client` instance and use
only calls proven read-only by the UI. They intentionally print raw text for
contract discovery; sanitize serials, UUIDs, usernames, paths, and process
commands before retaining or sharing output.

```python
async def safe_get(nas, path):
    async with nas.session.get(f"http://{nas.host}{path}") as response:
        return response.status, await response.text()


async def safe_post(nas, path, cmd):
    async with nas.session.post(
        f"http://{nas.host}{path}",
        data={"cmd": cmd},
        headers={
            "Host": nas.host,
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        },
    ) as response:
        return response.status, await response.text()


# Priority A
used_volumes = await safe_get(nas, "/xml/used_volume_info.xml")
dm_progress = await safe_get(nas, "/xml/dm_read_state.xml")
device_warning = await safe_post(nas, "/cgi-bin/home_mgr.cgi", "8")
processes = await safe_post(nas, "/cgi-bin/status_mgr.cgi", "cgi_process")
internet = await safe_get(
    nas, "/cgi-bin/network_mgr.cgi?cmd=cgi_get_internet_access"
)
```

Do not add the Priority B endpoints to an automated sweep. Test them individually
only after reviewing the intended request and expected sensitive fields.

## Recommended development direction

1. First capture sanitized Priority A responses without changing NAS state.
2. Extend `system_status()` compatibly (or add a detailed method) for buffer,
   cache, bonding, and LAN-rate fields; keep `now_time` explicitly non-uptime.
3. Design a read-only `volume_status()` around `used_volume_info.xml` only after
   a Mirror response is captured. Keep it distinct from capacity usage.
4. Add an optional Disk Manager progress method around `dm_read_state.xml`, with
   careful naming that does not promise RAID resync semantics.
5. Add structured USB/UPS helpers while preserving `usb_info()` raw output.
6. Correct the capacity-unit documentation and add `resync5` to the known RAID
   states in a separate implementation task.
7. Do not pursue uptime further without new firmware evidence or a new captured
   WD UI resource that explicitly exposes boot/elapsed time.
