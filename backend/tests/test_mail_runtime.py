from unittest.mock import MagicMock, patch

from django.core.management import call_command
from django.test import SimpleTestCase
from django.db import OperationalError

import start_web


class MailRuntimeTests(SimpleTestCase):
    def setUp(self):
        for name in ("schedule_membership_notices", "update_mail_health"):
            mocked = patch("jobs.management.commands.run_mail_queue." + name)
            mocked.start()
            self.addCleanup(mocked.stop)

    def test_worker_recovers_after_database_disconnect(self):
        with patch("jobs.management.commands.run_mail_queue.deliver_one", side_effect=[OperationalError("private"), False]) as identity, \
             patch("jobs.management.commands.run_mail_queue.deliver_case_email", return_value=False), \
             patch("jobs.management.commands.run_mail_queue.schedule_reminders"), \
             patch("jobs.management.commands.run_mail_queue.close_old_connections") as connections, \
             patch("jobs.management.commands.run_mail_queue.time.sleep", side_effect=[None, KeyboardInterrupt]), \
             self.assertLogs("jobs.mail", level="ERROR"):
            call_command("run_mail_queue")
        self.assertEqual(identity.call_count, 2)
        self.assertEqual(connections.call_count, 4)

    def test_once_reports_database_failure_to_operator(self):
        with patch("jobs.management.commands.run_mail_queue.deliver_one", side_effect=OperationalError), \
             patch("jobs.management.commands.run_mail_queue.schedule_reminders"), \
             self.assertRaises(OperationalError):
            call_command("run_mail_queue", once=True)

    def test_both_queues_are_processed_in_one_cycle(self):
        with patch("jobs.management.commands.run_mail_queue.deliver_one", side_effect=[True, False]) as identity, \
             patch("jobs.management.commands.run_mail_queue.deliver_case_email", side_effect=[True, False]) as case, \
             patch("jobs.management.commands.run_mail_queue.schedule_reminders") as reminders, \
             patch("jobs.management.commands.run_mail_queue.close_old_connections") as connections:
            call_command("run_mail_queue", once=True)
        self.assertEqual(identity.call_count, 2)
        self.assertEqual(case.call_count, 2)
        reminders.assert_called_once()
        self.assertEqual(connections.call_count, 2)

    @patch("start_web.signal.signal")
    @patch("start_web.subprocess.Popen")
    def test_dead_mail_process_stops_web_for_platform_restart(self, popen, signal):
        web, mail = MagicMock(), MagicMock()
        web.poll.return_value = None
        mail.poll.return_value = 1
        popen.side_effect = [web, mail]
        with patch.dict("os.environ", {"MAIL_WORKER_IN_WEB": "true", "PORT": "10000"}):
            self.assertEqual(start_web.main(), 1)
        self.assertIn("0.0.0.0:10000", popen.call_args_list[0].args[0])
        self.assertEqual(popen.call_args_list[1].args[0][-1], "run_mail_queue")
        web.terminate.assert_called_once()
        web.wait.assert_called_once()

    @patch("start_web.signal.signal")
    @patch("start_web.subprocess.Popen")
    def test_existing_web_only_mode_does_not_start_mail(self, popen, signal):
        popen.return_value.poll.return_value = 1
        with patch.dict("os.environ", {"MAIL_WORKER_IN_WEB": "false"}):
            self.assertEqual(start_web.main(), 1)
        popen.assert_called_once()
