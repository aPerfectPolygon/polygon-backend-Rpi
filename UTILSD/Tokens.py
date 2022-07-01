# uncomment if you want to run this file separately
# from UTILSD import configure_django_with_project_settings
# configure_django_with_project_settings()

import datetime as _dt
import typing as ty

import pandas as pd
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password

from UTILS.dev_utils.Objects import Int, Time
from UTILSD import Defaults as djn_def
from UTILSD import main as djn_utils


def _gen_token(token):
	if not token:
		token = str(Int.gen_random(5))
	return token


class Email:
	token_expire_in_hours = 2
	
	@staticmethod
	def send(
			request: djn_utils.CustomRequest,
			token: str = None,
			send_email: ty.Callable = None,
			**kwargs
	) -> djn_utils.CustomRequest:
		"""
		UpdatedAt: ---

		About:
		-----
		generate and send token to user
		** this function does not check email`s regex **
		* request.User must have following fields:
			email
			uid
			auth_email
			status
			
		Params:
		-----
		request: CustomRequest
		token: str, default: None
			to send this token except auto-generated token

		Django Errors:
		-----
		main:
			| ---
		links:
			| UTILSD.main.CustomUser.authenticate_email
			| UTILSD.main.check_regex
		possible attack:
			| ---
		unexpected:
			| status: 410
			| comment: no user attached to request
			| Message: UTILSD.Defaults.Messages.bad_input
			| Result: null
			| ----------------------------------------------------
		"""
		if not request.User.uid:
			djn_utils.d_raise(
				request,
				djn_def.Messages.bad_input,
				f'no user attached to request {djn_def.Messages.unexpected}',
				do_raise=False,
				code=410
			)
			return request
		if request.User.auth_email:
			djn_utils.d_raise(
				request,
				djn_def.Messages.already_verified,
				code=409
			)
		
		request.User.authenticate_email(request, new_status=False)
		token = _gen_token(token)
		
		# request.db.server.delete('tokens_email', [('uid', '=', request.User.uid)], schema='users_data')
		request.db.server.insert(
			'tokens_email',
			pd.DataFrame(columns=['uid', 'token'], data=[[request.User.uid, token]]),
			schema='users_data'
		)
		
		if send_email is None:
			# noinspection PyProtectedMember
			djn_utils.Templates(request).email_verify_token(token, **kwargs)
		else:
			send_email(request, token)
		
		return request
	
	@staticmethod
	def verify(
			request: djn_utils.CustomRequest,
			email: str,
			token: str,
			send_email: bool = False
	) -> djn_utils.CustomRequest:
		"""
		UpdatedAt: ---

		About:
		-----
		verify the `token` for `email`
		* this function can return html/json response based on request

		Django Errors:
		-----
		main:
			| status: 409
			| comment: ---
			| Message: UTILSD.Defaults.Messages.already_verified
			| Result: null
			| ----------------------------------------------------
			| status: 404
			| comment: token not found
			| Message: UTILSD.Defaults.Messages.no_token
			| Result: null
			| ----------------------------------------------------
			| status: 409
			| comment: token already used by user
			| Message: UTILSD.Defaults.Messages.already_used
			| Result: null
			| ----------------------------------------------------
			| status: 404
			| comment: ---
			| Message: UTILSD.Defaults.Messages.token_expired
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
		
		# region find token
		conds = [('token', '=', token)]
		if request.User.uid is not None:
			conds.append(('uid', '=', request.User.uid))
		
		data = request.db.server.read(
			'tokens_email',
			['created', 'is_used', 'uid'],
			conds
		).values.tolist()
		if not data:
			djn_utils.d_raise(
				request,
				djn_def.Messages.no_token,
				f'email token({token}) not found',
				code=404
			)
		created, is_used, uid = data[0]
		# endregion
		
		# region check user which token was assigned to
		request.User.uid = int(uid)
		request.User.info(request, {'template': 'info'})
		request.lang = request.User.lang
		
		if request.User.auth_email:
			djn_utils.d_raise(
				request,
				djn_def.Messages.already_verified,
				code=409,
				template=djn_def.templates['email']['already_verified'][request.lang],
			)
		if request.User.email.replace('.', '') != email.replace('.', ''):
			djn_utils.d_raise(
				request,
				djn_def.Messages.no_token,
				f'email token({token}) not found for email',
				code=404
			)
		# endregion
		
		# region check token
		if is_used:
			djn_utils.d_raise(
				request,
				djn_def.Messages.already_used,
				f'email token({token}) is already used by user',
				code=409,
				template=djn_def.templates['email']['already_used'][request.lang]
			)
		if Time.ParseTimeDelta(request.start - created).hours > Email.token_expire_in_hours:
			djn_utils.d_raise(
				request,
				djn_def.Messages.token_expired,
				f'email token({token}) for user is older than {Email.token_expire_in_hours} hours',
				code=404,
				template=djn_def.templates['email']['expired'][request.lang]
			)
		# endregion
		
		request.User.authenticate_email(request)
		request.db.server.update(
			'tokens_email',
			pd.DataFrame(columns=['is_used'], data=[[True]]),
			[('uid', '=', request.User.uid), ('token', '=', token)]
		)
		request.User.email = email
		
		if send_email:
			djn_utils.Templates(request).email_verify_successful()
		
		return request


class ForgetPassword:
	token_expire_in_minutes = 30
	token_use_expire_in_minutes = 60
	
	@staticmethod
	def send(request: djn_utils.CustomRequest, email: str, token: str = None) -> djn_utils.CustomRequest:
		"""
		UpdatedAt: ---

		About:
		-----
		generate and send token to user

		Params:
		-----
		request: CustomRequest
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
			| status: 410
			| comment: user does not have password and cant change it
			| Message: UTILSD.Defaults.Messages.no_password
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
		request.db.server.schema = 'users_data'
		djn_utils.check_regex(request, email, 'email')
		
		# region find user
		uid = request.db.server.read(
			'account_account', ['id', 'password', 'status', 'email', 'lang'],
			[("replace(email, '.', '')", '=', email.replace('.', ''))],
		).to_dict('records')
		if not uid:
			djn_utils.d_raise(request, djn_def.Messages.email_not_found, code=404)
		
		request.User.uid = uid[0]['id']
		request.User.status = uid[0]['status']
		request.User.email = uid[0]['email']
		request.User.password = uid[0]['password']
		request.User.lang = uid[0]['lang']
		request.lang = request.User.lang
		
		if request.User.status == djn_def.Fields.status_map['suspended']:
			djn_utils.d_raise(request, djn_def.Messages.suspended_user, code=403)
		
		if request.User.password is None:
			djn_utils.d_raise(
				request,
				djn_def.Messages.no_password,
				code=410
			)
		
		# endregion
		
		token = _gen_token(token)
		# request.db.delete('tokens_forget_pass', [('uid', '=', user.uid)])
		request.db.server.insert(
			'tokens_forget_pass', pd.DataFrame(columns=['uid', 'token'], data=[[request.User.uid, token]]))
		
		djn_utils.Templates(request).email_password_change_token(token)
		return request
	
	@staticmethod
	def verify(request: djn_utils.CustomRequest, email: str, token: str) -> djn_utils.CustomRequest:
		"""
		UpdatedAt: ---

		About:
		-----
		verify the `token` for user

		Django Errors:
		-----
		main:
			| status: 404
			| comment: token not found for user
			| Message: UTILSD.Defaults.Messages.no_token
			| Result: null
			| ----------------------------------------------------
			| status: 409
			| comment: ---
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
			| comment: ---
			| Message: UTILSD.Defaults.Messages.suspended_user
			| Result: null
			| ----------------------------------------------------
		links:
			| UTILSD.main.check_regex
			| UTILSD.main.CustomUser.authenticate_email
		possible attack:
			| status: 404
			| comment: no user found  (unrelated message)
			| Message: UTILSD.Defaults.Messages.no_token
			| Result: null
			| ----------------------------------------------------
		unexpected:
			| ---
		"""
		request.db.server.schema = 'users_data'
		djn_utils.check_regex(request, email, 'email')
		
		conds = [("replace(email, '.', '')", '=', email.replace('.', ''))]
		if request.User.uid is not None:
			conds.append(('main_table.id', '=', request.User.uid))
		
		# region find user
		uid = request.db.server.read(
			'account_account',
			['main_table.id', 'status', 'email', 'lang'],
			conds,
		).to_dict('records')
		if not uid:
			djn_utils.d_raise(
				request,
				djn_def.Messages.no_token,
				f'user not found (unrelated message) {djn_def.Messages.possible_attack}',
				code=404,
			)
		request.User.uid = uid[0]['id']
		request.User.status = uid[0]['status']
		request.User.email = uid[0]['email']
		request.User.lang = uid[0]['lang']
		request.lang = request.User.lang
		
		if request.User.status == djn_def.Fields.status_map['suspended']:
			djn_utils.d_raise(request, djn_def.Messages.suspended_user, code=403)
		
		# endregion
		
		# region find token and check it
		data = request.db.server.read(
			'tokens_forget_pass',
			['created', 'is_used', 'is_verified'],
			[('uid', '=', request.User.uid), ('token', '=', token)]
		).values.tolist()
		if not data:
			djn_utils.d_raise(request, djn_def.Messages.no_token, code=404)
		created, is_used, is_verified = data[0]
		if is_used:
			djn_utils.d_raise(
				request,
				djn_def.Messages.already_used,
				code=409,
				template=djn_def.templates['forget_password']['verify']['already_used'][request.lang]
			)
		if is_verified:
			djn_utils.d_raise(
				request,
				djn_def.Messages.already_verified,
				code=409,
				template=djn_def.templates['forget_password']['verify']['already_verified'][request.lang]
			)
		if Time.ParseTimeDelta(request.start - created).minutes > ForgetPassword.token_expire_in_minutes:
			djn_utils.d_raise(
				request,
				djn_def.Messages.token_expired,
				template=djn_def.templates['forget_password']['verify']['expired'][request.lang]
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
		change `password` for user

		Django Errors:
		-----
		main:
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
			| status: 409
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
			| status: 400
			| comment: user does not have password (must not happen)
			| Message: UTILSD.Defaults.Messages.bad_input
			| Result: null
			| ----------------------------------------------------
		unexpected:
			| ---
		"""
		request.db.server.schema = 'users_data'
		djn_utils.check_regex(request, email, 'email')
		djn_utils.check_regex(request, password, 'password')
		
		# region find user
		uid = request.db.server.read(
			'account_account', ['id', 'password', 'status', 'email', 'lang'],
			[("replace(email, '.', '')", '=', email.replace('.', ''))]
		).to_dict('records')
		if not uid:
			djn_utils.d_raise(
				request,
				djn_def.Messages.bad_input,
				djn_def.Messages.possible_attack,
			)
		
		request.User.uid = uid[0]['id']
		request.User.password = uid[0]['password']
		request.User.status = uid[0]['status']
		request.User.email = uid[0]['email']
		request.User.lang = uid[0]['lang']
		request.lang = request.User.lang
		
		if request.User.password is None:
			djn_utils.d_raise(
				request,
				djn_def.Messages.bad_input,
				f'user does not have password {djn_def.Messages.possible_attack} {djn_def.Messages.must_not_happen}'
			)
		
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
				f'forget_pass token not found {djn_def.Messages.possible_attack}',
			)
		
		data = data.loc[
			data.created >= request.start - _dt.timedelta(minutes=ForgetPassword.token_use_expire_in_minutes)]
		if data.empty:
			djn_utils.d_raise(
				request,
				djn_def.Messages.bad_input,
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
				code=409
			)
		
		# update password
		acc = get_user_model().objects.filter(id=request.User.uid)[0]
		acc.set_password(password)
		acc.save()
		
		data['is_used'] = True
		data.set_index('id', inplace=True)
		request.db.server.multiple_update('tokens_forget_pass', data[['is_used']])
		
		djn_utils.Templates(request).email_password_change_successful()
		return request
