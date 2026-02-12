from dotenv import load_dotenv
import os
from urllib import request as open_web
import time
import features
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CallbackQueryHandler, ContextTypes, filters
import asyncio
import signal
import sys

load_dotenv()
api_key = os.getenv("API_KEY")
# Initialize the bot application using python-telegram-bot
app = (
    ApplicationBuilder()
    .token(api_key)
    .connect_timeout(30)  # Time to establish connection
    .read_timeout(30)    # Time to wait for data
    .build()
)
feature = features.Features(app.bot)  # Pass the bot instance to features
Commands_slash = ['/ai', '/non_ai']


# Updated handlers for python-telegram-bot
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming messages"""
    message = update.message
    if not message:
        return

    chat_id = message.chat_id
    first_name = message.from_user.first_name if message.from_user.first_name else ""
    last_name = message.from_user.last_name if message.from_user.last_name else ""

    # Convert message to the format expected by features
    msg_dict = {
        'chat': {
            'id': chat_id,
            'first_name': first_name,
            'last_name': last_name
        },
        'message_id': message.message_id
    }

    # Handle different message types
    if message.text:
        msg_dict['text'] = message.text
        key = 'text'
    elif message.voice:
        msg_dict['voice'] = {'file_id': message.voice.file_id}
        key = 'voice'
    elif message.photo:
        # Take the largest photo
        photo = message.photo[-1]
        msg_dict['photo'] = [{'file_id': photo.file_id}
                             for photo in message.photo]
        key = 'photo'
    elif message.video:
        msg_dict['video'] = {'file_id': message.video.file_id}
        key = 'video'
    elif message.document:
        msg_dict['document'] = {
            'file_id': message.document.file_id,
            'file_name': message.document.file_name
        }
        key = 'document'
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
                        text="Chat bot is disabled. Please enable it to use this feature."
                    )
                    return
                # Set chat mode to AI
                feature.set_chat_mode(chat_id, True)
                await context.bot.send_message(chat_id=chat_id, text="Chat mode set to AI.")
            elif command == Commands_slash[1]:
                # Set chat mode to non-AI
                feature.set_chat_mode(chat_id, False)
                await context.bot.send_message(chat_id=chat_id, text="Chat mode set to non-AI.")
        else:
            name = f'{first_name} {last_name}'
            print(name)
            print('Received:', command, 'chat_id', chat_id)
            authorized = False
            print(feature.random)
            if feature.pending == 0 or chat_id != feature.aut_chat_id:
                for i in feature.auth_list['authorized']:
                    if i['chat_id'] == chat_id:
                        authorized = True
                        break
                if authorized:
                    list_command = command.split()
                    try:
                        await feature.execute_chat_command_async(
                            chat_id, command, list_command, first_name, last_name, context)
                    except Exception as e:
                        print(e)
                        await context.bot.send_message(
                            chat_id=chat_id, text=f"Error executing command: {str(e)}")
                else:
                    await feature.send_first_auth_code_async(chat_id, name, context)
            else:
                await feature.receive_auth_code_async(name, chat_id, command, context)
    elif key in ["voice", "photo", "video", "document"]:
        # Create a minimal message dict for download_file compatibility
        msg_for_download = {
            'chat': {'id': chat_id},
            'message_id': message.message_id
        }

        if key == "voice":
            msg_for_download['voice'] = {'file_id': message.voice.file_id}
        elif key == "photo":
            msg_for_download['photo'] = [
                {'file_id': photo.file_id} for photo in message.photo]
        elif key == "video":
            msg_for_download['video'] = {'file_id': message.video.file_id}
        elif key == "document":
            msg_for_download['document'] = {
                'file_id': message.document.file_id,
                'file_name': message.document.file_name
            }

        speach_recon, command = await feature.download_file_async(msg_for_download, key, update, context)

        if speach_recon is True:
            name = f'{first_name} {last_name}'
            list_command = command.split()
            try:
                await feature.execute_chat_command_async(
                    chat_id, command, list_command, first_name, last_name, context)
            except Exception as e:
                print(e)
                await context.bot.send_message(
                    chat_id=chat_id, text=f"Error executing command: {str(e)}"
                )


async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle callback queries from inline keyboards"""
    query = update.callback_query
    await query.answer()  # Acknowledge the callback query

    # Create a message-like dict for compatibility with existing code
    msg_dict = {
        'data': query.data,
        'message': {
            'chat': {
                'id': query.message.chat_id,
                'first_name': query.from_user.first_name if query.from_user.first_name else "",
                'last_name': query.from_user.last_name if query.from_user.last_name else ""
            }
        }
    }

    await feature.reply_button_async(msg_dict, context)


async def start_bot():
    """Start the bot"""
    # Add handlers
    app.add_handler(MessageHandler(filters.TEXT | filters.VOICE |
                    filters.PHOTO | filters.VIDEO | filters.Document.ALL, handle_message))
    app.add_handler(CallbackQueryHandler(handle_callback_query))

    # Send test message
    await feature.test_message_async(app.bot)
    # Start the bot
    await app.initialize()
    await app.start()
    print("Bot started...")

    # Run the bot until interrupted
    async with app:
        await app.updater.start_polling()
        # Keep the bot running
        while True:
            await asyncio.sleep(1)


def signal_handler(sig, frame):
    print('Stopping bot...')
    sys.exit(0)


if __name__ == '__main__':
    # Handle Ctrl+C gracefully
    signal.signal(signal.SIGINT, signal_handler)

    # Connect to the internet
    connected = False
    while not connected:
        try:
            x = open_web.urlopen('https://google.com/')
            connected = True
        except Exception:
            connected = False
            time.sleep(1)

    print(feature.auth_list)

    # Run the bot
    asyncio.run(start_bot())
