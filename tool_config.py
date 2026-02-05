from langchain_core.tools import tool
from adaptors.tool_adaptor import execute_llm_tool
from langchain_community.tools import DuckDuckGoSearchRun


def build_tools(feature, tool_ctx):

    @tool
    async def video() -> str:
        """Start or stop webcam streaming"""
        await execute_llm_tool(feature, "video", {}, tool_ctx)
        return "Video streaming toggled"

    @tool
    async def types(text: str) -> str:
        """Type text on the system keyboard"""
        await execute_llm_tool(
            feature,
            "types",
            {"text": text},
            tool_ctx
        )
        return f"Typed text: {text}"

    @tool
    async def send(path: str) -> str:
        """Send a file to the user by path"""
        await execute_llm_tool(
            feature,
            "send",
            {"text": path},
            tool_ctx
        )
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
        
    return [video, types, send, screenshot, screen_share, remove_user, get_authorized_users, toggle_rdp_tunnel, DuckDuckGoSearchRun()]