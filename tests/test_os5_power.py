"""Focused offline tests for guarded WD OS 5 power actions."""

import asyncio
import unittest
from collections import deque
from unittest.mock import patch
from xml.etree import ElementTree

import aiohttp

from wdnas_client import client
from wdnas_client.exceptions import (
    InvalidLoginError,
    PowerActionBlockedError,
    RequestFailedError,
)


class FakeResponse:
    """Minimal asynchronous response context manager."""

    def __init__(self, *, status=200, text=""):
        self.status = status
        self._text = text

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


class FakeSession:
    """Return deterministic responses and record outgoing requests."""

    def __init__(self, *responses):
        self.responses = deque(responses)
        self.calls = []
        self.closed = False

    def post(self, url, **kwargs):
        self.calls.append(("POST", url, kwargs))
        if not self.responses:
            raise AssertionError(f"Unexpected POST request to {url}")
        response = self.responses.popleft()
        if isinstance(response, BaseException):
            raise response
        return response


class OS5PowerTests(unittest.IsolatedAsyncioTestCase):
    """Exercise the source-confirmed preflight and power sequence."""

    @staticmethod
    def make_client(*responses, version=5):
        nas = client("admin", "secret", "nas.invalid", version)
        nas.session = FakeSession(*responses)
        return nas

    @staticmethod
    def allowed_response():
        return FakeResponse(text="<root><res>0</res></root>")

    def assert_power_calls(self, nas, command):
        headers = {
            "Host": "nas.invalid",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        }
        self.assertEqual(
            nas.session.calls,
            [
                (
                    "POST",
                    "http://nas.invalid/cgi-bin/hd_config.cgi",
                    {"data": "cmd=cgi_Detect_Dangerous", "headers": headers},
                ),
                (
                    "POST",
                    "http://nas.invalid/cgi-bin/system_mgr.cgi",
                    {"data": f"cmd={command}", "headers": headers},
                ),
            ],
        )

    async def test_successful_preflight_sends_one_reboot(self):
        nas = self.make_client(self.allowed_response(), FakeResponse())

        await nas.reboot()

        self.assert_power_calls(nas, "cgi_restart")

    async def test_successful_preflight_sends_one_shutdown(self):
        nas = self.make_client(self.allowed_response(), FakeResponse())

        await nas.shutdown()

        self.assert_power_calls(nas, "cgi_shutdown")

    async def test_blocked_preflight_never_sends_power_command(self):
        nas = self.make_client(FakeResponse(text="<root><res>7</res></root>"))

        with self.assertRaises(PowerActionBlockedError) as raised:
            await nas.reboot()

        self.assertEqual(raised.exception.status_code, 7)
        self.assertEqual(len(nas.session.calls), 1)

    async def test_malformed_or_unexpected_preflight_is_safe(self):
        responses = (
            "<root>",
            "<root></root>",
            "<root><res>unknown</res></root>",
        )
        for content in responses:
            with self.subTest(content=content):
                nas = self.make_client(FakeResponse(text=content))
                with self.assertRaises((ElementTree.ParseError, TypeError, ValueError)):
                    await nas.shutdown()
                self.assertEqual(len(nas.session.calls), 1)

    async def test_preflight_http_error_never_sends_power_command(self):
        nas = self.make_client(FakeResponse(status=503))

        with self.assertRaises(RequestFailedError):
            await nas.reboot()

        self.assertEqual(len(nas.session.calls), 1)

    async def test_preflight_timeout_is_not_retried(self):
        nas = self.make_client(SlowResponse())

        with (
            patch("wdnas_client.POWER_ACTION_TIMEOUT", 0.01),
            self.assertRaises(TimeoutError),
        ):
            await nas.reboot()

        self.assertEqual(len(nas.session.calls), 1)

    async def test_action_http_error_is_not_retried(self):
        nas = self.make_client(self.allowed_response(), FakeResponse(status=500))

        with self.assertRaises(RequestFailedError):
            await nas.shutdown()

        self.assert_power_calls(nas, "cgi_shutdown")

    async def test_action_timeout_is_not_retried(self):
        nas = self.make_client(self.allowed_response(), SlowResponse())

        with (
            patch("wdnas_client.POWER_ACTION_TIMEOUT", 0.01),
            self.assertRaises(TimeoutError),
        ):
            await nas.shutdown()

        self.assert_power_calls(nas, "cgi_shutdown")

    async def test_connection_loss_is_not_retried(self):
        nas = self.make_client(
            self.allowed_response(),
            aiohttp.ClientConnectionError("connection lost"),
        )

        with self.assertRaises(aiohttp.ClientConnectionError):
            await nas.reboot()

        self.assert_power_calls(nas, "cgi_restart")

    async def test_server_disconnect_after_command_is_accepted_without_retry(self):
        nas = self.make_client(
            self.allowed_response(),
            aiohttp.ServerDisconnectedError(),
        )

        await nas.reboot()

        self.assert_power_calls(nas, "cgi_restart")

    async def test_missing_or_closed_session_prevents_preflight(self):
        missing = client("admin", "secret", "nas.invalid", 5)
        with self.assertRaises(InvalidLoginError):
            await missing.reboot()

        closed = self.make_client(self.allowed_response())
        closed.session.closed = True
        with self.assertRaises(InvalidLoginError):
            await closed.shutdown()
        self.assertEqual(closed.session.calls, [])

    async def test_os2_rejects_power_actions_without_http_requests(self):
        nas = self.make_client(self.allowed_response(), version=2)

        with self.assertRaises(ValueError):
            await nas.reboot()
        with self.assertRaises(ValueError):
            await nas.shutdown()

        self.assertEqual(nas.session.calls, [])


if __name__ == "__main__":
    unittest.main()
