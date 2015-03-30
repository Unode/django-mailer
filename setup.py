#!/usr/bin/env python
# encoding: utf-8
# ----------------------------------------------------------------------------

from setuptools import setup
from django_mailer import get_version

setup(
    name='django-mailer-2',
    version=get_version(),
    description=("A reusable Django app for queueing the sending of email "
                 "(forked aaloy on a frok from James Tauber's django-mailer)"),
    long_description=open('docs/usage.rst').read(),
    author='Antoni Aloy',
    author_email='antoni.aloy@gmail.com',
    url='http://github.com/APSL/django-mailer-2',
    install_requires = [
        'Django>=1.4',
        'pyzmail>=1.0.3',
        'lockfile>=0.8',
    ],
    packages=[
        'django_mailer',
        'django_mailer.management',
        'django_mailer.management.commands',
    ],
    include_package_data=True,
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Framework :: Django',
    ]
)
