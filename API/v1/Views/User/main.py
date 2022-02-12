from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password

from UTILS import engines
from UTILSD import Defaults as djn_def
from UTILSD import main as djn_utils


def login(request: djn_utils.CustomRequest, info: djn_utils.ApiInfo):
	"""
	UpdatedAt: ---

	About:
	-----
	log users in (login can be done via email or username)

	Input:
	-----
	| Link: User/login
	| methods: post
	| required body:
	| 	username: str
	| 	password: str

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
		| ---
	links:
		| UTILSD.main.CustomUser.login
	possible attack:
		| ---
	unexpected:
		| ---
	"""
	username = request.input_body['username']
	password = request.input_body['password']
	request.input_body['password'] = '****'
	
	request.User.login(request, username, password)
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
	| required body:
	|	old_password: str
	|	new_password: str -> must match with password regex

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
		| status: 400
		| comment: ---
		| Message: UTILSD.Defaults.Messages.bad_old_password
		| Result: null
		| ----------------------------------------------------
		| status: 409
		| comment: ---
		| Message: UTILSD.Defaults.Messages.repetitive_password
		| Result: null
		| ----------------------------------------------------
	links:
		| UTILSD.main.check_regex
	possible attack:
		| ---
	unexpected:
		| ---
	"""
	old_password = request.input_body['old_password']
	new_password = request.input_body['new_password']
	
	if not check_password(old_password, request.User.password):
		djn_utils.d_raise(
			request,
			djn_def.Messages.bad_old_password,
		)
	
	if old_password == new_password:
		djn_utils.d_raise(
			request,
			djn_def.Messages.repetitive_password,
			code=409,
		)
	
	djn_utils.check_regex(request, new_password, 'password')
	
	acc = get_user_model().objects.filter(id=request.User.uid)[0]
	acc.set_password(new_password)
	acc.save()
	
	engines.Email.send(
		request.User.email,
		'Password Changed',
		template=djn_def.templates['email']['forgetPasswordSeries']['changed'],
	)
	return djn_utils.d_response(request, djn_def.Messages.ok)
