"""
WSGI config for workease project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.1/howto/deployment/wsgi/
"""

import os
import logging

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'workease.settings')

application = get_wsgi_application()

# Safe auto-migration on deployment / container start when DATABASE_URL is configured
if os.environ.get('DATABASE_URL'):
    try:
        from django.core.management import call_command
        call_command('migrate', interactive=False)
    except Exception as e:
        logging.getLogger(__name__).warning(f"Auto-migration skipped or failed: {e}")
