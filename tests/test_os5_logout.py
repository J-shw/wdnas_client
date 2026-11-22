"""Focused regression tests for safe WD OS 5 session cleanup."""

import asyncio
import unittest
from collections import deque
from http.cookies import SimpleCookie
from unittest.mock import patch

import aiohttp

from wdnas_client import client
from wdnas_client.exceptions import RequestFailedError

SYSTEM_INFO_XML = """\
<root>
  <disk id="0"><name>Disk 1</name><connected>1</connected><vendor>WD</vendor>
    <model>Example</model><rev>1</rev><sn>REDACTED</sn><size>1000</size>
    <failed>0</failed><healthy>1</healthy><removable>0</removable>
    <over_temp>0</over_temp><temp>35</temp><sleep>0</sleep></disk>
  <vol id="1"><name>Volume_1</name><label>Data</label><encrypted>0</encrypted>
    <unlocked>1</unlocked><mounted>1</mounted><size>900</size></vol>
  <total_size>1000</total_size><total_used_size>400</total_used_size>
  <total_unused_size>600</total_unused_size>
</root>
"""


class FakeHeaders(dict):
    """Mapping with aiohttp's getall helper."""

    def getall(self, key, default=None):
        value = self.get(key)
        if value is None:
            return [] if default is None else default
        return value if isinstance(value, list) else [value]


class FakeResponse:
    """Minimal asynchronous response context manager."""

    def __init__(self, *, status=200, text="", cookies=None, headers=None):
        self.status = status
        self._text = text
        self.cookies = SimpleCookie(cookies or {})
        self.headers = FakeHeaders(headers or {})

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False

    async def text(self):
        return self._text


class SlowResponse(FakeResponse):
    """Response whose context entry never completes by itself."""

    async def __aenter__(self):
        await asyncio.Event().wait()


class FakeCookieJar:
    """Store cookie updates made by the historical login implementation."""

    def __init__(self):
        self.cookies = {}

    def update_cookies(self, cookies):
        self.cookies.update(cookies)


class FakeSession:
    """Return deterministic responses and record outgoing requests."""

    def __init__(self, *responses, delete_error=None):
        self.responses = deque(responses)
        self.delete_error = delete_error
        self.calls = []
        self.cookie_jar = FakeCookieJar()
        self.closed = False
        self.close_calls = 0

    def _request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        if method == "DELETE" and self.delete_error is not None:
            raise self.delete_error
        if not self.responses:
            raise AssertionError(f"Unexpected {method} request to {url}")
        return self.responses.popleft()

    def get(self, url, **kwargs):
        return self._request("GET", url, **kwargs)

    def post(self, url, **kwargs):
        return self._request("POST", url, **kwargs)

    def delete(self, url, **kwargs):
        return self._request("DELETE", url, **kwargs)

    async def close(self):
        self.close_calls += 1
        self.closed = True


class OS5LogoutTests(unittest.IsolatedAsyncioTestCase):
    """Exercise OS 5 logout without physical NAS access."""

    @staticmethod
    def login_response(*, cookie=True, raw_cookie=False):
        cookies = {"PHPSESSID": "session-token"} if cookie else None
        headers = (
            {"Set-Cookie": ["PHPSESSID=session-token; Path=/"]} if raw_cookie else None
        )
        return FakeResponse(cookies=cookies, headers=headers)

    async def test_context_exit_sends_one_logout_without_new_login(self):
        session = FakeSession(self.login_response(), FakeResponse(status=204))

        with patch("wdnas_client.aiohttp.ClientSession", return_value=session):
            async with client("admin", "secret", "nas.invalid", 5):
                pass

        self.assertEqual(
            [call[:2] for call in session.calls],
            [
                ("POST", "http://nas.invalid/nas/v1/auth"),
                ("DELETE", "http://nas.invalid/nas/v1/auth"),
            ],
        )
        self.assertEqual(
            session.calls[1][2],
            {
                "headers": {
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    "Host": "nas.invalid",
                }
            },
        )
        self.assertTrue(session.closed)

    async def test_raw_login_cookie_is_ownership_evidence(self):
        session = FakeSession(
            self.login_response(cookie=False, raw_cookie=True),
            FakeResponse(status=204),
        )

        with patch("wdnas_client.aiohttp.ClientSession", return_value=session):
            async with client("admin", "secret", "nas.invalid", 5) as nas:
                self.assertIsNone(nas.phpsessid)

        self.assertEqual([call[0] for call in session.calls], ["POST", "DELETE"])

    async def test_protected_response_confirms_ownership_without_phpsessid(self):
        session = FakeSession(
            self.login_response(cookie=False),
            FakeResponse(text=SYSTEM_INFO_XML),
            FakeResponse(status=204),
        )

        with patch("wdnas_client.aiohttp.ClientSession", return_value=session):
            async with client("admin", "secret", "nas.invalid", 5) as nas:
                self.assertIsNone(nas.phpsessid)
                await nas.system_info()

        self.assertEqual([call[0] for call in session.calls], ["POST", "GET", "DELETE"])

    async def test_no_ownership_evidence_performs_local_cleanup_only(self):
        session = FakeSession(self.login_response(cookie=False))

        with patch("wdnas_client.aiohttp.ClientSession", return_value=session):
            async with client("admin", "secret", "nas.invalid", 5):
                pass

        self.assertEqual([call[0] for call in session.calls], ["POST"])
        self.assertTrue(session.closed)

    async def test_failed_protected_read_does_not_authorize_logout(self):
        session = FakeSession(
            self.login_response(cookie=False),
            FakeResponse(status=403),
        )
        nas = client("admin", "secret", "nas.invalid", 5)

        with patch("wdnas_client.aiohttp.ClientSession", return_value=session):
            await nas.__aenter__()
        with self.assertRaises(RequestFailedError):
            await nas.system_info()
        await nas.close()

        self.assertEqual([call[0] for call in session.calls], ["POST", "GET"])
        self.assertTrue(session.closed)

    async def test_failed_login_closes_locally_without_server_logout(self):
        session = FakeSession(FakeResponse(status=403))

        with (
            patch("wdnas_client.aiohttp.ClientSession", return_value=session),
            self.assertRaises(RequestFailedError),
        ):
            await client("admin", "secret", "nas.invalid", 5).__aenter__()

        self.assertEqual([call[0] for call in session.calls], ["POST"])
        self.assertTrue(session.closed)

    async def test_logout_http_error_closes_locally_and_is_not_retried(self):
        session = FakeSession(self.login_response(), FakeResponse(status=503))
        nas = client("admin", "secret", "nas.invalid", 5)

        with patch("wdnas_client.aiohttp.ClientSession", return_value=session):
            await nas.__aenter__()

        with self.assertRaises(RequestFailedError):
            await nas.close()
        with self.assertRaises(RequestFailedError):
            await nas.close()

        self.assertEqual([call[0] for call in session.calls], ["POST", "DELETE"])
        self.assertTrue(session.closed)

    async def test_logout_connection_failure_closes_and_is_not_retried(self):
        session = FakeSession(
            self.login_response(),
            delete_error=aiohttp.ClientConnectionError("logout failed"),
        )
        nas = client("admin", "secret", "nas.invalid", 5)

        with patch("wdnas_client.aiohttp.ClientSession", return_value=session):
            await nas.__aenter__()

        with self.assertRaises(aiohttp.ClientConnectionError):
            await nas.close()
        with self.assertRaises(aiohttp.ClientConnectionError):
            await nas.close()

        self.assertEqual([call[0] for call in session.calls], ["POST", "DELETE"])
        self.assertTrue(session.closed)

    async def test_logout_timeout_closes_and_is_not_retried(self):
        session = FakeSession(self.login_response(), SlowResponse())
        nas = client("admin", "secret", "nas.invalid", 5)

        with patch("wdnas_client.aiohttp.ClientSession", return_value=session):
            await nas.__aenter__()

        with (
            patch("wdnas_client.SESSION_ACTION_TIMEOUT", 0.01),
            self.assertRaises(TimeoutError),
        ):
            await nas.close()
        with self.assertRaises(TimeoutError):
            await nas.close()

        self.assertEqual([call[0] for call in session.calls], ["POST", "DELETE"])
        self.assertTrue(session.closed)

    async def test_repeated_cleanup_sends_one_logout(self):
        session = FakeSession(self.login_response(), FakeResponse(status=204))
        nas = client("admin", "secret", "nas.invalid", 5)

        with patch("wdnas_client.aiohttp.ClientSession", return_value=session):
            await nas.__aenter__()
        await nas.close()
        await nas.close()

        self.assertEqual([call[0] for call in session.calls], ["POST", "DELETE"])

    async def test_concurrent_cleanup_sends_one_logout(self):
        session = FakeSession(self.login_response(), FakeResponse(status=204))
        nas = client("admin", "secret", "nas.invalid", 5)

        with patch("wdnas_client.aiohttp.ClientSession", return_value=session):
            await nas.__aenter__()
        await asyncio.gather(nas.close(), nas.close(), nas.close())

        self.assertEqual([call[0] for call in session.calls], ["POST", "DELETE"])

    async def test_primary_context_exception_is_not_masked_by_logout_failure(self):
        session = FakeSession(self.login_response(), FakeResponse(status=503))

        with (
            patch("wdnas_client.aiohttp.ClientSession", return_value=session),
            self.assertRaisesRegex(RuntimeError, "primary failure"),
        ):
            async with client("admin", "secret", "nas.invalid", 5):
                raise RuntimeError("primary failure")

        self.assertTrue(session.closed)

    async def test_logout_without_open_session_is_safe(self):
        missing = client("admin", "secret", "nas.invalid", 5)
        await missing.logout()

        closed_session = FakeSession()
        closed_session.closed = True
        closed = client("admin", "secret", "nas.invalid", 5)
        closed.session = closed_session
        closed._server_session_owned = True
        await closed.logout()

        self.assertEqual(closed_session.calls, [])

    async def test_os2_context_lifecycle_remains_local_only(self):
        session = FakeSession(
            FakeResponse(
                cookies={
                    "PHPSESSID": "session-token",
                    "WD-CSRF-TOKEN": "csrf-token",
                }
            )
        )

        with patch("wdnas_client.aiohttp.ClientSession", return_value=session):
            async with client("admin", "secret", "nas.invalid", 2):
                pass

        self.assertEqual([call[0] for call in session.calls], ["POST"])
        self.assertTrue(session.closed)


if __name__ == "__main__":
    unittest.main()
