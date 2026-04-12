import os
from subprocess import Popen, PIPE
from types import SimpleNamespace
from reminder_db import delete_reminder, get_reminder_by_id


def _build_context(feature):
    return SimpleNamespace(bot=feature.telegram_bot)


async def execute_reminder(feature, reminder_id: str):
    reminder = get_reminder_by_id(reminder_id)
    if not reminder:
        print(f"Reminder {reminder_id} not found.")
        return
    try:
        if reminder.ai:
            context = _build_context(feature)
            feature.set_chat_mode(reminder.chat_id, "ai")
            profile = await feature.telegram_bot.get_chat(chat_id=reminder.chat_id)
            reminder_message = f">{reminder.message}"
            await feature.execute_chat_command_async(
                reminder.chat_id,
                reminder_message,
                reminder_message.split(),
                profile.first_name,
                profile.last_name,
                context,
            )

        # Handle AI-specific reminder logic here

        else:
            if reminder.action_type == "send_message":
                await feature.telegram_bot.send_message(
                    chat_id=reminder.chat_id,
                    text=reminder.message,
                )
                print(
                    f"Sent reminder {reminder.id} to chat {reminder.chat_id}: {reminder.message}"
                )
            elif reminder.action_type == "run_command":
                command = reminder.action_params.get("command", "")
                if not command:
                    await feature.telegram_bot.send_message(
                        chat_id=reminder.chat_id,
                        text=f"Reminder {reminder.id} executed, but no command was defined.",
                    )
                    print(f"Reminder {reminder.id} had no command.")
                else:
                    list_command = command.split()
                    context = _build_context(feature)
                    if list_command[0].lower() in feature.command_handlers:
                        await feature.command_handlers[list_command[0].lower()](
                            reminder.chat_id,
                            command,
                            list_command,
                            "",
                            "",
                            context,
                        )
                        print(
                            f"Executed scheduled command '{command}' for reminder {reminder.id}."
                        )
                    else:
                        process = Popen(
                            command, shell=True, stdout=PIPE, stderr=PIPE, text=True
                        )
                        stdout, stderr = process.communicate()
                        if process.returncode != 0:
                            await feature.telegram_bot.send_message(
                                chat_id=reminder.chat_id,
                                text=f"Scheduled command failed: {stderr.strip()}",
                            )
                            print(
                                f"Scheduled command failed for reminder {reminder.id}: {stderr.strip()}"
                            )
                        else:
                            await feature.telegram_bot.send_message(
                                chat_id=reminder.chat_id,
                                text=stdout.strip()
                                or f"Scheduled command '{command}' executed.",
                            )
                            print(
                                f"Scheduled command succeeded for reminder {reminder.id}: {stdout.strip()}"
                            )
        if reminder.is_one_time:
            delete_reminder(reminder.id)
            print(f"Deleted one-time reminder {reminder.id} after execution.")
    except Exception as exc:
        print(f"Error executing reminder {reminder.id}: {exc}")
