import os

from UTILSD.Defaults import *
from UTILS.dev_utils.Database.Psql.main import Databases
from UTILS.prj_utils import Defaults as prj_def

# if a variable is added
#   remember to add it to configure_django_with_project_settings()

BASE_DIR = prj_def.project_root
SECRET_KEY = 'E$XGchn$456&6ref+[}][xvdf76dSh65$%tare'
DEBUG = not prj_def.is_server
# DEBUG = True
APPEND_SLASH = False
ALLOWED_HOSTS = '*'
REST_FRAMEWORK = {
	'DEFAULT_AUTHENTICATION_CLASSES': [],
	'DEFAULT_PERMISSION_CLASSES': [],
	'DEFAULT_RENDERER_CLASSES': [
		'rest_framework.renderers.JSONRenderer',
	],
	'EXCEPTION_HANDLER': 'DUtils.CustomFunctions._d_exception_handler',
}

INSTALLED_APPS = [
	'account',
	'datetimeutc',
	
	'django.contrib.admin',
	'django.contrib.auth',
	'django.contrib.contenttypes',
	'django.contrib.sessions',
	'django.contrib.messages',
	'django.contrib.staticfiles',
	'rest_framework',
]

MIDDLEWARE = [
	'UTILSD.main.FakeHeadersMiddleware',
	
	'django.middleware.security.SecurityMiddleware',
	'django.contrib.sessions.middleware.SessionMiddleware',
	'django.middleware.common.CommonMiddleware',
	# 'django.middleware.csrf.CsrfViewMiddleware',
	'django.contrib.auth.middleware.AuthenticationMiddleware',
	'django.contrib.messages.middleware.MessageMiddleware',
	'django.middleware.clickjacking.XFrameOptionsMiddleware',
	
	'UTILSD.main.MainMiddleware',
]
ROOT_URLCONF = 'Rpi.urls'

TEMPLATES = [
	{
		'BACKEND': 'django.template.backends.django.DjangoTemplates',
		'DIRS': [BASE_DIR / 'templates'],
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

DATABASES = {
	'default': {
		'ENGINE': 'django.db.backends.postgresql_psycopg2',
		'NAME': Databases['default']['name'],
		'USER': Databases['default']['user'],
		'PASSWORD': Databases['default']['pass'],
		'HOST': Databases['default']['host'],
		'PORT': str(Databases['default']['port']),
		'OPTIONS': {
			'options': f'-c search_path="users_data"'
		},
	}
}

AUTH_USER_MODEL = 'account.Account'
WSGI_APPLICATION = 'Rpi.wsgi.application'
CONN_MAX_AGE = 300

AUTH_PASSWORD_VALIDATORS = [
	{
		'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
	},
	{
		'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
	},
	{
		'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
	},
	{
		'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
	},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_L10N = True
USE_TZ = False
MEDIA_ROOT = BASE_DIR / 'media'
MEDIA_URL = '/media/'
STATIC_ROOT = None
STATIC_URL = 'static/'
DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'

