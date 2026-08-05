#!/usr/bin/env python
# django_shell.py

import argparse

from django.core.management import call_command
from boot_django import boot_django, APP_NAME  # noqa


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('testname', default='', nargs='?',
                        help='Module paths to test; '
                             'can be modulename, modulename.TestCase or modulename.TestCase.test_method')
    parser.add_argument('-v', '--verbosity', default=2, type=int, choices=[0, 1, 2, 3],
                        help='Verbosity level;'
                             ' 0=minimal output, 1=normal output, 2=verbose output, 3=very verbose output')
    parser.add_argument('--canary', action='store_true', help='Run only canary tests (skips canary tests by default)')

    testname = parser.parse_args().testname
    verbosity = parser.parse_args().verbosity
    run_canary = parser.parse_args().canary

    # We still only want to test this app's tests, so if no specific test is supplied,
    # we use the app name to restrict testing
    if not testname:
        testname = APP_NAME

    # If the canary flag is set, we want to run only the canary tests, otherwise we want to exclude them
    if run_canary:
        canary_command_flag = '--tag=canary'
    else:
        canary_command_flag = '--exclude-tag=canary'

    boot_django()
    print(f'running test(s) for {APP_NAME}')
    call_command('test', testname, canary_command_flag, verbosity=verbosity)
