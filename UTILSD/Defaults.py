import copy

from UTILS.prj_utils import Defaults as prj_def
from UTILS import Cache


class Messages:
	# region main
	ok = '[OK]'
	unexpected = '[UNEXPECTED ERROR]'
	bad_input = '[BAD INPUT]'
	regex_error = '[REGEX ERROR]'
	market_unavailable = '[MARKET UNAVAILABLE]'
	not_found_404 = '[404 Not Found]'
	access_blocked = '[ACCESS BLOCKED]'
	get_social = '[GET SOCIAL]'
	redirection = '[REDIRECTION]'
	bad_timestamp = '[BAD TIMESTAMP]'
	method_not_allowed = '[METHOD NOT ALLOWED]'
	possible_attack = '[POSSIBLE ATTACK]'
	encryption_at_risk = '[ENCRYPTION AT RISK]'
	email_encoding_at_risk = '[EMAIL ENCODING AT RISK]'
	out_of_date = '[OUT OF DATE]'
	bad_token = '[BAD TOKEN]'
	must_not_happen = '[MUST NOT HAPPEN]'
	inactive_user = '[INACTIVE_USER]'
	suspended_user = '[SUSPENDED_USER]'
	already_exists = '[ALREADY EXISTS]'
	already_verified = '[ALREADY VERIFIED]'
	already_used = '[ALREADY USED]'
	no_token = '[NO TOKEN]'
	token_expired = '[TOKEN EXPIRED]'
	account_not_found = '[ACCOUNT NOT FOUND]'
	referral_not_found = '[REFERRAL NOT FOUND]'
	not_available = '[NOT AVAILABLE]'
	# endregion
	
	# region change password
	bad_old_password = '[BAD OLD PASSWORD]'
	repetitive_password = '[REPETITIVE_PASSWORD]'
	# endregion
	
	pass


class Models:
	none = 'None'
	test = 'Test'
	app = 'App'
	web = 'Web'
	
	all = [test, app, web]


class Platforms:
	none = 'None'
	# when adding platform remember to create users_token_{platform} table
	test = 'Test'
	app = 'App'
	web = 'Web'
	
	all = [test, app, web]


class TokenExpiration:
	test = 31536000  # 60*60*24*356  ~ 1 year
	app = 31536000  # 60*60*24*356  ~ 1 year
	web = 31536000  # 60*60*24*356  ~ 1 year


def _r(r, e, **kwargs):
	return {'regex': r, 'err': e, **kwargs}


class Fields:
	# persian numbers = \u06F0-\u06F9
	status_map = {
		'active': 'ACTIVE',
		'inactive': 'INACTIVE',
		'suspended': 'SUSPENDED',
	}
	regex_map = {
		'username': _r(
			"^[a-zA-Z](?=.{5,20}$)(?![_.])(?!polygon_)(?!.*[_.]{2})[a-zA-Z0-9._]+(?<![_.])$",  # signup/edit-profile regex
			'not standard',
			regex2="^[a-zA-Z](?=.{5,20}$)(?![_.])(?!.*[_.]{2})[a-zA-Z0-9._]+(?<![_.])$"  # login regex
		),
		'password': _r(
			# r'(?=.{9,})(?=.*?[^\w\s])(?=.*?[0-9])(?=.*?[A-Z]).*?[a-z].*'
			# r"^(?=.*[A-Za-z].*)(?=.*[0-9].*)[A-Za-z0-9]{8,}$"
			r"^(?=.*[A-Za-z])(?=.*[0-9]).{8,}$",
			'Password Too Weak',
			ignore_illegal_chars=True
		),
		'email': _r(
			r"^(?!\.)(?!.*\.$)(?!.*?\.\.)[a-zA-Z0-9._-]{0,61}@(?!\.)[a-zA-Z]+\.(?!\.)[a-zA-Z]+$",
			'not standard',
			ignore_illegal_chars=True
		),
	}


app_force_version = 1
app_current_version = 1
templates = {
	'main': {
		'error': {
			prj_def.Languages.fa: 'main/error/fa-ir.html',
			prj_def.Languages.en: 'main/error/en-us.html',
		},
		'success': {
			prj_def.Languages.fa: 'main/success/fa-ir.html',
			prj_def.Languages.en: 'main/success/en-us.html',
		},
		'forward': {
			prj_def.Languages.fa: 'main/forward/fa-ir.html',
			prj_def.Languages.en: 'main/forward/en-us.html',
		}
	},
	'email': {
		'signupSeries': {
			'signup': {
				prj_def.Languages.fa: 'email/signupSeries/signup/fa-ir.html',
				prj_def.Languages.en: 'email/signupSeries/signup/en-us.html',
			},
			'welcome': {
				prj_def.Languages.fa: 'email/signupSeries/welcome/fa-ir.html',
				prj_def.Languages.en: 'email/signupSeries/welcome/en-us.html',
			},
		},
		'forgetPasswordSeries': {
			'to_change': {
				prj_def.Languages.fa: 'email/forgetPasswordSeries/to_change/fa-ir.html',
				prj_def.Languages.en: 'email/forgetPasswordSeries/to_change/en-us.html',
			},
			'changed': {
				prj_def.Languages.fa: 'email/forgetPasswordSeries/changed/fa-ir.html',
				prj_def.Languages.en: 'email/forgetPasswordSeries/changed/en-us.html',
			},
		}
	}
}
links = {}

allowed_hosts = ['127.0.0.1', 'localhost', Cache.host.split(':')[0]]
if prj_def.ip not in allowed_hosts:
	allowed_hosts.append(prj_def.ip)

descriptions_api_based = {}
for api_msg, trns in Cache.translations['description_based_on_api'].by_key.items():
	api, msg = api_msg.split('.')
	if api not in descriptions_api_based:
		descriptions_api_based.update({api: {'type': 'message'}})
	descriptions_api_based[api].update({getattr(Messages, msg): {'type': 'lang', **trns}})
descriptions_message_based = {
	getattr(Messages, msg): {'type': 'lang', **trns}
	for msg, trns in Cache.translations['descriptions_based_on_message'].by_key.items()
}
descriptions_user_info_field_translator = copy.deepcopy(
	Cache.translations['descriptions_user_info_field_translator'].by_key
)

social_urls = []
support_email = 'elyasnz.1999@gmail.com'
