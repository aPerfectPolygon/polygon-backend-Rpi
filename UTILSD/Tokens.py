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


def _gen_token(token):
	if not token:
		token = str(Int.gen_random(5))
	return token


class Email:
	token_expire_in_minutes = 30
	
	@staticmethod
	def send(request: djn_utils.CustomRequest, email: str, token: str = None) -> djn_utils.CustomRequest:
		"""
		UpdatedAt: ---

		About:
		-----
		generate and send token to `email`

		Params:
		-----
		token: str, default: None
			to send this token except auto-generated token

		Django Errors:
		-----
		main:
			| status: 404
			| comment: (not raised)
			| Message: UTILSD.Defaults.Messages.account_not_found
			| Result: null
			| ----------------------------------------------------
			| status: 409
			| comment: ---
			| Message: UTILSD.Defaults.Messages.already_verified
			| Result: null
			| ----------------------------------------------------
		links:
			| UTILSD.main.check_regex
			| UTILSD.main.CustomUser.authenticate_email
		possible attack:
			| ---
		unexpected:
			| ---
		"""
		djn_utils.check_regex(request, email, 'email')
		request.db.server.schema = 'users_data'
		
		# region find user
		user = request.db.server.read(
			'account_account',
			['main_table.id', 'auth_email', 'status'],
			[('email', '=', email)],
			[('inner', 'users_data.users_info', 'info', 'main_table.id', '=', 'info.uid')]
		).values.tolist()
		if not user:
			djn_utils.d_raise(
				request,
				djn_def.Messages.account_not_found,
				f'email `{email}` (not raised)',
				code=404,
				do_raise=False
			)
			return request
		
		request.User.email = email
		request.User.uid, request.User.auth_email, request.User.status = user[0]
		
		# endregion
		
		if request.User.auth_email:
			djn_utils.d_raise(
				request,
				djn_def.Messages.already_verified,
				f'email {email}',
				code=409
			)
		
		request.User.authenticate_email(request, new_status=False)
		token = _gen_token(token)
		
		# request.db.server.delete('tokens_email', [('uid', '=', request.User.uid)])
		request.db.server.insert('tokens_email', pd.DataFrame(columns=['uid', 'token'], data=[[request.User.uid, token]]))
		engines.Email.send(
			request.User.email,
			'Activation',
			template=djn_def.templates['email']['signupSeries']['signup'][request.lang],
			template_content={'token': token}
		)
		
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
		links:
			| UTILSD.main.check_regex
			| UTILSD.main.CustomUser.authenticate_email
		possible attack:
			| status: 404
			| comment: no user found  (unrelated message) (client must treat this error as `no_token` error)
			| Message: UTILSD.Defaults.Messages.no_token
			| Result: null
			| ----------------------------------------------------
		unexpected:
			| ---
		"""
		djn_utils.check_regex(request, email, 'email')
		request.db.server.schema = 'users_data'
		
		# region find user
		user = request.db.server.read(
			'account_account',
			['id'],
			[('email', '=', email)],
		).id.values.tolist()
		if not user:
			djn_utils.d_raise(
				request,
				djn_def.Messages.no_token,
				f'no user found with email `{email}` (unrelated message) {djn_def.Messages.possible_attack}',
				code=404,
			)
		
		request.User.uid = int(user[0])
		request.User.info(request, {'template': 'info'})
		# endregion
		
		if request.User.auth_email:
			djn_utils.d_raise(
				request,
				djn_def.Messages.already_verified,
				f'{email}',
				code=409
			)
		
		# region find token and check it
		data = request.db.server.read(
			'tokens_email',
			['created', 'is_used'],
			[('uid', '=', request.User.uid), ('token', '=', token)]
		).values.tolist()
		if not data:
			djn_utils.d_raise(
				request,
				djn_def.Messages.no_token,
				f'email token({token}) not found for user',
				code=404
			)
		created, is_used = data[0]
		if is_used:
			djn_utils.d_raise(
				request,
				djn_def.Messages.already_used,
				f'email token({token}) is already used by user himself',
				code=409
			)
		if Time.ParseTimeDelta(request.start - created).minutes > Email.token_expire_in_minutes:
			djn_utils.d_raise(
				request,
				djn_def.Messages.token_expired,
				f'email token({token}) for user is older than {Email.token_expire_in_minutes} minutes',
			)
		# endregion
		
		request.User.authenticate_email(request)
		request.db.server.update(
			'tokens_email',
			pd.DataFrame(columns=['is_used'], data=[[True]]),
			[('uid', '=', request.User.uid), ('token', '=', token)]
		)
		
		engines.Email.send(
			request.User.email,
			'Welcome',
			template=djn_def.templates['email']['signupSeries']['welcome'][request.lang],
			template_content={'username': request.User.username}
		)
		
		return request


class ForgetPassword:
	token_expire_in_minutes = 3
	token_use_expire_in_minutes = 60
	
	@staticmethod
	def send(request: djn_utils.CustomRequest, email: str, token: str = None) -> djn_utils.CustomRequest:
		"""
		UpdatedAt: ---

		About:
		-----
		generate and send token to `email`

		Params:
		-----
		token: str, default: None
			to send this `token` except `auto-generated token`

		Django Errors:
		-----
		main:
			| status: 404
			| comment: (not raised)
			| Message: UTILSD.Defaults.Messages.account_not_found
			| Result: null
			| ----------------------------------------------------
			| status: 403
			| comment: ---
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
		
		# region find user
		uid = request.db.server.read(
			'account_account',
			['id', 'status'],
			[('email', '=', email)]
		).values.tolist()
		if not uid:
			djn_utils.d_raise(
				request,
				djn_def.Messages.account_not_found,
				f'email `{email}` (not raised)',
				code=404,
				do_raise=False
			)
			return request
		
		request.User.email = email
		request.User.uid, request.User.status = uid[0]
		
		if request.User.status == djn_def.Fields.status_map['suspended']:
			djn_utils.d_raise(request, djn_def.Messages.suspended_user, code=403)
		# endregion
		
		token = _gen_token(token)
		# request.db.delete('tokens_forget_pass', [('uid', '=', request.User.uid)])
		request.db.server.insert(
			'tokens_forget_pass', pd.DataFrame(columns=['uid', 'token'], data=[[request.User.uid, token]]))
		
		engines.Email.send(
			request.User.email,
			'Forget Password Verification',
			template=djn_def.templates['email']['forgetPasswordSeries']['to_change'][request.lang],
			template_content={'token': token}
		)
		
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
			| comment: token already verified by user himself
			| Message: UTILSD.Defaults.Messages.already_verified
			| Result: null
			| ----------------------------------------------------
			| status: 400
			| comment: ---
			| Message: UTILSD.Defaults.Messages.token_expired
			| Result: null
			| ----------------------------------------------------
		links:
			| UTILSD.main.check_regex
			| UTILSD.main.CustomUser.authenticate_email
		possible attack:
			| status: 404
			| comment: no user found  (unrelated message) (client must treat this error as `no_token` error)
			| Message: UTILSD.Defaults.Messages.no_token
			| Result: null
			| ----------------------------------------------------
		unexpected:
			| ---
		"""
		djn_utils.check_regex(request, email, 'email')
		request.db.server.schema = 'users_data'
		
		# region find user
		uid = request.db.server.read(
			'account_account',
			['id', 'status'],
			[('email', '=', email)]
		).values.tolist()
		if not uid:
			djn_utils.d_raise(
				request,
				djn_def.Messages.no_token,
				f'no user found with email `{email}` (unrelated message) {djn_def.Messages.possible_attack}',
				code=404,
			)
		request.User.email = email
		request.User.uid, request.User.status = uid[0]
		
		# endregion
		
		# region find token and check it
		data = request.db.server.read(
			'tokens_forget_pass',
			['created', 'is_used', 'is_verified'],
			[('uid', '=', request.User.uid), ('token', '=', token)]
		).values.tolist()
		if not data:
			djn_utils.d_raise(
				request,
				djn_def.Messages.no_token,
				f'forget_pass token({token}) not found for user',
				code=404
			)
		created, is_used, is_verified = data[0]
		if is_used:
			djn_utils.d_raise(
				request,
				djn_def.Messages.already_used,
				f'forget_pass token({token}) is already used by user himself',
				code=409
			)
		if is_verified:
			djn_utils.d_raise(
				request,
				djn_def.Messages.already_verified,
				f'forget_pass token({token}) is already verified by user himself',
				code=409
			)
		if Time.ParseTimeDelta(request.start - created).minutes > ForgetPassword.token_expire_in_minutes:
			djn_utils.d_raise(
				request,
				djn_def.Messages.token_expired,
				f'forget_pass token({token}) for user is older than {ForgetPassword.token_expire_in_minutes} minutes',
			)
		# endregion
		
		# if email is not authenticated, authenticate user email
		request.User.authenticate_email(request)
		request.db.server.update(
			'tokens_forget_pass',
			pd.DataFrame(columns=['is_verified'], data=[[True]]),
			[('uid', '=', request.User.uid), ('token', '=', token)]
		)
		
		return request
	
	@staticmethod
	def change(request: djn_utils.CustomRequest, email: str, password: str) -> djn_utils.CustomRequest:
		"""
		UpdatedAt: ---

		About:
		-----
		change `password` for user with `email`

		Django Errors:
		-----
		main:
			| status: 400
			| comment: no forget_pass token found for user in last {expiration_time} minutes
			| Message: UTILSD.Defaults.Messages.token_expired
			| Result: null
			| ----------------------------------------------------
			| status: 409
			| comment: no unused forget_pass token found for user
			| Message: UTILSD.Defaults.Messages.already_used
			| Result: null
			| ----------------------------------------------------
			| status: 403
			| comment: ---
			| Message: UTILSD.Defaults.Messages.suspended_user
			| Result: null
			| ----------------------------------------------------
			| status: 400
			| comment: previous and new password must not match
			| Message: UTILSD.Defaults.Messages.repetitive_password
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
			| comment: ** multiple reasons **
			| Message: UTILSD.Defaults.Messages.bad_input
			| Result: null
			| ----------------------------------------------------
		unexpected:
			| ---
		"""
		djn_utils.check_regex(request, email, 'email')
		djn_utils.check_regex(request, password, 'password')
		request.db.server.schema = 'users_data'
		
		# region find user
		user = request.db.server.read(
			'account_account',
			['id', 'password', 'status'],
			[('email', '=', email)]
		).values.tolist()
		if not user:
			djn_utils.d_raise(
				request,
				djn_def.Messages.bad_input,
				f'no user found with email `{email}` {djn_def.Messages.possible_attack}',
			)
		request.User.email = email
		request.User.uid, request.User.password, request.User.status = user[0]
		
		if request.User.status == djn_def.Fields.status_map['suspended']:
			djn_utils.d_raise(request, djn_def.Messages.suspended_user, code=403)
		# endregion
		
		# region find token and check it
		data = request.db.server.read(
			'tokens_forget_pass',
			['id', 'created', 'is_used', 'is_verified'],
			[('uid', '=', request.User.uid)],
			order_by=['id', 'desc']
		)
		if data.empty:
			djn_utils.d_raise(
				request,
				djn_def.Messages.bad_input,
				f'no forget_pass token found for user {djn_def.Messages.possible_attack}',
			)
		
		data = data.loc[
			data.created >= request.start - _dt.timedelta(minutes=ForgetPassword.token_use_expire_in_minutes)]
		if data.empty:
			djn_utils.d_raise(
				request,
				djn_def.Messages.token_expired,
				f'no forget_pass token found for user in last {ForgetPassword.token_use_expire_in_minutes} minutes {djn_def.Messages.possible_attack}',
			)
		
		data = data.loc[~data.is_used]
		if data.empty:
			djn_utils.d_raise(
				request,
				djn_def.Messages.already_used,
				'no unused forget_pass token found for user',
				code=409
			)
		
		data = data.loc[data.is_verified]
		if data.empty:
			djn_utils.d_raise(
				request,
				djn_def.Messages.bad_input,
				f'no verified forget_pass token found for user {djn_def.Messages.possible_attack}',
			)
		
		# endregion
		
		if check_password(password, request.User.password):
			djn_utils.d_raise(
				request,
				djn_def.Messages.repetitive_password,
				f'previous and new password can`t match',
			)
		
		# update password
		acc = get_user_model().objects.filter(email=email)[0]
		acc.set_password(password)
		acc.save()
		
		data['is_used'] = True
		data.set_index('id', inplace=True)
		request.db.server.multiple_update('tokens_forget_pass', data[['is_used']])
		
		engines.Email.send(
			request.User.email,
			'Password Changed',
			template=djn_def.templates['email']['forgetPasswordSeries']['changed'][request.lang],
		)
		return request
