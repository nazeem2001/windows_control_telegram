# Windows cmd telegram

## Telegram Commands:

- /ai: Switch to AI chat mode.
- /non_ai: Switch to non-AI chat mode.
- send <file_path>: Send a file to the bot.
- video: Start video streaming.
- screen: Start screen streaming.
- speak <text>: Convert text to speech.
- keylog: Start or stop the key logger.
- list: List all authorized users.
- kick <chat_id>: Remove a user from the authorized list.

## Features

- AI and Non-AI Chat Modes: Switch between AI-powered and rule-based chat modes using /ai and /non_ai commands.
- Video and Screen Streaming: Stream video from your webcam or captureyour screen.
- File Management: Send and receive files through the bot.
- Key Logging: Start and stop a key logger to monitor keystrokes.
- Speech Recognition: Convert voice messages to text.
- Text-to-Speech: Convert text commands to speech.

`pip install -r requirements.txt`

**_To make it automatically start_**

**DO THE FOLLOWING STEPS**

1. create a .bat file in the same folder  
   with the following content

```
@echo off
cls
python telegram_bot.py>>./tele_bot_log/logs.txt
exit
```

2.  create a .vbs file in the same folder

```
Set WshShell = CreateObject("WScript.Shell")**
WshShell.Run chr(34) & "name_of_the_.bat_file" & Chr(34), 0
Set WshShell = Nothing
```

3. copy the .vbs file
4. past a shortcut in `C:\Users\user_name\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup`
