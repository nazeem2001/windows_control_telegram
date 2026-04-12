import json
import os
import uuid
from dataclasses import dataclass
from datetime import datetime

REMINDERS_FOLDER = "reminders"
REMINDERS_FILE = os.path.join(REMINDERS_FOLDER, "reminders.json")


@dataclass
class Reminder:
    id: str
    chat_id: int
    user_id: str
    ai: bool
    trigger_time: datetime
    message: str
    action_type: str
    action_params: dict
    recurrence_pattern: str
    is_one_time: bool
    created_at: datetime

    def to_dict(self):
        return {
            "id": self.id,
            "chat_id": self.chat_id,
            "user_id": self.user_id,
            "ai": self.ai,
            "trigger_time": self.trigger_time.isoformat(),
            "message": self.message,
            "action_type": self.action_type,
            "action_params": self.action_params,
            "recurrence_pattern": self.recurrence_pattern,
            "is_one_time": self.is_one_time,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            id=data["id"],
            chat_id=int(data["chat_id"]),
            user_id=str(data.get("user_id", "")),
            ai=bool(data.get("ai", False)),
            trigger_time=datetime.fromisoformat(data["trigger_time"]),
            message=data.get("message", "Reminder"),
            action_type=data.get("action_type", "send_message"),
            action_params=data.get("action_params", {}),
            recurrence_pattern=data.get("recurrence_pattern", None),
            is_one_time=data.get("is_one_time", True),
            created_at=datetime.fromisoformat(
                data.get("created_at", datetime.now().isoformat())
            ),
        )


def ensure_storage():
    os.makedirs(REMINDERS_FOLDER, exist_ok=True)
    if not os.path.exists(REMINDERS_FILE):
        with open(REMINDERS_FILE, "w", encoding="utf-8") as f:
            json.dump([], f, indent=2)


def load_reminders():
    ensure_storage()
    with open(REMINDERS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_reminders(reminders):
    ensure_storage()
    with open(REMINDERS_FILE, "w", encoding="utf-8") as f:
        json.dump(reminders, f, indent=2)


def save_reminder(reminder: Reminder):
    reminders = load_reminders()
    reminders = [r for r in reminders if r.get("id") != reminder.id]
    reminders.append(reminder.to_dict())
    save_reminders(reminders)


def delete_reminder(reminder_id: str):
    reminders = load_reminders()
    reminders = [r for r in reminders if r.get("id") != reminder_id]
    save_reminders(reminders)


def update_reminder(reminder: Reminder):
    save_reminder(reminder)


def get_reminder_by_id(reminder_id: str):
    reminders = load_reminders()
    for item in reminders:
        if item.get("id") == reminder_id:
            return Reminder.from_dict(item)
    return None


def list_reminders(chat_id=None):
    reminders = [Reminder.from_dict(item) for item in load_reminders()]
    if chat_id is not None:
        reminders = [rem for rem in reminders if rem.chat_id == chat_id]
    return reminders
