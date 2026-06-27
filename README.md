# Windows Command Telegram Bot

A remote-control bot for Windows that can be driven from Telegram or Discord, with optional AI assistance via LangChain and Ollama.

## Overview

This project combines a bot backend with local system tools so you can control a Windows machine remotely. It supports:

- Telegram and Discord transports
- AI chat mode with Ollama and LangChain
- Rule-based command mode with NLP confirmation
- Screen and webcam streaming, screenshots, keyboard input, and terminal execution
- Reminder scheduling and execution
- Authorized-user management and logging
- Optional tunnel support through ngrok or FRP

## Features

- AI-powered command handling in `/ai` mode
- Rule-based command execution in `/non_ai` mode
- Cross-platform messaging through Telegram and Discord
- File transfer and basic system interaction helpers
- Optional text-to-speech and media handling when the required tools are available
- Reminder creation using natural language
- FRP tunnel control via the `rdp` and `frpip` commands
- Authorization checks and admin-only actions

## Installation

1. Install Python dependencies:

```bash
pip install -r requirements.txt
```

2. If you want AI chat features, install the additional model dependencies:

```bash
pip install -r ai-requirements.txt
```

3. Install Ollama and pull the model used by the bot:

```bash
ollama pull gemma4
```

4. Create your environment file:

Windows:

```powershell
copy env.example .env
```

Linux / macOS:

```bash
cp env.example .env
```

Then edit `.env` and set values such as:

- `API_KEY`
- `ADMIN_CHAT_ID`
- `ADMIN_NAME`
- `NGROK_TOKEN`
- `DISCORD_TOKEN` (optional for Discord support)
- `CHAT_BOT_ENABLED`
- `FFMPEG_PATH_PREFIX` (optional)

5. Run the bot:

```bash
python main.py
```

Optional: create the provided `lanchBot.bat` / `lanchBot.vbs` files for automatic startup on Windows (see Auto-Start Configuration).

Troubleshooting

- If you don't intend to run Ollama locally, skip the Ollama/`ai-requirements.txt` steps and run in non-AI mode.
- If ngrok tunnels fail, verify `NGROK_TOKEN` and that no other service is occupying required local ports.

## Architecture

### Core Components

- **chains.py**: LangChain agent configuration using Ollama (gemma 4 model) with integrated tools and audio generation via ChatterboxTTS
- **tool_config.py**: Tool definitions and system command execution handlers
- **tool_adaptor.py**: Bridge between Telegram commands and tool execution
- **features.py**: Feature flag management for tool availability
- **trainer.py**: ML-based text classifier for command recognition
- **reminder_db.py**: Reminder data storage and retrieval
- **reminder_parser.py**: Natural language reminder parsing
- **reminder_executor.py**: Executing scheduled reminders and actions
- **scheduler_manager.py**: APScheduler-based reminder scheduling

### Available Tools/Commands

The AI agent has access to the following tools:

- **video**: Start or stop webcam streaming
- **screenshot**: Capture and send a screenshot of the whole screen
- **screen_share**: Toggle screen sharing on or off
- **types**: Type text using the system keyboard
- **send**: Send a file to the user by file path
- **execute_command_terminal**: Execute terminal commands with automatic window focus for opened applications
- **toggle_rdp_tunnel**: Toggle RDP tunnel for remote desktop access
- **schedule_reminder**: Create a reminder using natural language input
- **get_authorized_users**: Retrieve list of authorized users
- **remove_user**: Remove a user from the authorized list
- **Web Search**: DuckDuckGo search integration for information retrieval

## Operating Modes

### AI Chat Mode (`/ai`)

Uses the LangChain agent with gemma 4 to understand natural language and intelligently use available tools.

### Non-AI Chat Mode (`/non_ai`)

Rule-based command processing using machine learning classification for command recognition.

### Text-to-Speech Mode

Generate audio responses from AI outputs with ChatterboxTTS (supports chunking for long texts).

## Command Execution Flow

### AI Mode (`/ai`) - Intelligent Execution

1. User sends a natural language command or question
2. LangChain agent receives the input along with system status
3. gemma 4 model analyzes the request and determines which tools to use
4. Agent automatically invokes appropriate tools from `command_handlers`
5. Tool output is processed and returned to user
6. Optional: Response can be converted to audio using ChatterboxTTS

**Example**: "Turn on video streaming" → Agent recognizes intent → Calls `video()` → Stream starts automatically

### Non-AI Mode (`/non_ai`) - Rule-Based Execution with NLP Confirmation

1. User sends a command
2. If command starts with `>`, it's executed directly (bypass NLP)
3. Otherwise, the command text is analyzed by the trained ML classifier
4. If confidence is high (>50%), command executes immediately
5. If confidence is low, user is asked for confirmation with yes/no buttons
6. On confirmation, the command from `command_handlers` is executed

**Flow**:

```
User Input → NLP Classifier → Confidence Check
                                    ↓
                            High (>50%)        Low (<50%)
                                ↓                  ↓
                            Execute         Ask Confirmation
                                ↓                  ↓
                            Return Result    User Responds
```

## NLP Classification in Non-AI Mode

The bot uses a trained **Naive Bayes classifier with TF-IDF vectorization** (`text_classifier.joblib`) for command prediction:

- **Training**: Model trained on command examples to recognize patterns and context
- **Prediction**: Analyzes user input and outputs probability scores for each command
- **Confirmation Threshold**: 50% confidence threshold triggers confirmation dialog
- **Confirmation Messages**: Pre-defined messages ask users to confirm intent (e.g., "did you mean to start/stop video streaming?")
- **Yes/No Response**: User selects yes to execute predicted command or no to force direct execution

This approach balances automation with safety, catching potential misunderstandings while maintaining speed for clear commands.

## Tunneling Infrastructure with ngrok

**ngrok** is the core tunneling service that enables remote access to local services:

### Streaming Services (Video & Screen)

- **Local Flask Server**: Video and screen capture services run on `localhost:5000`
- **ngrok Tunnel**: Creates a public HTTPS tunnel connecting to the local Flask app
- **Public URL**: Bot sends users a public ngrok URL (e.g., `https://random-id.ngrok.io`)
  - Video streaming: Base URL (`/`)
  - Screen sharing: Appended path (`/screen`)
- **Live Updates**: When toggled, the `live_server()` method:
  1. Starts Flask server in background thread
  2. Establishes ngrok tunnel
  3. Broadcasts public URL to authorized users

### Remote Desktop Tunnel (RDP)

- **RDP Service**: Windows RDP runs locally (default port 3389)
- **ngrok Tunnel**: Creates a TCP tunnel exposing local RDP service
- **Remote Access**: Users connect via RDP client using the public ngrok endpoint
- **State Management**: `rdp_active` flag tracks tunnel status (prevents conflicts with streaming services)

### Security & Constraints

- **Token-Based Auth**: ngrok authenticated via `NGROK_TOKEN` from environment variables
- **Conflict Prevention**: Only one service type can use ngrok at a time:
  - Cannot start streaming while RDP tunnel is active
  - Cannot start RDP while streaming is active
  - Bot enforces these constraints to prevent resource conflicts

- **Direct Commands**: Use tools via natural language in AI mode
- **Bypass NLP**: Prefix with `>` to execute commands directly (e.g., `>send file.txt`)
- **Telegram Admin Commands**:
  - `/ai`: Switch to AI mode
  - `/non_ai`: Switch to non-AI mode
  - `list`: Get authorized users
  - `kick <chat_id>`: Remove user
  - `rdp`: Toggle RDP tunnel
  - `video`: Toggle video stream
  - `screen`: Toggle screen share
  - `speak <text>`: Text-to-speech command
  - `remind <text>`: Schedule a reminder via natural language
  - `schedule_reminder <text>`: Schedule a reminder via natural language
  - `list_reminders`: List scheduled reminders
  - `delete_reminder <id>`: Remove a scheduled reminder
  - `test_reminder <id>`: Test a scheduled reminder
  - `nlp`: Toggle NLP processing mode
  - `clear_history`: Clear chat history

## Tunnels and Remote Access

The bot can expose local services through tunneling tools:

- `ngrok` for streaming and remote access helpers
- `FRP` via the built-in `frpc` wrapper for tunnel management

## Project Structure

- `main.py` — entry point and bot startup
- `features.py` — command handling, auth checks, reminders, and tunnel logic
- `telegram_transport.py` — Telegram messaging adapter
- `discord_transport.py` — Discord messaging adapter
- `transport.py` — shared transport interface
- `chains.py` — LangChain and AI integration
- `tool_config.py` — tool definitions and command handlers
- `trainer.py` — NLP classification model
- `reminder_*.py` — reminder parsing, storage, and execution
- `scheduler_manager.py` — reminder scheduling
- `templates/` — HTML templates for the web UI
- `downloads/` — generated media and output files
- `tele_bot_log/` — runtime logs

## Auto-Start on Windows

You can use the provided startup scripts to launch the bot automatically on login:

- `lanchBot.bat`
- `lanchBot.vbs`

Copy the `.vbs` shortcut to the Windows Startup folder to enable automatic startup.
