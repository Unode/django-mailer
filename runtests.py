#!/usr/bin/env python
# encoding: utf-8
# ----------------------------------------------------------------------------

import os
import sys
import socket
import atexit
from time import sleep
from subprocess import Popen

parent = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, parent)
os.environ['DJANGO_SETTINGS_MODULE'] = 'django_mailer.testapp.settings'

# Django 1.7 and later requires a separate .setup() call
import django
try:
    django.setup()
except AttributeError:
    pass

from django.test.simple import DjangoTestSuiteRunner


# Helper functions to check if the smtpd server is listening

def get_IPs(hostname):
    output = {}
    addrs = socket.getaddrinfo(hostname, 0, 0, 0, socket.IPPROTO_TCP)

    for family, socktype, proto, canonname, sockaddr in addrs:
        addr = sockaddr[0]
        output[family] = addr

    return output


def port_used(addr="localhost", port=None):
    "Return True if port is in use, False otherwise"
    if port is None:
        raise TypeError("Argument 'port' may not be None")

    # If we got an address name, resolve it both to IPv6 and IPv4.
    IPs = get_IPs(addr)

    # Prefer IPv4
    for family in (socket.AF_INET, socket.AF_INET6):
        try:
            addr = IPs[family]
        except KeyError:
            continue

        s = socket.socket(family, socket.SOCK_STREAM)
        result = s.connect_ex((addr, port))
        s.close()
        if result == 0:
            # connection was successful
            return True
    else:
        return False


def wait_for_listen(port, timeout=10, frequency=2.0):
    # timeout = seconds
    # frequency = times per second
    for i in range(int(timeout * frequency)):
        if port_used(port=port):
            return True
        else:
            sleep(1.0 / frequency)


def runtests(*test_args):
    devnull = open(os.devnull, 'w')
    daemon = Popen(["python", "-m", "smtpd", "-n", "-c", "DebuggingServer",
                    "localhost:1025"], stdout=devnull, stderr=devnull)
    atexit.register(daemon.kill)

    if not wait_for_listen(1025):
        # Daemon failed to start
        sys.exit(-1)

    test_args = test_args or ['testapp']

    parent = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, parent)
    runner = DjangoTestSuiteRunner(verbosity=1, interactive=True,
                                   failfast=False)
    failures = runner.run_tests(test_args)

    daemon.kill()

    sys.exit(failures)


if __name__ == '__main__':
    runtests()
