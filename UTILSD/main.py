# uncomment if you want to run this file separately
# from UTILSD import configure_django_with_project_settings
# configure_django_with_project_settings()

import binascii
import datetime
import os
import re
import typing as ty
from abc import ABC

import pandas as pd
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password, make_password
from django.core.handlers.wsgi import WSGIRequest
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import redirect
from django.template.response import SimpleTemplateResponse
from django.urls import path, re_path
from django.urls import resolve, ResolverMatch
from rest_framework import exceptions
from rest_framework.decorators import api_view
from rest_framework.request import Request
from rest_framework.response import Response

from UTILS import dev_utils, engines, Cache
from UTILS.dev_utils import Log
from UTILS.dev_utils.Database import log as db_log
from UTILS.dev_utils.Database.Psql import Psql
from UTILS.dev_utils.Objects import String, Time, List, Json
from UTILS.prj_utils import Defaults as prj_def
from UTILS.prj_utils.main import Encryptions
from UTILSD import Defaults as djn_def
from UTILS.dev_utils.Objects.Google.reCaptcha import verify as verify_recaptcha


class ApiInfo:
	"""
	platform -> choose from UTILSD.Defaults.Platforms				[REQUIRED]  [CAN SET GLOBALLY]
	methods -> Examples : GET, POST, OPTIONS, PUT, DELETE, ...		[REQUIRED]  [CAN SET GLOBALLY]
	name -> name of api (same as `name` in `path()`)				[REQUIRED]
	input_model -> choose from UTILSD.Defaults.Models				[REQUIRED]  [CAN SET GLOBALLY]
	output_model -> choose from UTILSD.Defaults.Models				[REQUIRED]  [CAN SET GLOBALLY]
	
	token_required -> select if this API needs to authenticate user's before accessing it
		SeeAlso: UTILSD.main.MainMiddleware.utils.check_user_if_required
	token_expiration_in_seconds -> how many seconds must pass for token to expire
		SeeAlso: UTILSD.main.MainMiddleware.utils.check_user_if_required

	response_just_message -> just return `Message`:str as response
		SeeAlso: UTILSD.main._make_json_response_ready
	response_additional_headers -> additional headers to overwrite on response headers
	response_html -> if True -> ignores output model and only returns html response
		in case of another response model(json, ...) converts it to html based on status code
		if 200 <= status < 300: main/success.html, else: main/error.html  SeeAlso: UTILSD.main._d_main_return

	** User Fields only works if `token_required` is set to `True` **
	user_fields_to_have -> [DO NOT CHANGE] (used by middleware) new fields will be appended and drop_duplicated
	user_fields_needed -> set user fields needed for API to fetch them from DB and update `request.User`
		for all fields SeeAlso: UTILSD.main.CustomUser.info

	input_params_required -> which keys MUST be in request parameters
	input_params_optional -> which keys CAN be in request parameters
	input_params_block_additional -> block(raise) if additional keys where in request parameters?
	input_body_required -> which keys MUST be in request body
	input_body_optional -> which keys CAN be in request body
	input_body_block_additional -> block(raise) if additional keys where in request body?
	validation_error_as_possible_attack -> to treat errors about input as possible attack
	** for more info about input keys SeeAlso: UTILSD.main.MainMiddleware.utils.check_api_input_data **

	content_types_to_accept_standard -> [DO NOT CHANGE] (used by middleware) new items will be appended and drop_duplicated
	content_types_to_accept -> content types to support in addition to *content_types_to_accept_standard*
	
	allow_files -> if a file was uploaded to this API treat it as possible_attack
	
	"""
	platform: str = None
	methods: ty.List[str] = None
	name: str = None
	input_model: str = None
	output_model: str = None
	
	token_required: bool = False
	token_expiration_in_seconds: int = 0
	
	response_just_message: bool = False
	response_additional_headers: dict = {}
	response_html: bool = False
	
	user_fields_to_have: dict = {
		'main': ['status', 'lang'],  # SeeAlso: UTILSD.main.MainMiddleware.utils.check_active_user_if_detected
	}
	user_fields_needed: dict = {**user_fields_to_have}
	user_must_be_active: bool = False
	
	input_params_required: dict = {}
	input_params_optional: dict = {}
	input_params_block_additional: bool = True
	input_body_required: dict = {}
	input_body_optional: dict = {}
	input_body_block_additional: bool = True
	validation_error_as_possible_attack: bool = True
	
	content_types_to_accept_standard = ['application/json', 'multipart/form-data', 'text/plain']
	content_types_to_accept = [*content_types_to_accept_standard]
	
	allow_files = False
	
	recaptcha_action = None
	
	attrs = [
		'platform',
		'methods',
		'name',
		'input_model',
		'output_model',
		'token_required',
		'token_expiration_in_seconds',
		'response_just_message',
		'response_additional_headers',
		'user_fields_to_have',
		'user_fields_needed',
		'user_must_be_active',
		'input_params_required',
		'input_params_optional',
		'input_params_block_additional',
		'input_body_required',
		'input_body_optional',
		'input_body_block_additional',
		'validation_error_as_possible_attack',
		'response_html',
		'content_types_to_accept_standard',
		'content_types_to_accept',
		'allow_files',
		'recaptcha_action'
	]
	
	def __init__(
			self,
			platform: str = djn_def.Platforms.none,
			methods: ty.List[str] = None,
			input_model: str = djn_def.Models.none,
			output_model: str = djn_def.Models.none,
			**kwargs
	):
		# region validate
		if platform not in djn_def.Platforms.all and platform != djn_def.Platforms.none:
			raise ValueError(f'bad platform {platform}')
		if input_model not in djn_def.Models.all and input_model != djn_def.Models.none:
			raise ValueError(f'bad input_model {input_model}')
		if output_model not in djn_def.Models.all and output_model != djn_def.Models.none:
			raise ValueError(f'bad output_model {output_model}')
		# endregion
		
		if methods is None:
			methods = []
		
		self.platform = platform
		self.methods = methods
		self.input_model = input_model
		self.output_model = output_model
		
		for k, v in self._handle_kwargs(kwargs).items():
			setattr(self, k, v)
	
	def __repr__(self):
		return {attr: getattr(self, attr) for attr in self.attrs}
	
	def __str__(self):
		return str(self.__repr__())
	
	def _handle_kwargs(self, kwargs):
		return {attr: kwargs.get(attr, getattr(self, attr)) for attr in self.attrs}
	
	def update(self, **kwargs):
		res = ApiInfo(**(self._handle_kwargs(kwargs)))
		for k, v in res.user_fields_to_have.items():
			if k in res.user_fields_needed:
				res.user_fields_needed.update({k: List.drop_duplicates(res.user_fields_needed[k] + v)})
			else:
				res.user_fields_needed.update({k: v})
		res.content_types_to_accept = List.drop_duplicates(
			res.content_types_to_accept_standard + res.content_types_to_accept
		)
		return res
	
	def path_generator(self, url: str, callback: callable, **kwargs):
		_n = kwargs.pop('name', url.replace('/', '_'))
		if kwargs.pop('re_path', False):
			return re_path(
				url,
				callback,
				name=_n,
				kwargs={'info': self.update(name=_n, **kwargs)}
			)
		else:
			return path(
				url,
				callback,
				name=_n,
				kwargs={'info': self.update(name=_n, **kwargs)}
			)


class CustomUser:
	info_fields = {
		'main': [
			'first_name',
			'last_name',
			'username',
			'password',
			'signed_up_with',
			'email',
			'status',
			'auth_email',
			'lang',
		],
		'info': [
			'birth_date'
		],
		'notification': ['token_app', 'token_web', 'token_test'],
		'unread_counts': ['notification'],
		'get_token': True,
	}
	all_fields = {
		'main': [
			'first_name',
			'last_name',
			'username',
			'password',
			'signed_up_with',
			'email',
			'status',
			'auth_email',
			'date_joined',
			'last_login',
			'is_admin',
			'is_staff',
			'is_superuser',
			'modified',
			'lang',
		],
		'info': [
			'birth_date',
			'modified',
		],
		'notification': [
			'token_app',
			'token_web',
			'token_test'
		],
		'unread_counts': ['notification'],
		'get_token': True
	}
	
	def __init__(self):
		self.uid = None
		self.token = None
		
		# main
		self.first_name = None
		self.last_name = None
		self.username = None
		self.password = None
		self.signed_up_with = None
		self.email = None
		self.status = None
		self.auth_email = None
		self.date_joined = None
		self.last_login = None
		self.is_admin = None
		self.is_staff = None
		self.is_superuser = None
		self.m_modified = None
		self.lang = None
		
		# info
		self.birth_date = None
		self.i_modified = None
		
		# notification
		self.notification_token_app = None
		self.notification_token_web = None
		self.notification_token_test = None
		
		# unread_counts
		self.unread_counts_notification = None
	
	def __repr__(self):
		return self.data_as_dict()
	
	def __str__(self):
		return str(self.data_as_dict())
	
	def data_as_dict(self) -> dict:
		"""return user's data as dictionary"""
		return {
			'uid': self.uid,
			'token': self.token,
			'first_name': self.first_name,
			'last_name': self.last_name,
			'username': self.username,
			'password': self.password,
			'signed_up_with': self.signed_up_with,
			'email': self.email,
			'status': self.status,
			'auth_email': self.auth_email,
			'date_joined': self.date_joined,
			'last_login': self.last_login,
			'is_admin': self.is_admin,
			'is_staff': self.is_staff,
			'is_superuser': self.is_superuser,
			'm_modified': self.m_modified,
			'lang': self.lang,
			'birth_date': self.birth_date,
			'i_modified': self.i_modified,
			'notification_token_app': self.notification_token_app,
			'notification_token_web': self.notification_token_web,
			'notification_token_test': self.notification_token_test,
			'unread_counts_notification': self.unread_counts_notification,
			
		}
	
	def info(self, request, fields: dict):
		"""
		UpdatedAt: ---

		About:
		-----
		fetch specified `fields` of users data from database and update `self` with them

		Parameters:
		-----
		request: CustomRequest
		fields: dict = {
		| 	'template': 'info',  # all
		| 	'main': [
		| 		'first_name',
		| 		'last_name',
		| 		'username',
		| 		'password',
		| 		'signed_up_with',
		| 		'email',
		| 		'status',
		| 		'auth_email',
		| 		'date_joined',
		| 		'last_login',
		| 		'is_admin',
		| 		'is_staff',
		| 		'is_superuser',
		| 		'modified',
		| 		'lang',
		| 	],
		| 	'info': [
		| 		'birth_date',
		| 		'modified',
		| 	],
		| 	'notification': [
		| 		'token_app',
		| 		'token_web',
		| 		'token_test',
		|	],
		| 	'unread_counts': [
		| 		'notification',
		| 	]
		| 	'get_token': true,
		| }

		Django Errors:
		-----
		main:
			| ---
		links:
			| ---
		possible attack:
			| ---
		unexpected:
			| status: 400
			| comment: (not raised)  no fields specified
			| Message: UTILSD.Defaults.Messages.unexpected
			| Result: null
			| -------------------------------------------------------
			| status: 400
			| comment: (not raised)  uid Not Found
			| Message: UTILSD.Defaults.Messages.unexpected
			| Result: null
			| -------------------------------------------------------
		"""
		
		# region prepare fields
		template = fields.pop('template', None)
		if template:
			if template == 'info':
				template_data = self.info_fields
			elif template == 'all':
				template_data = self.all_fields
			else:
				template_data = None
			
			if template_data:
				for k, v in template_data.items():
					if k in fields and isinstance(fields[k], list):
						fields.update({k: List.drop_duplicates(fields[k] + v)})
					else:
						fields.update({k: v})
		
		get_token = fields.get('get_token', False)
		if get_token and (self.token is not None or request.info.platform == djn_def.Platforms.none):
			get_token = False
		
		main_fields = fields.get('main', [])
		info_fields = fields.get('info', [])
		notification_fields = fields.get('notification', [])
		unread_counts_fields = fields.get('unread_counts', [])
		
		if not (main_fields + info_fields + notification_fields + unread_counts_fields):
			d_raise(
				request,
				djn_def.Messages.unexpected,
				f'no fields specified ({request.info.name})',
				do_raise=False
			)
			return self
		# endregion
		
		# region prepare joins
		_joins = []
		if main_fields:
			if 'modified' in main_fields:
				main_fields.remove('modified')
				main_fields.append('acc.modified as m_modified')
		if info_fields:
			if 'modified' in info_fields:
				info_fields.remove('modified')
				info_fields.append('info.modified as i_modified')
			_joins.append('inner join users_data.users_info info on acc.id = info.uid')
		if notification_fields:
			if 'token_app' in notification_fields:
				notification_fields.remove('token_app')
				notification_fields.append('notification.token_app as notification_token_app')
			if 'token_web' in notification_fields:
				notification_fields.remove('token_web')
				notification_fields.append('notification.token_web as notification_token_web')
			if 'token_test' in notification_fields:
				notification_fields.remove('token_test')
				notification_fields.append('notification.token_test as notification_token_test')
			_joins.append('inner join users_data.users_notification_settings notification on acc.id = notification.uid')
		if unread_counts_fields:
			_joins.append('inner join users_data.users_unread_counts unread_counts on acc.id = unread_counts.uid')
		if get_token:
			_joins.append(f'left join users_data."users_token_{request.info.platform}" u_token on acc.id = u_token.uid')
		# endregion
		
		# region prepare selects
		_select_fields = [
			item if '.' in item else f'"{item}"'
			for item in main_fields + info_fields + notification_fields + unread_counts_fields
		]
		if get_token:
			_select_fields.append('u_token.token as "token"')
		# endregion
		
		# region fetch from db
		try:
			data = request.db.server.custom(
				f"select {','.join(_select_fields)} from users_data.account_account acc {' '.join(_joins)} where acc.id = {self.uid}",
				None,
				to_commit=False,
				to_fetch=True,
				# print_query=True
			).to_dict(orient='records')[0]
		except IndexError:
			d_raise(
				request,
				djn_def.Messages.unexpected,
				f'uid Not Found `{self.uid}`',
				do_raise=False
			)
			return self
		# endregion
		
		# region assigning
		for _f in main_fields + info_fields:
			if ' as ' in _f:
				_f = _f.split(' as ')[1]
			setattr(self, _f, data[_f])
		for _f in notification_fields:
			if ' as ' in _f:
				_f = _f.split(' as ')[1]
				setattr(self, _f, data[_f])
			else:
				setattr(self, f'notification_{_f}', data[_f])
		for _f in unread_counts_fields:
			if ' as ' in _f:
				_f = _f.split(' as ')[1]
				setattr(self, _f, data[_f])
			else:
				setattr(self, f'unread_counts_{_f}', data[_f])
		if get_token:
			self.token = data['token']
		# endregion
		
		return self
	
	def get_user_info(self, request) -> ty.Optional[dict]:
		"""
		UpdatedAt: ---
			
		About:
		-----
		return user's info as dictionary

		Parameters:
		-----
		request: CustomRequest

		Response:
		-----
		Json Object with these keys and types:
			uid: int
			token: str
			status: str
			auth_email: bool
			first_name: str
			last_name: str
			username: str
			has_password: bool
			signed_up_with: str -> [email, google]
			email: str
			birth_date: int
			lang: str
			curr_version: int
			force_version: int
			unread_notification_count: int
			has_notification_token: bool

		Django Errors:
		-----
		main:
			| ---
		links:
			| ---
		possible attack:
			| ---
		unexpected:
			| ---
		"""
		
		if request.info.platform == djn_def.Platforms.app:
			has_notification_token = bool(self.notification_token_app)
		elif request.info.platform == djn_def.Platforms.web:
			has_notification_token = bool(self.notification_token_web)
		elif request.info.platform == djn_def.Platforms.test:
			has_notification_token = bool(self.notification_token_test)
		else:
			has_notification_token = False
		
		return {
			# region info
			'uid': self.uid,
			'token': self.token,
			'status': self.status,
			'auth_email': self.auth_email,
			'first_name': self.first_name,
			'last_name': self.last_name,
			'username': self.username,
			'has_password': self.password is not None,
			'signed_up_with': self.signed_up_with,
			'email': self.email,
			'birth_date': self.birth_date,
			'lang': self.lang,
			'unread_notification_count': self.unread_counts_notification,
			'has_notification_token': has_notification_token,
			# endregion
			# region version specification
			'curr_version': djn_def.app_current_version,
			'force_version': djn_def.app_force_version,
			# endregion
		}
	
	def authenticate_email(self, request, new_status: bool = True):
		"""
		UpdatedAt: ---

		About:
		-----
		authenticate user's email

		Parameters:
		-----
		request: CustomRequest
		new_status: bool, default -> True
			what is user's email authentication new status

		Django Errors:
		-----
		main:
			| status: 403
			| comment: cant authenticate suspended user`s email
			| Message: UTILSD.Defaults.Messages.suspended_user
			| Result: null
			| ----------------------------------------------------
		links:
			| ---
		possible attack:
			| ---
		unexpected:
			| ---
		"""
		# self.info(request, {'main': ['status', 'auth_email']})
		
		if self.status == djn_def.Fields.status_map['suspended']:
			d_raise(
				request,
				djn_def.Messages.suspended_user,
				f'cant authenticate suspended user`s email with new_status({new_status})',
				code=403,
			)
		
		if new_status:
			if not self.auth_email:
				request.db.server.update(
					'account_account',
					pd.DataFrame(columns=['auth_email'], data=[[True]]),
					[('id', '=', self.uid)],
					schema='users_data'
				)
				self.auth_email = True
			if self.status == djn_def.Fields.status_map['inactive']:
				request.db.server.update(
					'account_account',
					pd.DataFrame(columns=['status'], data=[[djn_def.Fields.status_map['active']]]),
					[('id', '=', self.uid)],
					schema='users_data'
				)
				self.status = djn_def.Fields.status_map['active']
		else:
			if self.auth_email:
				request.db.server.update(
					'account_account',
					pd.DataFrame(columns=['auth_email'], data=[[False]]),
					[('id', '=', self.uid)],
					schema='users_data'
				)
				self.auth_email = False
			if self.status == djn_def.Fields.status_map['active']:
				request.db.server.update(
					'account_account',
					pd.DataFrame(columns=['status'], data=[[djn_def.Fields.status_map['inactive']]]),
					[('id', '=', self.uid)],
					schema='users_data'
				)
				self.status = djn_def.Fields.status_map['inactive']
		return self
	
	def signup_with_google(
			self,
			request,
			google_data: ty.Optional[dict],
			auto_login: bool = False
	):
		"""
		UpdatedAt: ---

		About:
		-----
		sign user up and update `self` with new user

		Parameters:
		-----
		request: CustomRequest
		google_data: optional[dict]
			* email
			* email_verified (must be True)
			* given_name
			* family_name
			* picture
		password: str
		auto_login: bool, default: False
			log user in after successful signup

		Response:
		-----
		if user exists and is inactive:
			| status: 200
			| comment: ---
			| Message: UTILSD.Defaults.Messages.ok
			| Result: UTILSD.main.CustomUser.get_user_info
		if user exists and is active:
			| status: 200
			| comment: ---
			| Message: UTILSD.Defaults.Messages.user_logged_in
			| Result: UTILSD.main.CustomUser.get_user_info

		Django Errors:
		-----
		main:
			| status: 403
			| comment: ---
			| Message: UTILSD.Defaults.Messages.suspended_user
			| Result: null
			| ----------------------------------------------------
		links:
			| UTILSD.main.check_regex
		possible attack:
			| status: 400
			| comment: google did not verify the token
			| Message: UTILSD.Defaults.Messages.bad_input
			| Result: ---
			| ----------------------------------------------------
			| status: 400
			| comment: email is not verified
			| Message: UTILSD.Defaults.Messages.bad_input
			| Result: ---
			| ----------------------------------------------------
		unexpected:
			| status: 400
			| comment: bad google data
			| Message: UTILSD.Defaults.Messages.bad_input
			| Result: ---
			| ----------------------------------------------------
		"""
		# region check google_data
		if not google_data:
			d_raise(
				request,
				djn_def.Messages.bad_input,
				f'google not verified the token {djn_def.Messages.possible_attack}'
			)
		
		try:
			email = google_data['email']
			email_verified = google_data['email_verified']
			given_name = google_data['given_name']
			family_name = google_data['family_name']
			picture = google_data['picture']
		except:
			d_raise(
				request,
				djn_def.Messages.bad_input,
				f'bad google_data {djn_def.Messages.unexpected}'
			)
			return  # just for ide warnings
		
		if not email_verified:
			d_raise(
				request,
				djn_def.Messages.bad_input,
				f'email is not verified {djn_def.Messages.possible_attack}'
			)
		
		# endregion
		
		request.db.server.schema = 'users_data'
		
		# region check if user exists
		user = request.db.server.read(
			'account_account', ['id', 'status'], [("replace(email, '.', '')", '=', email.replace('.', ''))]
		).to_dict('records')
		if user:
			user = user[0]
			self.uid = user['id']
			self.status = user['status']
			if self.status == djn_def.Fields.status_map['active']:
				if auto_login:
					Token(request).regenerate()
				
				self.info(request, {'template': 'info', 'main': ['date_joined']})
				d_raise(
					request,
					djn_def.Messages.user_logged_in,
					result=self.get_user_info(request),
					code=200
				)
			elif self.status == djn_def.Fields.status_map['inactive']:
				if auto_login:
					Token(request).regenerate()
				
				# update user with new data
				request.db.server.update(
					'account_account',
					pd.DataFrame(
						[[
							given_name, family_name, email, None, 'google',
							True, djn_def.Fields.status_map['active']
						]],
						columns=[
							'first_name', 'last_name', 'email', 'password',
							'signed_up_with', 'auth_email', 'status'
						]
					),
					[('id', '=', self.uid)],
					schema='users_data'
				)
				
				self.info(request, {'template': 'info', 'main': ['date_joined']})
				d_raise(
					request,
					djn_def.Messages.user_logged_in,
					result=self.get_user_info(request),
					code=200
				)
			elif self.status == djn_def.Fields.status_map['suspended']:
				d_raise(
					request,
					djn_def.Messages.suspended_user,
					code=403
				)
			d_raise(
				request,
				djn_def.Messages.bad_input,
				f'{djn_def.Messages.possible_attack} {djn_def.Messages.must_not_happen}'
			)
		# endregion
		
		# create user
		try:
			acc = get_user_model()(
				first_name=given_name,
				last_name=family_name,
				email=email,
				username=gen_random_username(request.db.server),
				signed_up_with='google',
				lang=request.lang,
				auth_email=True,
				status=djn_def.Fields.status_map['active']
			)
			acc.save()
			self.uid = acc.id
		except Exception as e:
			d_raise(
				request,
				djn_def.Messages.already_exists,
				e,
				exc_comment=djn_def.Messages.must_not_happen,
				code=409
			)
			return  # just for ide warnings
		
		# create user`s related records across other tables
		request.db.server.insert('users_info', pd.DataFrame(columns=['uid'], data=[[acc.id]]))
		request.db.server.insert('users_notification_settings', pd.DataFrame(columns=['uid'], data=[[acc.id]]))
		request.db.server.insert('users_unread_counts', pd.DataFrame(columns=['uid'], data=[[acc.id]]))
		
		if auto_login:
			Token(request).create()
		self.info(request, {'template': 'info', 'main': ['date_joined']})
	
	def signup_with_email(self, request, email: str, password: str, auto_login: bool = False) -> int:
		"""
		UpdatedAt: ---

		About:
		-----
		sign user up and update `self` with new user and return response code
		* return value is only 200 or 201
			* 200: not new user
			* 201: new user

		Parameters:
		-----
		request: CustomRequest
		email: str
		password: str
		auto_login: bool, default: False
			log user in after successful signup

		Response:
		-----
		if user exists and is inactive:
			| status: 200
			| comment: ---
			| Message: UTILSD.Defaults.Messages.ok
			| Result: null

		Django Errors:
		-----
		main:
			| status: 409
			| comment: user already exists
			| Message: UTILSD.Defaults.Messages.already_exists
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
		check_regex(request, email, 'email')
		check_regex(request, password, 'password')
		
		request.db.server.schema = 'users_data'
		
		# region check if user exists
		user = request.db.server.read(
			'account_account', ['id', 'status'], [("replace(email, '.', '')", '=', email.replace('.', ''))]
		).to_dict('records')
		if user:
			user = user[0]
			self.uid = user['id']
			self.status = user['status']
			
			if self.status == djn_def.Fields.status_map['active']:
				d_raise(
					request,
					djn_def.Messages.already_exists,
					code=409
				)
			elif self.status == djn_def.Fields.status_map['inactive']:
				if auto_login:
					Token(request).regenerate()
				
				# update user with new data
				request.db.server.update(
					'account_account',
					pd.DataFrame(
						[['', '', make_password(password)]],
						columns=['first_name', 'last_name', 'password']
					),
					[('id', '=', self.uid)],
					schema='users_data'
				)
				
				self.info(request, {'template': 'info', 'main': ['date_joined']})
				return 200
			elif self.status == djn_def.Fields.status_map['suspended']:
				d_raise(
					request,
					djn_def.Messages.suspended_user,
					code=403,
				)
			d_raise(
				request,
				djn_def.Messages.bad_input,
				f'{djn_def.Messages.possible_attack} {djn_def.Messages.must_not_happen}'
			)
		# endregion
		
		# create user
		try:
			acc = get_user_model()(
				email=email,
				username=gen_random_username(request.db.server),
				signed_up_with='email',
				lang=request.lang
			)
			acc.set_password(password)
			acc.save()
			self.uid = acc.id
		except Exception as e:
			d_raise(
				request,
				djn_def.Messages.already_exists,
				e,
				exc_comment=djn_def.Messages.must_not_happen,
				code=409
			)
			return  # just for ide warnings
		
		# create user`s related records across other tables
		request.db.server.insert('users_info', pd.DataFrame(columns=['uid'], data=[[acc.id]]))
		request.db.server.insert('users_notification_settings', pd.DataFrame(columns=['uid'], data=[[acc.id]]))
		request.db.server.insert('users_unread_counts', pd.DataFrame(columns=['uid'], data=[[acc.id]]))
		
		if auto_login:
			Token(request).create()
		self.info(request, {'template': 'info', 'main': ['date_joined']})
		
		return 201
	
	def login(self, request, username: str, password: str, treat_as: str = None):
		"""
		UpdatedAt: ---

		About:
		-----
		log user in with treating `username` as username and email

		Parameters:
		-----
		request: CustomRequest
		username: str
		password: str
		treat_as: str, default: None
			treat `username` as what (username or email)

		Django Errors:
		-----
		main:
			| status: 404
			| comment: username not found
			| Message: UTILSD.Defaults.Messages.account_not_found
			| Result: null
			| ----------------------------------------------------
			| status: 404
			| comment: bad password
			| Message: UTILSD.Defaults.Messages.account_not_found
			| Result: null
			| ----------------------------------------------------
			| status: 403
			| comment: ---
			| Message: UTILSD.Defaults.Messages.inactive_user
			| Result: null
			| ---------------------------------------------------------------
			| status: 403
			| comment: ---
			| Message: UTILSD.Defaults.Messages.suspended_user
			| Result: null
			| ---------------------------------------------------------------
		links:
			| ---
		possible attack:
			| ---
		unexpected:
			| ---
		"""
		request.db.server.schema = 'users_data'
		user = None
		
		if (not treat_as or treat_as == 'username') and check_regex(
				request, username, 'username',
				do_raise=False, check_regex2=True
		):
			user = request.db.server.read(
				'account_account',
				['id', 'password', 'status'],
				[('username', '=', username)]
			).to_dict('records')
		
		if not user and (not treat_as or treat_as == 'email') and check_regex(
				request, username, 'email',
				do_raise=False
		):
			user = request.db.server.read(
				'account_account',
				['id', 'password', 'status'],
				[("replace(email, '.', '')", '=', username.replace('.', ''))]
			).to_dict('records')
		
		if not user:
			d_raise(
				request,
				djn_def.Messages.account_not_found,
				f'login attempt `{username}` `{password}`',
				code=404
			)
			return  # just for ide warnings
		user = user[0]
		self.uid = user['id']
		self.status = user['status']
		
		if not check_password(password, user['password']):
			d_raise(
				request,
				djn_def.Messages.account_not_found,
				f'login attempt `{username}` `{password}` (bad password)',
				code=404
			)
		
		if self.status == djn_def.Fields.status_map['inactive']:
			d_raise(
				request,
				djn_def.Messages.inactive_user,
				code=403,
			)
		elif self.status == djn_def.Fields.status_map['suspended']:
			d_raise(
				request,
				djn_def.Messages.suspended_user,
				code=403,
			)
		elif self.status != djn_def.Fields.status_map['active']:
			d_raise(
				request,
				djn_def.Messages.inactive_user,
				f'user is not active {djn_def.Messages.must_not_happen}',
				code=403,
			)
		
		Token(request).regenerate()
		request.db.server.update(
			'account_account',
			pd.DataFrame([["timezone('utc', now())", request.lang]], columns=['last_login', 'lang']),
			[('id', '=', self.uid)]
		)
		self.info(request, {'template': 'info', 'main': ['date_joined']})
	
	def upgrade(self, request):
		pass
	
	def downgrade(self, request):
		pass
	
	def update_notification_unread_count(self, request, force=False):
		if self.unread_counts_notification is not None and (self.unread_counts_notification < 100 or force):
			self.unread_counts_notification = request.db.server.custom(
				f"""update users_data.users_unread_counts set notification = (
						select count('id') from (
							select 'id' from users_data.users_notification_inventory
							where
								created >= '{self.date_joined}'
								and ({self.uid} = any(uids) or uids is NULL)
								and not {self.uid} = any(users_seen)
							limit 100
						) x
					) where uid = {self.uid} returning notification""",
				None,
				to_commit=True,
				to_fetch=True
			).values.tolist()[0][0]
	
	def topic_assign(self, topic: str):
		_tokens = pd.Series([
			self.notification_token_app,
			self.notification_token_web,
			self.notification_token_test,
		]).dropna().tolist()
		if not _tokens:
			return
		
		engines.Notification.Topic.assign(topic, _tokens)
	
	def topic_unassign(self, topic: str):
		_tokens = pd.Series([
			self.notification_token_app,
			self.notification_token_web,
			self.notification_token_test,
		]).dropna().tolist()
		if not _tokens:
			return
		
		engines.Notification.Topic.unassign(topic, _tokens)
	
	def send_notification(
			self,
			title: str,
			body: str,
			target: int = 0,
			image: str = None,
			icon: str = None,
			url: str = None,
			web_url: str = None,
			choices: ty.List[str] = None,
			**kwargs
	):
		engines.Notification.send(
			[self.uid],
			title,
			body,
			target,
			image,
			icon,
			url,
			web_url,
			choices,
			**kwargs
		)
	
	def set_notification_token(self, request, token: str, _do_raise=True):
		"""
		UpdatedAt: ---

		About:
		-----
		set user's notification token

		Parameters:
		-----
		request: CustomRequest
		token: str

		Django Errors:
		-----
		main:
			| ---
		links:
			| ---
		possible attack:
			| status: 400
			| comment: firebase did not validate token
			| Message: UTILSD.Defaults.Messages.bad_input
			| Result: null
			| ----------------------------------------------------
		unexpected:
			| ---
		"""
		if not engines.Notification.validate(token):
			d_raise(
				request,
				djn_def.Messages.bad_input,
				f'firebase did not validate token {djn_def.Messages.possible_attack}',
				do_raise=_do_raise,
				code=410
			)
			return
		
		if request.info.platform == djn_def.Platforms.app:
			col = 'token_app'
		elif request.info.platform == djn_def.Platforms.web:
			col = 'token_web'
		elif request.info.platform == djn_def.Platforms.test:
			col = 'token_test'
		else:
			return
		self.update_notification_unread_count(request)
		
		if getattr(self, f'notification_{col}') == token:
			return
		
		request.db.server.schema = 'users_data'
		request.db.server.update(
			'users_notification_settings',
			pd.DataFrame([[None]], columns=[col]),
			[(col, '=', token)],
		)
		request.db.server.update(
			'users_notification_settings',
			pd.DataFrame([[token]], columns=[col]),
			[('uid', '=', self.uid)],
		)
		setattr(self, f'notification_{col}', token)


class CustomDb:
	def __init__(self):
		self.server = Psql('')
	
	def open(self):
		self.server.open()
	
	def close(self):
		self.server.close()


class CustomRequest(Request, ABC):
	input_body: dict = None
	input_params: dict = None
	User = CustomUser()
	
	path: str = None
	start: datetime.datetime = None
	headers: dict = None
	client_ip: str = None
	resolver_match: ResolverMatch = None
	info: ApiInfo = None
	db: CustomDb = None
	market: str = None
	lang: str = None


class CustomException(exceptions.APIException):
	def __init__(
			self,
			message,
			comment,
			description,
			result,
			code,
			template,
			template_data,
			**kwargs
	):
		self.message = message
		self.comment = comment
		self.description = description
		self.result = result
		self.code = code
		self.template = template
		self.template_data = template_data
		self.kwargs = kwargs
	
	def __repr__(self):
		return f'[{self.code}] {self.message}'
	
	def __str__(self):
		return self.__repr__()


class Token:
	def __init__(self, request: CustomRequest):
		self.request = request
	
	class DoesNotExist(BaseException):
		pass
	
	@staticmethod
	def _generate() -> str:
		return binascii.hexlify(os.urandom(20)).decode()
	
	@staticmethod
	def _is_admin(uid):
		return uid in [1]
	
	def _check_user(self):
		uid = self.request.User.uid
		if not uid:
			raise RuntimeError('No User Specified')
		return uid
	
	def regenerate(self, platform: str = None, token: str = None) -> str:
		"""(insert or update) and read token"""
		uid = self._check_user()
		if platform is None:
			platform = self.request.info.platform
		if token is None:
			token = self._generate()
		
		if self._is_admin(uid):
			return self.get_or_create(platform)['token']
		
		return self.request.db.server.upsert(
			f'users_token_{platform}',
			pd.DataFrame(
				columns=['uid', 'token'],
				data=[[uid, token]]
			).set_index('uid'),
			ts_columns='created',
			returning=['token'],
			schema='users_data'
		).token.values[0]
	
	def delete(self, platform=None):
		uid = self._check_user()
		if self._is_admin(uid):
			return self.get_or_create(platform)
		
		if platform is None:
			platform = self.request.info.platform
		
		self.request.db.server.delete(
			f'users_token_{platform}',
			[('uid', '=', uid)],
			schema='users_data'
		)
	
	def is_expired(self, platform=None) -> bool:
		uid = self._check_user()
		if platform is None:
			platform = self.request.info.platform
		
		return self.request.db.server.exists(
			f'users_token_{platform}',
			[
				('uid', '=', uid),
				(
					f"extract(epoch from '{self.request.start}' - created)",
					'>', self.request.info.token_expiration_in_seconds
				)
			],
			schema='users_data'
		)
	
	def get_or_create(self, platform=None) -> dict:
		""" insert, read """
		uid = self._check_user()
		
		if platform is None:
			platform = self.request.info.platform
		
		_q = f"""
		with sel as (
			select token, created, uid
			from users_data."users_token_{platform}"
			where uid = {uid}
		), ins as (
			insert into users_data."users_token_{platform}" (token, created, uid)
			select '{self._generate()}' token, '{self.request.start}' created, {uid} uid
				where not exists (select 1 x from sel)
				returning token, created, uid
			)
		select token, created, uid from ins union
		select token, created, uid from sel;
		"""
		res = self.request.db.server.custom(_q, None, to_commit=True, to_fetch=True).values[0]
		res = dict(zip(['token', 'created', 'uid'], res))
		return res
	
	def get(self, platform=None, **kwargs) -> dict:
		try:
			if platform is None:
				platform = self.request.info.platform
			
			return self.request.db.server.read(
				f'users_token_{platform}',
				['token', 'created', 'uid'],
				[(k, '=', v) for k, v in kwargs.items()],
				schema='users_data'
			).to_dict('records')[0]
		except:
			raise self.DoesNotExist
	
	def create(self, platform=None) -> dict:
		return self.get_or_create(platform)


class MainMiddleware:
	class utils:
		@staticmethod
		def get_request_headers(request: WSGIRequest) -> dict:
			""" get required data from request headers and ignore environment variables"""
			_vars = [
				'NUMBER_OF_PROCESSORS', 'COMMONPROGRAMFILES', 'COMMONPROGRAMFILES(X86)', 'COMPUTERNAME',
				'_OLD_VIRTUAL_PATH', '__INTELLIJ_COMMAND_HISTFILE__', 'SYSTEMDRIVE', 'LOGONSERVER', 'TEMP',
				'TMP', 'HOMEPATH', '_OLD_VIRTUAL_PROMPT', 'PATHEXT', 'IDEA_INITIAL_DIRECTORY', 'PYCHARM', 'USERNAME',
				'PROGRAMFILES', 'PROGRAMFILES(X86)', 'USERDOMAIN_ROAMINGPROFILE', 'LOCALAPPDATA', 'TERMINAL_EMULATOR',
				'PROCESSOR_IDENTIFIER', 'DRIVERDATA', 'APPDATA', 'ALLUSERSPROFILE', 'USERDOMAIN', 'PROCESSOR_LEVEL',
				'PROGRAMDATA', 'COMSPEC', 'PROCESSOR_ARCHITECTURE', 'PUBLIC', 'SYSTEMROOT', 'PROCESSOR_REVISION',
				'ONEDRIVE', 'PSMODULEPATH', 'PATH', 'USERPROFILE', 'WINDIR', 'PROGRAMW6432', 'OS', 'VIRTUAL_ENV',
				'HOMEDRIVE', 'COMMONPROGRAMW6432', 'DJANGO_SETTINGS_MODULE', 'RUN_MAIN', 'SERVER_NAME',
				'GATEWAY_INTERFACE', 'SERVER_PORT', 'REMOTE_HOST', 'SCRIPT_NAME',
				'PROMPT'
			]
			headers = {}
			for k, v in request.META.items():
				if k in _vars or k.startswith(('wsgi', 'waitress', 'gunicorn')):
					continue
				headers.update({k: v})
			if 'CONTENT_TYPE' not in headers:
				headers.update({'CONTENT_TYPE': 'text/plain'})
			
			return headers
		
		@staticmethod
		def get_request_client_ip(request: WSGIRequest) -> str:
			""" get client ip from request """
			ip = request.META.get('HTTP_X_FORWARDED_FOR')
			if not ip:
				ip = request.META.get('HTTP_X_REAL_IP')
				if not ip:
					ip = request.META.get('REMOTE_ADDR')
			return ip
		
		@staticmethod
		def handle_resolver_match(request: WSGIRequest) -> WSGIRequest:
			"""
			UpdatedAt: ---

			About:
			-----
			finds request's view (if can not find -> fill parameters with None)

			Django Errors:
			-----
			main:
				| ---
			links:
				| ---
			possible attack:
				| ---
			unexpected:
				| ---
			"""
			try:
				request.resolver_match = resolve(request.path)
				request.info = request.resolver_match.kwargs['info']
			except:
				request.resolver_match = None
				request.info = ApiInfo()
				# noinspection PyUnresolvedReferences
				request.info.input_body_block_additional = False
				# noinspection PyUnresolvedReferences
				request.info.input_params_block_additional = False
			
			return request
		
		@staticmethod
		def convert_request_wsgi_to_drf(request: WSGIRequest) -> ty.Union[CustomRequest, HttpResponse]:
			"""
			UpdatedAt: ---

			About:
			-----
			converts WSGI Request to DRF(django rest framework)

			Django Errors:
			-----
			main:
				| ---
			links:
				| ---
			possible attack:
				| status: 405
				| comment: unexpected error while converting WSGI to DRF
				| Message: UTILSD.Defaults.Messages.method_not_allowed
				| Result: null
				| -------------------------------------------------------
			unexpected:
				| ---
			"""
			try:
				if request.method in all_methods:
					res = wsgi_convertor(request).data
				else:
					res = api_view([request.method])(lambda x: Response({'request': x}))(request).data
				
				if 'detail' in res:
					raise Exception(res['detail'])
				res = res['request']
				
				# add request attrs to res
				res.resolver_match = request.resolver_match
				# noinspection PyUnresolvedReferences
				res.info = request.info
				res.headers = request.headers
				# noinspection PyUnresolvedReferences
				res.client_ip = request.client_ip
			except Exception as e:
				request.input_params = dict(request.GET)
				if request.POST:
					request.input_body = request.POST
				elif request.body:
					request.input_body = request.body.decode('utf-8')
				else:
					request.input_body = {}
				
				if getattr(e, 'default_code') == 'not_acceptable':
					comment = 'WSGI -> DRF'
				else:
					comment = f'WSGI -> DRF {djn_def.Messages.unexpected}'
				
				res = m_raise(
					request,
					djn_def.Messages.bad_input,
					e,
					exc_comment=comment,
				)
			return res
		
		@staticmethod
		def fill_request_params(request: CustomRequest) -> CustomRequest:
			"""
			UpdatedAt: ---

			About:
			-----
			fill input_body, input_params, input_body

			Django Errors:
			-----
			main:
				| ---
			links:
				| ---
			possible attack:
				| status: 400
				| comment: cant load request data
				| Message: UTILSD.Defaults.Messages.bad_input
				| Result: null
			unexpected:
				| ---
			"""
			
			try:
				request.input_params = dict(request.query_params)
			except:
				request.input_params = {}
			try:
				request.input_body = dict(request.data)
			except:
				request.input_body = {}
			
			lang = request.headers.get('HTTP_ACCEPT_LANGUAGE', prj_def.Languages.en)
			if lang not in prj_def.Languages.all:
				lang = prj_def.Languages.fa
			request.lang = lang
			
			return request
		
		@staticmethod
		def check_request_method(request: CustomRequest) -> ty.Union[CustomRequest, HttpResponse]:
			"""
			UpdatedAt: ---

			About:
			-----
			check if request method is in allowed methods specified for request

			Django Errors:
			-----
			main:
				| status: 405
				| comment: bad method
				| Message: UTILSD.Defaults.Messages.method_not_allowed
				| Result: null
			links:
				| ---
			possible attack:
				| ---
			unexpected:
				| ---
			"""
			
			if request.info.methods and request.method not in request.info.methods:
				return m_raise(
					request,
					djn_def.Messages.method_not_allowed,
					f'{request.method}',
					code=405
				)
			return request
		
		@staticmethod
		def handle_cors(request: CustomRequest) -> ty.Union[CustomRequest, HttpResponse]:
			"""
			UpdatedAt: ---

			About:
			-----
			if request method is OPTIONS -> return response with pre-set headers to handle CORS

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
				| ---
			possible attack:
				| ---
			unexpected:
				| ---
			"""
			
			if request.method == 'OPTIONS':
				request.info.response_additional_headers = {
					'Access-Control-Max-Age': '86400',
					'Access-Control-Allow-Headers': 'accept, accept-encoding, content-type, dnt, origin, user-agent, x-csrftoken, x-requested-with',
					'Access-Control-Allow-Methods': 'GET, POST',
				}
				return m_raise(
					request,
					djn_def.Messages.ok,
					do_log=False,
					empty_response=True,
					code=200
				)
			return request
		
		@staticmethod
		def ban_bad_requests(request: CustomRequest) -> ty.Union[CustomRequest, HttpResponse]:
			"""
			UpdatedAt: ---

			About:
			-----
			handle postman requests and unsupported content types

			Django Errors:
			-----
			main:
				| ---
			links:
				| ---
			possible attack:
				| status: 400
				| comment: bad request agent
				| Message: UTILSD.Defaults.Messages.bad_input
				| Result: ** just_message **
				| ---------------------------------------------------------------
				| status: 400
				| comment: bad content type
				| Message: UTILSD.Defaults.Messages.bad_input
				| Result: ** just_message **
				| ---------------------------------------------------------------
				| status: 400
				| comment: bad host
				| Message: UTILSD.Defaults.Messages.bad_input
				| Result: ** just_message **
				| ---------------------------------------------------------------
				| status: 400
				| comment: ip blocked
				| Message: UTILSD.Defaults.Messages.ip_blocked
				| Result: ---
				| ---------------------------------------------------------------
			unexpected:
				| ---
			"""
			
			# content-types
			_content_type = request.headers.get('CONTENT_TYPE', '').split(';')[0]
			if _content_type not in request.info.content_types_to_accept:
				_cm = f'bad content type `{_content_type}`'
				if request.resolver_match is not None or request.path in djn_def.social_urls:
					_cm += f' {djn_def.Messages.possible_attack}'
				
				return m_raise(
					request,
					djn_def.Messages.bad_input,
					_cm,
					response_just_message=True
				)
			
			if not prj_def.is_server:
				return request
			
			# bad useragent
			ua = request.headers.get('HTTP_USER_AGENT', '')
			if re.match('postman|curl|nmap', ua, re.IGNORECASE):
				return m_raise(
					request,
					djn_def.Messages.bad_input,
					f'request from banned user agent `{ua}` {djn_def.Messages.possible_attack}',
					response_just_message=True
				)
			
			if 'HTTP_POSTMAN_TOKEN' in request.headers:
				return m_raise(
					request,
					djn_def.Messages.bad_input,
					f'request from postman {djn_def.Messages.possible_attack}',
					response_just_message=True
				)
			
			# ban bad host
			host = request.headers.get('HTTP_HOST')
			if host is None or host.split(':')[0] not in djn_def.allowed_hosts:
				return m_raise(
					request,
					djn_def.Messages.bad_input,
					f'bad host `{host}` {djn_def.Messages.possible_attack}',
					response_just_message=True
				)
			
			if request.db.server.exists(
					'ip_blocked',
					[('ip', '=', request.client_ip), ('block_until', '>=', request.start)],
					schema='users_data'
			):
				return m_raise(
					request,
					djn_def.Messages.ip_blocked,
					f'ip blocked {djn_def.Messages.possible_attack}',
				)
			
			return request
		
		@staticmethod
		def check_input_model(request: CustomRequest) -> ty.Union[CustomRequest, HttpResponse]:
			"""errors are based on model"""
			if request.info.input_model == djn_def.Models.app:
				"""
				UpdatedAt: ---

				Django Errors:
				-----
				main:
					| ---
				links:
					| ---
				possible attack:
					| status: 400
					| comment: 'input' key not provided
					| Message: UTILSD.Defaults.Messages.bad_input
					| Result: null
					| ---------------------------------------------------------------
					| status: 400
					| comment: decryption error
					| Message: UTILSD.Defaults.Messages.bad_input
					| Result: null
					| ---------------------------------------------------------------
					| status: 400
					| comment: not json serializable (encryption at risk)
					| Message: UTILSD.Defaults.Messages.bad_input
					| Result: null
					| ---------------------------------------------------------------
					| status: 400
					| comment: `HEADERS` key not provided (encryption at risk)
					| Message: UTILSD.Defaults.Messages.bad_input
					| Result: null
					| ---------------------------------------------------------------
					| status: 400
					| comment: `CONTENTS` key not provided (encryption at risk)
					| Message: UTILSD.Defaults.Messages.bad_input
					| Result: null
					| ---------------------------------------------------------------
					| status: 400
					| comment: `TIMESTAMP` header not provided (encryption at risk)
					| Message: UTILSD.Defaults.Messages.bad_input
					| Result: null
					| ---------------------------------------------------------------
					| status: 451
					| comment: request timestamp is old
					| Message: UTILSD.Defaults.Messages.bad_timestamp
					| Result: null
					| ---------------------------------------------------------------
				unexpected:
					| ---
				"""
				
				__input = request.input_body.get('input')
				if not __input:
					return m_raise(
						request,
						djn_def.Messages.bad_input,
						comment=f"'input' key not provided {djn_def.Messages.possible_attack} %100"
					)
				
				try:
					decrypted = Encryptions.V1().decrypt(request.input_body['input'])
				except Exception as err:
					return m_raise(
						request,
						djn_def.Messages.bad_input,
						err,
						exc_comment=f'decryption error {djn_def.Messages.possible_attack} %100'
					)
				
				try:
					input_data = Json.decode(decrypted, do_raise=True)
				except Exception as err:
					return m_raise(
						request,
						djn_def.Messages.bad_input,
						err,
						exc_comment=f'not json serializable {djn_def.Messages.possible_attack} %100 {djn_def.Messages.encryption_at_risk}'
					)
				
				headers = input_data.get('HEADERS')
				contents = input_data.get('CONTENTS')
				
				if headers is None:
					return m_raise(
						request,
						djn_def.Messages.bad_input,
						comment=f'`HEADERS` key not provided {djn_def.Messages.possible_attack} %100 {djn_def.Messages.encryption_at_risk}'
					)
				if contents is None:
					return m_raise(
						request,
						djn_def.Messages.bad_input,
						comment=f'`CONTENTS` key not supplied {djn_def.Messages.possible_attack} %100 {djn_def.Messages.encryption_at_risk}'
					)
				
				request.META.update(headers)
				request.headers.update(headers)
				request.input_body = contents
				
				timestamp = request.headers.get('HTTP_TIMESTAMP')
				if timestamp is None:
					return m_raise(
						request,
						djn_def.Messages.bad_input,
						comment=f'`TIMESTAMP` header not provided {djn_def.Messages.possible_attack} %100 {djn_def.Messages.encryption_at_risk}'
					)
				try:
					timestamp = Time.ts2dt(timestamp, 'gmt', remove_tz=True)
				except:
					return m_raise(
						request,
						djn_def.Messages.bad_input,
						comment=f'bad `TIMESTAMP` header {djn_def.Messages.possible_attack} %100 {djn_def.Messages.encryption_at_risk}'
					)
				if abs(Time.ParseTimeDelta(request.start - timestamp).hours) >= 48:
					return m_raise(
						request,
						djn_def.Messages.bad_timestamp,
						comment=f"{timestamp}, curr_ts -> ({request.start}) {djn_def.Messages.possible_attack} %70",
						code=451
					)
			elif request.info.input_model == djn_def.Models.web:
				"""
				UpdatedAt: ---

				Django Errors:
				-----
				main:
					| ---
				links:
					| ---
				possible attack:
					| status: 400
					| comment: 'input' key not provided
					| Message: UTILSD.Defaults.Messages.bad_input
					| Result: null
					| ---------------------------------------------------------------
					| status: 400
					| comment: decryption error
					| Message: UTILSD.Defaults.Messages.bad_input
					| Result: null
					| ---------------------------------------------------------------
					| status: 400
					| comment: not json serializable (encryption at risk)
					| Message: UTILSD.Defaults.Messages.bad_input
					| Result: null
					| ---------------------------------------------------------------
					| status: 400
					| comment: `HEADERS` key not provided (encryption at risk)
					| Message: UTILSD.Defaults.Messages.bad_input
					| Result: null
					| ---------------------------------------------------------------
					| status: 400
					| comment: `CONTENTS` key not provided (encryption at risk)
					| Message: UTILSD.Defaults.Messages.bad_input
					| Result: null
					| ---------------------------------------------------------------
					| status: 400
					| comment: `TIMESTAMP` header not provided (encryption at risk)
					| Message: UTILSD.Defaults.Messages.bad_input
					| Result: null
					| ---------------------------------------------------------------
					| status: 451
					| comment: request timestamp is old
					| Message: UTILSD.Defaults.Messages.bad_timestamp
					| Result: null
					| ---------------------------------------------------------------
				unexpected:
					| ---
				"""
				
				__input = request.input_body.get('input')
				if not __input:
					return m_raise(
						request,
						djn_def.Messages.bad_input,
						comment=f"'input' key not provided {djn_def.Messages.possible_attack} %100"
					)
				
				try:
					decrypted = Encryptions.V1().decrypt(request.input_body['input'])
				except Exception as err:
					return m_raise(
						request,
						djn_def.Messages.bad_input,
						err,
						exc_comment=f'decryption error {djn_def.Messages.possible_attack} %100'
					)
				
				try:
					input_data = Json.decode(decrypted, do_raise=True)
				except Exception as err:
					return m_raise(
						request,
						djn_def.Messages.bad_input,
						err,
						exc_comment=f'not json serializable {djn_def.Messages.possible_attack} %100 {djn_def.Messages.encryption_at_risk}'
					)
				
				headers = input_data.get('HEADERS')
				contents = input_data.get('CONTENTS')
				
				if headers is None:
					return m_raise(
						request,
						djn_def.Messages.bad_input,
						comment=f'`HEADERS` key not provided {djn_def.Messages.possible_attack} %100 {djn_def.Messages.encryption_at_risk}'
					)
				if contents is None:
					return m_raise(
						request,
						djn_def.Messages.bad_input,
						comment=f'`CONTENTS` key not supplied {djn_def.Messages.possible_attack} %100 {djn_def.Messages.encryption_at_risk}'
					)
				
				request.META.update(headers)
				request.headers.update(headers)
				request.input_body = contents
				
				timestamp = request.headers.get('HTTP_TIMESTAMP')
				if timestamp is None:
					return m_raise(
						request,
						djn_def.Messages.bad_input,
						comment=f'`TIMESTAMP` header not provided {djn_def.Messages.possible_attack} %100 {djn_def.Messages.encryption_at_risk}'
					)
				try:
					timestamp = Time.ts2dt(timestamp, 'gmt', remove_tz=True)
				except:
					return m_raise(
						request,
						djn_def.Messages.bad_input,
						comment=f'bad `TIMESTAMP` header {djn_def.Messages.possible_attack} %100 {djn_def.Messages.encryption_at_risk}'
					)
				if abs(Time.ParseTimeDelta(request.start - timestamp).hours) >= 48:
					return m_raise(
						request,
						djn_def.Messages.bad_timestamp,
						comment=f"{timestamp}, curr_ts -> ({request.start}) {djn_def.Messages.possible_attack} %70",
						code=451
					)
			return request
		
		@staticmethod
		def check_platform_required_data(request: CustomRequest) -> ty.Union[CustomRequest, HttpResponse]:
			""" errors are based on platform """
			if request.info.platform == djn_def.Platforms.app:
				"""
				UpdatedAt: ---
				
				Django Errors:
				-----
				main:
					| status: 426
					| comment: update required
					| Message: UTILSD.Defaults.Messages.out_of_date
					| Result: null
				links:
					| ---
				possible attack:
					| status: 400
					| comment: `APP_VERSION` header not provided (encryption_at_risk)
					| Message: UTILSD.Defaults.Messages.bad_input
					| Result: null
					| ---------------------------------------------------------------
					| status: 400
					| comment: `APP_VERSION` header is not numeric (encryption_at_risk)
					| Message: UTILSD.Defaults.Messages.bad_input
					| Result: null
					| ---------------------------------------------------------------
				unexpected:
					| ---
				"""
				app_version = request.headers.get('HTTP_APP_VERSION')
				if not app_version:
					return m_raise(
						request,
						djn_def.Messages.bad_input,
						f'`APP_VERSION` header not provided {djn_def.Messages.possible_attack} %100 '
						f'{djn_def.Messages.encryption_at_risk}'
					)
				if not isinstance(app_version, int):
					return m_raise(
						request,
						djn_def.Messages.bad_input,
						f'`APP_VERSION` header is not numeric {djn_def.Messages.possible_attack} %100 '
						f'{djn_def.Messages.encryption_at_risk}'
					)
				
				if app_version < djn_def.app_force_version:
					return m_raise(
						request,
						djn_def.Messages.out_of_date,
						f'{app_version}<{djn_def.app_force_version}',
						result={'link': 'UPDATE_LINK'},  # fillme
						code=426
					)
				
				to_update = {
					'token': request.headers.get('HTTP_AUTHENTICATION'),
					'HTTP_APP_VERSION': app_version
				}
				request.headers.update(to_update)
				request.META.update(to_update)
			elif request.info.platform == djn_def.Platforms.web:
				request.headers.update({'token': request.headers.get('HTTP_AUTHENTICATION')})
			elif request.info.platform == djn_def.Platforms.test:
				request.headers.update({
					'token': request.headers.get('HTTP_AUTHENTICATION'),
					'testnet_user': request.headers.get('HTTP_TESTNET_AUTHENTICATION'),
				})
				if not request.headers['testnet_user']:
					d_raise(
						request,
						djn_def.Messages.possible_attack,
						f'no testnet_user {djn_def.Messages.possible_attack}',
						do_raise=False
					)
					return m_raise(
						request,
						djn_def.Messages.not_found_404,
						code=404,
						response_just_message=True,
						response_additional_headers={'Content-Type': 'text/plain'}
					)
				
				uid = request.db.server.read(
					'users_token_testnet',
					['uid'],
					[('token', '=', request.headers['testnet_user'])],
					schema='users_data'
				).uid.tolist()
				if not uid and not (
						re.match('^\/v1\/Test\/User\/SignupSeries\/(signup|re_send|verify)$', request.path)
						and request.db.server.count(
					'account_account', 'id', [('status', '=', 'ACTIVE')], schema='users_data') == 0
				):
					return m_raise(
						request,
						djn_def.Messages.not_found_404,
						f'testnet_user not found {djn_def.Messages.possible_attack}',
						code=404,
						response_just_message=True,
						response_additional_headers={'Content-Type': 'text/plain'}
					)
				
				if uid:
					request.headers['testnet_user'] = uid[0]
			
			return request
		
		@staticmethod
		def check_user_if_required(request: CustomRequest) -> ty.Union[CustomRequest, HttpResponse]:
			"""
			UpdatedAt: ---

			Django Errors:
			-----
			main:
				| status: 401
				| comment: token not supplied
				| Message: UTILSD.Defaults.Messages.bad_token
				| Result: null
				| ---------------------------------------------------------------
				| status: 401
				| comment: token does not exist
				| Message: UTILSD.Defaults.Messages.bad_token
				| Result: null
				| ---------------------------------------------------------------
				| status: 401
				| comment: token expired
				| Message: UTILSD.Defaults.Messages.bad_token
				| Result: null
				| ---------------------------------------------------------------
			links:
				| ---
			possible attack:
				| ---
			unexpected:
				| ---
			"""
			if request.info.token_required:
				token = request.headers.get('token')
				
				if token is None:
					return m_raise(
						request,
						djn_def.Messages.bad_token,
						f'token not supplied',
						code=401
					)
				_Token = Token(request)
				
				try:
					request.User.uid = _Token.get(token=token)['uid']
				except Token.DoesNotExist:
					return m_raise(
						request,
						djn_def.Messages.bad_token,
						f'token does not exist',
						code=401
					)
				if _Token.is_expired():
					return m_raise(
						request,
						djn_def.Messages.bad_token,
						f'token expired',
						code=401,
					)
				
				request.User.token = token
				request.User.info(request, request.info.user_fields_needed)
				request.lang = request.User.lang
			
			return request
		
		@staticmethod
		def check_active_user_if_detected(request: CustomRequest) -> ty.Union[CustomRequest, HttpResponse]:
			"""
			UpdatedAt: ---

			Django Errors:
			-----
			main:
				| status: 403
				| comment: inactive user
				| Message: UTILSD.Defaults.Messages.inactive_user
				| Result: null
				| ---------------------------------------------------------------
				| status: 403
				| comment: suspended user
				| Message: UTILSD.Defaults.Messages.suspended_user
				| Result: null
				| ---------------------------------------------------------------
			links:
				| ---
			possible attack:
				| ---
			unexpected:
				| ---
			"""
			if request.User.uid is None:
				# no user detected
				return request
			
			if request.info.user_must_be_active and request.User.status != djn_def.Fields.status_map['active']:
				if request.User.status == djn_def.Fields.status_map['inactive']:
					return m_raise(
						request,
						djn_def.Messages.inactive_user,
						f'user is {request.User.status}',
						code=403,
					)
				else:
					return m_raise(
						request,
						djn_def.Messages.suspended_user,
						f'user is {request.User.status}',
						code=403,
					)
			
			return request
		
		@staticmethod
		def check_api_input_data(request: CustomRequest) -> ty.Union[CustomRequest, HttpResponse]:
			"""
			UpdatedAt: ---
			
			About:
			------
			loop over body and params of request and convert lists with one item to item itself
			and also check input data of request with required input data
			
			Django Errors:
			-----
			main:
				| ---
			links:
				| UTILSD.main.Validation.check_keys_with_types
			possible attack:
				| ---
			unexpected:
				| ---
			"""
			
			validator = Validation(
				request,
				possible_attack=request.info.validation_error_as_possible_attack,
				from_middleware=True
			)
			
			# body
			if request.info.recaptcha_action:
				request.info.input_body_optional.update({'recaptcha_token': [str]})
			
			_all = {
				**request.info.input_body_required,
				**request.info.input_body_optional,
			}
			for k, v in request.input_body.items():
				if list not in _all.get(k, [None]) and isinstance(v, list) and len(v) == 1:
					request.input_body[k] = v[0]
			
			res = validator.check_keys_with_types(
				request.input_body,
				request.info.input_body_required,
				request.info.input_body_optional,
				request.info.name,
				request.info.input_body_block_additional,
			)
			if res is not None:
				return res
			
			# params
			_all = {
				**request.info.input_params_required,
				**request.info.input_params_optional,
			}
			for k, v in request.input_params.items():
				if list not in _all.get(k, [None]) and isinstance(v, list) and len(v) == 1:
					request.input_params[k] = v[0]
			
			res = validator.check_keys_with_types(
				request.input_params,
				request.info.input_params_required,
				request.info.input_params_optional,
				request.info.name,
				request.info.input_params_block_additional,
			)
			if res is not None:
				return res
			
			return request
		
		@staticmethod
		def check_recaptcha(request: CustomRequest) -> ty.Union[CustomRequest, HttpResponse]:
			"""
			UpdatedAt: ---

			About:
			-----
			check and raise error if captcha token is not sent or valid
			** token must be sent in `recaptcha_token` key **
			** this check will be enabled if `recaptcha_action` is set in request.info **
			** `recaptcha_action` == 'all' -> do not check action and accept them all **

			Django Errors:
			-----
			main:
				| ---
			links:
				| ---
			possible attack:
				| status: 400
				| comment: token not sent
				| Message: UTILSD.Defaults.Messages.bad_input
				| Result: null
				| ----------------------------------------------------
				| status: 412
				| comment: token can not be verified
				| Message: UTILSD.Defaults.Messages.bad_recaptcha
				| Result: null
				| ----------------------------------------------------
			unexpected:
				| status: 400
				| comment: bad platform
				| Message: UTILSD.Defaults.Messages.bad_input
				| Result: null
				| ----------------------------------------------------
			"""
			if request.info.recaptcha_action is None:
				return request
			
			token = request.input_body.get('recaptcha_token')
			if not token:
				if request.info.platform == djn_def.Platforms.test:
					return request
				return m_raise(
					request,
					djn_def.Messages.bad_input,
					f'recaptcha not sent {djn_def.Messages.possible_attack}'
				)
			
			if request.info.platform == djn_def.Platforms.app:
				secret = prj_def.recaptcha_secret_app
			elif request.info.platform == djn_def.Platforms.web:
				secret = prj_def.recaptcha_secret_web
			elif request.info.platform == djn_def.Platforms.test:
				secret = prj_def.recaptcha_secret_web
			else:
				return m_raise(
					request,
					djn_def.Messages.bad_input,
					f'bad platform {request.info.platform} {djn_def.Messages.unexpected}'
				)
			
			verify_result = verify_recaptcha(
				secret,
				token,
				djn_def.recaptcha_hosts,
				djn_def.recaptcha_package_names,
				None if request.info.recaptcha_action == 'all' else [request.info.recaptcha_action]
			)
			if not verify_result['success']:
				return m_raise(
					request,
					djn_def.Messages.bad_recaptcha,
					f'{Json.encode(verify_result["obj"])} {djn_def.Messages.possible_attack}',
					code=412
				)
			return request
		
		@staticmethod
		def apply_output_model(request: ty.Union[CustomRequest, WSGIRequest], result: HttpResponse) -> HttpResponse:
			""" get output data ready for client """
			if hasattr(request.User, 'to_downgrade'):
				request.User.downgrade(request)
			
			request.db.close()
			if request.info.response_html:
				return result
			
			# noinspection PyUnresolvedReferences
			if hasattr(result, 'data'):
				data = result.data
				if request.info.output_model == djn_def.Models.app:
					result.content = f'"{Encryptions.V1().encrypt(Json.encode(data))}"'
				elif request.info.output_model == djn_def.Models.web:
					result.content = f'"{Encryptions.V1().encrypt(Json.encode(data))}"'
				elif request.info.output_model == djn_def.Models.none:
					result.content = Json.encode(data)
				elif request.info.output_model == djn_def.Models.test:
					result.content = Json.encode(data)
				del result.data
			
			return result
		
		@staticmethod
		def handle_popup(
				request: ty.Union[CustomRequest, WSGIRequest],
				result: ty.Union[HttpResponse, SimpleTemplateResponse]
		) -> HttpResponse:
			""" add `Popup` key to result """
			if not hasattr(result, 'data'):
				return result
			
			result.data.update({'Popup': None})
			
			if 200 <= result.status_code < 400:
				request_popups = Cache.api_popups.loc[Cache.api_popups.api == request.path]
				if request_popups.empty:
					return result
				request_popups = request_popups.loc[
					(request_popups.uids == '||')
					| (request_popups.uids.str.contains(f'|{request.User.uid}|'))
					]
				if request_popups.empty:
					return result
				
				popup_ids = request.db.server.custom(
					f"select id from users_data.popup where id in %s and not({request.User.uid} = any(users_seen)) order by id",
					[tuple(request_popups.id.tolist())], to_commit=False, to_fetch=True
				).id.tolist()
				if not popup_ids:
					return result
				result.data.update({'Popup': popup_ids[0]})
			return result
	
	def __init__(self, get_response):
		self.get_response = get_response
	
	def __call__(self, request: WSGIRequest):
		"""
		UpdatedAt: ---

		About:
		-----
			| set start time for request
			| get headers from request.META
			| get client ip from request.META
			| handle resolvers
			| convert request from WSGI to DRF
			| assign empty token to request headers
				later it will be filled with real token by 'Check.input_model' function
			| open a database connection for request (this connection will be closed on every error or at the end)
			| assign empty user to request
			| fill request input body and params
			| ban bad requests
			| handle cors
			| check input model
			| handle 404
			| check request method
			| check platform required data
			| check user if required
			| check active user if detected
			| check api input data
			| check reCaptcha
			| RUN API VIEW
			| apply output model
			| handle popup
			| close database connection

		Django Errors:
		-----
		main:
			| ---
		links:
			| UTILSD.main.MainMiddleware.utils. ** all functions **
		possible attack:
			| ---
		unexpected:
			| status: 400
			| comment: unhandled error
			| Message: UTILSD.Defaults.Messages.unexpected
			| Result: null
			| ---------------------------------------------------------------
		"""
		# set start time for request
		request.start = Time.dtnow('gmt', remove_tz=True)
		
		# get headers from request.META
		setattr(request, 'headers', self.utils.get_request_headers(request))
		
		# get client ip from request.META
		setattr(request, 'client_ip', self.utils.get_request_client_ip(request))
		
		# assign empty token to request headers
		request.headers.update({'token': None})
		
		# open a database connection for request
		request.db = CustomDb()
		request.db.server.open()
		
		# assign empty user to request
		request.User = CustomUser()
		
		# assign default language
		request.lang = prj_def.Languages.en
		
		# handle resolvers
		request = self.utils.handle_resolver_match(request)
		
		# convert request from WSGI to DRF
		res = self.utils.convert_request_wsgi_to_drf(request)
		if isinstance(res, HttpResponse):
			return self.utils.apply_output_model(request, res)
		request = res
		
		# fill request input body and params
		request = self.utils.fill_request_params(request)
		
		# ban bad requests
		res = self.utils.ban_bad_requests(request)
		if isinstance(res, HttpResponse):
			return self.utils.apply_output_model(request, res)
		request = res
		
		# handle CORS
		res = self.utils.handle_cors(request)
		if isinstance(res, HttpResponse):
			return self.utils.apply_output_model(request, res)
		request = res
		
		# check request method
		res = self.utils.check_request_method(request)
		if isinstance(res, HttpResponse):
			return self.utils.apply_output_model(request, res)
		request = res
		
		# check input model
		res = self.utils.check_input_model(request)
		if isinstance(res, HttpResponse):
			return self.utils.apply_output_model(request, res)
		request = res
		
		# handle 404
		res = handler404(request, from_middleware=True)
		if isinstance(res, HttpResponse):
			return self.utils.apply_output_model(request, res)
		request = res
		
		# check platform required data
		res = self.utils.check_platform_required_data(request)
		if isinstance(res, HttpResponse):
			return self.utils.apply_output_model(request, res)
		request = res
		
		# check user if required
		res = self.utils.check_user_if_required(request)
		if isinstance(res, HttpResponse):
			return self.utils.apply_output_model(request, res)
		request = res
		
		# check active user if detected
		res = self.utils.check_active_user_if_detected(request)
		if isinstance(res, HttpResponse):
			return self.utils.apply_output_model(request, res)
		request = res
		
		# check api input data
		res = self.utils.check_api_input_data(request)
		if isinstance(res, HttpResponse):
			return self.utils.apply_output_model(request, res)
		request = res
		
		# check reCaptcha
		res = self.utils.check_recaptcha(request)
		if isinstance(res, HttpResponse):
			return self.utils.apply_output_model(request, res)
		request = res
		
		# RUN VIEW
		res = self.get_response(request)
		
		# response will reach this code no matter what (even if error occurs) [except for middleware errors]
		
		# if this api has popup return it
		res = self.utils.handle_popup(request, res)
		
		# apply output model
		return self.utils.apply_output_model(request, res)
	
	@staticmethod
	def process_exception(request, exc):
		if not isinstance(exc, CustomException):
			exc = d_raise(
				request,
				djn_def.Messages.unexpected,
				exc,
				exc_comment='[UNHANDLED]',
				do_raise=False,
				print_not_raised=False,
			)
		
		if exc.template and request.info.response_html:
			return _make_html_response_ready(
				request,
				exc.template,
				exc.template_data,
				exc.code,
				**exc.kwargs
			)
		
		return _make_json_response_ready(
			request,
			exc.message,
			exc.comment,
			exc.description,
			exc.result,
			exc.code,
			**exc.kwargs
		)


class FakeHeadersMiddleware:
	def __init__(self, get_response):
		self.get_response = get_response
	
	def __call__(self, request: CustomRequest):
		""" Add some Additional headers to response. """
		res = self.get_response(request)
		res.headers = dict(res.headers)
		
		res.headers.update({
			# 'Server': 'Apache/2.4.1 (Unix)',
			# 'Via': 'James',
			'X-Frame-Options': 'SAMEORIGIN',
			'X-XSS-Protection': '1; mode=block',
			'X-Content-Type-Options': 'nosniff',
			# 'Referrer-Policy': 'strict-origin-when-cross-origin',
			'Referrer-Policy': 'no-referrer-when-downgrade',
			'Content-Security-Policy': "default-src * data: 'unsafe-eval' 'unsafe-inline'",
			'Strict-Transport-Security': "max-age=31536000; includeSubDomains; preload",
		})
		if not hasattr(res, 'template_name') and not res.headers['Content-Type'].startswith('image'):
			res.headers['Content-Type'] = 'application/json'
		if hasattr(res, 'response_additional_headers'):
			res.headers.update(res.response_additional_headers)
		
		res.headers.update({
			'Access-Control-Allow-Origin': request.headers['HTTP_ORIGIN'] if bool(
				re.match(
					'^https://(?:.+\.)?polygon\.com$',
					request.headers.get('HTTP_ORIGIN', ''))
			) else '',
			'Access-Control-Allow-Credentials': 'true',
		})
		# res.headers.update({'Access-Control-Allow-Origin': '*'})
		return res


class Validation:
	""" validate api data and raise errors in case of bad data """
	
	def __init__(self, request: CustomRequest, possible_attack=False, from_middleware=False):
		"""
		possible_attack: treat errors as possible attack
		from_middleware: this class is called from Middleware (raise should use m_raise instead of d_raise)
		"""
		self.request = request
		self.possible_attack = possible_attack
		self.from_middleware = from_middleware
	
	def _handle_kwargs(self, kwargs: dict) -> dict:
		""" applies to all method to get some standard kwargs """
		return {
			'possible_attack': kwargs.get('possible_attack', self.possible_attack),
			'djn_def.Messages.bad_input': kwargs.get('djn_def.Messages.bad_input', djn_def.Messages.bad_input),
			'err_code': kwargs.get('err_code', 400),
			'must_be_list': kwargs.get('must_be_list', False),
		}
	
	def _raise(
			self,
			message: str,
			comment: str,
			code=400,
			**kwargs
	) -> ty.Union[HttpResponse, CustomException]:
		""" raise error based on `from_middleware` or not """
		func = m_raise if self.from_middleware else d_raise
		return func(
			self.request,
			message,
			comment,
			code=code,
			location=Log.curr_info(4)
		)
	
	def check_type(
			self,
			data,
			type_to_be,
			tag: str,
			**kwargs
	):
		"""
		UpdatedAt: ---

		Django Errors:
		-----
		main:
			| status: 400
			| comment: bad type
			| Message: UTILSD.Defaults.Messages.bad_input
			| Result: null
			| ---------------------------------------------------------------
		links:
			| ---
		possible attack:
			| ---
		unexpected:
			| ---
		"""
		possible_attack = kwargs.pop('possible_attack', self.possible_attack)
		type_to_be = type_to_be if dev_utils.is_itterable(type_to_be) else [type_to_be]
		
		if type(data) not in type_to_be:
			return self._raise(
				djn_def.Messages.bad_input,
				f'`{tag}` `{type(data)}` must be `{type_to_be}`'
				f'{djn_def.Messages.possible_attack if possible_attack else ""}',
				**kwargs
			)
	
	def check_standard(
			self,
			data,
			standard_ones: list,
			tag: str,
			**kwargs
	):
		"""
		UpdatedAt: ---

		Django Errors:
		-----
		main:
			| status: 400
			| comment: data must be list to check standard
			| Message: UTILSD.Defaults.Messages.bad_input
			| Result: null
			| ---------------------------------------------------------------
			| status: 400
			| comment: data not in standard ones
			| Message: UTILSD.Defaults.Messages.bad_input
			| Result: null
			| ---------------------------------------------------------------
		links:
			| ---
		possible attack:
			| ---
		unexpected:
			| ---
		"""
		possible_attack = kwargs.pop('possible_attack', self.possible_attack)
		must_be_list = kwargs.pop('must_be_list', False)
		if must_be_list and not isinstance(data, list):
			return self._raise(
				djn_def.Messages.bad_input,
				f'`{tag}` `{type(data)}` must be list to check standard '
				f'{djn_def.Messages.possible_attack if possible_attack else ""}',
				**kwargs
			)
		if isinstance(data, dict):
			data = list(data.keys())
		if isinstance(data, list):
			has_error = not List.contains(data, standard_ones, to_log=False, **kwargs)
		else:
			has_error = data not in standard_ones
		
		if has_error:
			return self._raise(
				djn_def.Messages.bad_input,
				f'`{tag}` not in standard ones '
				f'{djn_def.Messages.possible_attack if possible_attack else ""}',
				**kwargs
			)
	
	def check_duplicates(
			self,
			data: list,
			tag: str,
			**kwargs
	):
		"""
		UpdatedAt: ---

		Django Errors:
		-----
		main:
			| status: 400
			| comment: data must be list to check duplicates
			| Message: UTILSD.Defaults.Messages.bad_input
			| Result: null
			| ---------------------------------------------------------------
			| status: 400
			| comment: data contains duplicate values
			| Message: UTILSD.Defaults.Messages.bad_input
			| Result: null
			| ---------------------------------------------------------------
		links:
			| ---
		possible attack:
			| ---
		unexpected:
			| ---
		"""
		possible_attack = kwargs.pop('possible_attack', self.possible_attack)
		
		if not isinstance(data, list):
			return self._raise(
				djn_def.Messages.bad_input,
				f'`{tag}` `{type(data)}` must be list to check duplicates '
				f'{djn_def.Messages.possible_attack if possible_attack else ""}',
				**kwargs
			)
		
		if List.has_duplicates(data):
			return self._raise(
				djn_def.Messages.bad_input,
				f'`{tag}` contains duplicate values '
				f'{djn_def.Messages.possible_attack if possible_attack else ""}',
				**kwargs
			)
	
	def check_keys(
			self,
			data,
			required_keys: list,
			optional_keys: list,
			tag: str = None,
			block_additional_keys=True,
			**kwargs
	):
		"""
		UpdatedAt: ---

		Django Errors:
		-----
		main:
			| status: 400
			| comment: data must be dict to check keys
			| Message: UTILSD.Defaults.Messages.bad_input
			| Result: null
			| ---------------------------------------------------------------
			| status: 400
			| comment: data which is required is not present in input
			| Message: UTILSD.Defaults.Messages.bad_input
			| Result: null
			| ---------------------------------------------------------------
			| status: 400
			| comment: data contains additional keys which is blocked
			| Message: UTILSD.Defaults.Messages.bad_input
			| Result: null
			| ---------------------------------------------------------------
		links:
			| ---
		possible attack:
			| ---
		unexpected:
			| ---
		"""
		possible_attack = kwargs.pop('possible_attack', self.possible_attack)
		
		if not isinstance(data, dict):
			return self._raise(
				djn_def.Messages.bad_input,
				f'`{tag}` `{type(data)}` must be dict to check keys '
				f'{djn_def.Messages.possible_attack if possible_attack else ""}',
				**kwargs
			)
		for item in required_keys:
			if item not in data:
				return self._raise(
					djn_def.Messages.bad_input,
					f'`{tag}` `{item}` which is required is not present in input '
					f'{djn_def.Messages.possible_attack if possible_attack else ""}',
					**kwargs
				)
		if block_additional_keys:
			additional_keys = set(data.keys()) - set(required_keys + optional_keys)
			if additional_keys:
				return self._raise(
					djn_def.Messages.bad_input,
					f'`{tag}` contains additional key(s) which is blocked `{list(additional_keys)}`'
					f'{djn_def.Messages.possible_attack if possible_attack else ""}',
					**kwargs
				)
	
	def check_keys_with_types(
			self,
			data,
			required_keys: dict,
			optional_keys: dict,
			tag: str = None,
			block_additional_keys=True,
			**kwargs
	):
		"""
		UpdatedAt: ---

		Django Errors:
		-----
		main:
			| status: 400
			| comment: data must be dict to check keys & types
			| Message: UTILSD.Defaults.Messages.bad_input
			| Result: null
			| ---------------------------------------------------------------
			| status: 400
			| comment: data which is required is not present in input
			| Message: UTILSD.Defaults.Messages.bad_input
			| Result: null
			| ---------------------------------------------------------------
			| status: 400
			| comment: data required body has bad value type
			| Message: UTILSD.Defaults.Messages.bad_input
			| Result: null
			| ---------------------------------------------------------------
			| status: 400
			| comment: data optional body has bad value type
			| Message: UTILSD.Defaults.Messages.bad_input
			| Result: null
			| ---------------------------------------------------------------
			| status: 400
			| comment: data contains additional keys which is blocked
			| Message: UTILSD.Defaults.Messages.bad_input
			| Result: null
			| ---------------------------------------------------------------
			| status: 400
			| comment: checkTruthiness failed
			| Message: UTILSD.Defaults.Messages.bad_input
			| Result: null
			| ---------------------------------------------------------------
		links:
			| ---
		possible attack:
			| ---
		unexpected:
			| ---
		"""
		possible_attack = kwargs.pop('possible_attack', self.possible_attack)
		
		if type(data) is not dict:
			return self._raise(
				djn_def.Messages.bad_input,
				f'`{tag}` `{type(data)}` must be dict to check multiple keys & types '
				f'{djn_def.Messages.possible_attack if possible_attack else ""}',
				**kwargs
			)
		for item, types in required_keys.items():
			if item not in data:
				return self._raise(
					djn_def.Messages.bad_input,
					f'`{tag}` `{item}` which is required is not present in input '
					f'{djn_def.Messages.possible_attack if possible_attack else ""}',
					**kwargs
				)
			if types and type(data[item]) not in types:
				return self._raise(
					djn_def.Messages.bad_input,
					f'`{tag}` `{item}` `{type(data[item])}` must be in {types} '
					f'{djn_def.Messages.possible_attack if possible_attack else ""}',
					**kwargs
				)
			if 'checkTruthiness' in types and not data[item]:
				return self._raise(
					djn_def.Messages.bad_input,
					f'`{tag}` `{item}` checkTruthiness failed '
					f'{djn_def.Messages.possible_attack if possible_attack else ""}',
					**kwargs
				)
		for item, types in optional_keys.items():
			if types and item in data:
				if type(data[item]) not in types:
					return self._raise(
						djn_def.Messages.bad_input,
						f'`{tag}` `{item}` `{type(data[item])})` must be in {types} '
						f'{djn_def.Messages.possible_attack if possible_attack else ""}',
						**kwargs
					)
			
			if 'checkTruthiness' in types and item in data and not data[item]:
				return self._raise(
					djn_def.Messages.bad_input,
					f'`{tag}` `{item}` checkTruthiness failed '
					f'{djn_def.Messages.possible_attack if possible_attack else ""}',
					**kwargs
				)
		
		if block_additional_keys:
			additional_keys = set(data.keys()) - set(list(required_keys.keys()) + list(optional_keys.keys()))
			if additional_keys:
				return self._raise(
					djn_def.Messages.bad_input,
					f'`{tag}` contains additional key(s) which is blocked `{list(additional_keys)}`'
					f'{djn_def.Messages.possible_attack if possible_attack else ""}',
					**kwargs
				)


# region Response

def d_response(
		request: CustomRequest,
		message: str,
		comment: str = None,
		result: ty.Union[dict, list] = None,
		description: ty.Union[dict, str] = None,
		code: int = 200,
		**kwargs
):
	"""
	log and send response to client

	kwargs:
		redirect_to:
			redirect client to this address.
		template:
			return template response
		template_data:
			dictionary to render template with
		UTILSD.main._make_json_response_ready kwargs
		UTILS.dev_utils.Database.main.log kwargs

	"""
	db_log(
		request=request,
		response_message=message,
		response_result=result,
		comment=comment,
		response_code=code,
		location=Log.curr_info(3),
		**kwargs
	)
	
	template = kwargs.pop('template', None)
	template_data = kwargs.pop('template_data', {})
	
	if template and request.info.response_html:
		return _make_html_response_ready(
			request,
			template,
			template_data,
			code,
			**kwargs
		)
	else:
		return _make_json_response_ready(
			request,
			message,
			comment,
			description,
			result,
			code,
			**kwargs
		)


def d_raise(
		request: CustomRequest,
		message: str,
		comment: ty.Union[str, Exception] = None,
		result: ty.Union[dict, list] = None,
		description: ty.Union[dict, str] = None,
		code: int = 400,
		location: str = None,
		exception_class=CustomException,
		**kwargs
) -> CustomException:
	"""
	log and raise proper exception to send an error response to client

	kwargs:
		do_raise: bool, default: True
			indicates whether to raise the error or just log it
		exc_comment:
			specify comment for exception in `comment`
		template:
			raise error and return template response
		template_data:
			dictionary to render template with
		UTILSD.main._make_json_response_ready kwargs
		UTILS.dev_utils.Database.main.log kwargs
		UTILS.dev_utils.Log.main.log kwargs
		kwargs to pass to exception_class

	"""
	
	comment = comment if comment else ''
	if isinstance(comment, Exception):
		comment = f'{kwargs.pop("exc_comment", "")} {comment.__class__.__name__}({comment})'
	location = location if location else Log.curr_info(3)
	do_raise = kwargs.pop('do_raise', True)
	if not do_raise and kwargs.pop('print_not_raised', True):
		comment = f'(not raised) {comment}'
	
	Log.log(
		f'{message} {comment} user({request.User.uid}) {request.client_ip} [{code}]',
		django=True,
		location=location,
		**kwargs
	)
	db_log(
		request=request,
		response_message=message,
		comment=comment,
		response_result=result,
		response_code=code,
		location=location,
		**kwargs
	)
	
	exc = exception_class(
		message,
		comment,
		description,
		result,
		code,
		kwargs.pop('template', None),
		kwargs.pop('template_data', {}),
		**kwargs
	)
	if do_raise:
		raise exc
	return exc


def m_raise(
		request: ty.Union[CustomRequest, WSGIRequest],
		message: str,
		comment: ty.Union[str, Exception] = None,
		description: ty.Union[dict, str] = None,
		result: ty.Union[dict, list] = None,
		code: int = 400,
		location: str = None,
		**kwargs
):
	"""
	[for MiddleWare ONLY]

	log and raise proper exception to send an error response to client

	kwargs:
		do_raise: bool, default: True
			indicates whether to raise the error or just log it
		exc_comment:
			specify comment for exception in `comment`
		UTILSD.main._make_json_response_ready kwargs
		UTILS.dev_utils.Database.main.log kwargs
		UTILS.dev_utils.Log.main.log kwargs

	"""
	
	comment = comment if comment else ''
	if isinstance(comment, Exception):
		comment = f'{kwargs.pop("exc_comment", "")} {comment.__class__.__name__}({comment})'
	location = location if location else Log.curr_info(3)
	
	try:
		__client_ip = request.client_ip
	except AttributeError:
		__client_ip = ''
	
	uid = request.User.uid if hasattr(request, 'User') else None
	
	if kwargs.pop('do_log', True):
		Log.log(
			f'{message} {comment} user({uid}) {__client_ip} [{code}]',
			django=True,
			location=location,
			**kwargs
		)
	db_log(
		request=request,
		response_message=message,
		comment=comment,
		response_result=result,
		response_code=code,
		location=location,
		**kwargs
	)
	
	return _make_json_response_ready(
		request,
		message,
		comment,
		description,
		result,
		code,
		**kwargs
	)


# region utils

def _d_exception_handler(exc, context):
	""" DRF exception handler (raise exception to catch it in Middleware handler) """
	raise exc


def _d_main_return(
		request: CustomRequest,
		data: ty.Union[dict, str],
		code: int,
		template: str = None,
		**kwargs
) -> ty.Union[HttpResponse, HttpResponseRedirect]:
	"""
	main function to return response to client
	"""
	
	redirect_to = kwargs.pop('redirect_to', None)
	if kwargs.pop('empty_response', False):
		res = HttpResponse('', status=code)
		res.data = None
	elif redirect_to:
		res = redirect(redirect_to)
		res.data = None
	elif request.info.response_html:
		if not template:
			if 200 <= code < 300:
				template = djn_def.templates['main']['success'][request.lang]
			else:
				template = djn_def.templates['main']['error'][request.lang]
				data = {}
		
		with open(f'{prj_def.project_root}/templates/{template}', 'r', encoding='utf-8') as f:
			res = SimpleTemplateResponse('main.html', {'myhtml': f.read().format(**data), **data}, status=code)
			res.template_address = template
			res.render()
	else:
		res = HttpResponse('', status=code)
		res.data = data
	
	res.response_additional_headers = {
		**request.info.response_additional_headers,
		**kwargs.pop('response_additional_headers', {})
	}
	return res


def _find_description_based_on_type(
		description,
		request: CustomRequest,
		code: int,
		message: str
):
	"""
	Example Configurations:
	{
		'API_NAME': {
			'type': 'code',
			400: {
				'type': 'message',
				djn_def.Messages.maximum_symbols: {
					'type': 'lang',
					'fa-ir': {
						'type': 'platform',
						'Web': 'PERSIAN'
					},
					'en-us': 'English Error',
				}
			}
		}
	}
	-------------------------------
	{
		'API_NAME': 'XX'
	}
	"""
	
	def main(desc):
		if not isinstance(desc, dict):
			return desc
		
		if desc['type'] == 'code':
			return main(desc.get(code))
		elif desc['type'] == 'message':
			return main(desc.get(message))
		elif desc['type'] == 'lang':
			return main(desc.get(request.lang))
		elif desc['type'] == 'platform':
			return main(desc.get(request.info.platform))
	
	return main(description)


def find_description(
		request: CustomRequest,
		code: int,
		message: str,
		result: ty.Union[dict, list],
		description: ty.Optional[ty.Union[dict, str]],
):
	if not description:
		# if no description was received from upper level consider using api_based description
		description = djn_def.descriptions_api_based.get(request.info.name)
	
	# search for api_based description
	description = _find_description_based_on_type(
		description,
		request,
		code,
		message
	)
	
	if description is None:
		# if no descriptions were found search for message_based description
		description = _find_description_based_on_type(
			djn_def.descriptions_message_based.get(message),
			request,
			code,
			message
		)
	
	# region fill custom descriptions
	if request.info.name == 'User_update' and code == 406:
		description = description.format(
			djn_def.descriptions_user_info_field_translator.get(result.get('field'), {}).get(request.lang, '')
		)
	# endregion
	
	return description


def _make_json_response_ready(
		request: CustomRequest,
		message: str,
		comment: str,
		description: ty.Optional[ty.Union[dict, str]],
		result: ty.Union[dict, list],
		code: int,
		**kwargs
):
	"""
	make a json serializable data to return to client
	"""
	# handle response_just_message
	if request.info.response_just_message or kwargs.pop('response_just_message', False):
		data = message
	else:
		data = {
			'Message': message,
			'Description': find_description(request, code, message, result, description),
			'Result': result,
		}
		if not prj_def.is_server:
			data.update({'comment': comment})
	
	return _d_main_return(request, data, code, **kwargs)


def _make_html_response_ready(
		request: CustomRequest,
		template: str,
		data: dict,
		code: int,
		**kwargs
):
	"""
	make template ready to return to client
	"""
	
	return _d_main_return(request, data, code, template, **kwargs)


# endregion


# endregion

# region Generate Random

def gen_random_username(db: Psql) -> str:
	"""
	generate random name for user's username and check for it to not be duplicate
	db: Psql(server)
	"""
	
	name = f'polygon_{String.gen_random_with_timestamp()}'
	while db.exists('account_account', [('username', '=', name)], schema='users_data'):
		name = f'polygon_{String.gen_random_with_timestamp()}'
	return name


# endregion

# region Regex


def check_regex(request: CustomRequest, to_check: str, field_name: str, **kwargs):
	"""
	UpdatedAt: ---

	About:
	-----
	check `to_check` regex and raise error if did not match

	Django Errors:
	-----
	main:
		| status: 406
		| comment: regex_error
		| Message: UTILSD.Defaults.Messages.bad_input
		| Result: {"field": " **field_that_caused_error** "}
		| ----------------------------------------------------
	links:
		| ---
	possible attack:
		| ---
	unexpected:
		| status: 400
		| comment: field_name not found
		| Message: UTILSD.Defaults.Messages.unexpected
		| Result: null
		| ----------------------------------------------------
	"""
	
	def r_filter(_to_check: str, r_map: dict, check_regex2=False) -> ty.Optional[bool]:
		r = r_map.get('regex')
		r2 = r_map.get('regex2')
		r_err = r_map.get('err')
		ignore_illegal_chars = r_map.get('ignore_illegal_chars', False)
		r = r2 if check_regex2 else r
		
		if None in [r, r_err]:
			return
		if r == 'ALL':
			return True
		
		match = bool(re.search(r, _to_check))
		if match and not ignore_illegal_chars:
			return String.r_handle_illegal_chars(_to_check, except_keys=[','], ultra=True, injection_avoid=True)
		return match
	
	if field_name not in djn_def.Fields.regex_map.keys():
		d_raise(
			request,
			djn_def.Messages.unexpected,
			f'field `{field_name}` not found',
		)
	
	do_raise = kwargs.pop('do_raise', True)
	field_name_to_raise_with = kwargs.pop('field_name_to_raise_with', None)
	if not r_filter(to_check, djn_def.Fields.regex_map[field_name], **kwargs):
		if not do_raise:
			return False
		d_raise(
			request,
			djn_def.Messages.regex_error,
			f'{field_name} `{to_check}` {djn_def.Fields.regex_map[field_name]["err"]}',
			result={'field': field_name_to_raise_with if field_name_to_raise_with else field_name},
			code=406,
		)
	
	return True


# endregion

# region MiniView
def handler404(request: CustomRequest, force=False, from_middleware=False) -> ty.Union[CustomRequest, HttpResponse]:
	"""
	UpdatedAt: ---

	About:
	-----
	handle if no view was found for url

	Django Errors:
	-----
	main:
		| status: 404
		| comment: cant load request data
		| Message: UTILSD.Defaults.Messages.not_found_404
		| Result: null
	links:
		| ---
	possible attack:
		| ---
	unexpected:
		| ---
	"""
	
	if request.resolver_match is None or force:
		if request.info is None:
			request.info = ApiInfo()
		
		request.info.response_just_message = True
		request.info.response_additional_headers = {'Content-Type': 'text/plain'}
		
		func = m_raise if from_middleware else d_raise
		return func(
			request,
			djn_def.Messages.not_found_404,
			code=404
		)
	return request


# endregion

all_methods = [
	'GET',
	'POST',
	'PUT',
	'PATCH',
	'DELETE',
	'COPY',
	'HEAD',
	'OPTIONS',
	'LINK',
	'UNLINK',
	'PURGE',
	'LOCK',
	'UNLOCK',
	'PROPFIND',
	'VIEW'
]
wsgi_convertor = api_view(all_methods)(lambda x: Response({'request': x}))
