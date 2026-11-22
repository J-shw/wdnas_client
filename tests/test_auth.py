"""Regression tests for the existing API 2 and OS 5 login behavior."""

import base64
import unittest
from unittest.mock import patch

from tests.fakes import FakeResponse, FakeSession
from wdnas_client import client
from wdnas_client.exceptions import InvalidLoginError, RequestFailedError


class AuthenticationTests(unittest.IsolatedAsyncioTestCase):
    """Exercise existing authentication without network access."""

    def test_rejects_unsupported_api_version(self):
        with self.assertRaisesRegex(ValueError, "Must be 2 or 5"):
            client("admin", "secret", "nas.invalid", 4)

    async def test_api2_login_sends_encoded_credentials_and_stores_tokens(self):
        response = FakeResponse(
            cookies={"PHPSESSID": "session-token", "WD-CSRF-TOKEN": "csrf-token"},
            headers={
                "Set-Cookie": [
                    "PHPSESSID=session-token; Path=/",
                    "WD-CSRF-TOKEN=csrf-token; Path=/",
                ]
            },
        )
        session = FakeSession(response)
        nas = client("Admin", "secret", "nas.invalid", 2)
        nas.session = session

        await nas.login()

        expected_password = base64.b64encode(b"secret").decode()
        self.assertEqual(nas.username, "admin")
        self.assertEqual(nas.phpsessid, "session-token")
        self.assertEqual(nas.wd_csrf_token, "csrf-token")
        self.assertEqual(
            session.calls,
            [
                (
                    "POST",
                    "http://nas.invalid/cgi-bin/login_mgr.cgi",
                    {
                        "data": (
                            f"cmd=wd_login&username=admin&pwd={expected_password}"
                        ),
                        "headers": {
                            "Content-Type": (
                                "application/x-www-form-urlencoded; charset=UTF-8"
                            ),
                            "Host": "nas.invalid",
                        },
                    },
                )
            ],
        )

    async def test_api2_login_rejects_missing_required_cookies(self):
        nas = client("admin", "secret", "nas.invalid", 2)
        nas.session = FakeSession(FakeResponse(cookies={"PHPSESSID": "only-one"}))

        with self.assertRaises(InvalidLoginError):
            await nas.login()

    async def test_os5_login_sends_json_and_stores_session_cookie(self):
        response = FakeResponse(cookies={"PHPSESSID": "session-token"})
        session = FakeSession(response)
        nas = client("Admin", "secret", "nas.invalid", 5)
        nas.session = session

        await nas.login()

        self.assertEqual(nas.phpsessid, "session-token")
        self.assertEqual(
            session.calls[0],
            (
                "POST",
                "http://nas.invalid/nas/v1/auth",
                {
                    "json": {
                        "username": "admin",
                        "password": base64.b64encode(b"secret").decode(),
                    },
                    "headers": {
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                        "Host": "nas.invalid",
                    },
                },
            ),
        )

    async def test_os5_login_currently_accepts_200_without_session_cookie(self):
        """Document the existing permissive OS 5 behavior."""
        nas = client("admin", "secret", "nas.invalid", 5)
        nas.session = FakeSession(FakeResponse(status=200))

        await nas.login()

        self.assertIsNone(nas.phpsessid)

    async def test_login_raises_request_failed_for_http_error(self):
        nas = client("admin", "secret", "nas.invalid", 5)
        nas.session = FakeSession(FakeResponse(status=403))

        with self.assertRaises(RequestFailedError) as raised:
            await nas.login()

        self.assertIn("403", str(raised.exception))

    async def test_context_manager_creates_and_closes_session(self):
        session = FakeSession(FakeResponse(cookies={"PHPSESSID": "session-token"}))
        with patch("wdnas_client.aiohttp.ClientSession", return_value=session):
            async with client("admin", "secret", "nas.invalid", 5) as nas:
                self.assertIs(nas.session, session)
                self.assertFalse(session.closed)

        self.assertTrue(session.closed)


if __name__ == "__main__":
    unittest.main()
