import discord
from types import SimpleNamespace
import features
from transport import TransportAdapter


class ConfirmView(discord.ui.View):
    """Discord View with Yes/No buttons (equivalent to Telegram InlineKeyboardMarkup)."""

    def __init__(self, feature: features.Features = None):
        super().__init__(timeout=12000)
        self.feature = feature

    def set_callback_data(self, interaction: discord.Interaction):

        if (
            f"dc:{interaction.message.channel.id}" in self.feature.nlp_classifier_output
            and self.feature.nlp_classifier_output[
                f"dc:{interaction.message.channel.id}"
            ]
        ):
            return {
                "data": "",
                "message": {
                    "chat": {
                        "id": f"dc:{interaction.message.channel.id}",  # interaction.message.channel.id,
                        "first_name": "first_name",
                        "last_name": "last_name",
                    }
                },
            }
        return None

    @discord.ui.button(label="Yes", style=discord.ButtonStyle.success, custom_id="yes")
    async def yes_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        try:
            dc_context = SimpleNamespace(bot=self.feature.dc_transport)

            msg = self.set_callback_data(interaction)
            msg["data"] = "yes"

            original_transport = self.feature.transport
            self.feature.transport = self.feature.dc_transport

            await self.feature.reply_button_async(msg, dc_context)
        finally:
            if original_transport:
                self.feature.transport = original_transport

    @discord.ui.button(label="No", style=discord.ButtonStyle.danger, custom_id="no")
    async def no_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
      
        try:
            dc_context = SimpleNamespace(bot=self.feature.dc_transport)

            msg = self.set_callback_data(interaction)
            msg["data"] = "no"

            original_transport = self.feature.transport
            self.feature.transport = self.feature.dc_transport

            await self.feature.reply_button_async(msg, dc_context)
        finally:
            if original_transport:
                self.feature.transport = original_transport


class CommandDropdown(discord.ui.Select):
    """Dropdown select menu (equivalent to Telegram ReplyKeyboardMarkup)."""

    def __init__(self, options_map: dict, feature_instance: features.Features = None):
        options = [
            discord.SelectOption(label=label, value=value)
            for label, value in options_map.items()
        ]
        super().__init__(
            placeholder="Select a command...",
            options=options,
            custom_id="command_select",
        )
        self.feature = feature_instance

    async def callback(self, interaction: discord.Interaction):
        try:
            dc_context = SimpleNamespace(bot=self.feature.dc_transport)

            original_transport = self.feature.transport
            self.feature.transport = self.feature.dc_transport

            await self.feature.execute_chat_command_async(
                f"dc:{interaction.message.channel.id}",
                self.values[0],
                [self.values[0]],
                "first_name",
                "last_name",
                dc_context,
            )
        finally:
            if original_transport:
                self.feature.transport = original_transport


class CommandDropdownView(discord.ui.View):
    """View that wraps a CommandDropdown select menu."""

    def __init__(self, options_map: dict, feature_instance: features.Features = None):
        super().__init__(timeout=120)
        self.add_item(CommandDropdown(options_map, feature_instance=feature_instance))


class DiscordTransport(TransportAdapter):
    """Wraps a discord.py Client as a TransportAdapter."""

    platform = "dc"

    def __init__(self, client: discord.Client):
        self.client = client

    def _resolve_channel(self, chat_id):
        """Resolve a channel ID, stripping any platform prefix."""
        raw_id = chat_id
        if isinstance(raw_id, str) and raw_id.startswith("dc:"):
            raw_id = int(raw_id.split(":", 1)[1])
        return self.client.get_channel(int(raw_id))

    def _convert_reply_markup(
        self, reply_markup, feature_instance: features.Features = None
    ):
        """Convert a Telegram reply_markup to a Discord View, or return None."""
        if reply_markup is None:
            return None

        # InlineKeyboardMarkup -> ConfirmView (yes/no buttons)
        from telegram import InlineKeyboardMarkup, ReplyKeyboardMarkup

        if isinstance(reply_markup, InlineKeyboardMarkup):
            return ConfirmView(feature=feature_instance)

        # ReplyKeyboardMarkup -> CommandDropdownView (select menu)
        if isinstance(reply_markup, ReplyKeyboardMarkup):
            options_map = {}
            for row in reply_markup.keyboard:
                for button in row:
                    label = button if isinstance(button, str) else button.text
                    options_map[label] = label
            return CommandDropdownView(options_map, feature_instance=feature_instance)

        return None

    async def send_message(
        self,
        chat_id,
        text,
        parse_mode=None,
        reply_markup=None,
        feature_instance: features.Features = None,
    ):
        channel = self._resolve_channel(chat_id)
        if channel:
            view = None
            if reply_markup:
                view = self._convert_reply_markup(reply_markup, feature_instance)
                await channel.send(content=text, view=view)
            else:
                print(f"Sending message to {chat_id}: {text} type: {type(text)}")
                await channel.send(text)

    async def send_photo(self, chat_id, photo):
        channel = self._resolve_channel(chat_id)
        if channel:
            if hasattr(photo, "read"):
                # file-like object (e.g. open("screen.png", "rb"))
                name = getattr(photo, "name", "image.png")
                await channel.send(file=discord.File(photo, name))
            else:
                await channel.send(file=discord.File(photo))

    async def send_document(self, chat_id, document):
        channel = self._resolve_channel(chat_id)
        if channel:
            if hasattr(document, "name"):
                await channel.send(file=discord.File(document, document.name))
            else:
                await channel.send(file=discord.File(document))

    async def send_voice(self, chat_id, voice):
        channel = self._resolve_channel(chat_id)
        if channel:
            if hasattr(voice, "read"):
                name = getattr(voice, "name", "voice.ogg")
                await channel.send(file=discord.File(voice, name))
            else:
                await channel.send(file=discord.File(voice))

    async def send_audio(self, chat_id, audio, caption=None, parse_mode=None):
        channel = self._resolve_channel(chat_id)
        if channel:
            content = caption or None
            if hasattr(audio, "read"):
                name = getattr(audio, "name", "audio.ogg")
                await channel.send(content=content, file=discord.File(audio, name))
            else:
                await channel.send(content=content, file=discord.File(audio))

    async def get_chat(self, chat_id):
        channel = self._resolve_channel(chat_id)
        if channel:
            return SimpleNamespace(
                first_name=getattr(channel, "name", "discord") or "discord",
                last_name="",
            )
        return SimpleNamespace(first_name="discord", last_name="")
