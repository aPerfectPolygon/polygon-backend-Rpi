# noinspection PyUnresolvedReferences
from UTILS.__defaults__ import *

# host = 'test.polygon.io'
host = ip

if is_server:
	api_domain = f'http://{host}/'
else:
	api_domain = f'http://{ip}:5947/'

fcm_api_key = ''  # fillme
kavenegar_key = ''  # fillme
recaptcha_secret_app = ''  # fillme
recaptcha_secret_web = ''  # fillme
