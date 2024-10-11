
class InvalidLoginError(Exception):
    pass

class RequestFailedError(Exception):
    def __init__(self, status_code):
        self.message = f"Request failed: {status_code}"
        super().__init__(self.message)