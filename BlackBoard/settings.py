"""
Django settings for BlackBoard project.

Generated by 'django-admin startproject' using Django 4.0.3.

For more information on this file, see
https://docs.djangoproject.com/en/4.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/4.0/ref/settings/
"""
import sys
import os
import json
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, os.path.join(BASE_DIR, 'apps'))

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.0/howto/deployment/checklist/

with open(os.path.join(BASE_DIR, 'config.json'), 'r') as f:
    ENV = json.load(f)

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = ENV.get('SECRET_KEY', '')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False
DEBUG_LEVEL = 'default'
ALLOWED_HOSTS = ['bbh.yangyq.net', '127.0.0.1']


# Application definition

def _gen_installed_apps():
    yield 'blackboard'
    yield 'wechat'
    if ENV.get('NOTICE_HOMEWORK_DEADLINE', False):
        yield 'django_apscheduler'


INSTALLED_APPS = list(_gen_installed_apps())

# INSTALLED_APPS = [
#     # 'django.contrib.admin',
#     # 'django.contrib.auth',
#     # 'django.contrib.contenttypes',
#     # 'django.contrib.sessions',
#     # 'django.contrib.messages',
#     # 'django.contrib.staticfiles',
#     'blackboard',
#     'wechat',
#     'django_apscheduler'
# ]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    # 'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    # 'django.middleware.csrf.CsrfViewMiddleware',
    # 'django.contrib.auth.middleware.AuthenticationMiddleware',
    # 'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'utils.URLVisitCount.URLVisitCountMiddleware'
]

ROOT_URLCONF = 'BlackBoard.urls'

# TEMPLATES = [
#     {
#         'BACKEND': 'django.template.backends.django.DjangoTemplates',
#         'DIRS': [BASE_DIR / 'templates']
#         ,
#         'APP_DIRS': True,
#         'OPTIONS': {
#             'context_processors': [
#                 'django.template.context_processors.debug',
#                 'django.template.context_processors.request',
#                 'django.contrib.auth.context_processors.auth',
#                 'django.contrib.messages.context_processors.messages',
#             ],
#         },
#     },
# ]

WSGI_APPLICATION = 'BlackBoard.wsgi.application'

# Database
# https://docs.djangoproject.com/en/4.0/ref/settings/#databases


DATABASES = {
    'default': {
        'ENGINE': 'mysql',
        'POOL_SIZE': 30,
        'NAME': ENV.get('MYSQL_NAME', ''),
        'HOST': ENV.get('MYSQL_HOST', '127.0.0.1'),
        'PORT': ENV.get('MYSQL_PORT', 3306),
        'USER': ENV.get('MYSQL_USER', ''),
        'PASSWORD': ENV.get('MYSQL_PASS', ''),
        'CONN_MAX_AGE': 28790
    }
}

if os.getenv('GITHUB_WORKFLOW'):
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        },
        "file":{
            "BACKEND": "django.core.cache.backends.filebased.FileBasedCache",
            "LOCATION":  os.path.join(BASE_DIR, "cache_response"),
        }
    }
else:
    REDIS_HOST = ENV.get('REDIS_HOST', 'localhost')
    REDIS_PORT = ENV.get('REDIS_PORT', 6379)
    REDIS_DB = ENV.get('REDIS_DB', 0)

    CACHES = {
        # "default": {
        #     "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        # },
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}",
            "OPTIONS": {
                "CLIENT_CLASS": "django_redis.client.DefaultClient",
            }
        },
        "file":{
            "BACKEND": "django.core.cache.backends.filebased.FileBasedCache",
            "LOCATION":  os.path.join(BASE_DIR, "cache_response"),
        }
    }

# Password validation
# https://docs.djangoproject.com/en/4.0/ref/settings/#auth-password-validators

# AUTH_PASSWORD_VALIDATORS = [
#     {
#         'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
#     },
#     {
#         'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
#     },
#     {
#         'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
#     },
#     {
#         'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
#     },
# ]

# Internationalization
# https://docs.djangoproject.com/en/4.0/topics/i18n/

LANGUAGE_CODE = 'zh-hans'

TIME_ZONE = 'Asia/Shanghai'

USE_I18N = True

USE_TZ = False

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "notice": {
            'format': '[%(asctime)s] %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S'
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "notice"
        },
        "notice_file": {
            "level": "DEBUG" if DEBUG else "INFO",
            "class": "logging.FileHandler",
            "filename": os.path.join(BASE_DIR, "logs/notice.log"),
            "formatter": "notice"
        },
    },
    "loggers": {
        "utils.scheduler": {
            "handlers": ["console", "notice_file"] if DEBUG else ["notice_file"],
            "level": "DEBUG" if DEBUG else "INFO",
            "propagate": False,
        },
    },
}

REST_FRAMEWORK = {
    # 用于禁用django auth模块
    'DEFAULT_AUTHENTICATION_CLASSES': [],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',
    ],
    'UNAUTHENTICATED_USER': None,
    'DEFAULT_PARSER_CLASSES': (
        'rest_framework.parsers.JSONParser',  # application/json
        'rest_framework.parsers.FormParser',  # application/x-www-form-urlencoded
        'rest_framework.parsers.MultiPartParser',  # multipart/form-data
    ),
    'DEFAULT_RENDERER_CLASSES': ('rest_framework.renderers.JSONRenderer',)
}

FILE_UPLOAD_HANDLERS = [
    "django.core.files.uploadhandler.TemporaryFileUploadHandler"
]

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.0/howto/static-files/

# STATIC_URL = 'static/'

# Default primary key field type
# https://docs.djangoproject.com/en/4.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# MINIAPP settings
APP_ID = ENV.get('APP_ID', '')
APP_SECRET = ENV.get('APP_SECRET', '')
TEMPLATE_ID = ENV.get('TEMPLATE_ID', '')

REST_FRAMEWORK_EXTENSIONS = {
    'DEFAULT_CACHE_KEY_FUNC': 'utils.funcs.key_func',
    'DEFAULT_USE_CACHE': 'default'
}

proxies = {
    # "http": "socks5://127.0.0.1:1080",
    # "https": "socks5://127.0.0.1:1080"
}

NOTICE_HOMEWORK_DEADLINE = ENV.get('NOTICE_HOMEWORK_DEADLINE', False)
