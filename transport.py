from abc import ABC, abstractmethod
from types import SimpleNamespace


class TransportAdapter(ABC):
    """
    Abstract base class for messaging platform adapters.
    All transport implementations must provide these methods so that
    Features / reminder_executor can send messages without knowing
    which platform is underneath.
    """

    platform: str = "unknown"

    @abstractmethod
    async def send_message(self, chat_id, text, parse_mode=None, reply_markup=None ,feature_instance=None):
        ...

    @abstractmethod
    async def send_photo(self, chat_id, photo):
        ...

    @abstractmethod
    async def send_document(self, chat_id, document):
        ...

    @abstractmethod
    async def send_voice(self, chat_id, voice):
        ...

    @abstractmethod
    async def send_audio(self, chat_id, audio, caption=None, parse_mode=None):
        ...

    @abstractmethod
    async def get_chat(self, chat_id):
        ...

    def make_context(self):
        """Return a minimal context-like object whose .bot is this transport."""
        return SimpleNamespace(bot=self)
