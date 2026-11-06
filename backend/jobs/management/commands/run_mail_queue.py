"""Mail-only worker suitable for sharing the existing web container."""
import time
import logging

from django.core.management.base import BaseCommand
from django.db import close_old_connections, InterfaceError, OperationalError

from jobs.mail import deliver_one
from jobs.communication import deliver_case_email, schedule_reminders


class Command(BaseCommand):
    help = "Process identity and case emails without running billing or document jobs."

    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true")

    def handle(self, *args, **options):
        try:
            while True:
                close_old_connections()
                try:
                    schedule_reminders()
                    for _ in range(100):
                        identity = deliver_one()
                        case = deliver_case_email()
                        if not identity and not case:
                            break
                except (InterfaceError, OperationalError):
                    if options["once"]:
                        raise
                    logging.getLogger("jobs.mail").exception("Mail queue database temporarily unavailable")
                finally:
                    close_old_connections()
                if options["once"]:
                    return
                time.sleep(10)
        except KeyboardInterrupt:
            return
