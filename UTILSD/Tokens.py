# uncomment if you want to run this file separately
# from UTILSD import configure_django_with_project_settings
# configure_django_with_project_settings()

import datetime as _dt

import pandas as pd
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password

import UTILS.engines as engines
from UTILS.dev_utils.Objects import Int, Time
from UTILSD import Defaults as djn_def
from UTILSD import main as djn_utils


class Email:
	@staticmethod
	def send(request: djn_utils.CustomRequest, email: str, **kwargs) -> djn_utils.CustomRequest:
		"""
		UpdatedAt: ---

		About:
		-----
		generate and send token to `email`

		Params:
		-----
		**kwargs:
			token: str, default: None
				to send this token except auto-generated token

		Django Errors:
		-----
		main:
			| status: 404
			| comment: no user found  (not raised)
			| Message: UTILSD.Defaults.Messages.account_not_found
			| Result: null
			| ----------------------------------------------------
			| status: 409
			| comment: ---
			| Message: UTILSD.Defaults.Messages.already_verified
			| Result: null
			| ----------------------------------------------------
			| status: 403
			| comment: suspended user
			| Message: UTILSD.Defaults.Messages.suspended_user
			| Result: null
			| ----------------------------------------------------
		links:
			| UTILSD.main.check_regex
		possible attack:
			| ---
		unexpected:
			| ---
		"""
		djn_utils.check_regex(request, email, 'email')
		
		request.db.server.schema = 'users_data'
		user = list(request.db.server.read(
			'account_account',
			['main_table.id', 'auth_email', 'status'],
			[('email', '=', email)],
			[('inner', 'users_data.users_info', 'info', 'main_table.id', '=', 'info.uid')]
		).values)
		if not user:
			djn_utils.d_raise(
				request,
				djn_def.Messages.account_not_found,
				f'no user found with email `{email}` (not raised)',
				code=404,
				do_raise=False
			)
			return request
		
		request.User.uid, request.User.auth_email, request.User.status = user[0]
		request.User.email = email
		user = request.User
		
		if request.User.auth_email:
			djn_utils.d_raise(
				request,
				djn_def.Messages.already_verified,
				f'{email} user({user.uid})',
				code=409
			)
		if request.User.status == djn_def.Fields.status_map['suspended']:
			djn_utils.d_raise(
				request,
				djn_def.Messages.suspended_user,
				f'user is {request.User.status}',
				code=403,
			)
		
		request.User.authenticate_email(request, new_status=False)
		token = kwargs.pop('token', Int.gen_random(5))
		
		request.db.server.delete('tokens_email', [('uid', '=', user.uid)])
		request.db.server.insert('tokens_email', pd.DataFrame(columns=['uid', 'token'], data=[[user.uid, token]]))
		engines.Email.send(user.email, 'SignUpVerify', token)
		
		return request
	
	@staticmethod
	def verify(request: djn_utils.CustomRequest, email: str, token: str) -> djn_utils.CustomRequest:
		"""
		UpdatedAt: ---
		About:
		-----
		verify the `token` for `email`

		Django Errors:
		-----
		main:
			| status: 404
			| comment: no user found  (unrelated message) (client must treat this error as `no_token` error)
			| Message: UTILSD.Defaults.Messages.no_token
			| Result: null
			| ----------------------------------------------------
			| status: 409
			| comment: ---
			| Message: UTILSD.Defaults.Messages.already_verified
			| Result: null
			| ----------------------------------------------------
			| status: 404
			| comment: token not found for user
			| Message: UTILSD.Defaults.Messages.no_token
			| Result: null
			| ----------------------------------------------------
			| status: 409
			| comment: token already used by user himself
			| Message: UTILSD.Defaults.Messages.already_used
			| Result: null
			| ----------------------------------------------------
			| status: 400
			| comment: ---
			| Message: UTILSD.Defaults.Messages.token_expired
			| Result: null
			| ----------------------------------------------------
			| status: 403
			| comment: suspended user
			| Message: UTILSD.Defaults.Messages.suspended_user
			| Result: null
			| ----------------------------------------------------
		links:
			| UTILSD.main.check_regex
		possible attack:
			| ---
		unexpected:
			| ---
		"""
		expire_hours = 24
		djn_utils.check_regex(request, email, 'email')
		request.db.server.schema = 'users_data'
		user = list(request.db.server.read(
			'account_account',
			['id'],
			[('email', '=', email)],
		).id.values)
		if not user:
			djn_utils.d_raise(
				request,
				djn_def.Messages.no_token,
				f'no user found with email `{email}` (unrelated message)',
				code=404,
			)
		
		request.User.uid = int(user[0])
		request.User.info(request, {'template': 'info', 'main': ['referred_by'], 'activities': ['signup']})
		user = request.User
		
		if request.User.status == djn_def.Fields.status_map['suspended']:
			djn_utils.d_raise(
				request,
				djn_def.Messages.suspended_user,
				f'user is {request.User.status}',
				code=403,
			)
		
		if user.auth_email:
			djn_utils.d_raise(
				request,
				djn_def.Messages.already_verified,
				f'{email} user({user.uid})',
				code=409
			)
		
		data = list(request.db.server.read(
			'tokens_email',
			['created', 'is_used'],
			[
				('uid', '=', user.uid),
				('token', '=', token),
			]
		).values)
		if not data:
			djn_utils.d_raise(
				request,
				djn_def.Messages.no_token,
				f'sms token({token}) not found for user({user.uid})',
				code=404
			)
		created, is_used = data[0]
		if is_used:
			djn_utils.d_raise(
				request,
				djn_def.Messages.already_used,
				f'sms token({token}) is already used by user({user.uid}) himself',
				code=409
			)
		if Time.ParseTimeDelta(request.start - created).hours > expire_hours:
			djn_utils.d_raise(
				request,
				djn_def.Messages.token_expired,
				f'sms token({token}) for user({user.uid}) is older than {expire_hours} hours',
			)
		
		request.db.server.update(
			'tokens_email',
			pd.DataFrame(columns=['is_used'], data=[[True]]),
			[
				('uid', '=', user.uid),
				('token', '=', token),
			]
		)
		request.User.authenticate_email(request)
		
		engines.Email.send(
			user.email,
			'welcomee',
			user.username,
		)
		
		return request


class ForgetPassword:
	@staticmethod
	def send(request: djn_utils.CustomRequest, email: str, **kwargs) -> djn_utils.CustomRequest:
		"""
		UpdatedAt: 2021-10-06
			2021-08-02 -> remove extra errors
			2021-10-06 -> added `suspended_user` error

		About:
		-----
		generate and send token to `email`

		Params:
		-----
		**kwargs:
			token: str, default: None
				to send this `token` except `auto-generated token`

		Django Errors:
		-----
		main:
			| status: 404
			| comment: no user found  (not raised)
			| Message: UTILSD.Defaults.Messages.account_not_found
			| Result: null
			| ----------------------------------------------------
			| status: 403
			| comment: suspended user
			| Message: UTILSD.Defaults.Messages.suspended_user
			| Result: null
			| ----------------------------------------------------
		links:
			| UTILSD.main.check_regex
		possible attack:
			| ---
		unexpected:
			| ---
		"""
		djn_utils.check_regex(request, email, 'email')
		
		request.db.server.schema = 'users_data'
		uid = list(request.db.server.read(
			'account_account',
			['id', 'status'],
			[('email', '=', email)]
		).values)
		if not uid:
			djn_utils.d_raise(
				request,
				djn_def.Messages.account_not_found,
				f'no user found with email `{email}` (not raised)',
				code=404,
				do_raise=False
			)
			return request
		request.User.uid, request.User.status = uid[0]
		request.User.email = email
		user = request.User
		
		if request.User.status == djn_def.Fields.status_map['suspended']:
			djn_utils.d_raise(
				request,
				djn_def.Messages.suspended_user,
				f'user is {request.User.status}',
				code=403,
			)
		
		token = kwargs.pop('token', Int.gen_random(5))
		
		# request.db.delete('tokens_forget_pass', [('uid', '=', user.uid)])
		request.db.server.insert('tokens_forget_pass', pd.DataFrame(columns=['uid', 'token'], data=[[user.uid, token]]))
		
		engines.Email.send(user.email, 'ChangePasswordVerify', token)
		
		return request
	
	@staticmethod
	def verify(request: djn_utils.CustomRequest, email: str, token: str) -> djn_utils.CustomRequest:
		"""
		UpdatedAt: 2021-10-06
			2021-08-02 -> remove extra errors
			2021-10-06 -> added `suspended_user` error

		About:
		-----
		verify the `token` for `email`

		Django Errors:
		-----
		main:
			| status: 404
			| comment: no user found  (unrelated message) (client must treat this error as `no_token` error)
			| Message: UTILSD.Defaults.Messages.no_token
			| Result: null
			| ----------------------------------------------------
			| status: 404
			| comment: token not found for user
			| Message: UTILSD.Defaults.Messages.no_token
			| Result: null
			| ----------------------------------------------------
			| status: 409
			| comment: token already used by user himself
			| Message: UTILSD.Defaults.Messages.already_used
			| Result: null
			| ----------------------------------------------------
			| status: 409
			| comment: ---
			| Message: UTILSD.Defaults.Messages.already_verified
			| Result: null
			| ----------------------------------------------------
			| status: 400
			| comment: ---
			| Message: UTILSD.Defaults.Messages.token_expired
			| Result: null
			| ----------------------------------------------------
			| status: 403
			| comment: suspended user
			| Message: UTILSD.Defaults.Messages.suspended_user
			| Result: null
			| ----------------------------------------------------
		links:
			| UTILSD.main.check_regex
		possible attack:
			| ---
		unexpected:
			| ---
		"""
		expire_minutes = 2
		djn_utils.check_regex(request, email, 'email')
		
		request.db.server.schema = 'users_data'
		uid = list(request.db.server.read(
			'account_account',
			['id', 'status'],
			[('email', '=', email)]
		).values)
		if not uid:
			djn_utils.d_raise(
				request,
				djn_def.Messages.no_token,
				f'no user found with email `{email}` (unrelated message)',
				code=404,
			)
		request.User.uid, request.User.status = uid[0]
		request.User.email = email
		user = request.User
		
		if request.User.status == djn_def.Fields.status_map['suspended']:
			djn_utils.d_raise(
				request,
				djn_def.Messages.suspended_user,
				f'user is {request.User.status}',
				code=403,
			)
		
		data = list(request.db.server.read(
			'tokens_forget_pass',
			['created', 'is_used', 'is_verified'],
			[
				('uid', '=', user.uid),
				('token', '=', token),
			]
		).values)
		if not data:
			djn_utils.d_raise(
				request,
				djn_def.Messages.no_token,
				f'forget_pass token({token}) not found for user({user.uid})',
				code=404
			)
		created, is_used, is_verified = data[0]
		if is_used:
			djn_utils.d_raise(
				request,
				djn_def.Messages.already_used,
				f'forget_pass token({token}) is already used by user({user.uid}) himself',
				code=409
			)
		if is_verified:
			djn_utils.d_raise(
				request,
				djn_def.Messages.already_verified,
				f'forget_pass token({token}) is already verified by user({user.uid}) himself',
				code=409
			)
		if Time.ParseTimeDelta(request.start - created).minutes > expire_minutes:
			djn_utils.d_raise(
				request,
				djn_def.Messages.token_expired,
				f'forget_pass token({token}) for user({user.uid}) is older than {expire_minutes} minutes',
			)
		
		# if email is not authenticated, authenticate user email
		request.User.authenticate_email(request)
		request.db.server.update(
			'tokens_forget_pass',
			pd.DataFrame(columns=['is_verified'], data=[[True]]),
			[
				('uid', '=', user.uid),
				('token', '=', token),
			]
		)
		
		return request
	
	@staticmethod
	def change(request: djn_utils.CustomRequest, email: str, password: str) -> djn_utils.CustomRequest:
		"""
		UpdatedAt: 2021-10-06
			2021-08-02 ->
				remove extra errors
				moved [`already_used`(409)] to main errors from possible attack errors
			2021-10-06 -> added `suspended_user` error
			2021-11-30 -> renamed possible attack errors to bad_input

		About:
		-----
		change `password` for user with `email`

		Django Errors:
		-----
		main:
			| status: 400
			| comment: ---
			| Message: UTILSD.Defaults.Messages.token_expired
			| Result: null
			| ----------------------------------------------------
			| status: 400
			| comment: previous and new password must not match
			| Message: UTILSD.Defaults.Messages.repetitive_password
			| Result: null
			| ----------------------------------------------------
			| status: 409
			| comment: token already used by user himself (must do the forget password process again)
			| Message: UTILSD.Defaults.Messages.already_used
			| Result: null
			| ----------------------------------------------------
			| status: 403
			| comment: suspended user
			| Message: UTILSD.Defaults.Messages.suspended_user
			| Result: null
			| ----------------------------------------------------
		links:
			| UTILSD.main.check_regex
		possible attack:
			| status: 400
			| comment: no user found
			| Message: UTILSD.Defaults.Messages.bad_input
			| Result: null
			| ----------------------------------------------------
			| status: 400
			| comment: token not found for user
			| Message: UTILSD.Defaults.Messages.bad_input
			| Result: null
			| ----------------------------------------------------
			| status: 400
			| comment: code not verified
			| Message: UTILSD.Defaults.Messages.bad_input
			| Result: null
			| ----------------------------------------------------
		unexpected:
			| ---
		"""
		expire_minutes = 60
		djn_utils.check_regex(request, email, 'email')
		djn_utils.check_regex(request, password, 'password')
		
		request.db.server.schema = 'users_data'
		user = list(request.db.server.read(
			'account_account',
			['id', 'password', 'status'],
			[('email', '=', email)]
		).values)
		if not user:
			djn_utils.d_raise(
				request,
				djn_def.Messages.bad_input,
				f'no user found with email `{email}` {djn_def.Messages.possible_attack}',
			)
		request.User.uid, request.User.password, request.User.status = user[0]
		request.User.email = email
		user = request.User
		
		if request.User.status == djn_def.Fields.status_map['suspended']:
			djn_utils.d_raise(
				request,
				djn_def.Messages.suspended_user,
				f'user is {request.User.status}',
				code=403,
			)
		
		data = request.db.server.read(
			'tokens_forget_pass',
			['id', 'created', 'is_used', 'is_verified'],
			[('uid', '=', user.uid)],
			order_by=['id', 'desc']
		)
		if data.empty:
			djn_utils.d_raise(
				request,
				djn_def.Messages.bad_input,
				f'no forget_pass token found for user({user.uid}) {djn_def.Messages.possible_attack}',
			)
		data = data.loc[data.created >= request.start - _dt.timedelta(minutes=expire_minutes)]
		if data.empty:
			djn_utils.d_raise(
				request,
				djn_def.Messages.token_expired,
				f'user({user.uid})\'s last token is older than {expire_minutes} minutes',
			)
		
		# must check with `==`
		data = data.loc[data.is_used == False]
		if data.empty:
			djn_utils.d_raise(
				request,
				djn_def.Messages.already_used,
				f'user({user.uid})\'s last token is already used by himself',
				code=409
			)
		# must check with `==`
		data = data.loc[data.is_verified == True]
		if data.empty:
			djn_utils.d_raise(
				request,
				djn_def.Messages.bad_input,
				f'user({user.uid})\'s last token is not verified by himself {djn_def.Messages.possible_attack}',
			)
		data['is_used'] = True
		data.set_index('id', inplace=True)
		
		if check_password(password, user.password):
			djn_utils.d_raise(
				request,
				djn_def.Messages.repetitive_password,
				f'user({user.uid}) previous and new password can\'t match',
			)
		
		acc = get_user_model().objects.filter(email=email)[0]
		acc.set_password(password)
		acc.save()
		
		request.db.server.multiple_update(
			'tokens_forget_pass',
			data[['is_used']]
		)
		
		engines.Email.send(email, 'PasswordChanged', djn_def.links['website'])
		request.input_body.update({'password': '******'})
		return request
