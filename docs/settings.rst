========
Settings
========

Following is a list of settings which can be added to your Django settings
configuration. All settings are optional and the default value is listed for
each.


MAILER_PAUSE_SEND
-----------------
Provides a way of temporarily pausing the sending of mail. Defaults to
``False``.

If this setting is ``True``, mail will not be sent when the ``send_mail``
command is called.


MAILER_USE_BACKEND
------------------
*Django 1.2 setting*

The mail backend to use when actually sending e-mail.
Defaults to ``'django.core.mail.backends.smtp.EmailBackend'``


MAILER_MAIL_ADMINS_PRIORITY
---------------------------
The default priority for messages sent via the ``mail_admins`` function of
Django Mailer 2.

The default value is ``constants.PRIORITY_HIGH``. Valid values are ``None``
or any of the priority from ``django_mailer.constants``:
``PRIORITY_EMAIL_NOW``, ``PRIORITY_HIGH``, ``PRIORITY_NORMAL`` or
``PRIORITY_LOW``.


MAILER_MAIL_MANAGERS_PRIORITY
-----------------------------
The default priority for messages sent via the ``mail_managers`` function of
Django Mailer 2.

The default value is ``None``. Valid values are the same as for
`MAILER_MAIL_ADMINS_PRIORITY`_.


MAILER_EMPTY_QUEUE_SLEEP
------------------------
For use with the ``django_mailer.engine.send_loop`` helper function. 

When queue is empty, this setting controls how long to wait (in seconds)
before checking again. Defaults to ``30``. 


MAILER_LOCK_WAIT_TIMEOUT
------------------------
A lock is set while the ``send_mail`` command is being run. This controls the
maximum number of seconds the command should wait if a lock is already in
place.

The default value is ``0`` which means to never wait for the lock to be
available.


MAILER_EMAIL_MAX_SENT
---------------------
When using the ``send_all`` or ``send_loop`` strategies, control how many
successful emails are sent before stopping the current delivery round.

If set to a positive integer, unprocessed emails will be evaluated in
subsequent delivery rounds.

The default value is ``None`` which means deliver all email in the queue in the
current round.


MAILER_EMAIL_MAX_DEFERRED
-------------------------
When using the ``send_all`` or ``send_loop`` strategies, control after how many
deferred emails the current delivery round is stopped.

If set to a positive integer, unprocessed emails will be evaluated in
subsequent delivery rounds.

The default value is ``None`` which means keep going regardless how many emails
get deferred.


MAILER_EMAIL_THROTTLE
---------------------
When using the ``send_all`` or ``send_loop`` strategies, introduce a pause
between the delivery of every message.

This variable gets passed to ``time.sleep()`` so any floating point value
should work. A value of ``0.5`` means 500 milliseconds of pause between emails.

The default value is ``0`` which means no pause between messages, in other words, deliver as fast as it can.
