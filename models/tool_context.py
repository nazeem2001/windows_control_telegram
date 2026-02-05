from dataclasses import dataclass
from telegram.ext import ContextTypes

@dataclass
class ToolContext:
    chat_id: int
    first_name: str
    last_name: str
    context: ContextTypes.DEFAULT_TYPE
