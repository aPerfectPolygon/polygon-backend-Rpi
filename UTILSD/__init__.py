def configure_django_with_project_settings():
	from django.conf import settings as django_settings

	if not django_settings.configured:
		import Rpi.settings as project_settings
		from django.conf import global_settings
		from django import setup

		django_settings.configure(
			global_settings,

			BASE_DIR=project_settings.BASE_DIR,
			SECRET_KEY=project_settings.SECRET_KEY,
			DEBUG=project_settings.DEBUG,
			APPEND_SLASH=project_settings.APPEND_SLASH,
			ALLOWED_HOSTS=project_settings.ALLOWED_HOSTS,
			REST_FRAMEWORK=project_settings.REST_FRAMEWORK,
			INSTALLED_APPS=project_settings.INSTALLED_APPS,
			MIDDLEWARE=project_settings.MIDDLEWARE,
			ROOT_URLCONF=project_settings.ROOT_URLCONF,
			TEMPLATES=project_settings.TEMPLATES,
			DATABASES=project_settings.DATABASES,
			AUTH_USER_MODEL=project_settings.AUTH_USER_MODEL,
			WSGI_APPLICATION=project_settings.WSGI_APPLICATION,
			CONN_MAX_AGE=project_settings.CONN_MAX_AGE,
			AUTH_PASSWORD_VALIDATORS=project_settings.AUTH_PASSWORD_VALIDATORS,
			LANGUAGE_CODE=project_settings.LANGUAGE_CODE,
			TIME_ZONE=project_settings.TIME_ZONE,
			USE_I18N=project_settings.USE_I18N,
			USE_L10N=project_settings.USE_L10N,
			USE_TZ=project_settings.USE_TZ,
			MEDIA_ROOT=project_settings.MEDIA_ROOT,
			MEDIA_URL=project_settings.MEDIA_URL,
			STATIC_ROOT=project_settings.STATIC_ROOT,
			STATIC_URL=project_settings.STATIC_URL,


		)
		setup()
