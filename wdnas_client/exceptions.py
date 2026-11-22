
class InvalidLoginError(Exception):
    pass

class RequestFailedError(Exception):
    def __init__(self, status_code):
        self.message = f"Request failed: {status_code}"
        super().__init__(self.message)


class PowerActionBlockedError(Exception):
    """Raised when the NAS reports that a power action is unsafe."""

    def __init__(self, status_code):
        self.status_code = status_code
        super().__init__(
            f"NAS power action blocked by cgi_Detect_Dangerous: {status_code}"
        )
