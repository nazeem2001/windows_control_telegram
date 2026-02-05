from models.tool_context import ToolContext


async def execute_llm_tool(
    feature,
    tool_name: str,
    arguments: dict,
    tool_ctx: ToolContext
):
    print(f"Executing tool: {tool_name} with arguments: {arguments}")
    if arguments:
        command = f'{tool_name} {arguments.get("text", tool_name)}'
        command_list = command.split()
        print(f"Command: {command}, Command List: {command_list}")
    else:
        command = tool_name
        command_list = [tool_name]

    return await feature.command_handlers[tool_name](
        tool_ctx.chat_id,
        command,
        command_list,
        tool_ctx.first_name,
        tool_ctx.last_name,
        tool_ctx.context
    )
