from UTILS.prj_utils import Defaults as prj_def


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
	repetitive_password = '[REPETITIVE_PASSWORD]'
	not_available = '[NOT AVAILABLE]'
	
	# endregion

	pass


class Models:
	none = 'None'
	test = 'Test'
	app = 'App'
	
	all = [test, app]


class Platforms:
	none = 'None'
	# when adding platform remember to create users_token_{platform} table
	test = 'Test'
	app = 'App'
	
	all = [test, app]


class TokenExpiration:
	test = 31536000  # 60*60*24*356  ~ 1 year
	app = 31536000  # 60*60*24*356  ~ 1 year


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
			"^(?=.{5,20}$)(?![_.])(?!Candle_)(?!.*[_.]{2})[a-zA-Z0-9._]+(?<![_.])$",  # signup/edit-profile regex
			'not standard',
			regex2="^(?=.{5,20}$)(?![_.])(?!.*[_.]{2})[a-zA-Z0-9._]+(?<![_.])$"  # login regex
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


app_force_version = 39
app_current_version = 39
templates = {
	'main': {
		'error': 'main/error.html',
		'force_update': 'main/force_update.html',
		'success': 'main/success.html',
		'forward': 'main/forward.html',
	}
}
links = {}

indicators = {
	'sbi': [
		'rsi',
		'stochastic',
		'cci',
		'bbands',
		'sma',
		'adx',
		'ichimoku',
		'macd',
		'ema',
		'psar'
	],
	'moi': [
		'candlestick_pattern',
		'harmonic_pattern',
		'trend',
		'fibonacci',
		'elliott_wave'
	]
}
indicators.update({'all': indicators['sbi'] + indicators['moi']})

allowed_hosts = ['127.0.0.1', 'localhost', '195.110.38.214', '212.33.206.19']
if prj_def.ip not in allowed_hosts:
	allowed_hosts.append(prj_def.ip)

descriptions_api_based = {
	'User_update': {
		'type': 'message',
		Messages.ok: 'بروزرسانی حساب کاربری شما با موفقیت انجام شد',
		Messages.regex_error: 'اطلاعات وارد شده در فیلد `{}` اشتباه میباشد'
	},
	'User_SignupSeries_signup': {
		'type': 'message',
		Messages.ok: 'کد قعال سازی با موفقیت ارسال شد',
		Messages.already_exists: 'حساب کاربری قبلا ایجاد شده، لطفا وارد شوید'
	},
}
descriptions_message_based = {}
descriptions_user_info_field_translator = {
	'first_name': {
		'fa': 'نام',
		'en': 'first name',
	},
	'last_name': {
		'fa': 'نام خانوادگی',
		'en': 'last name',
	},
	'username': {
		'fa': 'نام کاربری',
		'en': 'username',
	},
	'password': {
		'fa': 'رمز عبور',
		'en': 'password',
	},
	'email': {
		'fa': 'ایمیل',
		'en': 'email',
	},
}

social_urls = []
support_email = 'elyasnz.1999@gmail.com'
