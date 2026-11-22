"""Small aiohttp-compatible fakes used by the regression tests."""

from collections import deque
from http.cookies import SimpleCookie


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


class FakeCookieJar:
    """Record cookie updates without performing domain matching."""

    def __init__(self):
        self.cookies = {}

    def update_cookies(self, cookies):
        self.cookies.update(cookies)


class FakeSession:
    """Return deterministic responses and record outgoing requests."""

    def __init__(self, *responses):
        self.responses = deque(responses)
        self.calls = []
        self.cookie_jar = FakeCookieJar()
        self.closed = False

    def _request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        if not self.responses:
            raise AssertionError(f"Unexpected {method} request to {url}")
        return self.responses.popleft()

    def get(self, url, **kwargs):
        return self._request("GET", url, **kwargs)

    def post(self, url, **kwargs):
        return self._request("POST", url, **kwargs)

    async def close(self):
        self.closed = True
