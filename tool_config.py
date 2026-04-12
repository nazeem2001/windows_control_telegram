import time
from langchain_core.tools import tool
from adaptors.tool_adaptor import execute_llm_tool
from langchain_community.tools import DuckDuckGoSearchRun, DuckDuckGoSearchResults


def build_tools(feature, tool_ctx):

    @tool
    async def video() -> str:
        """Start or stop webcam streaming"""
        await execute_llm_tool(feature, "video", {}, tool_ctx)
        return "Video streaming toggled"

    @tool
    async def types(text: str) -> str:
        """Type text on the system keyboard"""
        await execute_llm_tool(feature, "types", {"text": text}, tool_ctx)
        return f"Typed text: {text}"

    @tool
    async def send(path: str) -> str:
        """Send a file to the user by path"""
        await execute_llm_tool(feature, "send", {"text": path}, tool_ctx)
        return f"Sent file at path: {path}"

    @tool
    async def screenshot() -> str:
        """Take a screenshot of the whole screen and send it to the user"""
        await execute_llm_tool(feature, "screenshot", {}, tool_ctx)
        return "Screenshot taken and sent"

    @tool
    async def screen_share() -> str:
        """Start or stop screen sharing"""
        await execute_llm_tool(feature, "screen", {}, tool_ctx)
        return "Screen sharing toggled"

    @tool
    async def remove_user(chat_id: str) -> str:
        """Remove user from the system"""
        return await execute_llm_tool(feature, "kick", {"text": chat_id}, tool_ctx)

    @tool
    async def get_authorized_users() -> str:
        """Get the list of authorized users"""
        await execute_llm_tool(feature, "list", {}, tool_ctx)
        return "Authorized users list sent"

    @tool
    async def toggle_rdp_tunnel() -> str:
        """Toggle RDP tunnel on or off"""
        return await execute_llm_tool(feature, "rdp", {}, tool_ctx)

    @tool
    async def execute_command_terminal(command: str) -> str:
        """Execute a terminal command on the system and focus opened app on Windows"""
        import subprocess
        import shlex
        import os
        import ctypes
        from ctypes import wintypes
        import time

        user32 = ctypes.WinDLL("user32", use_last_error=True)
        EnumWindows = user32.EnumWindows
        EnumWindowsProc = ctypes.WINFUNCTYPE(
            wintypes.BOOL, wintypes.HWND, wintypes.LPARAM
        )
        IsWindowVisible = user32.IsWindowVisible
        GetWindowThreadProcessId = user32.GetWindowThreadProcessId
        SetForegroundWindow = user32.SetForegroundWindow
        ShowWindow = user32.ShowWindow
        SW_RESTORE = 9

        def _find_hwnds_for_pid(pid):
            hwnds = []

            @EnumWindowsProc
            def _enum(hwnd, lParam):
                if IsWindowVisible(hwnd):
                    pid_dw = wintypes.DWORD()
                    GetWindowThreadProcessId(hwnd, ctypes.byref(pid_dw))
                    if pid_dw.value == pid:
                        hwnds.append(hwnd)
                return True

            EnumWindows(_enum, 0)
            return hwnds

        def bring_process_to_front(pid, timeout=5.0):
            end = time.time() + timeout
            while time.time() < end:
                hwnds = _find_hwnds_for_pid(pid)
                if hwnds:
                    for hwnd in hwnds:
                        ShowWindow(hwnd, SW_RESTORE)
                        SetForegroundWindow(hwnd)
                    return True
                time.sleep(0.05)
            return False

        try:
            print(command)
            args = shlex.split(command)
            if args and args[0].lower() == "start":
                if len(args) < 2:
                    return "Error: 'start' requires a target"
                target = args[1]
                try:
                    proc = subprocess.Popen(
                        args[1:],
                        stdin=subprocess.DEVNULL,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        shell=False,
                    )
                    try:
                        bring_process_to_front(proc.pid)
                    except Exception:
                        pass
                    return f"Started: {target}"
                except FileNotFoundError:
                    try:
                        os.startfile(target)
                        return f"Started: {target}"
                    except Exception as e:
                        return f"Error starting {target}: {e}"
                except Exception as e:
                    return f"Error starting {target}: {e}"
            proc = subprocess.Popen(
                args,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                shell=True,
            )
            stdout, stderr = proc.communicate()
            return (
                stdout
                if stdout
                else (stderr if stderr else f"Command finished: {command}")
            )
        except ValueError as e:
            return f"Error parsing command: {str(e)}"
        except Exception as e:
            return f"Error executing command: {str(e)}"
    async def schedule_reminder(natural_language_input: str) -> str:
        """Schedule a reminder for a future time."""
        await execute_llm_tool(
            feature,
            "schedule_reminder",
            {"text": natural_language_input},
            tool_ctx,
            add_ai_flag=True,
        )
        return f"Scheduled reminder: {natural_language_input}"

    @tool
    def get_date_time() -> str:
        """Get the current date and time from the system"""
        return time.ctime()

    @tool
    async def clear_history() -> str:
        """Clear the chat history"""
        return await execute_llm_tool(feature, "clear_history", {}, tool_ctx)

    return [
        video,
        types,
        send,
        screenshot,
        get_date_time,
        screen_share,
        remove_user,
        get_authorized_users,
        toggle_rdp_tunnel,
        execute_command_terminal,
        schedule_reminder,
        clear_history,
        DuckDuckGoSearchRun(),
    ]
