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
	| Link: User/SignupSeries/signup
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
	| status: 201
	| comment: user created and sent token
	| Message: UTILSD.Defaults.Messages.ok
	| Result: UTILSD.main.CustomUser.get_user_info
	| ----------------------------------------------------
	| status: 200
	| comment: user was previously created but not activated (sent token again)
	| Message: UTILSD.Defaults.Messages.ok
	| Result: UTILSD.main.CustomUser.get_user_info
	| ----------------------------------------------------

	Django Errors:
	-----
	main:
		| ---
	links:
		| UTILSD.main.CustomUser.signup
		| UTILSD.Tokens.Email.send  (errors must not happen)
	possible attack:
		| ---
	unexpected:
		| ---
	"""
	email = request.input_body['email']
	password = request.input_body['password']
	
	res = request.User.signup(request, email, password, auto_login=True)
	request = Tokens.Email.send(request, email)
	
	if not isinstance(res, djn_utils.CustomUser):
		# user was previously created buy not activated (sent token again)
		return res
	
	return djn_utils.d_response(
		request,
		djn_def.Messages.ok,
		result=request.User.get_user_info(request),
		code=201
	)


class Email:
	@staticmethod
	def verify(request: djn_utils.CustomRequest, info: djn_utils.ApiInfo):
		"""
		UpdatedAt: ---

		About:
		-----
		verify email token for user

		Input:
		-----
		| Link: User/SignupSeries/Email/verify
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
	
	@staticmethod
	def re_send(request: djn_utils.CustomRequest, info: djn_utils.ApiInfo):
		"""
		UpdatedAt: ---

		About:
		-----
		resend email token to user

		Input:
		-----
		| Link: User/SignupSeries/Email/re_send
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
			| ---
		links:
			| UTILSD.Tokens.Email.send
		possible attack:
			| ---
		unexpected:
			| ---
		"""
		email = request.input_body['email']
		
		request = Tokens.Email.send(request, email)
		return djn_utils.d_response(request, djn_def.Messages.ok)
