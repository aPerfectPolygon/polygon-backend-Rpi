import copy

from UTILS import Cache
from UTILS.prj_utils import Defaults as prj_def


class Messages:
	# region main
	ok = '[OK]'
	not_found = '[NOT FOUND]'
	unexpected = '[UNEXPECTED ERROR]'
	bad_input = '[BAD INPUT]'
	bad_recaptcha = '[BAD RECAPTCHA]'
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
	ip_blocked = '[IP BLOCKED]'
	email_not_found = '[EMAIL NOT FOUND]'
	user_logged_in = '[USER LOGGED IN]'
	no_password = '[NO PASSWORD]'
	# endregion
	
	# region change password
	bad_old_password = '[BAD OLD PASSWORD]'
	repetitive_password = '[REPETITIVE_PASSWORD]'
	# endregion
	
	# region ProfileUpdate
	username_already_exists = '[USERNAME ALREADY EXISTS]'
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
		'first_name': _r(
			r"^[\u0621-\u0628\u062A-\u063A\u0641-\u0642\u0644-\u0648\u064E-\u0651\u0655\u067E\u0686\u0698\u0020\u2000-\u200F\u2028-\u202F\u06A9\u06AF\u06BE\u06CC\u0629\u0643\u0649-\u064B\u064D\u06D5A-Za-z]{1,30}$",
			'len<30 && cant contain illegal characters'
		),
		'last_name': _r(
			r"^[\u0621-\u0628\u062A-\u063A\u0641-\u0642\u0644-\u0648\u064E-\u0651\u0655\u067E\u0686\u0698\u0020\u2000-\u200F\u2028-\u202F\u06A9\u06AF\u06BE\u06CC\u0629\u0643\u0649-\u064B\u064D\u06D5A-Za-z]{1,30}$",
			'len<30 && cant contain illegal characters'
		),
		'username': _r(
			"^[a-zA-Z](?=.{5,20}$)(?![_.])(?!polygon_)(?!.*[_.]{2})[a-zA-Z0-9._]+(?<![_.])$",
			# signup/edit-profile regex
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
	'email': {
		'already_verified': {
			prj_def.Languages.fa: 'email/already_verified/fa-ir.html',
			prj_def.Languages.en: 'email/already_verified/en-us.html',
		},
		'already_used': {
			prj_def.Languages.fa: 'email/already_used/fa-ir.html',
			prj_def.Languages.en: 'email/already_used/en-us.html',
		},
		'expired': {
			prj_def.Languages.fa: 'email/expired/fa-ir.html',
			prj_def.Languages.en: 'email/expired/en-us.html',
		},
		'to_confirm': {
			prj_def.Languages.fa: 'email/to_confirm/fa-ir.html',
			prj_def.Languages.en: 'email/to_confirm/en-us.html',
		},
		'confirmed': {
			prj_def.Languages.fa: 'email/confirmed/fa-ir.html',
			prj_def.Languages.en: 'email/confirmed/en-us.html',
		},
	},
	'forget_password': {
		'send': {
			'success': {
				prj_def.Languages.fa: 'forget_password/send/success/fa-ir.html',
				prj_def.Languages.en: 'forget_password/send/success/en-us.html',
			}
		},
		'change': {
			'success': {
				prj_def.Languages.fa: 'forget_password/change/success/fa-ir.html',
				prj_def.Languages.en: 'forget_password/change/success/en-us.html',
			}
		},
		'verify': {
			'success': {
				prj_def.Languages.fa: 'forget_password/verify/success/fa-ir.html',
				prj_def.Languages.en: 'forget_password/verify/success/en-us.html',
			},
			'already_used': {
				prj_def.Languages.fa: 'forget_password/verify/already_used/fa-ir.html',
				prj_def.Languages.en: 'forget_password/verify/already_used/en-us.html',
			},
			'already_verified': {
				prj_def.Languages.fa: 'forget_password/verify/already_verified/fa-ir.html',
				prj_def.Languages.en: 'forget_password/verify/already_verified/en-us.html',
			},
			'expired': {
				prj_def.Languages.fa: 'forget_password/verify/expired/fa-ir.html',
				prj_def.Languages.en: 'forget_password/verify/expired/en-us.html',
			}
		}
	},
	'main': {
		'error': {
			prj_def.Languages.fa: 'main/error/fa-ir.html',
			prj_def.Languages.en: 'main/error/en-us.html',
		},
		'success': {
			prj_def.Languages.fa: 'main/success/fa-ir.html',
			prj_def.Languages.en: 'main/success/en-us.html',
		},
	},
}
links = {
	'api_domain': prj_def.api_domain
}

allowed_hosts = [
	'127.0.0.1', 'localhost', prj_def.host
]
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

recaptcha_hosts = []
recaptcha_package_names = []
