"""Regression tests for established monitoring methods."""

import unittest
from xml.etree import ElementTree

from tests.fakes import FakeResponse, FakeSession
from wdnas_client import client
from wdnas_client.exceptions import RequestFailedError

SYSTEM_INFO_XML = """\
<root>
  <disk id="0">
    <name>Disk 1</name><connected>1</connected><vendor>WD</vendor>
    <model>Example</model><rev>1</rev><sn>REDACTED</sn>
    <size>1000</size><failed>0</failed><healthy>1</healthy>
    <removable>0</removable><over_temp>0</over_temp><temp>35</temp>
    <sleep>0</sleep>
  </disk>
  <vol id="1">
    <name>Volume_1</name><label>Data</label><encrypted>0</encrypted>
    <unlocked>1</unlocked><mounted>1</mounted><size>900</size>
  </vol>
  <total_size>1000</total_size>
  <total_used_size>400</total_used_size>
  <total_unused_size>600</total_unused_size>
</root>
"""


class MonitoringTests(unittest.IsolatedAsyncioTestCase):
    """Exercise representative public monitoring calls offline."""

    @staticmethod
    def make_client(response, *, version=5):
        nas = client("admin", "secret", "nas.invalid", version)
        nas.session = FakeSession(response)
        nas.wd_csrf_token = "csrf-token"
        return nas

    async def test_system_info_parses_disks_volumes_and_capacity(self):
        nas = self.make_client(FakeResponse(text=SYSTEM_INFO_XML))

        result = await nas.system_info()

        self.assertEqual(result["size"], {"total": 1000, "used": 400, "unused": 600})
        self.assertEqual(result["disks"][0]["temp"], 35)
        self.assertTrue(result["disks"][0]["healthy"])
        self.assertEqual(result["volumes"][0]["label"], "Data")
        self.assertTrue(result["volumes"][0]["mounted"])

    async def test_api2_monitoring_sends_csrf_token(self):
        nas = self.make_client(FakeResponse(text=SYSTEM_INFO_XML), version=2)

        await nas.system_info()

        self.assertEqual(
            nas.session.calls[0][2]["headers"],
            {"Host": "nas.invalid", "X-CSRF-Token": "csrf-token"},
        )

    async def test_system_status_parses_cpu_and_memory(self):
        response = FakeResponse(
            text=(
                "<root><cpu>17%</cpu><mem_total>1024</mem_total>"
                "<mem_free>256</mem_free><mem2_total>1 GB</mem2_total></root>"
            )
        )
        nas = self.make_client(response)

        result = await nas.system_status()

        self.assertEqual(
            result,
            {
                "cpu": 17,
                "memory": {"total": 1024, "unused": 256, "simple": "1 GB"},
            },
        )
        self.assertEqual(nas.session.calls[0][2]["data"], "cmd=resource")

    async def test_share_names_returns_successful_json_items(self):
        nas = self.make_client(
            FakeResponse(text='{"success": true, "item": ["Public", "Backup"]}')
        )

        self.assertEqual(await nas.share_names(), ["Public", "Backup"])

    async def test_device_and_firmware_information_are_parsed(self):
        nas = client("admin", "secret", "nas.invalid", 5)
        nas.session = FakeSession(
            FakeResponse(
                text=(
                    "<root><serial_number>REDACTED</serial_number>"
                    "<name>Test NAS</name><description>My Cloud</description></root>"
                )
            ),
            FakeResponse(text="<root><fw>5.00.000</fw><oled>ready\n</oled></root>"),
        )

        device = await nas.device_info()
        firmware = await nas.system_version()

        self.assertEqual(
            device,
            {
                "serial_number": "REDACTED",
                "name": "Test NAS",
                "description": "My Cloud",
            },
        )
        self.assertEqual(firmware, {"firmware": "5.00.000", "oled": "ready"})

    async def test_http_error_raises_request_failed(self):
        nas = self.make_client(FakeResponse(status=503))

        with self.assertRaises(RequestFailedError) as raised:
            await nas.network_info()

        self.assertIn("503", str(raised.exception))

    async def test_malformed_xml_propagates_parse_error(self):
        nas = self.make_client(FakeResponse(text="<root>"))

        with self.assertRaises(ElementTree.ParseError):
            await nas.system_info()

    async def test_version_specific_methods_reject_api2(self):
        nas = self.make_client(FakeResponse(), version=2)

        for method_name in ("cloud_access", "usb_info", "uptime"):
            with self.subTest(method=method_name), self.assertRaises(ValueError):
                await getattr(nas, method_name)()

        self.assertEqual(nas.session.calls, [])


if __name__ == "__main__":
    unittest.main()
