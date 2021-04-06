#!/usr/bin/env python
# django_shell.py

from django.core.management import call_command
from boot_django import boot_django, APP_NAME  # noqa


boot_django()
print(f'running canary tests for {APP_NAME}')
call_command('test', APP_NAME, '--tag=canary', verbosity=2)

# TODO: consider collecting switches and arguments
#  from the command line (like -v or a specific test module
#  or function) and passing them on to call command
