from unittest.mock import patch

from django.core.management import call_command
from django.test import SimpleTestCase, override_settings


class WorkerDeploymentTests(SimpleTestCase):
    def run_cycle(self, backend, local=False):
        with override_settings(DOCUMENT_STORAGE_BACKEND=backend, DOCUMENT_LOCAL_STORAGE_ENABLED=local), \
             patch("jobs.management.commands.run_operations.schedule_reminders"), \
             patch("jobs.management.commands.run_operations.deliver_one", return_value=False), \
             patch("jobs.management.commands.run_operations.deliver_case_email", return_value=False), \
             patch("jobs.management.commands.run_operations.call_command"), \
             patch("jobs.management.commands.run_operations.close_old_connections") as connections, \
             patch("jobs.management.commands.run_operations.scan_one") as scanner:
            call_command("run_operations", once=True)
        self.assertEqual(connections.call_count, 2)
        return scanner

    def test_s3_documents_are_scanned_in_bounded_cycle(self):
        self.run_cycle("s3").assert_called_once_with()

    def test_disabled_documents_do_not_contact_storage_or_scanner(self):
        self.run_cycle("disabled").assert_not_called()

    def test_local_enabled_documents_are_scanned(self):
        self.run_cycle("local", local=True).assert_called_once_with()
