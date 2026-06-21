from transport import TransportAdapter


class TelegramTransport(TransportAdapter):
    """Wraps a python-telegram-bot Bot instance as a TransportAdapter."""

    platform = "tg"

    def __init__(self, bot):
        self.bot = bot

    async def send_message(self, chat_id, text, parse_mode=None, reply_markup=None,feature_instance=None):
        kwargs = {"chat_id": chat_id, "text": text}
        if parse_mode:
            kwargs["parse_mode"] = parse_mode
        if reply_markup:
            kwargs["reply_markup"] = reply_markup
        return await self.bot.send_message(**kwargs)

    async def send_photo(self, chat_id, photo):
        return await self.bot.send_photo(chat_id=chat_id, photo=photo)

    async def send_document(self, chat_id, document):
        return await self.bot.send_document(chat_id=chat_id, document=document)

    async def send_voice(self, chat_id, voice):
        return await self.bot.send_voice(chat_id=chat_id, voice=voice)

    async def send_audio(self, chat_id, audio, caption=None, parse_mode=None):
        kwargs = {"chat_id": chat_id, "audio": audio}
        if caption:
            kwargs["caption"] = caption
        if parse_mode:
            kwargs["parse_mode"] = parse_mode
        return await self.bot.send_audio(**kwargs)

    async def get_chat(self, chat_id):
        return await self.bot.get_chat(chat_id=chat_id)
