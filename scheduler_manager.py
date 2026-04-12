from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.jobstores.base import JobLookupError
from datetime import datetime
from reminder_db import delete_reminder, list_reminders, Reminder, get_reminder_by_id
from reminder_executor import execute_reminder
from reminder_parser import get_local_timezone


class SchedulerManager:
    def __init__(self, feature):
        self.feature = feature
        self.scheduler = AsyncIOScheduler(timezone=get_local_timezone())
        self.scheduler.configure(coalesce=True, max_instances=1)

    def start(self):
        """Start the scheduler and load persisted reminders from storage."""
        if not self.scheduler.running:
            self.scheduler.start()
        self.load_scheduled_reminders()
        print("Loaded scheduled reminders from reminders.json")

    def shutdown(self):
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)

    def load_scheduled_reminders(self):
        now = datetime.now(self.scheduler.timezone)
        for reminder in list_reminders():
            print(
                f"Checking reminder {reminder.id} with trigger time {reminder.trigger_time}"
            )
            if reminder.is_one_time and reminder.trigger_time <= now:
                print(f"Deleting one-time reminder {reminder.id}")
                delete_reminder(reminder.id)
                continue
            self._schedule_reminder_job(reminder)

    def add_reminder(self, reminder: Reminder):
        from reminder_db import save_reminder

        save_reminder(reminder)
        self._schedule_reminder_job(reminder)

    def remove_reminder(self, reminder_id: str):
        try:
            self.scheduler.remove_job(reminder_id)
        except JobLookupError:
            pass
        delete_reminder(reminder_id)

    def list_reminders(self, chat_id=None):
        return list_reminders(chat_id)

    def _schedule_reminder_job(self, reminder: Reminder):
        print(
            f"Scheduling reminder {reminder.id} with trigger time {reminder.trigger_time}"
        )
        trigger = self._build_trigger(reminder)
        if trigger is None:
            return
        print(f"Adding job for reminder {reminder.id} with trigger {trigger}")
        self.scheduler.add_job(
            execute_reminder,
            trigger=trigger,
            args=[self.feature, reminder.id],
            id=reminder.id,
            replace_existing=True,
        )

    def _build_trigger(self, reminder: Reminder):
        if reminder.recurrence_pattern is None:
            return DateTrigger(run_date=reminder.trigger_time)

        if reminder.recurrence_pattern == "daily":
            return CronTrigger(
                hour=reminder.trigger_time.hour,
                minute=reminder.trigger_time.minute,
                timezone=self.scheduler.timezone,
            )

        weekdays = {
            "monday": "mon",
            "tuesday": "tue",
            "wednesday": "wed",
            "thursday": "thu",
            "friday": "fri",
            "saturday": "sat",
            "sunday": "sun",
        }
        if reminder.recurrence_pattern in weekdays:
            return CronTrigger(
                day_of_week=weekdays[reminder.recurrence_pattern],
                hour=reminder.trigger_time.hour,
                minute=reminder.trigger_time.minute,
                timezone=self.scheduler.timezone,
            )

        return DateTrigger(run_date=reminder.trigger_time)
