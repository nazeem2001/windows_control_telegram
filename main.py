from dotenv import load_dotenv
import os
from urllib import request as open_web
import time
import features
from types import SimpleNamespace
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
import asyncio
import signal
import sys
import scheduler_manager
from transport import TransportAdapter
from telegram_transport import TelegramTransport

load_dotenv()
api_key = os.getenv("API_KEY")
discord_token = os.getenv("DISCORD_TOKEN")
# Initialize the bot application using python-telegram-bot
app = (
    ApplicationBuilder()
    .token(api_key)
    .connect_timeout(30)  # Time to establish connection
    .read_timeout(30)  # Time to wait for data
    .build()
)
import discord
from discord_transport import DiscordTransport

discord_ready = False
intents = discord.Intents.default()
intents.message_content = True
intents.presences = True
client = discord.Client(intents=intents)
dc_transport = DiscordTransport(client)

telegram_transport = TelegramTransport(app.bot)

feature = features.Features(
    app.bot, transport=telegram_transport, dc_transport=dc_transport
)  # Pass the bot instance to features
scheduler = scheduler_manager.SchedulerManager(feature)
feature.set_scheduler_manager(scheduler)
Commands_slash = ["/ai", "/non_ai"]


# Updated handlers for python-telegram-bot
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming messages"""
    message = update.message
    if not message:
        return

    # Wrap context so that context.bot is the transport adapter
    context = SimpleNamespace(bot=telegram_transport)

    chat_id = message.chat_id
    first_name = message.from_user.first_name if message.from_user.first_name else ""
    last_name = message.from_user.last_name if message.from_user.last_name else ""

    # Convert message to the format expected by features
    msg_dict = {
        "chat": {"id": chat_id, "first_name": first_name, "last_name": last_name},
        "message_id": message.message_id,
    }

    # Handle different message types
    if message.text:
        msg_dict["text"] = message.text
        key = "text"
    elif message.voice:
        msg_dict["voice"] = {"file_id": message.voice.file_id}
        key = "voice"
    elif message.photo:
        # Take the largest photo
        photo = message.photo[-1]
        msg_dict["photo"] = [{"file_id": photo.file_id} for photo in message.photo]
        key = "photo"
    elif message.video:
        msg_dict["video"] = {"file_id": message.video.file_id}
        key = "video"
    elif message.document:
        msg_dict["document"] = {
            "file_id": message.document.file_id,
            "file_name": message.document.file_name,
        }
        key = "document"
    else:
        return  # Unsupported message type

    # Process the message
    if key == "text":
        command = message.text
        if command in Commands_slash:
            if command == Commands_slash[0]:
                if not feature.chat_bot_enabled:
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text="Chat bot is disabled. Please enable it to use this feature.",
                    )
                    return
                # Set chat mode to AI
                feature.set_chat_mode(chat_id, True)
                await context.bot.send_message(
                    chat_id=chat_id, text="Chat mode set to AI."
                )
            elif command == Commands_slash[1]:
                # Set chat mode to non-AI
                feature.set_chat_mode(chat_id, False)
                await context.bot.send_message(
                    chat_id=chat_id, text="Chat mode set to non-AI."
                )
        else:
            name = f"{first_name} {last_name}"
            print(name)
            print("Received:", command, "chat_id", chat_id)
            authorized = False
            print(feature.random)
            if feature.pending == 0 or chat_id != feature.aut_chat_id:
                for i in feature.auth_list["authorized"]:
                    if i["chat_id"] == chat_id:
                        authorized = True
                        break
                if authorized:
                    list_command = command.split()
                    # try:
                    await feature.execute_chat_command_async(
                        chat_id,
                        command,
                        list_command,
                        first_name,
                        last_name,
                        context,
                    )
                    # except Exception as e:
                    #     print(e)
                    #     await context.bot.send_message(
                    #         chat_id=chat_id, text=f"Error executing command: {str(e)}"
                    # )
                else:
                    await feature.send_first_auth_code_async(chat_id, name, context)
            else:
                await feature.receive_auth_code_async(name, chat_id, command, context)
    elif key in ["voice", "photo", "video", "document"]:
        # Create a minimal message dict for download_file compatibility
        msg_for_download = {"chat": {"id": chat_id}, "message_id": message.message_id}

        if key == "voice":
            msg_for_download["voice"] = {"file_id": message.voice.file_id}
        elif key == "photo":
            msg_for_download["photo"] = [
                {"file_id": photo.file_id} for photo in message.photo
            ]
        elif key == "video":
            msg_for_download["video"] = {"file_id": message.video.file_id}
        elif key == "document":
            msg_for_download["document"] = {
                "file_id": message.document.file_id,
                "file_name": message.document.file_name,
            }

        speach_recon, command = await feature.download_file_async(
            msg_for_download, key, update, context
        )

        if speach_recon is True:
            name = f"{first_name} {last_name}"
            list_command = command.split()
            try:
                await feature.execute_chat_command_async(
                    chat_id,
                    command,
                    list_command,
                    first_name,
                    last_name,
                    context,
                    is_audio=True,
                )
            except Exception as e:
                print(e)
                await context.bot.send_message(
                    chat_id=chat_id, text=f"Error executing command: {str(e)}"
                )


async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle callback queries from inline keyboards"""
    query = update.callback_query
    await query.answer()  # Acknowledge the callback query

    # Wrap context so that context.bot is the transport adapter
    context = SimpleNamespace(bot=telegram_transport)

    # Create a message-like dict for compatibility with existing code
    msg_dict = {
        "data": query.data,
        "message": {
            "chat": {
                "id": query.message.chat_id,
                "first_name": (
                    query.from_user.first_name if query.from_user.first_name else ""
                ),
                "last_name": (
                    query.from_user.last_name if query.from_user.last_name else ""
                ),
            }
        },
    }

    await feature.reply_button_async(msg_dict, context)


async def start_discord(feature_instance):
    """Start the Discord bot alongside the Telegram bot."""

    # Patch feature to use Discord transport when handling Discord messages

    # We create a thin wrapper that temporarily swaps transport for Discord calls
    @client.event
    async def on_ready():
        global discord_ready
        discord_ready = True
        print(f"Discord bot logged in as {client.user}")

    @client.event
    async def on_message(message):
        if message.author == client.user:
            return
        print(
            f"Received message from Discord: {message.content} (channel: {message.channel.name})"
        )
        await client.change_presence(
            status=discord.Status.online,
            activity=discord.Activity(
                type=discord.ActivityType.listening, name="your commands!"
            ),
        )
        # Use "dc:" prefix to namespace Discord channel IDs away from Telegram
        chat_id = f"dc:{message.channel.id}"
        first_name = message.author.display_name or ""
        last_name = ""
        command = message.content
        list_command = command.split()

        # Create a context whose .bot is the Discord transport
        dc_context = SimpleNamespace(bot=dc_transport)

        # Temporarily swap feature's transport to Discord so that any
        # internal self.transport calls (e.g. save_file_in_fin) route
        # to the correct platform.
        original_transport = feature_instance.transport
        feature_instance.transport = dc_transport
        try:
            # Authorization check
            authorized = False
            if feature_instance.pending == 0 or chat_id != feature_instance.aut_chat_id:
                for u in feature_instance.auth_list["authorized"]:
                    if str(u["chat_id"]) == str(chat_id):
                        authorized = True
                        break
                if authorized:
                    if command in Commands_slash:
                        if command == Commands_slash[0]:
                            if not feature.chat_bot_enabled:
                                await dc_context.bot.send_message(
                                    chat_id=chat_id,
                                    text="Chat bot is disabled. Please enable it to use this feature.",
                                )
                                return
                            # Set chat mode to AI
                            feature.set_chat_mode(chat_id, True)
                            await dc_context.bot.send_message(
                                chat_id=chat_id, text="Chat mode set to AI."
                            )
                        elif command == Commands_slash[1]:
                            # Set chat mode to non-AI
                            feature.set_chat_mode(chat_id, False)
                            await dc_context.bot.send_message(
                                chat_id=chat_id, text="Chat mode set to non-AI."
                            )
                    else:
                        await feature_instance.execute_chat_command_async(
                            chat_id,
                            command,
                            list_command,
                            first_name,
                            last_name,
                            dc_context,
                        )
                else:
                    name = f"{first_name} {last_name}"
                    await feature_instance.send_first_auth_code_async(
                        chat_id, name, dc_context
                    )
            else:
                name = f"{first_name} {last_name}"
                await feature_instance.receive_auth_code_async(
                    name, chat_id, command, dc_context
                )
        finally:
            feature_instance.transport = original_transport
        await client.change_presence(
            status=discord.Status.online,
            activity=discord.Activity(
                type=discord.ActivityType.unknown, name="your commands!"
            ),
        )

    await client.start(discord_token)


async def _run_telegram(app):
    """Run Telegram bot with polling; isolate failures."""
    try:
        await app.initialize()
        await app.start()
        print("Telegram bot started.")
        await app.updater.start_polling()
        # Keep task alive while polling runs
        while True:
            await asyncio.sleep(60)
    except Exception as e:
        print(f"[Telegram] Failed: {e}")


async def _run_discord(feature, client, discord_token):
    """Run Discord bot; isolate failures."""
    try:
        await start_discord(feature)
    except Exception as e:
        print(f"[Discord] Failed: {e}")


async def start_bot():
    """Start the bot"""
    # Add handlers
    app.add_handler(
        MessageHandler(
            filters.TEXT
            | filters.VOICE
            | filters.PHOTO
            | filters.VIDEO
            | filters.Document.ALL,
            handle_message,
        )
    )
    app.add_handler(CallbackQueryHandler(handle_callback_query))

    scheduler.start()
    print("Scheduler loaded persisted reminders from reminders.json")

    tasks = []

    # Telegram task (isolated)
    tasks.append(_run_telegram(app))

    # Discord task (isolated)
    if discord_token:
        tasks.append(_run_discord(feature, client, discord_token))
        print("Discord bot starting alongside Telegram bot...")

    # Test message after Discord is ready (non-blocking)
    async def send_test_on_ready():
        try:
            if discord_token:
                await client.wait_until_ready()
            await feature.test_message_async()
        except Exception as e:
            print(f"[TestMessage] Failed: {e}")

    tasks.append(send_test_on_ready())

    try:
        await asyncio.gather(*tasks, return_exceptions=True)
        while True:
            await asyncio.sleep(1)
    finally:
        scheduler.shutdown()


def signal_handler(sig, frame):
    print("Stopping bot...")
    sys.exit(0)


if __name__ == "__main__":
    # Handle Ctrl+C gracefully
    signal.signal(signal.SIGINT, signal_handler)

    # Connect to the internet
    connected = False
    while not connected:
        try:
            x = open_web.urlopen("https://google.com/")
            connected = True
        except Exception:
            connected = False
            time.sleep(1)

    print(feature.auth_list)

    # Run the bot
    asyncio.run(start_bot())
