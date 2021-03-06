"""
Django settings for system_conf project.

Generated by 'django-admin startproject' using Django 2.0.6.

For more information on this file, see
https://docs.djangoproject.com/en/2.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/2.0/ref/settings/
"""
# stdlib
import os
import logging
from typing import List
# lib
from logstash_async.formatter import LogstashFormatter
from logstash_async.handler import AsynchronousLogstashHandler
# local
from .settings_local import *


# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Path to the public key (change for development)
PUBLIC_KEY_FILE = os.path.join(BASE_DIR, 'public-key.rsa')

SECRET_KEY = os.getenv('POD_SECRET_KEY', '0!81woi!8^bi51@@fys8%9a3hcz=!46xdf*e+4l*oa!$g#dyl6')
POD_NAME = os.getenv('POD_NAME', 'pod')
ORGANIZATION_URL = os.getenv('ORGANIZATION_URL', 'example.com')

CLOUDCIX_API_USERNAME = os.getenv('CLOUDCIX_API_USERNAME', 'user@example.com')
CLOUDCIX_API_KEY = os.getenv('CLOUDCIX_API_KEY', 'cloudcix_api_key')
CLOUDCIX_API_PASSWORD = os.getenv('CLOUDCIX_API_PASSWORD', 'pw')
CLOUDCIX_API_URL = f'https://legacy_api.{POD_NAME}.{ORGANIZATION_URL}/'
CLOUDCIX_API_V2_URL = f'https://{POD_NAME}.{ORGANIZATION_URL}/'
CLOUDCIX_API_VERSION = 2

PAM_NAME = os.getenv('PAM_NAME', 'pam')
PAM_ORGANIZATION_URL = os.getenv('PAM_ORGANIZATION_URL', 'example.com')

EMAIL_HOST = os.getenv('EMAIL_HOST', f'mail.example.com')
EMAIL_HOST_USER = os.getenv('EMAIL_USER', f'notifications@example.com')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_PASSWORD', 'email_pw')
EMAIL_PORT = os.getenv('EMAIL_PORT', 25)
EMAIL_USE_TLS = True

SUPER_USERS = os.getenv('SUPER_USER_IDS', '').split(',')
SUPER_USERS = [int(i) for i in SUPER_USERS if i != ''] + [1]

INFLUX_PORT = 443
try:
    CLOUDCIX_INFLUX_DATABASE
except NameError:
    ORG = ORGANIZATION_URL.split('.')[0]
    CLOUDCIX_INFLUX_DATABASE = f'{ORG}_metrics'

LOGSTASH_ENABLE = os.getenv('LOGSTASH_ENABLE', False)

if f'{PAM_NAME}.{PAM_ORGANIZATION_URL}' == 'support.cloudcix.com':
    LOGSTASH_ENABLE = True
    INFLUX_URL = 'influx.support.cloudcix.com'
    LOGSTASH_URL = 'logstash.support.cloudcix.com'
    ELASTICSEARCH_DSL = {
        'default': {
            'hosts': 'elasticsearch.support.cloudcix.com'
        },
    }
else:
    LOGSTASH_URL = os.getenv('LOGSTASH_URL', '')
    INFLUX_URL = os.getenv('INFLUX_URL', '')
    ELASTICSEARCH_DSL = {
        'default': {
            'hosts': os.getenv('ELASTICSEARCH_DSL_HOST', '')
        },
    }

if not LOGSTASH_ENABLE:
    logging.disable(logging.CRITICAL)

logger = logging.getLogger()
fmt = logging.Formatter(fmt='%(asctime)s - %(name)s: %(levelname)s: %(message)s', datefmt='%d/%m/%y @ %H:%M:%S')
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(fmt)
logger.addHandler(stream_handler)


# CORS Headers Settings
CORS_ORIGIN_ALLOW_ALL = True
CORS_ALLOW_HEADERS = (
    'x-requested-with',
    'content-type',
    'accept',
    'origin',
    'authorization',
    'x-csrftoken',
    'x-auth-token',
    'x-subject-token',
    'content-disposition',
)
CORS_EXPOSE_HEADERS = (
    'content-type',
    'content-disposition',
)
CORS_ALLOW_METHODS = (
    'GET',
    'POST',
    'PUT',
    'DELETE',
    'PATCH',
    'HEAD',
    'OPTIONS',
)

# Database Routers
# https://docs.djangoproject.com/en/2.0/topics/db/multi-db/
DATABASE_ROUTERS: List[str] = [
    'cloudcix_rest.db_router.CloudCIXRouter',
] + DATABASE_ROUTERS

# Installed apps
INSTALLED_APPS: List[str] = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.staticfiles',
    # CloudCIX Rest
    'cloudcix_rest',
    # Libs
    'rest_framework',
    'corsheaders',
    'raven.contrib.django.raven_compat',
    'django_elasticsearch_dsl'
] + INSTALLED_APPS

# Internationalization
# https://docs.djangoproject.com/en/2.0/topics/i18n/
LANGUAGE_CODE = 'en-ie'
TIME_ZONE = 'UTC'
USE_TZ = False

# Logging
# Temporarily log to stdout
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
}

# Installed Middleware (keep as small as possible)
MIDDLEWARE = [
    'django_jaeger.middleware.DjangoJaegerMiddleware',
    'middleware.MetricsMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'middleware.OpenAPIDeepObjectParserMiddleware',
]

# Rest Framework Settings
REST_FRAMEWORK = {
    # Render as json even without `?format=json`
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    # Use our token auth class for authentication
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'cloudcix_rest.auth.CloudCIXTokenAuth',
    ],
    # Set up throttling
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'user': '20/second',
    },
    # Ensure that by default the user is authenticated before rendering stuff
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    # Set a default model serializer class
    'DEFAULT_MODEL_SERIALIZER_CLASS': (
        'rest_framework.serializers.HyperlinkedModelSerializer'
    ),
    # Set the default format for APIClient requests to be json
    'TEST_REQUEST_DEFAULT_FORMAT': 'json',
}

ROOT_URLCONF = 'system_conf.urls'

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.0/howto/static-files/
STATIC_URL = '/static/'

# Templates
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# Application definition
WSGI_APPLICATION = 'system_conf.wsgi.application'

DOCS_PATH = None
