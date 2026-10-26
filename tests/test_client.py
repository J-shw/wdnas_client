import asyncio
import http.cookies
import unittest
from pathlib import Path
from unittest.mock import patch
from xml.etree import ElementTree

import aiohttp
from yarl import URL

from wdnas_client import client
from wdnas_client.exceptions import (
    InvalidLoginError,
    PowerActionBlockedError,
    RequestFailedError,
    UptimeUnavailableError,
)

V4_FIXTURES = Path(__file__).parent / "fixtures" / "v4"


def v4_fixture(name):
    return (V4_FIXTURES / name).read_text(encoding="utf-8")


class Headers(dict):
    def getall(self, key, default=None):
        value = self.get(key)
        if value is None:
            return [] if default is None else default
        return value if isinstance(value, list) else [value]


class FakeResponse:
    def __init__(
        self,
        status=200,
        text="",
        cookies=None,
        headers=None,
        history=None,
        url=None,
    ):
        self.status = status
        self._text = text
        self.cookies = cookies or http.cookies.SimpleCookie()
        self.headers = Headers(headers or {})
        self.history = history or ()
        self.url = URL(url) if url is not None else None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False

    async def text(self):
        return self._text


class CookieJar:
    def __init__(self):
        self.updates = []
        self.cookies = http.cookies.SimpleCookie()

    def update_cookies(self, cookies, response_url=None):
        self.updates.append((cookies, response_url))
        for key, value in cookies.items():
            self.cookies[key] = getattr(value, "value", value)

    def filter_cookies(self, url):
        return self.cookies


class FakeSession:
    def __init__(self, response):
        self.responses = list(response) if isinstance(response, (list, tuple)) else None
        self.response = response
        self.calls = []
        self.cookie_jar = CookieJar()
        self.closed = False
        self.sent_cookies = []

    def _record(self, method, url, kwargs):
        self.calls.append((method, url, kwargs))
        cookies = self.cookie_jar.filter_cookies(URL(url))
        self.sent_cookies.append({key: morsel.value for key, morsel in cookies.items()})

    def _next_response(self, url):
        response = (
            self.responses.pop(0) if self.responses is not None else self.response
        )
        if getattr(response, "url", None) is None:
            response.url = URL(url)
        return response

    def post(self, url, **kwargs):
        self._record("POST", url, kwargs)
        return self._next_response(url)

    def get(self, url, **kwargs):
        self._record("GET", url, kwargs)
        return self._next_response(url)

    def delete(self, url, **kwargs):
        self._record("DELETE", url, kwargs)
        return self._next_response(url)

    def put(self, url, **kwargs):
        self._record("PUT", url, kwargs)
        return self._next_response(url)

    async def close(self):
        self.closed = True


class ClientTests(unittest.IsolatedAsyncioTestCase):
    def make_client(self, response, version=5):
        nas = client("Admin", "secret", "nas.local", version)
        nas.session = FakeSession(response)
        return nas

    def make_power_client(self, response, version=5):
        nas = self.make_client(response, version)
        nas.phpsessid = "session-id"
        nas.session.cookie_jar.update_cookies({"PHPSESSID": "session-id"})
        if version == 5:
            nas._server_session_owned = True
        return nas

    async def test_os5_login(self):
        cookies = http.cookies.SimpleCookie()
        cookies["PHPSESSID"] = "session-id"
        response = FakeResponse(
            cookies=cookies,
            headers={"Set-Cookie": "PHPSESSID=session-id; Path=/"},
        )
        nas = self.make_client(response)
        await nas.login()
        self.assertEqual(nas.phpsessid, "session-id")
        method, url, kwargs = nas.session.calls[0]
        self.assertEqual((method, url), ("POST", "http://nas.local/nas/v1/auth"))
        self.assertEqual(kwargs["json"]["username"], "admin")
        self.assertEqual(kwargs["json"]["password"], "c2VjcmV0")

    async def test_os5_login_uses_historical_response_cookie_handling(self):
        cookies = http.cookies.SimpleCookie()
        cookies["PHPSESSID"] = "response-session"
        nas = self.make_client(FakeResponse(cookies=cookies))

        await nas.login()

        self.assertEqual(nas.phpsessid, "response-session")

    async def test_os5_login_uses_historical_raw_set_cookie_update(self):
        response = FakeResponse(
            headers={"Set-Cookie": "PHPSESSID=header-session; Path=/; HttpOnly"}
        )
        nas = self.make_client(response)

        await nas.login()

        # Commit 4e6389f updates the jar from the raw header, but deliberately
        # only assigns ``phpsessid`` from ``response.cookies``.
        self.assertIsNone(nas.phpsessid)
        jar_cookie = nas.session.cookie_jar.filter_cookies(
            URL("http://nas.local/cgi-bin/system_mgr.cgi")
        )["PHPSESSID"]
        self.assertEqual(jar_cookie.value, "header-session")
        self.assertIsNone(nas.session.cookie_jar.updates[0][1])

    async def test_os5_power_uses_historical_jar_cookie_without_phpsessid(self):
        nas = self.make_client(
            [
                FakeResponse(
                    headers={"Set-Cookie": "PHPSESSID=header-session; Path=/"}
                ),
                FakeResponse(text="<config><res>0</res></config>"),
                FakeResponse(),
            ]
        )

        await nas.login()
        self.assertIsNone(nas.phpsessid)
        await nas.reboot()

        self.assertEqual(
            [call[2].get("data") for call in nas.session.calls],
            [None, "cmd=cgi_Detect_Dangerous", "cmd=cgi_restart"],
        )
        self.assertEqual(
            sum(call[1].endswith("/nas/v1/auth") for call in nas.session.calls),
            1,
        )

    async def test_os5_power_guard_uses_actual_cgi_cookie_path_on_ip_host(self):
        jar = aiohttp.CookieJar(unsafe=True)
        cookie = http.cookies.SimpleCookie()
        cookie["PHPSESSID"] = "cgi-session"
        cookie["PHPSESSID"]["path"] = "/cgi-bin"
        jar.update_cookies(
            cookie,
            response_url=URL("http://192.0.2.10/cgi-bin/session-source"),
        )
        nas = client("Admin", "secret", "192.0.2.10", 5)
        nas.session = FakeSession(
            [FakeResponse(text="<config><res>0</res></config>"), FakeResponse()]
        )
        nas.session.cookie_jar = jar

        await nas.reboot()

        self.assertEqual(
            [call[2]["data"] for call in nas.session.calls],
            ["cmd=cgi_Detect_Dangerous", "cmd=cgi_restart"],
        )

    async def test_os5_power_guard_does_not_require_sendable_session_cookie(self):
        for response_url, path in (
            ("http://nas.local/nas/v1/auth", "/nas"),
            ("http://other.local/cgi-bin/session-source", "/cgi-bin"),
        ):
            with self.subTest(response_url=response_url, path=path):
                jar = aiohttp.CookieJar()
                cookie = http.cookies.SimpleCookie()
                cookie["PHPSESSID"] = "not-for-power-target"
                cookie["PHPSESSID"]["path"] = path
                jar.update_cookies(cookie, response_url=URL(response_url))
                nas = self.make_client(
                    [
                        FakeResponse(text="<config><res>0</res></config>"),
                        FakeResponse(),
                    ]
                )
                nas.session.cookie_jar = jar

                await nas.reboot()

                self.assertEqual(
                    [call[2]["data"] for call in nas.session.calls],
                    ["cmd=cgi_Detect_Dangerous", "cmd=cgi_restart"],
                )

    async def test_os5_power_guard_diagnostic_contains_only_safe_metadata(self):
        nas = client("Admin", "secret", "nas.local", 5)
        nas.phpsessid = "never-log-session-value"

        with (
            self.assertLogs("wdnas_client", level="WARNING") as logs,
            self.assertRaises(InvalidLoginError),
        ):
            await nas.reboot()

        diagnostic = logs.output[0]
        self.assertIn("api_version=5", diagnostic)
        self.assertIn("session_present=False", diagnostic)
        self.assertIn("session_closed=False", diagnostic)
        self.assertIn("phpsessid_present=True", diagnostic)
        self.assertIn("preflight_started=False", diagnostic)
        self.assertIn("phase=session_guard", diagnostic)
        self.assertIn("exception_type=InvalidLoginError", diagnostic)
        self.assertNotIn("never-log-session-value", diagnostic)
        self.assertNotIn("nas.local", diagnostic)

    async def test_os5_http_200_without_cookie_keeps_historical_result(self):
        response = FakeResponse(text='{"error":"ACCOUNT_IN_USE"}')
        nas = self.make_client(response)

        await nas.login()

        self.assertIsNone(nas.phpsessid)
        self.assertEqual(len(nas.session.calls), 1)
        self.assertEqual(
            [call[0] for call in nas.session.calls],
            ["POST"],
        )

    async def test_os5_failed_protected_read_closes_without_server_logout(self):
        session = FakeSession(
            [
                FakeResponse(text='{"error":"ACCOUNT_IN_USE"}'),
                FakeResponse(status=403),
            ]
        )
        nas = client("Admin", "secret", "nas.local", 5)

        with patch("wdnas_client.aiohttp.ClientSession", return_value=session):
            await nas.__aenter__()
            with self.assertRaises(RequestFailedError):
                await nas.system_info()
            await nas.close()

        self.assertEqual([call[0] for call in session.calls], ["POST", "GET"])
        self.assertTrue(session.closed)
        self.assertFalse(nas._server_session_owned)

    async def test_os5_protected_read_confirms_session_ownership(self):
        system_xml = (
            "<config><disk id='1'><name>Disk</name><connected>1</connected>"
            "<vendor>WD</vendor><model>disk</model><rev>1</rev><sn>disk-1</sn>"
            "<size>1</size><failed>0</failed><healthy>1</healthy>"
            "<removable>0</removable><over_temp>0</over_temp><temp>30</temp>"
            "<sleep>0</sleep></disk><vol id='1'><name>Volume</name>"
            "<label>Volume 1</label><encrypted>0</encrypted><unlocked>1</unlocked>"
            "<mounted>1</mounted><size>1</size></vol><total_size>1</total_size>"
            "<total_used_size>0</total_used_size>"
            "<total_unused_size>1</total_unused_size></config>"
        )
        session = FakeSession(
            [FakeResponse(), FakeResponse(text=system_xml), FakeResponse(status=204)]
        )
        nas = client("Admin", "secret", "nas.local", 5)

        with patch("wdnas_client.aiohttp.ClientSession", return_value=session):
            await nas.__aenter__()
            await nas.system_info()
            await nas.close()

        self.assertEqual([call[0] for call in session.calls], ["POST", "GET", "DELETE"])
        self.assertTrue(session.closed)

    async def test_os5_non_200_uses_historical_request_failure(self):
        for status in (401, 403):
            with self.subTest(status=status):
                nas = self.make_client(FakeResponse(status=status))
                with self.assertRaises(RequestFailedError) as caught:
                    await nas.login()
                self.assertEqual(caught.exception.status_code, status)
                self.assertEqual(len(nas.session.calls), 1)

    async def test_os2_login_remains_compatible(self):
        cookies = http.cookies.SimpleCookie()
        cookies["PHPSESSID"] = "session-id"
        cookies["WD-CSRF-TOKEN"] = "csrf-token"
        response = FakeResponse(cookies=cookies)
        nas = self.make_client(response, version=2)
        await nas.login()
        self.assertEqual(nas.phpsessid, "session-id")
        self.assertEqual(nas.wd_csrf_token, "csrf-token")
        method, url, kwargs = nas.session.calls[0]
        self.assertEqual(
            (method, url), ("POST", "http://nas.local/cgi-bin/login_mgr.cgi")
        )
        self.assertIn("cmd=wd_login", kwargs["data"])

    async def test_v4_login_uses_query_parameters_and_reuses_session(self):
        nas = client("Admin", "secret", "nas.local", 4)
        session = FakeSession(FakeResponse(text="<local_login/>"))

        with patch("wdnas_client.aiohttp.ClientSession", return_value=session):
            self.assertIs(await nas.__aenter__(), nas)
            self.assertIs(await nas.__aenter__(), nas)

        self.assertEqual(len(session.calls), 1)
        method, url, kwargs = session.calls[0]
        self.assertEqual(
            (method, url),
            ("GET", "http://nas.local/api/2.1/rest/local_login"),
        )
        self.assertEqual(kwargs["params"], {"username": "admin", "password": "secret"})

        await nas.close()
        self.assertTrue(session.closed)
        self.assertEqual(len(session.calls), 2)
        self.assertEqual(
            session.calls[1][:2],
            ("GET", "http://nas.local/api/2.1/rest/logout"),
        )

    async def test_os5_context_uses_historical_default_client_session(self):
        nas = client("Admin", "secret", "192.0.2.10", 5)
        cookies = http.cookies.SimpleCookie()
        cookies["PHPSESSID"] = "opaque-session-value"
        session = FakeSession(
            FakeResponse(
                cookies=cookies,
                headers={"Set-Cookie": "PHPSESSID=opaque-session-value; Path=/"},
            )
        )

        with patch(
            "wdnas_client.aiohttp.ClientSession", return_value=session
        ) as constructor:
            await nas.__aenter__()

        constructor.assert_called_once_with()
        self.assertEqual(nas.phpsessid, "opaque-session-value")
        self.assertFalse(session.closed)
        await nas.close()
        self.assertTrue(session.closed)
        self.assertEqual([call[0] for call in session.calls], ["POST", "DELETE"])

    async def test_os5_historical_cookie_jar_protects_device_info(self):
        device_xml = (
            "<config><serial_number>serial</serial_number><name>nas</name>"
            "<description>WD My Cloud Mirror</description></config>"
        )
        session = FakeSession(
            [
                FakeResponse(headers={"Set-Cookie": "PHPSESSID=same-session; Path=/"}),
                FakeResponse(text=device_xml),
                FakeResponse(status=204),
            ]
        )
        nas = client("Admin", "secret", "192.0.2.10", 5)

        with patch("wdnas_client.aiohttp.ClientSession", return_value=session):
            await nas.__aenter__()
            device = await nas.device_info()
            await nas.close()

        self.assertEqual(device["serial_number"], "serial")
        self.assertEqual(
            [call[:2] for call in session.calls],
            [
                ("POST", "http://192.0.2.10/nas/v1/auth"),
                ("POST", "http://192.0.2.10/cgi-bin/system_mgr.cgi"),
                ("DELETE", "http://192.0.2.10/nas/v1/auth"),
            ],
        )
        self.assertEqual(session.sent_cookies[0], {})
        self.assertEqual(session.sent_cookies[1]["PHPSESSID"], "same-session")
        self.assertEqual(session.sent_cookies[2]["PHPSESSID"], "same-session")
        self.assertEqual(
            sum(
                call[1].endswith("/nas/v1/auth") and call[0] == "POST"
                for call in session.calls
            ),
            1,
        )

    async def test_default_aiohttp_cookie_jar_rejects_ip_host_cookies(self):
        cookies = http.cookies.SimpleCookie()
        cookies["PHPSESSID"] = "opaque-session-value"
        jar = aiohttp.CookieJar()

        jar.update_cookies(
            cookies,
            response_url=URL("http://192.0.2.10/nas/v1/auth"),
        )

        self.assertNotIn(
            "PHPSESSID",
            jar.filter_cookies(URL("http://192.0.2.10/nas/v1/auth")),
        )

    async def test_v4_login_rejects_401_and_403(self):
        for status in (401, 403):
            with self.subTest(status=status):
                nas = self.make_client(FakeResponse(status=status), version=4)
                with self.assertRaises(InvalidLoginError) as caught:
                    await nas.login()
                self.assertEqual(caught.exception.status_code, status)

    async def test_v4_monitoring_reuses_one_authenticated_session(self):
        session = FakeSession(
            [
                FakeResponse(text="<local_login/>"),
                FakeResponse(
                    text="<system_information><capacity>2TB</capacity>"
                    "</system_information>"
                ),
                FakeResponse(text=v4_fixture("storage_usage.xml")),
                FakeResponse(text=v4_fixture("internet_access.xml")),
                FakeResponse(text="<logout/>"),
            ]
        )
        nas = client("Admin", "secret", "nas.local", 4)

        with patch("wdnas_client.aiohttp.ClientSession", return_value=session):
            await nas.__aenter__()
            await nas.system_info()
            await nas.internet_access()
            await nas.__aenter__()
            await nas.close()

        login_url = "http://nas.local/api/2.1/rest/local_login"
        self.assertEqual(sum(call[1] == login_url for call in session.calls), 1)
        self.assertEqual(len(session.calls), 5)
        self.assertTrue(session.closed)

    async def test_v4_login_transport_error_does_not_expose_query(self):
        class FailingSession(FakeSession):
            def get(self, url, **kwargs):
                raise aiohttp.ClientConnectionError(
                    f"{url}?username=admin&password=secret"
                )

        nas = client("Admin", "secret", "nas.local", 4)
        nas.session = FailingSession(FakeResponse())

        with self.assertRaises(aiohttp.ClientConnectionError) as caught:
            await nas.login()

        self.assertNotIn("admin", str(caught.exception))
        self.assertNotIn("secret", str(caught.exception))

    async def test_v4_xml_parsing_and_cached_identity_requests(self):
        system_information = """<system_information>
          <manufacturer>Western Digital Corporation</manufacturer>
          <model_description>WD My Cloud</model_description>
          <model_name>WDMyCloud</model_name><model_number>sq</model_number>
          <host_name>NAS02</host_name><capacity>2TB</capacity>
          <serial_number>REDACTED-SERIAL</serial_number>
        </system_information>"""
        firmware_info = """<firmware_info><current_firmware><package>
          <name>WDMyCloud</name><version>04.06.00-111</version>
          <description>Core F/W</description>
        </package></current_firmware></firmware_info>"""
        system_state = """<system_state><status>ready</status>
          <temperature>good</temperature><smart>good</smart><volume>good</volume>
          <free_space>good</free_space><reported_status>good</reported_status>
        </system_state>"""
        nas = self.make_client(
            [
                FakeResponse(text=system_information),
                FakeResponse(text=v4_fixture("storage_usage.xml")),
                FakeResponse(text=firmware_info),
                FakeResponse(text=system_state),
            ],
            version=4,
        )

        raw_info = await nas.system_information()
        system = await nas.system_info()
        device = await nas.device_info()
        firmware = await nas.firmware_info()
        version = await nas.system_version()
        state = await nas.system_state()

        self.assertEqual(raw_info["model_number"], "sq")
        self.assertEqual(system["size"]["total"], 1_964_257_656_832)
        self.assertEqual(system["size"]["used"], 1_508_405_891_072)
        self.assertEqual(system["size"]["unused"], 455_851_765_760)
        self.assertEqual(device["name"], "NAS02")
        self.assertEqual(device["description"], "WD My Cloud")
        self.assertEqual(device["serial_number"], "REDACTED-SERIAL")
        self.assertEqual(firmware["version"], "04.06.00-111")
        self.assertEqual(version["firmware"], "04.06.00-111")
        self.assertEqual(state["status"], "ready")
        self.assertEqual(state["temperature"], "good")
        self.assertEqual(state["smart"], "good")
        self.assertEqual(len(nas.session.calls), 4)

    async def test_v4_storage_usage_preserves_verified_byte_values(self):
        nas = self.make_client(
            FakeResponse(text=v4_fixture("storage_usage.xml")), version=4
        )

        result = await nas.storage_usage()

        self.assertEqual(result["size"], 1_964_257_656_832)
        self.assertEqual(result["usage"], 1_508_405_891_072)
        self.assertEqual(result["free"], 455_851_765_760)
        self.assertEqual(
            result["used_percentage"],
            1_508_405_891_072 * 100 / 1_964_257_656_832,
        )
        self.assertEqual(
            sum(result[key] for key in ("video", "photos", "music", "other")),
            result["usage"],
        )

    async def test_v4_storage_usage_missing_or_malformed_required_fields(self):
        for xml in (
            "<storage_usage><size>100</size></storage_usage>",
            "<storage_usage><size>invalid</size><usage>1</usage></storage_usage>",
            "<storage_usage><size>100</size><usage>-1</usage></storage_usage>",
        ):
            with self.subTest(xml=xml):
                nas = self.make_client(FakeResponse(text=xml), version=4)
                with self.assertRaises(ValueError):
                    await nas.storage_usage()

    async def test_v4_storage_usage_zero_capacity_and_excess_usage(self):
        zero = self.make_client(
            FakeResponse(
                text="<storage_usage><size>0</size><usage>0</usage></storage_usage>"
            ),
            version=4,
        )
        result = await zero.storage_usage()
        self.assertEqual(result["free"], 0)
        self.assertIsNone(result["used_percentage"])

        excess = self.make_client(
            FakeResponse(
                text="<storage_usage><size>100</size><usage>101</usage></storage_usage>"
            ),
            version=4,
        )
        with self.assertRaises(ValueError):
            await excess.storage_usage()

    async def test_v4_storage_usage_allows_missing_media_categories(self):
        nas = self.make_client(
            FakeResponse(
                text="<storage_usage><size>100</size><usage>25</usage></storage_usage>"
            ),
            version=4,
        )

        result = await nas.storage_usage()

        self.assertEqual(result["free"], 75)
        self.assertEqual(result["used_percentage"], 25)
        self.assertTrue(
            all(result[key] is None for key in ("video", "photos", "music", "other"))
        )

    async def test_v4_system_info_falls_back_when_storage_usage_is_unavailable(self):
        system_information = (
            "<system_information><capacity>2TB</capacity></system_information>"
        )
        nas = self.make_client(
            [FakeResponse(text=system_information), FakeResponse(status=404)],
            version=4,
        )

        result = await nas.system_info()

        self.assertEqual(result["size"]["total"], 2_000_000_000_000)
        self.assertIsNone(result["size"]["used"])
        self.assertIsNone(result["size"]["unused"])
        self.assertIsNone(result["size"]["used_percentage"])
        self.assertFalse(result["storage_usage_available"])

    async def test_v4_internet_access_uses_verified_connectivity_element(self):
        for xml, expected in (
            (v4_fixture("internet_access.xml"), True),
            (
                "<internet_access><connectivity>false</connectivity></internet_access>",
                False,
            ),
        ):
            with self.subTest(expected=expected):
                nas = self.make_client(FakeResponse(text=xml), version=4)
                self.assertIs(await nas.internet_access(), expected)

    async def test_v4_internet_access_rejects_missing_or_invalid_values(self):
        for xml in (
            "<internet_access/>",
            "<internet_access><status>true</status></internet_access>",
            "<internet_access><connectivity>unknown</connectivity></internet_access>",
        ):
            with self.subTest(xml=xml):
                nas = self.make_client(FakeResponse(text=xml), version=4)
                with self.assertRaises(ValueError):
                    await nas.internet_access()

    async def test_v4_optional_endpoints_report_401_and_403(self):
        for method_name in ("storage_usage", "internet_access"):
            for status in (401, 403):
                with self.subTest(method=method_name, status=status):
                    nas = self.make_client(FakeResponse(status=status), version=4)
                    with self.assertRaises(InvalidLoginError) as caught:
                        await getattr(nas, method_name)()
                    self.assertEqual(caught.exception.status_code, status)

    async def test_v4_incomplete_and_malformed_xml(self):
        incomplete = self.make_client(
            FakeResponse(
                text="<system_information><model_number>sq</model_number></system_information>"
            ),
            version=4,
        )
        self.assertIsNone((await incomplete.system_info())["size"]["total"])
        self.assertIsNone((await incomplete.device_info())["serial_number"])

        malformed = self.make_client(FakeResponse(text="<system_state>"), version=4)
        with self.assertRaises(ElementTree.ParseError):
            await malformed.system_state()

        wrong_root = self.make_client(FakeResponse(text="<html/>"), version=4)
        with self.assertRaises(ValueError):
            await wrong_root.system_state()

    async def test_v4_expired_session_raises_auth_error(self):
        for status in (401, 403):
            with self.subTest(status=status):
                nas = self.make_client(FakeResponse(status=status), version=4)
                with self.assertRaises(InvalidLoginError) as caught:
                    await nas.system_state()
                self.assertEqual(caught.exception.status_code, status)

    async def test_v4_unverified_operations_are_explicitly_unsupported(self):
        nas = self.make_client(FakeResponse(), version=4)
        for method_name in (
            "share_names",
            "network_info",
            "accounts",
            "alerts",
        ):
            with self.subTest(method=method_name), self.assertRaises(ValueError):
                await getattr(nas, method_name)()
        self.assertEqual(nas.session.calls, [])

    async def test_os5_logout_uses_existing_session_without_phpsessid(self):
        nas = self.make_power_client(FakeResponse(status=204))
        nas.phpsessid = None
        nas._authenticated = True

        await nas.logout()
        await nas.logout()

        self.assertEqual(
            nas.session.calls,
            [
                (
                    "DELETE",
                    "http://nas.local/nas/v1/auth",
                    {
                        "headers": {
                            "Accept": "application/json",
                            "Content-Type": "application/json",
                            "Host": "nas.local",
                        }
                    },
                )
            ],
        )
        self.assertFalse(nas.session.closed)

    async def test_v4_logout_uses_source_confirmed_endpoint_once(self):
        nas = self.make_client(FakeResponse(status=200), version=4)
        nas._authenticated = True

        await nas.logout()
        await nas.logout()

        self.assertEqual(
            nas.session.calls,
            [
                (
                    "GET",
                    "http://nas.local/api/2.1/rest/logout",
                    {"headers": {"Accept": "application/xml", "Host": "nas.local"}},
                )
            ],
        )
        self.assertFalse(nas._authenticated)
        self.assertFalse(nas.session.closed)

    async def test_v4_logout_failure_still_closes_and_is_not_retried(self):
        nas = self.make_client(FakeResponse(status=503), version=4)
        nas._authenticated = True

        with self.assertRaises(RequestFailedError) as caught:
            await nas.close()
        self.assertEqual(caught.exception.status_code, 503)
        self.assertTrue(nas.session.closed)

        with self.assertRaises(RequestFailedError):
            await nas.close()
        self.assertEqual(len(nas.session.calls), 1)

    async def test_v4_logout_timeout_is_ambiguous_and_never_retried(self):
        class SlowGetResponse:
            async def __aenter__(self):
                await asyncio.Event().wait()

            async def __aexit__(self, exc_type, exc, traceback):
                return False

        nas = self.make_client(SlowGetResponse(), version=4)
        nas._authenticated = True

        with (
            patch("wdnas_client.SESSION_ACTION_TIMEOUT", 0.01),
            self.assertRaises(TimeoutError),
        ):
            await nas.close()
        self.assertTrue(nas.session.closed)

        with self.assertRaises(TimeoutError):
            await nas.close()
        self.assertEqual(len(nas.session.calls), 1)

    async def test_v4_concurrent_cleanup_sends_exactly_one_logout(self):
        nas = self.make_client(FakeResponse(status=200), version=4)
        nas._authenticated = True

        await asyncio.gather(nas.close(), nas.close(), nas.close())

        self.assertEqual(
            [call[:2] for call in nas.session.calls],
            [("GET", "http://nas.local/api/2.1/rest/logout")],
        )
        self.assertTrue(nas.session.closed)

    async def test_os5_close_logs_out_then_closes_local_session(self):
        nas = self.make_power_client(FakeResponse(status=204))
        nas._authenticated = True

        await nas.close()

        self.assertEqual(
            [call[:2] for call in nas.session.calls],
            [("DELETE", "http://nas.local/nas/v1/auth")],
        )
        self.assertTrue(nas.session.closed)
        self.assertIsNone(nas.phpsessid)

    async def test_os5_concurrent_cleanup_sends_exactly_one_logout(self):
        nas = self.make_power_client(FakeResponse(status=204))
        nas._authenticated = True

        await asyncio.gather(nas.close(), nas.close(), nas.close())
        await nas.close()

        self.assertEqual(
            [call[:2] for call in nas.session.calls],
            [("DELETE", "http://nas.local/nas/v1/auth")],
        )
        self.assertTrue(nas.session.closed)

    async def test_os5_logout_http_error_closes_and_is_not_retried(self):
        nas = self.make_power_client(FakeResponse(status=503))
        nas._authenticated = True

        with self.assertRaises(RequestFailedError) as caught:
            await nas.close()
        self.assertEqual(caught.exception.status_code, 503)
        self.assertTrue(nas.session.closed)

        with self.assertRaises(RequestFailedError):
            await nas.close()
        self.assertEqual(len(nas.session.calls), 1)

    async def test_os5_logout_connection_failure_closes_and_is_not_retried(self):
        class FailingDeleteSession(FakeSession):
            def delete(self, url, **kwargs):
                self._record("DELETE", url, kwargs)
                raise aiohttp.ClientConnectionError("logout failed")

        nas = self.make_power_client(FakeResponse())
        nas.session = FailingDeleteSession(FakeResponse())
        nas._authenticated = True

        with self.assertRaises(aiohttp.ClientConnectionError):
            await nas.close()
        self.assertTrue(nas.session.closed)

        with self.assertRaises(aiohttp.ClientConnectionError):
            await nas.close()
        self.assertEqual(len(nas.session.calls), 1)

    async def test_os5_logout_timeout_closes_and_is_not_retried(self):
        class SlowDeleteResponse:
            async def __aenter__(self):
                await asyncio.Event().wait()

            async def __aexit__(self, exc_type, exc, traceback):
                return False

        nas = self.make_power_client(SlowDeleteResponse())
        nas._authenticated = True

        with (
            patch("wdnas_client.SESSION_ACTION_TIMEOUT", 0.01),
            self.assertRaises(TimeoutError),
        ):
            await nas.close()
        self.assertTrue(nas.session.closed)

        with self.assertRaises(TimeoutError):
            await nas.close()
        self.assertEqual(len(nas.session.calls), 1)

    async def test_context_exit_does_not_mask_original_exception(self):
        nas = self.make_power_client(FakeResponse(status=503))
        nas._authenticated = True

        original = RuntimeError("original failure")
        with self.assertRaises(RuntimeError) as caught:
            try:
                raise original
            except RuntimeError:
                await nas.__aexit__(RuntimeError, original, original.__traceback__)
                raise

        self.assertIs(caught.exception, original)
        self.assertTrue(nas.session.closed)

    async def test_os2_close_remains_local_and_does_not_call_logout_endpoint(self):
        nas = self.make_client(FakeResponse(), version=2)
        nas.phpsessid = "session-id"
        nas.wd_csrf_token = "csrf-token"

        await nas.close()

        self.assertEqual(nas.session.calls, [])
        self.assertTrue(nas.session.closed)

        with self.assertRaises(ValueError):
            await nas.logout()

    async def test_failed_os5_context_login_keeps_historical_cleanup_behavior(self):
        nas = client("Admin", "secret", "nas.local", 5)
        session = FakeSession(FakeResponse(status=401))

        with (
            patch("wdnas_client.aiohttp.ClientSession", return_value=session),
            self.assertRaises(RequestFailedError),
        ):
            await nas.__aenter__()

        self.assertFalse(session.closed)
        self.assertIsNone(nas.phpsessid)

    async def test_failed_os5_login_does_not_invoke_new_cleanup_manager(self):
        class FailingCloseSession(FakeSession):
            async def close(self):
                self.closed = True
                raise RuntimeError("local cleanup failed")

        nas = client("Admin", "secret", "nas.local", 5)
        session = FailingCloseSession(FakeResponse(status=401))

        with (
            patch("wdnas_client.aiohttp.ClientSession", return_value=session),
            self.assertRaises(RequestFailedError) as caught,
        ):
            await nas.__aenter__()

        self.assertEqual(caught.exception.status_code, 401)
        self.assertFalse(session.closed)

    async def test_os5_logout_without_or_with_closed_session_is_safe(self):
        missing = client("Admin", "secret", "nas.local", 5)
        await missing.logout()

        closed = self.make_client(FakeResponse())
        closed._authenticated = True
        closed.session.closed = True
        await closed.logout()

        self.assertEqual(closed.session.calls, [])

    async def test_diagnostics_healthy_raid1(self):
        xml = """<config>
          <board_temperature>0</board_temperature><fan>0</fan>
          <hd_status><disk>healthy</disk><disk>healthy</disk></hd_status>
          <raid><cntVol>1</cntVol><res>1</res><cntDisk>2</cntDisk>
            <item id="1"><num>1</num><vol>Volume_1</vol>
            <raidmode>raid1</raidmode><state>clean</state></item>
          </raid></config>"""
        nas = self.make_client(FakeResponse(text=xml))
        result = await nas.diagnostics()
        self.assertEqual(result["board_temperature"], 0)
        self.assertEqual(result["fan_rpm"], 0)
        self.assertEqual(result["disk_statuses"], ["healthy", "healthy"])
        self.assertEqual(result["raid"]["volumes"][0]["mode"], "raid1")
        self.assertEqual(result["raid"]["volumes"][0]["state"], "clean")
        self.assertEqual(nas.session.calls[0][2]["data"], "cmd=2")

    async def test_diagnostics_raid_states_and_multiple_volumes(self):
        for state in (
            "degraded",
            "damaged",
            "resync",
            "resync5",
            "recovery",
            "migrate",
            "reshape",
            "expansion",
        ):
            with self.subTest(state=state):
                xml = f"""<config><raid><cntVol>2</cntVol><cntDisk>2</cntDisk>
                  <item id="1"><num>1</num><vol>A</vol><raidmode>raid1</raidmode><state>{state}</state></item>
                  <item id="2"><num>2</num><vol>B</vol><raidmode>jbod</raidmode><state>clean</state></item>
                </raid></config>"""
                result = await self.make_client(FakeResponse(text=xml)).diagnostics()
                self.assertEqual(result["raid"]["volume_count"], 2)
                self.assertEqual(len(result["raid"]["volumes"]), 2)
                self.assertEqual(result["raid"]["volumes"][0]["state"], state)

    async def test_diagnostics_missing_and_unknown_fields(self):
        xml = """<config><mystery><value>7</value></mystery>
          <hd_status><disk>unknown</disk><detail source="wd">kept</detail></hd_status><raid>
          <item id="9"><state>reshape</state><progress>42</progress></item>
          <vendor_flag>enabled</vendor_flag></raid></config>"""
        result = await self.make_client(FakeResponse(text=xml)).diagnostics()
        self.assertIsNone(result["board_temperature"])
        self.assertEqual(result["disk_statuses"], ["unknown"])
        self.assertEqual(
            result["disk_status_extra"]["detail"],
            {"value": "kept", "attributes": {"source": "wd"}},
        )
        self.assertEqual(result["extra"]["mystery"], {"value": 7})
        self.assertEqual(result["raid"]["extra"]["vendor_flag"], "enabled")
        self.assertEqual(result["raid"]["volumes"][0]["extra"]["progress"], 42)

    async def test_capacity_usage_one_and_multiple_volumes(self):
        xml = """<config>
          <item><volume>1</volume><total_size>1918590988</total_size>
            <use_size>1918589500</use_size><free_size>1488</free_size><used_rate>100</used_rate>
            <Shared_Pictures>10</Shared_Pictures><Shared_Music>20</Shared_Music>
            <Shared_Videos>30</Shared_Videos><other>kept</other></item>
          <item><volume>2</volume><total_size>1000</total_size>
            <use_size>250</use_size><free_size>750</free_size><used_rate>25</used_rate></item>
        </config>"""
        nas = self.make_client(FakeResponse(text=xml))
        result = await nas.capacity_usage()
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["total_size"], 1918590988)
        self.assertEqual(result[0]["used_size"], 1918589500)
        self.assertEqual(result[0]["free_size"], 1488)
        self.assertEqual(result[0]["shared_pictures"], 10)
        self.assertEqual(result[0]["extra"], {"other": "kept"})
        self.assertEqual(result[1]["used_rate"], 25)
        self.assertIsNone(result[1]["shared_videos"])

    async def test_usb_success_false_is_returned_and_get_is_used(self):
        nas = self.make_client(FakeResponse(text='{"success": false}'))
        result = await nas.usb_info()
        self.assertEqual(result, {"success": False})
        self.assertEqual(nas.session.calls[0][0], "GET")

    async def test_uptime_http_500_raises_compatible_exception(self):
        nas = self.make_client(FakeResponse(status=500))
        with self.assertRaises(UptimeUnavailableError) as caught:
            await nas.uptime()
        self.assertIsInstance(caught.exception, RequestFailedError)
        self.assertEqual(caught.exception.status_code, 500)

    async def test_uptime_other_server_error_remains_request_failed(self):
        nas = self.make_client(FakeResponse(status=503, text="Service unavailable"))
        with self.assertRaises(RequestFailedError) as caught:
            await nas.uptime()
        self.assertNotIsInstance(caught.exception, UptimeUnavailableError)

    async def test_existing_system_status_parser(self):
        xml = """<config><cpu>12%</cpu><mem_total>1024</mem_total>
          <mem_free>256</mem_free><mem2_total>1 GB</mem2_total></config>"""
        result = await self.make_client(FakeResponse(text=xml)).system_status()
        self.assertEqual(
            result,
            {
                "memory": {"total": 1024, "unused": 256, "simple": "1 GB"},
                "cpu": 12,
            },
        )

    async def test_existing_uptime_parser(self):
        xml = "<config><uptime>2 days 3 hours 4 minutes</uptime></config>"
        result = await self.make_client(FakeResponse(text=xml)).uptime()
        self.assertEqual(result, 183840)

    async def test_volume_status_raid1_ext4_and_sensitive_metadata(self):
        xml = """<config><volume_info><item>
          <volume>1</volume><raid_mode>raid1</raid_mode><raid_status>0</raid_status>
          <file_type>ext4</file_type><size>1918590988</size><used_size>100</used_size>
          <free_size>1918590888</free_size><percentage>1</percentage>
          <device>sdasdb</device><dev_num>2</dev_num><mount>/mnt/HD/HD_a2</mount>
          <mount_status>mounted</mount_status><volume_encrypt>0</volume_encrypt>
          <raid_uuid>sensitive-uuid</raid_uuid><scsi0_serial>sensitive-serial</scsi0_serial>
          <vendor_field>kept</vendor_field></item></volume_info></config>"""
        nas = self.make_client(FakeResponse(text=xml))
        result = await nas.volume_status()
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["raid_mode"], "raid1")
        self.assertEqual(result[0]["raid_status"], 0)
        self.assertEqual(result[0]["file_type"], "ext4")
        self.assertEqual(result[0]["dev_num"], 2)
        self.assertEqual(result[0]["mount_status"], "mounted")
        self.assertEqual(result[0]["volume_encrypt"], 0)
        self.assertEqual(result[0]["raid_uuid"], "sensitive-uuid")
        self.assertEqual(result[0]["scsi0_serial"], "sensitive-serial")
        self.assertEqual(result[0]["extra"], {"vendor_field": "kept"})
        self.assertEqual(nas.session.calls[0][0], "GET")

    async def test_volume_status_multiple_missing_and_unknown_raid_status(self):
        xml = """<config><volume_info>
          <item><volume>1</volume><raid_status>vendor-state</raid_status></item>
          <item><volume>2</volume><raid_mode>jbod</raid_mode></item>
        </volume_info></config>"""
        result = await self.make_client(FakeResponse(text=xml)).volume_status()
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["raid_status"], "vendor-state")
        self.assertIsNone(result[0]["file_type"])
        self.assertEqual(result[1]["volume"], 2)

    async def test_volume_status_accepts_volume_info_as_document_root(self):
        xml = "<volume_info><item><volume>7</volume></item></volume_info>"
        result = await self.make_client(FakeResponse(text=xml)).volume_status()
        self.assertEqual(result[0]["volume"], 7)

    async def test_system_warning_known_and_unknown_codes(self):
        expected = {
            0: "normal",
            1: "over_temperature",
            2: "system_busy_hotplug",
            99: "unknown",
        }
        for code, status in expected.items():
            with self.subTest(code=code):
                nas = self.make_client(
                    FakeResponse(text=f"<config><res>{code}</res></config>")
                )
                self.assertEqual(
                    await nas.system_warning(), {"code": code, "status": status}
                )

    async def test_internet_access_true_and_false(self):
        for value, expected in (("true", True), ("FALSE", False)):
            with self.subTest(value=value):
                xml = f"<internet_access><connectivity>{value}</connectivity></internet_access>"
                result = await self.make_client(
                    FakeResponse(text=xml)
                ).internet_access()
                self.assertIs(result, expected)

    async def test_internet_access_missing_or_unknown_is_not_false(self):
        for xml in (
            "<internet_access/>",
            "<internet_access><connectivity>unknown</connectivity></internet_access>",
        ):
            with self.subTest(xml=xml), self.assertRaises(ValueError):
                await self.make_client(FakeResponse(text=xml)).internet_access()

    async def test_process_info_empty_and_multiple(self):
        empty = await self.make_client(FakeResponse(text="<xml/>")).process_info()
        self.assertEqual(empty, [])

        xml = """<xml>
          <process_main><command>alpha</command><user>root</user><pid>12</pid>
            <cpu>28.1</cpu><mem>1524</mem></process_main>
          <process_main><command>beta</command><pid>13</pid><cpu>0</cpu></process_main>
        </xml>"""
        nas = self.make_client(FakeResponse(text=xml))
        result = await nas.process_info()
        self.assertEqual(
            result[0],
            {
                "command": "alpha",
                "user": "root",
                "pid": 12,
                "cpu": 28.1,
                "mem": 1524,
                "extra": {},
            },
        )
        self.assertIsNone(result[1]["user"])
        self.assertIsNone(result[1]["mem"])
        self.assertEqual(nas.session.calls[0][2]["data"], "cmd=cgi_process")

    async def test_process_info_preserves_bad_numeric_values(self):
        xml = """<xml><process_main><pid>not-a-pid</pid><cpu>busy</cpu>
          <mem>unknown</mem><vendor>kept</vendor></process_main></xml>"""
        result = await self.make_client(FakeResponse(text=xml)).process_info()
        self.assertEqual(result[0]["pid"], "not-a-pid")
        self.assertEqual(result[0]["cpu"], "busy")
        self.assertEqual(result[0]["mem"], "unknown")
        self.assertEqual(result[0]["extra"], {"vendor": "kept"})

    async def test_extended_system_status_preserves_legacy_fields(self):
        xml = """<xml><bonding>0</bonding><buffers>31360</buffers>
          <cached>220544</cached><cpu>4%</cpu><lan_r_speed>13191338173</lan_r_speed>
          <lan_t_speed>11278793837</lan_t_speed><lan2_r_speed>3</lan2_r_speed>
          <lan2_t_speed>4</lan2_t_speed><mem_total>509780</mem_total>
          <mem2_total>512MB</mem2_total><mem_free>20500</mem_free>
          <now_time>1792870243</now_time><process_main/><process_main/>
          <vendor_resource>kept</vendor_resource></xml>"""
        result = await self.make_client(FakeResponse(text=xml)).system_status()
        self.assertEqual(result["cpu"], 4)
        self.assertEqual(result["memory"]["total"], 509780)
        self.assertEqual(result["memory"]["unused"], 20500)
        self.assertEqual(result["memory"]["simple"], "512MB")
        self.assertEqual(result["memory"]["buffers"], 31360)
        self.assertEqual(result["memory"]["cached"], 220544)
        self.assertEqual(result["network"]["lan"]["received_raw"], 13191338173)
        self.assertEqual(result["network"]["lan2"]["transmitted_raw"], 4)
        self.assertEqual(result["bonding"], 0)
        self.assertEqual(result["now_time"], 1792870243)
        self.assertEqual(result["process_count"], 2)
        self.assertEqual(result["extra"], {"vendor_resource": "kept"})

    async def test_new_methods_http_errors(self):
        for method_name in (
            "volume_status",
            "system_warning",
            "internet_access",
            "process_info",
        ):
            with self.subTest(method=method_name):
                nas = self.make_client(FakeResponse(status=503))
                with self.assertRaises(RequestFailedError):
                    await getattr(nas, method_name)()

    async def test_new_methods_invalid_xml(self):
        for method_name in (
            "volume_status",
            "system_warning",
            "internet_access",
            "process_info",
        ):
            with self.subTest(method=method_name):
                nas = self.make_client(FakeResponse(text="<invalid"))
                with self.assertRaises(ElementTree.ParseError):
                    await getattr(nas, method_name)()

    async def test_new_methods_are_os5_only(self):
        for method_name in (
            "volume_status",
            "system_warning",
            "internet_access",
            "process_info",
        ):
            with self.subTest(method=method_name):
                nas = self.make_client(FakeResponse(), version=2)
                with self.assertRaises(ValueError):
                    await getattr(nas, method_name)()
                self.assertEqual(nas.session.calls, [])

    async def test_reboot_runs_safety_check_then_action(self):
        nas = self.make_power_client(
            [FakeResponse(text="<config><res>0</res></config>"), FakeResponse()]
        )
        await nas.reboot()
        self.assertEqual(
            [call[2]["data"] for call in nas.session.calls],
            ["cmd=cgi_Detect_Dangerous", "cmd=cgi_restart"],
        )

    async def test_shutdown_runs_safety_check_then_action(self):
        nas = self.make_power_client(
            [FakeResponse(text="<config><res>0</res></config>"), FakeResponse()]
        )
        await nas.shutdown()
        self.assertEqual(nas.session.calls[1][2]["data"], "cmd=cgi_shutdown")

    async def test_v4_reboot_uses_confirmed_put_and_existing_session(self):
        nas = self.make_client(FakeResponse(text="<shutdown/>"), version=4)
        nas._authenticated = True
        nas.session.cookie_jar.update_cookies({"V4SESSION": "existing-session"})

        await nas.reboot()

        self.assertEqual(len(nas.session.calls), 1)
        method, url, kwargs = nas.session.calls[0]
        self.assertEqual(
            (method, url),
            ("PUT", "http://nas.local/api/2.1/rest/shutdown"),
        )
        self.assertEqual(kwargs["params"], {"state": "reboot"})
        self.assertEqual(kwargs["data"], {"state": "reboot"})
        self.assertEqual(nas.session.sent_cookies[0]["V4SESSION"], "existing-session")

    async def test_v4_shutdown_uses_confirmed_put_without_login(self):
        nas = self.make_client(FakeResponse(text="<shutdown/>"), version=4)
        nas._authenticated = True

        await nas.shutdown()

        self.assertEqual(len(nas.session.calls), 1)
        method, url, kwargs = nas.session.calls[0]
        self.assertEqual(
            (method, url),
            ("PUT", "http://nas.local/api/2.1/rest/shutdown"),
        )
        self.assertEqual(kwargs["params"], {"state": "halt"})
        self.assertEqual(kwargs["data"], {"state": "halt"})

    async def test_v4_power_disconnect_is_ambiguous_and_never_retried(self):
        class DisconnectResponse:
            async def __aenter__(self):
                raise aiohttp.ServerDisconnectedError()

            async def __aexit__(self, exc_type, exc, traceback):
                return False

        nas = self.make_client(DisconnectResponse(), version=4)
        nas._authenticated = True

        with self.assertRaises(aiohttp.ServerDisconnectedError):
            await nas.reboot()

        self.assertEqual(len(nas.session.calls), 1)
        self.assertEqual(nas.session.calls[0][0], "PUT")

    async def test_v4_power_timeout_is_ambiguous_and_never_retried(self):
        class SlowResponse:
            async def __aenter__(self):
                await asyncio.Event().wait()

            async def __aexit__(self, exc_type, exc, traceback):
                return False

        nas = self.make_client(SlowResponse(), version=4)
        nas._authenticated = True

        with (
            patch("wdnas_client.v4.POWER_ACTION_TIMEOUT", 0.01),
            self.assertRaises(TimeoutError),
        ):
            await nas.shutdown()

        self.assertEqual(len(nas.session.calls), 1)
        self.assertEqual(nas.session.calls[0][0], "PUT")

    async def test_v4_power_action_requires_existing_authenticated_session(self):
        nas = self.make_client(FakeResponse(), version=4)

        with self.assertRaises(InvalidLoginError):
            await nas.reboot()

        self.assertEqual(nas.session.calls, [])

    async def test_power_action_is_blocked_before_action_request(self):
        nas = self.make_power_client(FakeResponse(text="<config><res>2</res></config>"))
        with self.assertRaises(PowerActionBlockedError):
            await nas.reboot()
        self.assertEqual(len(nas.session.calls), 1)

    async def test_power_action_accepts_only_server_disconnect(self):
        class DisconnectResponse:
            async def __aenter__(self):
                raise aiohttp.ServerDisconnectedError()

            async def __aexit__(self, exc_type, exc, traceback):
                return False

        nas = self.make_power_client(
            [
                FakeResponse(text="<config><res>0</res></config>"),
                DisconnectResponse(),
            ]
        )
        await nas.reboot()

        nas = self.make_power_client(
            [
                FakeResponse(text="<config><res>0</res></config>"),
                FakeResponse(status=503),
            ]
        )
        with self.assertRaises(RequestFailedError):
            await nas.reboot()

    async def test_power_actions_remain_unsupported_for_os2(self):
        for method_name in ("reboot", "shutdown"):
            with self.subTest(method=method_name):
                nas = self.make_client(FakeResponse(), version=2)
                with self.assertRaises(ValueError):
                    await getattr(nas, method_name)()
                self.assertEqual(nas.session.calls, [])

    async def test_power_action_rejects_unexpected_safety_responses(self):
        for xml in (
            "<config/>",
            "<config><res>busy</res></config>",
            "<invalid",
        ):
            with self.subTest(xml=xml):
                nas = self.make_power_client(FakeResponse(text=xml))
                with self.assertRaises((TypeError, ElementTree.ParseError)):
                    await nas.reboot()
                self.assertEqual(len(nas.session.calls), 1)

    async def test_power_action_timeout_never_sends_action(self):
        class SlowSafetyResponse:
            async def __aenter__(self):
                await asyncio.Event().wait()

            async def __aexit__(self, exc_type, exc, traceback):
                return False

        nas = self.make_power_client(SlowSafetyResponse())
        with (
            patch("wdnas_client.POWER_ACTION_TIMEOUT", 0.01),
            self.assertRaises(TimeoutError),
        ):
            await nas.reboot()
        self.assertEqual(len(nas.session.calls), 1)

    async def test_confirmed_power_action_timeout_is_never_retried(self):
        class SlowActionResponse:
            async def __aenter__(self):
                await asyncio.Event().wait()

            async def __aexit__(self, exc_type, exc, traceback):
                return False

        nas = self.make_power_client(
            [
                FakeResponse(text="<config><res>0</res></config>"),
                SlowActionResponse(),
            ]
        )
        with (
            patch("wdnas_client.POWER_ACTION_TIMEOUT", 0.01),
            self.assertRaises(TimeoutError),
        ):
            await nas.shutdown()

        self.assertEqual(
            [call[2]["data"] for call in nas.session.calls],
            ["cmd=cgi_Detect_Dangerous", "cmd=cgi_shutdown"],
        )

    async def test_power_action_accepts_open_session_without_cookie(self):
        nas = self.make_client(FakeResponse(text="<config><res>0</res></config>"))
        await nas.reboot()
        self.assertEqual(
            [call[2]["data"] for call in nas.session.calls],
            ["cmd=cgi_Detect_Dangerous", "cmd=cgi_restart"],
        )

    async def test_power_action_does_not_trust_or_require_phpsessid_attribute(self):
        nas = self.make_client(FakeResponse(text="<config><res>0</res></config>"))
        nas.phpsessid = "attribute-only-session"

        await nas.reboot()

        self.assertEqual(len(nas.session.calls), 2)

    async def test_power_action_rejects_missing_or_closed_http_session(self):
        missing = client("Admin", "secret", "nas.local", 5)
        with self.assertRaises(InvalidLoginError):
            await missing.reboot()

        closed = self.make_power_client(FakeResponse())
        closed.session.closed = True
        with self.assertRaises(InvalidLoginError):
            await closed.shutdown()
        self.assertEqual(closed.session.calls, [])

    async def test_power_safety_http_error_never_sends_action(self):
        nas = self.make_power_client(FakeResponse(status=401))
        with self.assertRaises(RequestFailedError) as caught:
            await nas.shutdown()
        self.assertEqual(caught.exception.status_code, 401)
        self.assertEqual(len(nas.session.calls), 1)


if __name__ == "__main__":
    unittest.main()
