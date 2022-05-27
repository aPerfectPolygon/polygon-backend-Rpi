from UTILSD import Defaults as djn_def
from UTILSD import main as djn_utils, Tokens


def send(request: djn_utils.CustomRequest, info: djn_utils.ApiInfo):
	"""
	UpdatedAt: ---

	About:
	-----
	send forget password token to user

	Input:
	-----
	| Link: User/ForgetPasswordSeries/send
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
	| Result: null
	| ----------------------------------------------------

	Django Errors:
	-----
	main:
		| ---
	links:
		| UTILSD.Tokens.ForgetPassword.send
	possible attack:
		| ---
	unexpected:
		| ---
	"""
	email = request.input_body['email']

	request = Tokens.ForgetPassword.send(request, email)
	return djn_utils.d_response(request, djn_def.Messages.ok)


def verify(request: djn_utils.CustomRequest, info: djn_utils.ApiInfo):
	"""
	UpdatedAt: ---

	About:
	-----
	verify user's ForgetPassword token

	Input:
	-----
	| Link: User/ForgetPasswordSeries/verify
	| methods: post
	| required body:
	|	email: str -> must match with email regex
	|	token: str

	Examples:
	-----
	| {
	| 	"email": "test@gmail.com",
	| 	"token": "12345",
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
		| ---
	links:
		| UTILSD.Tokens.ForgetPassword.verify
	possible attack:
		| ---
	unexpected:
		| ---
	"""
	email = request.input_body['email']
	token = request.input_body['token']

	request = Tokens.ForgetPassword.verify(request, email, token)
	return djn_utils.d_response(request, djn_def.Messages.ok)


def change(request: djn_utils.CustomRequest, info: djn_utils.ApiInfo):
	"""
	UpdatedAt: ---

	About:
	-----
	change user's password after verifying password

	Input:
	-----
	| Link: User/ForgetPasswordSeries/change
	| methods: post
	| required body:
	|	email: str -> must match with email regex
	|	password: str -> must match with password regex

	Examples:
	-----
	| {
	| 	"email": "test@gmail.com",
	| 	"password": "**********",
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
		| ---
	links:
		| UTILSD.Tokens.ForgetPassword.change
	possible attack:
		| ---
	unexpected:
		| ---
	"""
	email = request.input_body['email']
	password = request.input_body['password']
	request.input_body['password'] = '******'
	
	request = Tokens.ForgetPassword.change(request, email, password)
	return djn_utils.d_response(request, djn_def.Messages.ok)
