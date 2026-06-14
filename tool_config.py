import time
import inspect
from langchain_core.tools import tool
from adaptors.tool_adaptor import execute_llm_tool
from langchain_community.tools import DuckDuckGoSearchRun, DuckDuckGoSearchResults


def build_tools(feature, tool_ctx):
    """Build tools from both LLM config and explicit special tools"""

    def make_tool(cfg):
        """Create a tool from an LLM tool configuration"""
        async def _tool(**kwargs):
            # Map kwargs to parameters based on args_map
            params = {k: kwargs.get(v) for k, v in cfg["args_map"].items()} if cfg["args_map"] else {}
            if cfg.get("add_ai_flag"):
                 await execute_llm_tool(feature, cfg["command"], params, tool_ctx, add_ai_flag=True)
            else:
                await execute_llm_tool(feature, cfg["command"], params, tool_ctx)
            return f"{cfg['return_msg']} {'with parameters: ' + str(params) if params else ''}"
        
        _tool.__name__ = cfg["command"]
        _tool.__doc__ = cfg["description"]
           # Pydantic reads __annotations__ for type hints
        _tool.__annotations__ = {name: str for name in cfg["args_map"].values()}
    
            # Build a real signature so inspect.signature() works on it
        params = [
        inspect.Parameter(
            name=param_name,
            kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
            annotation=str,
        )
        for param_name in cfg["args_map"].values()
    ]
        _tool.__signature__ = inspect.Signature(parameters=params)
        
        return tool(_tool)
    print(feature._tool_configs)

    # Generate tools from LLM configs
    tools = [make_tool(cfg) for cfg in type(feature)._tool_configs]

    # Special tools with unique logic
    @tool
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

    # Combine all tools
    tools.extend([
        schedule_reminder,
        get_date_time,
        execute_command_terminal,
        DuckDuckGoSearchRun(),
    ])

    return tools
