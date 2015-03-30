from django.test import TestCase
from django_mailer import engine, models, settings
from lockfile import FileLock
from django.utils.six import StringIO
from .base import MailerTestCase
import logging
import time

try:
    from django.utils.timezone import now
except ImportError:
    import datetime
    now = datetime.datetime.now


class LockTest(TestCase):
    """
    Tests for Django Mailer trying to send mail when the lock is already in
    place.
    """

    def setUp(self):
        # Create somewhere to store the log debug output.
        self.output = StringIO()
        # Create a log handler which can capture the log debug output.
        self.handler = logging.StreamHandler(self.output)
        self.handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(message)s')
        self.handler.setFormatter(formatter)
        # Add the log handler.
        logger = logging.getLogger('django_mailer')
        logger.addHandler(self.handler)

        # Set the LOCK_WAIT_TIMEOUT to the default value.
        self.original_timeout = settings.LOCK_WAIT_TIMEOUT
        settings.LOCK_WAIT_TIMEOUT = 0

        # Use a test lock-file name in case something goes wrong, then emulate
        # that the lock file has already been acquired by another process.
        self.original_lock_path = engine.LOCK_PATH
        engine.LOCK_PATH += '.mailer-test'
        self.lock = FileLock(engine.LOCK_PATH)
        self.lock.unique_name += '.mailer_test'
        self.lock.acquire(0)

    def tearDown(self):
        # Remove the log handler.
        logger = logging.getLogger('django_mailer')
        logger.removeHandler(self.handler)

        # Revert the LOCK_WAIT_TIMEOUT to it's original value.
        settings.LOCK_WAIT_TIMEOUT = self.original_timeout

        # Revert the lock file unique name
        engine.LOCK_PATH = self.original_lock_path
        self.lock.release()

    def test_locked(self):
        # Acquire the lock so that send_all will fail.
        engine.send_all()
        self.output.seek(0)
        self.assertEqual(self.output.readlines()[-1].strip(),
                         'Lock already in place. Exiting.')
        # Try with a timeout.
        settings.LOCK_WAIT_TIMEOUT = .1
        engine.send_all()
        self.output.seek(0)
        self.assertEqual(self.output.readlines()[-1].strip(),
                         'Waiting for the lock timed out. Exiting.')

    def test_locked_timeoutbug(self):
        # We want to emulate the lock acquiring taking no time, so the next
        # three calls to time.time() always return 0 (then set it back to the
        # real function).
        original_time = time.time
        global time_call_count
        time_call_count = 0

        def fake_time():
            global time_call_count
            time_call_count = time_call_count + 1
            if time_call_count >= 3:
                time.time = original_time
            return 0
        time.time = fake_time
        try:
            engine.send_all()
            self.output.seek(0)
            self.assertEqual(self.output.readlines()[-1].strip(),
                             'Lock already in place. Exiting.')
        finally:
            time.time = original_time


class TestSendConfiguration(MailerTestCase):
    def setUp(self):
        super(TestSendConfiguration, self).setUp()

        self._backup = {
            "EMAIL_MAX_SENT": settings.EMAIL_MAX_SENT,
            "EMAIL_MAX_DEFERRED": settings.EMAIL_MAX_DEFERRED,
            "EMAIL_THROTTLE": settings.EMAIL_THROTTLE,
        }
        self.test_backend = "django_mailer.testapp.tests.base.TestEmailBackend"
        self.fail_backend = "django_mailer.testapp.tests.base.FailEmailBackend"

    def tearDown(self):
        super(TestSendConfiguration, self).tearDown()

        settings.EMAIL_MAX_SENT = self._backup["EMAIL_MAX_SENT"]
        settings.EMAIL_MAX_DEFERRED = self._backup["EMAIL_MAX_DEFERRED"]
        settings.EMAIL_THROTTLE = self._backup["EMAIL_THROTTLE"]

    def test_control_max_sent_amount(self):
        settings.EMAIL_MAX_SENT = 2

        self.queue_message()
        self.queue_message()
        self.queue_message()

        self.assertEqual(models.QueuedMessage.objects.count(), 3)
        self.assertEqual(models.Log.objects.count(), 0)

        engine.send_all(backend=self.test_backend)

        self.assertEqual(models.QueuedMessage.objects.count(), 1)
        self.assertEqual(models.Log.objects.count(), 2)

        # Send another round which should deliver all remaining messages
        engine.send_all(backend=self.test_backend)

        self.assertEqual(models.QueuedMessage.objects.count(), 0)
        self.assertEqual(models.Log.objects.count(), 3)

    def test_control_max_deferred_amount(self):
        settings.EMAIL_MAX_DEFERRED = 2

        # 2 will get deferred 3 remain undeferred
        self.queue_message()
        self.queue_message()
        self.queue_message()

        self.assertEqual(models.QueuedMessage.objects.count(), 3)
        self.assertEqual(models.QueuedMessage.objects.deferred().count(), 0)
        self.assertEqual(models.Log.objects.count(), 0)

        # 2 messages get deferred and 1 remains unprocessed
        engine.send_all(backend=self.fail_backend)

        self.assertEqual(models.QueuedMessage.objects.count(), 3)
        self.assertEqual(models.QueuedMessage.objects.deferred().count(), 2)
        self.assertEqual(models.Log.objects.count(), 2)

        models.QueuedMessage.objects.retry_deferred()

        # All remaining 3 messages get delivered
        engine.send_all(backend=self.test_backend)

        self.assertEqual(models.QueuedMessage.objects.count(), 0)
        self.assertEqual(models.QueuedMessage.objects.deferred().count(), 0)
        self.assertEqual(models.Log.objects.count(), 5)

    def test_throttling_delivery(self):
        TIME = 1  # throttle time = 1 second

        self.queue_message()
        self.queue_message()

        self.assertEqual(models.QueuedMessage.objects.count(), 2)

        # 3 will be delivered, 2 remain deferred
        start_time = time.time()
        engine.send_all(backend=self.test_backend)
        unthrottled_time = time.time() - start_time

        self.assertEqual(models.QueuedMessage.objects.count(), 0)

        settings.EMAIL_THROTTLE = TIME

        self.queue_message()
        self.queue_message()

        self.assertEqual(models.QueuedMessage.objects.count(), 2)

        # 3 will be delivered, 2 remain deferred
        start_time = time.time()
        engine.send_all(backend=self.test_backend)
        # 2*TIME because 2 emails are sent during the test
        throttled_time = (time.time() - start_time) - 2*TIME

        self.assertEqual(models.QueuedMessage.objects.count(), 0)

        # NOTE This is a bit tricky to test due to possible fluctuations on
        # execution time. This test may sometimes fail
        self.assertAlmostEqual(unthrottled_time, throttled_time, places=1)
