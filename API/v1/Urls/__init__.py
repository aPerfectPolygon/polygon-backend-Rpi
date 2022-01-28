from django.urls import path, include

from API.v1 import Views as v
from UTILS.dev_utils import Defaults as dev_def
from UTILSD import main as djn_utils


def url_patterns(base_info: djn_utils.ApiInfo):
	return [
		# region User
		
		# region SignupSeries
		base_info.path_generator(
			'User/SignupSeries/signup',
			v.User.SignupSeries.signup,
			input_body_required={
				'email': [str],
				'password': [str]
			},
		),
		base_info.path_generator(
			'User/SignupSeries/Email/verify',
			v.User.SignupSeries.Email.verify,
			input_body_required={
				'email': [str],
				'token': [str]
			}
		),
		base_info.path_generator(
			'User/SignupSeries/Email/re_send',
			v.User.SignupSeries.Email.re_send,
			input_body_required={
				'email': [str],
			}
		),
		
		# endregion
		
		# endregion
	]


app_name = 'api_v1'
urlpatterns = [
	path('App/', include('API.v1.Urls.app_urls', 'api_v1_app')),
]
if not dev_def.is_server:
	urlpatterns.append(path('Test/', include('API.v1.Urls.test_urls', 'api_v1_test')))
