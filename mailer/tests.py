from django.test import TestCase
from django.core import mail
from django.core.mail.backends.locmem import EmailBackend as LocMemEmailBackend

from mailer.models import Message, MessageLog
from mailer import send_mail as mailer_send_mail
from mailer import engine

import smtplib
import time


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


class FailingMailerEmailBackend(LocMemEmailBackend):
    def send_messages(self, email_messages):
        raise smtplib.SMTPSenderRefused(1, "foo", "foo@foo.com")


class TestBackend(TestCase):
    def test_save_to_db(self):
        """
        Test that using send_mail creates a Message object in DB instead, when EMAIL_BACKEND is set.
        """
        self.assertEqual(Message.objects.count(), 0)
        with self.settings(EMAIL_BACKEND="mailer.backend.DbBackend"):
            mail.send_mail("Subject", "Body", "sender@example.com", ["recipient@example.com"])
            self.assertEqual(Message.objects.count(), 1)


class TestSending(TestCase):
    def test_mailer_email_backend(self):
        """
        Test that calling "manage.py send_mail" actually sends mail using the
        specified MAILER_EMAIL_BACKEND
        """
        with self.settings(MAILER_EMAIL_BACKEND="mailer.tests.TestMailerEmailBackend"):
            mailer_send_mail("Subject", "Body", "sender1@example.com", ["recipient@example.com"])
            self.assertEqual(Message.objects.count(), 1)
            self.assertEqual(len(TestMailerEmailBackend.outbox), 0)
            engine.send_all()
            self.assertEqual(len(TestMailerEmailBackend.outbox), 1)
            self.assertEqual(Message.objects.count(), 0)
            self.assertEqual(MessageLog.objects.count(), 1)

    def test_retry_deferred(self):
        with self.settings(MAILER_EMAIL_BACKEND="mailer.tests.FailingMailerEmailBackend"):
            mailer_send_mail("Subject", "Body", "sender2@example.com", ["recipient@example.com"])
            engine.send_all()
            self.assertEqual(Message.objects.count(), 1)
            self.assertEqual(Message.objects.deferred().count(), 1)

        with self.settings(MAILER_EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend"):

            engine.send_all()
            self.assertEqual(len(mail.outbox), 0)
            # Should not have sent the deferred ones
            self.assertEqual(Message.objects.count(), 1)
            self.assertEqual(Message.objects.deferred().count(), 1)

            # Now mark them for retrying
            Message.objects.retry_deferred()
            engine.send_all()
            self.assertEqual(len(mail.outbox), 1)
            self.assertEqual(Message.objects.count(), 0)

    def test_control_max_delivery_amount(self):
        with self.settings(MAILER_EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend", MAILER_EMAIL_MAX_BATCH=2):  # noqa
            mailer_send_mail("Subject", "Body", "sender3@example.com", ["recipient@example.com"])
            mailer_send_mail("Subject", "Body", "sender4@example.com", ["recipient@example.com"])
            mailer_send_mail("Subject", "Body", "sender5@example.com", ["recipient@example.com"])
            self.assertEqual(Message.objects.count(), 3)
            self.assertEqual(len(mail.outbox), 0)
            engine.send_all()
            self.assertEqual(len(mail.outbox), 2)
            self.assertEqual(Message.objects.count(), 1)
            self.assertEqual(MessageLog.objects.count(), 2)

            # Send another round
            engine.send_all()
            self.assertEqual(len(mail.outbox), 3)
            self.assertEqual(Message.objects.count(), 0)
            self.assertEqual(MessageLog.objects.count(), 3)

    def test_control_max_retry_amount(self):
        with self.settings(MAILER_EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend"):
            # 5 normal emails scheduled for delivery
            mailer_send_mail("Subject", "Body", "sender6@example.com", ["recipient@example.com"])
            mailer_send_mail("Subject", "Body", "sender7@example.com", ["recipient@example.com"])
            mailer_send_mail("Subject", "Body", "sender8@example.com", ["recipient@example.com"])
            mailer_send_mail("Subject", "Body", "sender9@example.com", ["recipient@example.com"])
            mailer_send_mail("Subject", "Body", "sender10@example.com", ["recipient@example.com"])
            self.assertEqual(Message.objects.count(), 5)
            self.assertEqual(Message.objects.deferred().count(), 0)

        with self.settings(MAILER_EMAIL_BACKEND="mailer.tests.FailingMailerEmailBackend", MAILER_EMAIL_MAX_DEFERRED=2):  # noqa
            # 2 will get deferred 3 remain undeferred
            engine.send_all()
            self.assertEqual(Message.objects.count(), 5)
            self.assertEqual(Message.objects.deferred().count(), 2)

        with self.settings(MAILER_EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend", MAILER_EMAIL_MAX_DEFERRED=2):  # noqa
            # 3 will be delivered, 2 remain deferred
            engine.send_all()
            self.assertEqual(len(mail.outbox), 3)
            # Should not have sent the deferred ones
            self.assertEqual(Message.objects.count(), 2)
            self.assertEqual(Message.objects.deferred().count(), 2)

            # Now mark them for retrying
            Message.objects.retry_deferred()
            engine.send_all()
            self.assertEqual(len(mail.outbox), 5)
            self.assertEqual(Message.objects.count(), 0)

    def test_throttling_delivery(self):
        TIME = 1  # throttle time = 1 second

        with self.settings(MAILER_EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend"):
            # Calculate how long it takes to deliver 2 messages without throttling
            mailer_send_mail("Subject", "Body", "sender11@example.com", ["recipient@example.com"])
            mailer_send_mail("Subject", "Body", "sender12@example.com", ["recipient@example.com"])
            # 3 will be delivered, 2 remain deferred
            start_time = time.time()
            engine.send_all()
            unthrottled_time = time.time() - start_time

            self.assertEqual(len(mail.outbox), 2)
            self.assertEqual(Message.objects.count(), 0)

        with self.settings(MAILER_EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend", MAILER_EMAIL_THROTTLE=TIME):  # noqa
            mailer_send_mail("Subject", "Body", "sender13@example.com", ["recipient@example.com"])
            mailer_send_mail("Subject", "Body", "sender14@example.com", ["recipient@example.com"])
            # 3 will be delivered, 2 remain deferred
            start_time = time.time()
            engine.send_all()
            throttled_time = time.time() - start_time

            self.assertEqual(len(mail.outbox), 4)
            self.assertEqual(Message.objects.count(), 0)

        # NOTE This is a bit tricky to test due to possible fluctuations on
        # execution time. Test may randomly fail
        # NOTE 2*TIME because 2 emails are sent during the test
        self.assertAlmostEqual(unthrottled_time, throttled_time - 2*TIME, places=1)
