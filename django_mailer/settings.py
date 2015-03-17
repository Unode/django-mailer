from django.conf import settings
from django_mailer import constants

# Provide a way of temporarily pausing the sending of mail.
PAUSE_SEND = getattr(settings, "MAILER_PAUSE_SEND", False)

USE_BACKEND = getattr(settings, 'MAILER_USE_BACKEND',
                      'django.core.mail.backends.smtp.EmailBackend')

# Default priorities for the mail_admins and mail_managers methods.
MAIL_ADMINS_PRIORITY = getattr(settings, 'MAILER_MAIL_ADMINS_PRIORITY',
                               constants.PRIORITY_HIGH)
MAIL_MANAGERS_PRIORITY = getattr(settings, 'MAILER_MAIL_MANAGERS_PRIORITY',
                                 None)

# When queue is empty, how long to wait (in seconds) before checking again.
EMPTY_QUEUE_SLEEP = getattr(settings, "MAILER_EMPTY_QUEUE_SLEEP", 30)

# Lock timeout value. how long to wait for the lock to become available.
# default behavior is to never wait for the lock to be available.
# lockfile has a bug dealing with negative values so ensure it's always >= 0
LOCK_WAIT_TIMEOUT = max(getattr(settings, "MAILER_LOCK_WAIT_TIMEOUT", 0), 0)

# An optional alternate lock path, potentially useful if you have multiple
# projects running on the same server.
LOCK_PATH = getattr(settings, "MAILER_LOCK_PATH", None)


# Controls for delivery
# Allow sending a fixed/limited amount of emails in each delivery run
# defaults to None which means send everything in the queue
EMAIL_MAX_SENT = getattr(settings, "MAILER_EMAIL_MAX_SENT", None)

# Stop sending emails in the current round if more than X emails get deferred
# defaults to None which means keep going regardless
EMAIL_MAX_DEFERRED = getattr(settings, "MAILER_EMAIL_MAX_DEFERRED", None)

# When delivering, wait some time between emails to avoid server overload
# defaults to 0 for no waiting
EMAIL_THROTTLE = getattr(settings, "MAILER_EMAIL_THROTTLE", 0)
