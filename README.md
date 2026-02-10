# Windows Command Telegram Bot

A comprehensive Telegram bot for remote system control with AI-powered assistance using LangChain and Ollama.

## Overview

This project integrates a Telegram bot with intelligent AI capabilities (powered by Llama 3.1 via Ollama) to provide remote system control, automation, and interactive features. The bot supports both text-based and text-to-speech (TTS) modes with tool integration for system operations.
## Features Summary

- **AI-Powered Assistant**: Uses Llama 3.1 for intelligent command understanding and execution
- **Bidirectional Tool Control**: System webcam, screen capture, keyboard input, and terminal commands
- **Remote Desktop Access**: Secure RDP tunnel setup
- **File Transfer**: Send and receive files
- **Audio Generation**: Text-to-speech with customizable parameters
- **Command Classification**: ML-based intelligent command recognition
- **Multi-Mode Operation**: Support for AI and rule-based modes
- **Authorization Management**: Whitelist-based user authorization
- **Comprehensive Logging**: Full command and activity logs



## Installation

Install required dependencies:

```bash
pip install -r requirements.txt
```

Ensure you have Ollama installed and the Llama 3.1 model pulled:

```bash
ollama pull llama3.1
```

## Architecture

### Core Components

- **chains.py**: LangChain agent configuration using Ollama (Llama 3.1 model) with integrated tools and audio generation via ChatterboxTTS
- **tool_config.py**: Tool definitions and system command execution handlers
- **tool_adaptor.py**: Bridge between Telegram commands and tool execution
- **features.py**: Feature flag management for tool availability
- **trainer.py**: ML-based text classifier for command recognition

### Available Tools/Commands

The AI agent has access to the following tools:

- **video**: Start or stop webcam streaming
- **screenshot**: Capture and send a screenshot of the whole screen
- **screen_share**: Toggle screen sharing on or off
- **types**: Type text using the system keyboard
- **send**: Send a file to the user by file path
- **execute_command_terminal**: Execute terminal commands with automatic window focus for opened applications (currently fully supported in non-AI mode; AI mode support in progress)
- **toggle_rdp_tunnel**: Toggle RDP tunnel for remote desktop access
- **get_authorized_users**: Retrieve list of authorized users
- **remove_user**: Remove a user from the authorized list
- **Web Search**: DuckDuckGo search integration for information retrieval

## Operating Modes

### AI Chat Mode (`/ai`)

Uses the LangChain agent with Llama 3.1 to understand natural language and intelligently use available tools.

### Non-AI Chat Mode (`/non_ai`)

Rule-based command processing using machine learning classification for command recognition.

### Text-to-Speech Mode

Generate audio responses from AI outputs with ChatterboxTTS (supports chunking for long texts).

## Command Execution Flow

### AI Mode (`/ai`) - Intelligent Execution

1. User sends a natural language command or question
2. LangChain agent receives the input along with system status
3. Llama 3.1 model analyzes the request and determines which tools to use
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

## Auto-Start Configuration (Windows)

### Steps to Auto-Start:

1. Create a `.bat` file (e.g., `lanchBot.bat`):

```batch
@echo off
cls
python main.py>>./tele_bot_log/logs.txt
exit
```

2. Create a `.vbs` file (e.g., `lanchBot.vbs`):

```vbscript
Set WshShell = CreateObject("WScript.Shell")
WshShell.Run chr(34) & "lanchBot.bat" & Chr(34), 0
Set WshShell = Nothing
```

3. Copy the `.vbs` file shortcut to:
   ```
   C:\Users\<username>\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup
   ```

## Configuration

- **Environment Variables**: Copy `env.example` to `.env` and configure your Telegram token and settings
- **Ollama Model**: Configured to use Llama 3.1 (see `chains.py`)
- **Device Detection**: Automatically uses CUDA if available, otherwise CPU
- **Authorized Users**: Stored in `authorzed_Users/authorzed_Users.json`

## Project Structure

- `main.py`: Entry point
- `chains.py`: LangChain agent setup and TTS generation
- `tool_config.py`: Tool definitions
- `tool_adaptor.py`: Tool execution bridge
- `features.py`: Feature management
- `trainer.py`: ML classifier for command recognition
- `logger.py`: Logging utilities
- `templates/`: HTML templates for web interface
- `models/`: Context and configuration models
- `adaptors/`: Tool adapters
- `downloads/`: Generated files (audio, etc.)
- `tele_bot_log/`: Bot logs

