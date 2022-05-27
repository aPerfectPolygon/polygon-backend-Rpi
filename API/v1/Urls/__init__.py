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
			input_body_optional={
				'google_token': [str],
				'email': [str],
				'password': [str],
				'notification_token': [str]
			}
		),
		base_info.path_generator(
			'User/SignupSeries/verify',
			v.User.SignupSeries.verify,
			input_body_required={
				'email': [str],
				'token': [str]
			}
		),
		base_info.path_generator(
			'User/SignupSeries/re_send',
			v.User.SignupSeries.re_send,
			input_body_required={
				'email': [str],
			}
		),
		
		# endregion
		
		# region ForgetPasswordSeries
		base_info.path_generator(
			'User/ForgetPasswordSeries/send',
			v.User.ForgetPasswordSeries.send,
			input_body_required={
				'email': [str],
			}
		),
		base_info.path_generator(
			'User/ForgetPasswordSeries/verify',
			v.User.ForgetPasswordSeries.verify,
			input_body_required={
				'email': [str],
				'token': [str],
			}
		),
		base_info.path_generator(
			'User/ForgetPasswordSeries/change',
			v.User.ForgetPasswordSeries.change,
			input_body_required={
				'email': [str],
				'password': [str],
			}
		),
		# endregion
		
		base_info.path_generator(
			'User/login',
			v.User.login,
			input_body_optional={
				'username': [str],
				'password': [str],
				'polygon_token': [str],
				'google_token': [str]
			}
		),
		
		base_info.path_generator(
			'User/resign',
			v.User.resign,
			token_required=True,
			user_must_be_active=True,
			user_fields_needed={'template': 'info', 'main': ['date_joined']}
		),
		
		base_info.path_generator(
			'User/info',
			v.User.info_,
			token_required=True,
			user_fields_needed={'template': 'info'}
		),
		
		base_info.path_generator(
			'User/change_password',
			v.User.change_password,
			token_required=True,
			user_must_be_active=True,
			user_fields_needed={'main': ['password', 'email']},
			input_body_required={
				'new_password': [str]
			},
			input_body_optional={
				'old_password': [str]
			}
		),
		base_info.path_generator(
			'User/logout',
			v.User.logout,
			token_required=True,
		),
		
		# endregion
		# region Home
		base_info.path_generator(
			'Home/objects',
			v.Home.objects,
		),
		# endregion
	]


app_name = 'api_v1'
urlpatterns = [
	path('App/', include('API.v1.Urls.app_urls', 'api_v1_app')),
	path('Web/', include('API.v1.Urls.web_urls', 'api_v1_web')),
	path('Test/', include('API.v1.Urls.test_urls', 'api_v1_test')),
]
