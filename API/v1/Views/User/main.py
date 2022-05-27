import pandas as pd
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password

from UTILS import engines
from UTILS.dev_utils.Objects.Google.OAuth import verify as verify_google_token
from UTILSD import Defaults as djn_def
from UTILSD import main as djn_utils
from UTILSD.main import Token


def login(request: djn_utils.CustomRequest, info: djn_utils.ApiInfo):
	"""
	UpdatedAt: ---

	About:
	-----
	log users in
	* login can be done via:
		* username/password  (username, email)
		* google_token
		* polygon_token

	Input:
	-----
	| Link: User/login
	| methods: post
	| optional body:
	| 	username: str
	| 	password: str
	| 	polygon_token: str
	| 	google_token: str

	Examples:
	-----
	| {
	| 	"username": "test@gmail.com",
	| 	"password": "This1sP@ssword"
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
		| status: 404
		| comment: ---
		| Message: UTILSD.Defaults.Messages.account_not_found
		| Result: null
		| ----------------------------------------------------
	links:
		| UTILSD.main.CustomUser.login
	possible attack:
		| status: 400
		| comment: none of optional fields were set
		| Message: UTILSD.Defaults.Messages.bad_input
		| Result: null
		| ----------------------------------------------------
		| status: 400
		| comment: google did not verify the token
		| Message: UTILSD.Defaults.Messages.bad_input
		| Result: ---
		| ----------------------------------------------------
	unexpected:
		| ---
	"""
	username = request.input_body.get('username')
	password = request.input_body.get('password')
	polygon_token = request.input_body.get('polygon_token')
	google_token = request.input_body.get('google_token')
	request.db.server.schema = 'users_data'
	
	if google_token:
		google_data = verify_google_token(google_token)
		if not google_data:
			djn_utils.d_raise(
				request,
				djn_def.Messages.bad_input,
				f'google not verified the token {djn_def.Messages.possible_attack}'
			)
		
		uid = request.db.server.read(
			'account_account', ['id'], [("replace(email, '.', '')", '=', google_data['email'].replace('.', ''))]
		).id.tolist()
		if not uid:
			djn_utils.d_raise(
				request,
				djn_def.Messages.account_not_found,
				f'email `{google_data["email"]}`',
				code=404
			)
		request.User.uid = uid[0]
		Token(request).regenerate()
		request.db.server.update(
			'account_account',
			pd.DataFrame([["timezone('utc', now())", request.lang]], columns=['last_login', 'lang']),
			[('id', '=', request.User.uid)]
		)
		request.User.info(request, {'template': 'info', 'main': ['date_joined']})
	elif polygon_token:
		uid = request.db.server.read(
			f'users_token_{info.platform}', ['uid'], [('token', '=', polygon_token)]
		).uid.tolist()
		if not uid:
			djn_utils.d_raise(
				request,
				djn_def.Messages.account_not_found,
				code=404
			)
		request.User.uid = uid[0]
		Token(request).regenerate()
		request.db.server.update(
			'account_account',
			pd.DataFrame([["timezone('utc', now())", request.lang]], columns=['last_login', 'lang']),
			[('id', '=', request.User.uid)]
		)
		request.User.info(request, {'template': 'info', 'main': ['date_joined']})
	elif username and password:
		request.input_body['password'] = '****'
		request.User.login(request, username, password)
	else:
		djn_utils.d_raise(
			request,
			djn_def.Messages.bad_input,
			'none of optional keys were provided',
		)
	
	request.User.update_notification_unread_count(request)
	return djn_utils.d_response(
		request,
		djn_def.Messages.ok,
		result=request.User.get_user_info(request)
	)


def resign(request: djn_utils.CustomRequest, info: djn_utils.ApiInfo):
	"""
	UpdatedAt: ---

	About:
	-----
	change user token

	Input:
	-----
	| Link: User/resign
	| methods: post
	| token required: True
	| user must be active: True

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
		| UTILSD.main.MainMiddleware.utils.check_user_if_required
		| UTILSD.main.MainMiddleware.utils.check_active_user_if_detected
	possible attack:
		| ---
	unexpected:
		| ---
	"""
	request.User.token = djn_utils.Token(request).regenerate()
	request.User.update_notification_unread_count(request)
	
	return djn_utils.d_response(
		request,
		djn_def.Messages.ok,
		result=request.User.get_user_info(request)
	)


def info_(request: djn_utils.CustomRequest, info: djn_utils.ApiInfo):
	"""
	UpdatedAt: ---

	About:
	-----
	return user's info

	Input:
	-----
	| Link: User/info
	| methods: post
	| token required: True

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
		| UTILSD.main.MainMiddleware.utils.check_user_if_required
	possible attack:
		| ---
	unexpected:
		| ---
	"""
	return djn_utils.d_response(
		request,
		djn_def.Messages.ok,
		result=request.User.get_user_info(request)
	)


def logout(request: djn_utils.CustomRequest, info: djn_utils.ApiInfo):
	"""
	UpdatedAt: ---

	About:
	-----
	log user out and delete user's token

	Input:
	-----
	| Link: User/logout
	| methods: post
	| token required: True

	Response:
	-----
	| status: 200
	| comment: ---
	| Message: UTILSD.Defaults.Messages.ok
	| Result: null
	| ----------------------------------------------------

	Django Errors:
	-----
	main:
		| ---
	links:
		| UTILSD.main.MainMiddleware.utils.check_user_if_required
	possible attack:
		| ---
	unexpected:
		| ---
	"""
	djn_utils.Token(request).delete()
	
	# region notification related stuff
	if info.platform == djn_def.Platforms.app:
		column = 'token_app'
	elif info.platform == djn_def.Platforms.web:
		column = 'token_web'
	elif info.platform == djn_def.Platforms.test:
		column = 'token_test'
	else:
		column = None
	
	if column:
		request.db.server.update(
			'users_notification_settings',
			pd.DataFrame([[None]], columns=[column]),
			[('uid', '=', request.User.uid)],
			schema='users_data'
		)
	
	# endregion
	
	return djn_utils.d_response(request, djn_def.Messages.ok)


def change_password(request: djn_utils.CustomRequest, info: djn_utils.ApiInfo):
	"""
	UpdatedAt: ---

	About:
	-----
	change user's password

	Input:
	-----
	| Link: User/change_password
	| methods: post
	| token required: True
	| user must be active: True
	| required body:
	|	new_password: str -> must match with password regex
	| optional body:
	|	old_password: str


	Examples:
	-----
	| {
	| 	"old_password": "**********",
	| 	"new_password": "**********",
	| }
	| ------------------------------------------------------------

	Response:
	-----
	| status: 200
	| comment: ---
	| Message: UTILSD.Defaults.Messages.ok
	| Result: null
	| ----------------------------------------------------

	Django Errors:
	-----
	main:
		| status: 410
		| comment: ---
		| Message: UTILSD.Defaults.Messages.bad_old_password
		| Result: null
		| ----------------------------------------------------
		| status: 409
		| comment: ---
		| Message: UTILSD.Defaults.Messages.repetitive_password
		| Result: null
		| ----------------------------------------------------
		| status: 410
		| comment: user does not have password and cant change it
		| Message: UTILSD.Defaults.Messages.no_password
		| Result: null
		| ----------------------------------------------------
	links:
		| UTILSD.main.MainMiddleware.utils.check_user_if_required
		| UTILSD.main.MainMiddleware.utils.check_active_user_if_detected
		| UTILSD.main.check_regex
	possible attack:
		| ---
	unexpected:
		| ---
	"""
	new_password = request.input_body['new_password']
	old_password = request.input_body.get('old_password', '')
	
	if request.User.password is not None:
		if not check_password(old_password, request.User.password):
			djn_utils.d_raise(
				request,
				djn_def.Messages.bad_old_password,
				code=410
			)
		
		if old_password == new_password:
			djn_utils.d_raise(
				request,
				djn_def.Messages.repetitive_password,
				code=409,
			)
	else:
		djn_utils.d_raise(
			request,
			djn_def.Messages.no_password,
			code=410
		)
	
	djn_utils.check_regex(request, new_password, 'password')
	
	acc = get_user_model().objects.filter(id=request.User.uid)[0]
	acc.set_password(new_password)
	acc.save()
	
	engines.Email.send(
		request.User.email,
		'Password Changed',
		template=djn_def.templates['forget_password']['change']['success'][request.lang],
	)
	return djn_utils.d_response(request, djn_def.Messages.ok)
