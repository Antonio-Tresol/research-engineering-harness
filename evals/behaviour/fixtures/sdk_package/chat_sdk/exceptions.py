"""Error hierarchy for chat_sdk."""


class ChatSDKError(Exception):
    """Base class for every error this package raises."""


class APIConnectionError(ChatSDKError):
    pass


class APITimeoutError(APIConnectionError):
    pass


class APIStatusError(ChatSDKError):
    def __init__(self, message: str, *, status_code: int) -> None:
        super().__init__(message)
        self.status_code = status_code


class AuthenticationError(APIStatusError):
    pass


class RateLimitError(APIStatusError):
    pass


class BadRequestError(APIStatusError):
    pass


class InternalServerError(APIStatusError):
    pass
