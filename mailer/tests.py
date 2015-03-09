from django.test import TestCase

from mailer.models import Message, MessageLog
from mailer.engine import send_all

import smtplib


class TestMailerEmailBackend(object):
    outbox = []

    def __init__(self, **kwargs):
        del self.outbox[:]

    def open(self):
        pass

    def close(self):
        pass

    def send_messages(self, email_messages):
        self.outbox.extend(email_messages)


class FailingMailerEmailBackend(TestMailerEmailBackend):
    def send_messages(self, email_messages):
        raise smtplib.SMTPSenderRefused(1, "foo", "foo@foo.com")


class TestBackend(TestCase):

    def test_save_to_db(self):
        """
        Test that using send_mail creates a Message object in DB instead, when EMAIL_BACKEND is set.
        """
        from django.core.mail import send_mail
        self.assertEqual(Message.objects.count(), 0)
        with self.settings(EMAIL_BACKEND="mailer.backend.DbBackend"):
            send_mail("Subject", "Body", "sender@example.com", ["recipient@example.com"])
            self.assertEqual(Message.objects.count(), 1)


class TestSending(TestCase):
    def test_mailer_email_backend(self):
        """
        Test that calling "manage.py send_mail" actually sends mail using the
        specified MAILER_EMAIL_BACKEND
        """
        global sent_messages
        # Ensure sent_messages is empty
        del sent_messages[:]
        from mailer import send_mail
        with self.settings(MAILER_EMAIL_BACKEND="mailer.tests.TestMailerEmailBackend"):
            send_mail("Subject", "Body", "sender@example.com", ["recipient@example.com"])
            self.assertEqual(Message.objects.count(), 1)
            self.assertEqual(len(sent_messages), 0)
            from mailer.engine import send_all  # noqa
            send_all()
            self.assertEqual(len(sent_messages), 1)
            self.assertEqual(Message.objects.count(), 0)
            self.assertEqual(MessageLog.objects.count(), 1)

    def test_retry_deferred(self):
        global sent_messages
        # Ensure sent_messages is empty
        del sent_messages[:]

        from mailer import send_mail
        with self.settings(MAILER_EMAIL_BACKEND="mailer.tests.FailingMailerEmailBackend"):
            send_mail("Subject", "Body", "sender@example.com", ["recipient@example.com"])
            send_all()
            self.assertEqual(Message.objects.count(), 1)
            self.assertEqual(Message.objects.deferred().count(), 1)

        with self.settings(MAILER_EMAIL_BACKEND="mailer.tests.TestMailerEmailBackend"):
            send_all()
            self.assertEqual(len(sent_messages), 0)
            # Should not have sent the deferred ones
            self.assertEqual(Message.objects.count(), 1)
            self.assertEqual(Message.objects.deferred().count(), 1)

            # Now mark them for retrying
            Message.objects.retry_deferred()
            send_all()
            self.assertEqual(len(sent_messages), 1)
            self.assertEqual(Message.objects.count(), 0)

    def test_control_max_delivery_amount(self):
        global sent_messages
        # Ensure sent_messages is empty
        del sent_messages[:]

        from mailer import send_mail
        with self.settings(MAILER_EMAIL_BACKEND="mailer.tests.TestMailerEmailBackend", MAILER_EMAIL_MAX_BATCH=2):  # noqa
            send_mail("Subject1", "Body1", "sender1@example.com", ["recipient1@example.com"])
            send_mail("Subject2", "Body2", "sender2@example.com", ["recipient2@example.com"])
            send_mail("Subject3", "Body3", "sender3@example.com", ["recipient3@example.com"])
            self.assertEqual(Message.objects.count(), 3)
            self.assertEqual(len(sent_messages), 0)
            send_all()
            self.assertEqual(len(sent_messages), 2)
            self.assertEqual(Message.objects.count(), 1)
            self.assertEqual(MessageLog.objects.count(), 2)

    def test_control_max_retry_amount(self):
        global sent_messages
        # Ensure sent_messages is empty
        del sent_messages[:]

        from mailer import send_mail
        with self.settings(MAILER_EMAIL_BACKEND="mailer.tests.TestMailerEmailBackend"):  # noqa
            # 5 normal emails scheduled for delivery
            send_mail("Subject1", "Body1", "sender1@example.com", ["recipient1@example.com"])
            send_mail("Subject2", "Body2", "sender2@example.com", ["recipient2@example.com"])
            send_mail("Subject3", "Body3", "sender3@example.com", ["recipient3@example.com"])
            send_mail("Subject4", "Body4", "sender4@example.com", ["recipient4@example.com"])
            send_mail("Subject5", "Body5", "sender5@example.com", ["recipient5@example.com"])
            self.assertEqual(Message.objects.count(), 5)
            self.assertEqual(Message.objects.deferred().count(), 0)

        with self.settings(MAILER_EMAIL_BACKEND="mailer.tests.FailingMailerEmailBackend", MAILER_EMAIL_MAX_DEFERRED=2):  # noqa
            # 2 will get deferred 3 remain undeferred
            send_all()
            self.assertEqual(Message.objects.count(), 5)
            self.assertEqual(Message.objects.deferred().count(), 2)

        with self.settings(MAILER_EMAIL_BACKEND="mailer.tests.TestMailerEmailBackend", MAILER_EMAIL_MAX_DEFERRED=2):  # noqa
            # 3 will be delivered, 2 remain deferred
            send_all()
            self.assertEqual(len(sent_messages), 3)
            # Should not have sent the deferred ones
            self.assertEqual(Message.objects.count(), 2)
            self.assertEqual(Message.objects.deferred().count(), 2)

            # Now mark them for retrying
            Message.objects.retry_deferred()
            send_all()
            self.assertEqual(len(sent_messages), 2)
            self.assertEqual(Message.objects.count(), 0)
