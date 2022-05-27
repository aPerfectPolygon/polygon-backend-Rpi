from UTILS.dev_utils.Objects.Google.OAuth import verify as verify_google_token
from UTILSD import Defaults as djn_def
from UTILSD import main as djn_utils, Tokens


def signup(request: djn_utils.CustomRequest, info: djn_utils.ApiInfo):
	"""
	UpdatedAt: ---

	About:
	-----
	sign new users up and return their info

	Input:
	-----
	| Link: User/SignupSeries/signup, User/SignupSeriesV2/signup
	| methods: post
	| recaptcha_action: ss_signup
	| optional body:
	|   email: str -> must match with email regex
	|	password: str -> must match with password regex
	|	google_token: str

	Examples:
	-----
	| {
	| 	"email": "test@gmail.com",
	| 	"password": "**********",
	| }
	| ------------------------------------------------------------

	Response:
	-----
	| status: 201
	| comment: user created and sent token
	| Message: UTILSD.Defaults.Messages.ok
	| Result: UTILSD.main.CustomUser.get_user_info
	| ----------------------------------------------------
	| status: 200
	| comment: user was previously created buy not activated (sent token again)
	| Message: UTILSD.Defaults.Messages.ok
	| Result: UTILSD.main.CustomUser.get_user_info
	| ----------------------------------------------------

	Django Errors:
	-----
	main:
		| ---
	links:
		| UTILSD.main.CustomUser.signup_with_google
		| UTILSD.main.CustomUser.signup_with_email
		| UTILSD.main.CustomUser.set_notification_token
	possible attack:
		| ---
	unexpected:
		| ---
	"""
	email = request.input_body.get('email')
	password = request.input_body.get('password')
	
	google_token = request.input_body.get('google_token')
	
	notification_token = request.input_body.get('notification_token')
	
	if password:
		request.input_body['password'] = '****'
	
	if google_token is not None:
		request.User.signup_with_google(
			request, verify_google_token(google_token), auto_login=True
		)
		return djn_utils.d_response(
			request,
			djn_def.Messages.user_logged_in,
			result=request.User.get_user_info(request),
			code=201
		)
	elif email is not None and password is not None:
		response_code = request.User.signup_with_email(
			request, email, password, auto_login=True
		)
		request = Tokens.Email.send(request)
	else:
		djn_utils.d_raise(
			request,
			djn_def.Messages.bad_input,
			f'non of optional keys were provided {djn_def.Messages.possible_attack}'
		)
		return  # just for ide warnings
	
	if notification_token:
		request.User.set_notification_token(request, notification_token, _do_raise=False)
	
	return djn_utils.d_response(
		request,
		djn_def.Messages.ok,
		result=request.User.get_user_info(request),
		code=response_code
	)


def verify(request: djn_utils.CustomRequest, info: djn_utils.ApiInfo):
	"""
	UpdatedAt: ---

	About:
	-----
	verify email token for user

	Input:
	-----
	| Link: User/SignupSeries/verify
	| methods: post
	| required body:
	|	email: str -> must match with email regex
	|	token: str

	Examples:
	-----
	| {
	| 	"email": "test@gmail.com",
	| 	"token": "12345"
	| }
	| ------------------------------------------------------------

	Response:
	-----
	| status: 200
	| comment: ---
	| Message: UTILSD.Defaults.Messages.ok
	| Result: UTILSD.main.CustomUser.get_user_info
	| ----------------------------------------------------

	Django Errors:
	-----
	main:
		| ---
	links:
		| UTILSD.Tokens.Email.verify
	possible attack:
		| ---
	unexpected:
		| ---
	"""
	email = request.input_body['email']
	token = request.input_body['token']
	
	request = Tokens.Email.verify(request, email, token)
	
	return djn_utils.d_response(
		request,
		djn_def.Messages.ok,
		result=request.User.get_user_info(request),
	)


def re_send(request: djn_utils.CustomRequest, info: djn_utils.ApiInfo):
	"""
	UpdatedAt: ---

	About:
	-----
	resend token to user

	Input:
	-----
	| Link: User/SignupSeries/re_send
	| methods: post
	| required body:
	|	email: str -> must match with email regex

	Examples:
	-----
	| {
	| 	"email": "test@gmail.com",
	| }
	| ------------------------------------------------------------

	Response:
	-----
	| status: 200
	| comment: ---
	| Message: UTILSD.Defaults.Messages.ok
	| Result: UTILSD.main.CustomUser.get_user_info
	| ----------------------------------------------------

	Django Errors:
	-----
	main:
		| status: 409
		| comment: ---
		| Message: UTILSD.Defaults.Messages.already_verified
		| Result: null
		| ----------------------------------------------------
	links:
		| UTILSD.Tokens.Email.send
		| UTILSD.main.check_regex
	possible attack:
		| status: 404
		| comment: (not raised)
		| Message: UTILSD.Defaults.Messages.account_not_found
		| Result: null
		| ----------------------------------------------------
	unexpected:
		| ---
	"""
	email = request.input_body['email']

	request.db.server.schema = 'users_data'
	djn_utils.check_regex(request, email, 'email')
	
	user = request.db.server.read(
		'account_account',
		['id', 'email', 'auth_email', 'status'],
		[("replace(email, '.', '')", '=', email.replace('.', ''))]
	).to_dict('records')
	if user:
		request.User.uid = user[0]['id']
		request.User.email = user[0]['email']
		request.User.auth_email = user[0]['auth_email']
		request.User.status = user[0]['status']
		
		request = Tokens.Email.send(request)
	else:
		djn_utils.d_raise(
			request,
			djn_def.Messages.account_not_found,
			djn_def.Messages.possible_attack,
			code=404,
			do_raise=False
		)

	return djn_utils.d_response(request, djn_def.Messages.ok)
