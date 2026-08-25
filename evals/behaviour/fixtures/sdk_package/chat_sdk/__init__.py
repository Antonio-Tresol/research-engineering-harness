"""chat_sdk: a chat-completions client (offline build).

Quickstart:

    from chat_sdk import complete
    completion = complete("hello")
"""

from ._version import __version__
from .client import Client, complete
from .exceptions import ChatSDKError
from .models import Choice, Completion, ContentBlock, Message, Usage

__all__ = [
    "__version__",
    "Client",
    "ChatSDKError",
    "Choice",
    "Completion",
    "ContentBlock",
    "Message",
    "Usage",
    "complete",
]
