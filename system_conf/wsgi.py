"""
WSGI config for system_conf project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/2.0/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application
from raven.contrib.django.raven_compat.middleware.wsgi import Sentry

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'system_conf.settings')

application = Sentry(get_wsgi_application())
release = os.environ.get('RELEASE', 'test')
