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
from django.urls import path
from django.urls import resolve, ResolverMatch
from rest_framework import exceptions
from rest_framework.decorators import api_view
from rest_framework.request import Request
from rest_framework.response import Response

from UTILS import dev_utils
from UTILS.dev_utils import Log
from UTILS.dev_utils.Database import log as db_log
from UTILS.dev_utils.Database.Psql import Psql
from UTILS.dev_utils.Objects import String, Time, List, Json
from UTILS.prj_utils import Defaults as prj_def
from UTILS.prj_utils.main import Encryptions
from UTILSD import Defaults as djn_def


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

	** for more info about input keys SeeAlso: UTILSD.main.MainMiddleware.utils.check_api_input_data **
	input_params_required -> which keys must be in request parameters
	input_params_optional -> which keys can be in request parameters
	input_params_block_additional -> block(raise) if additional keys where in request parameters?
	input_body_required -> which keys must be in request body
	input_body_optional -> which keys can be in request body
	input_body_block_additional -> block(raise) if additional keys where in request body?
	validation_error_as_possible_attack -> to treat errors about input as possible attack

	allow_files -> if a file was uploaded to this API treat it as possible_attack
	
	content_types_to_accept_standard -> [DO NOT CHANGE] (used by middleware) new items will be appended and drop_duplicated
	content_types_to_accept -> content types to support in addition to *content_types_to_accept_standard*
	
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
		'main': ['status'],  # SeeAlso: UTILSD.main.MainMiddleware.utils.check_active_user_if_detected
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
	
	allow_files = False
	
	content_types_to_accept_standard = ['application/json', 'multipart/form-data', 'text/plain']
	content_types_to_accept = [*content_types_to_accept_standard]
	
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
		'allow_files',
		'content_types_to_accept_standard',
		'content_types_to_accept',
	]
	
	def __init__(
			self,
			platform: str = djn_def.Platforms.none,
			methods: ty.List[str] = None,
			input_model: str = djn_def.Models.none,
			output_model: str = djn_def.Models.none,
			**kwargs
	):
		if platform not in djn_def.Platforms.all and platform != djn_def.Platforms.none:
			raise ValueError(f'bad platform {platform}')
		if input_model not in djn_def.Models.all and input_model != djn_def.Models.none:
			raise ValueError(f'bad input_model {input_model}')
		if output_model not in djn_def.Models.all and output_model != djn_def.Models.none:
			raise ValueError(f'bad output_model {output_model}')
		
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
		res.content_types_to_accept = List.drop_duplicates(res.content_types_to_accept)
		return res
	
	def path_generator(self, url: str, callback: callable, **kwargs):
		_n = url.replace('/', '_')
		return path(
			url,
			callback,
			name=_n,
			kwargs={'info': self.update(name=_n, **kwargs)}
		)


class CustomUser:
	info_fields = {
		'main': [
			'username',
			'email',
			'status'
		],
		'info': [
			'auth_email',
		],
		'get_token': True,
	}
	all_fields = {
		'main': [
			'username',
			'password',
			'email',
			'status',
			'date_joined',
			'last_login',
			'is_admin',
			'is_staff',
			'is_superuser',
			
			'modified',
		],
		'info': [
			'auth_email',
			
			'created',
			'modified',
		],
		'get_token': True
	}
	
	def __init__(self):
		self.bad_user = False
		self.uid = None
		self.token = None
		
		# main
		self.username = None
		self.password = None
		self.email = None
		self.status = None
		self.date_joined = None
		self.last_login = None
		self.is_admin = None
		self.is_staff = None
		self.is_superuser = None
		self.m_modified = None
		
		# info
		self.auth_email = None
		self.i_created = None
		self.i_modified = None
	
	def __repr__(self):
		return self.data_as_dict()
	
	def __str__(self):
		return str(self.data_as_dict())
	
	def data_as_dict(self) -> dict:
		"""return user's data as dictionary"""
		return {
			'bad_user': self.bad_user,
			'uid': self.uid,
			'token': self.token,
			'username': self.username,
			'password': self.password,
			'email': self.email,
			'status': self.status,
			'date_joined': self.date_joined,
			'last_login': self.last_login,
			'is_admin': self.is_admin,
			'is_staff': self.is_staff,
			'is_superuser': self.is_superuser,
			'm_modified': self.m_modified,
			'auth_email': self.auth_email,
			'i_created': self.i_created,
			'i_modified': self.i_modified,
		}
	
	def info(self, request, fields: dict, **kwargs):
		"""
		UpdatedAt: ---

		About:
		-----
		fetch specified `fields` of users data in database and update `self` with them

		Parameters:
		-----
		request: CustomRequest
		fields: [dict, str], union
			Examples:
				str:
					'all' -> get all user's data from db
					'info' -> get required data for user's info API from db
				dict:
					{
						'template': 'info',  # all
						'main': [
							'username',
							'password',
							'email',
							'status',
							'date_joined',
							'last_login',
							'is_admin',
							'is_staff',
							'is_superuser',

							'modified',
						],
						'info': [
							'auth_email',

							'created',
							'modified',
						],
						'get_token': true,
					}
		**kwargs: dict optional
			uid: int, default -> self.uid

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
		
		template = fields.pop('template', None)
		if template:
			template_data = None
			if template == 'info':
				template_data = self.info_fields
			elif template == 'all':
				template_data = self.all_fields
			
			if template_data:
				for k, v in template_data.items():
					if k in fields:
						fields.update({k: List.drop_duplicates(fields[k] + v)})
					else:
						fields.update({k: v})
		
		get_token = fields.get('get_token', False)
		if get_token and self.token is not None:
			get_token = False
		
		main_fields = fields.get('main', [])
		info_fields = fields.get('info', [])
		uid = kwargs.get('uid', self.uid)
		
		if all(item == [] for item in [
			main_fields,
			info_fields,
		]):
			d_raise(
				request,
				djn_def.Messages.unexpected,
				f'no fields specified ({request.info.name})',
				do_raise=True
			)
			return self
		
		_joins = []
		if main_fields:
			if 'modified' in main_fields:
				main_fields.remove('modified')
				main_fields.append('acc.modified as m_modified')
		if info_fields:
			if 'modified' in info_fields:
				info_fields.remove('modified')
				info_fields.append('info.modified as i_modified')
			if 'created' in info_fields:
				info_fields.remove('created')
				info_fields.append('info.created as i_created')
			_joins.append('inner join users_data.users_info info on acc.id = info.uid')
		if get_token:
			_joins.append(f'left join users_data."users_token_{request.info.platform}" u_token on acc.id = u_token.uid')
		
		_select_fields = []
		for item in main_fields + info_fields:
			if '.' in item:
				_select_fields.append(item)
			else:
				_select_fields.append(f'"{item}"')
		if get_token:
			_select_fields.append('u_token.token as "token"')
		
		_joins = '\n\t'.join(_joins)
		_q = f"""
		select {','.join(_select_fields)}
			from users_data.account_account acc
				{_joins}
			where acc.id = {uid}
		"""
		# Print(_q)
		
		data = request.db.server.custom(_q, None, to_commit=False, to_fetch=True)
		if data.empty:
			self.bad_user = True
			d_raise(
				request,
				djn_def.Messages.unexpected,
				f'uid Not Found ({uid})',
				do_raise=False
			)
			return self
		data = data.to_dict(orient='records')[0]
		self.uid = uid
		
		for _f in main_fields + info_fields:
			if ' as ' in _f:
				_f = _f.split(' as ')[1]
			setattr(self, _f, data[_f])
		if get_token:
			self.token = data['token']
		
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
		**kwargs: dict optional
			uid: int, default -> self.uid

		Response:
		-----
		Json Object with these keys and types:
			uid: int
			token: str
			status: str
			username: str
			email: str
			auth_email: bool

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
			| comment: (not raised)  uid Not Found
			| Message: UTILSD.Defaults.Messages.unexpected
			| Result: null
			| -------------------------------------------------------
		"""
		return {
			# region info
			'uid': self.uid,
			'token': self.token,
			'status': self.status,
			'username': self.username,
			'email': self.email,
			'auth_email': self.auth_email,
			# endregion
			# region version specification
			'curr_version': djn_def.app_current_version,
			'force_version': djn_def.app_force_version,
			# endregion
		}
	
	def authenticate_email(self, request, **kwargs):
		"""
		UpdatedAt: ---

		About:
		-----
		authenticate user's email

		Parameters:
		-----
		request: CustomRequest
		**kwargs: dict optional
			uid: int, default -> self.uid
			new_status: bool, default -> True
				what is user's email authentication new status

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
			| comment: (not raised)  uid Not Found
			| Message: UTILSD.Defaults.Messages.unexpected
			| Result: null
			| -------------------------------------------------------
		"""
		uid = kwargs.pop('uid', self.uid)
		if not uid:
			d_raise(
				request,
				djn_def.Messages.unexpected,
				f'no user specified',
				do_raise=False
			)
			return
		
		# self.info({'main': ['status'], 'info': ['auth_email']}, uid)
		if self.status != djn_def.Fields.status_map['suspended']:
			if kwargs.pop('new_status', True):
				if not self.auth_email:
					request.db.server.update(
						'users_info',
						pd.DataFrame(columns=['auth_email'], data=[[True]]),
						[('uid', '=', uid)],
						schema='users_data'
					)
					self.auth_email = True
				if self.status == djn_def.Fields.status_map['inactive']:
					request.db.server.update(
						'account_account',
						pd.DataFrame(columns=['status'], data=[[djn_def.Fields.status_map['active']]]),
						[('id', '=', uid)],
						schema='users_data'
					)
					self.status = djn_def.Fields.status_map['active']
			else:
				if self.auth_email:
					request.db.server.update(
						'users_info',
						pd.DataFrame(columns=['auth_email'], data=[[False]]),
						[('uid', '=', uid)],
						schema='users_data'
					)
					self.auth_email = False
				if self.status == djn_def.Fields.status_map['active']:
					request.db.server.update(
						'account_account',
						pd.DataFrame(columns=['status'], data=[[djn_def.Fields.status_map['inactive']]]),
						[('id', '=', uid)],
						schema='users_data'
					)
					self.status = djn_def.Fields.status_map['inactive']
					
		return self
	
	def signup(self, request, email: str, password: str, **kwargs):
		"""
		UpdatedAt: ---

		About:
		-----
		check email regex
		check password regex
		check email conflict
		after checking were successful sign user up and update `User` object in request

		Parameters:
		-----
		request: CustomRequest
		email: str
		password: str
		**kwargs: dict optional
			auto_login: bool, default: False
				log user in after successful signup

		Response:
		-----
		if user exists and is inactive:
			| status: 200
			| comment: ---
			| Message: UTILSD.Defaults.Messages.ok
			| Result: null
		else:
			self

		Django Errors:
		-----
		main:
			| status: 409
			| comment: user already exists
			| Message: UTILSD.Defaults.Messages.already_exists
			| Result: null
			| ----------------------------------------------------
		links:
			| UTILSD.main.check_regex
		possible attack:
			| ---
		unexpected:
			| ---
		"""
		check_regex(request, password, 'password')
		check_regex(request, email, 'email')
		auto_login = kwargs.pop('auto_login', False)
		
		request.db.server.schema = 'users_data'
		_data = request.db.server.read(
			'account_account',
			['id', 'status'],
			[('email', '=', email)]
		).values.tolist()
		
		if _data:
			self.uid, _status = _data[0]
			if _status == djn_def.Fields.status_map['inactive']:
				if auto_login:
					Token(request).regenerate()
				
				request.db.server.update(
					'account_account',
					pd.DataFrame([[make_password(password)]], columns=['password']),
					[('id', '=', self.uid)],
					schema='users_data'
				)
				request.input_body['password'] = '****'
				
				self.info(request, {'template': 'info'})
				return d_response(
					request,
					djn_def.Messages.ok,
					result=self.get_user_info(request),
					code=200
				)
			d_raise(
				request,
				djn_def.Messages.already_exists,
				f'{email} uid -> {self.uid}',
				code=409
			)
		try:
			acc = get_user_model()(email=email, username=gen_random_username(request.db.server))
			acc.set_password(password)
			request.input_body['password'] = '****'
			acc.save()
			self.uid = acc.id
		except Exception as e:
			d_raise(
				request,
				djn_def.Messages.already_exists,
				e,
				exc_comment=f'{email} uid -> {self.uid} {djn_def.Messages.unexpected}',
				code=409
			)
			return  # just for ide warnings
		
		request.db.server.insert('users_info', pd.DataFrame(columns=['uid'], data=[[acc.id]]))
		
		if auto_login:
			Token(request).create()
		self.info(request, {'template': 'info'})
		
		return self
	
	def login(self, request, username: str, password: str, **kwargs):
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
		**kwargs: dict optional
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
		treat_as = kwargs.pop('treat_as', None)
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
			).values.tolist()
		
		if not user and (not treat_as or treat_as == 'email') and check_regex(
				request, username, 'email',
				do_raise=False
		):
			user = request.db.server.read(
				'account_account',
				['id', 'password', 'status'],
				[('email', '=', username)]
			).values.tolist()
		
		if not user:
			d_raise(
				request,
				djn_def.Messages.account_not_found,
				f'login attempt `{username}` `{password}`',
				code=404
			)
			return  # just for ide warnings
		uid, ok_password, status = user[0]
		
		if not check_password(password, ok_password):
			d_raise(
				request,
				djn_def.Messages.account_not_found,
				f'login attempt `{username}` `{password}` (bad password)',
				code=404
			)
		request.input_body['password'] = '****'
		
		request.User.status = status
		if request.User.status != djn_def.Fields.status_map['active']:
			if request.User.status == djn_def.Fields.status_map['inactive']:
				d_raise(
					request,
					djn_def.Messages.inactive_user,
					f'user is {request.User.status}',
					code=403,
				)
			else:
				d_raise(
					request,
					djn_def.Messages.suspended_user,
					f'user is {request.User.status}',
					code=403,
				)
		
		self.uid = uid
		Token(request).regenerate()
		request.db.server.update(
			'account_account',
			pd.DataFrame(columns=['last_login'], data=[["timezone('utc', now())"]]),
			[('id', '=', uid)]
		)
		self.info(request, {'template': 'info'})
		
		return self
	
	def upgrade(self, request):
		pass
	
	def downgrade(self, request):
		pass


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
		"""
		`platform` can be: app, web
		"""
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
	
	def regenerate(self) -> str:
		"""(insert or update) and read token"""
		uid = self._check_user()
		if self._is_admin(uid):
			return self.get_or_create()['token']
		
		return self.request.db.server.upsert(
			f'users_token_{self.request.info.platform}',
			pd.DataFrame(
				columns=['uid', 'token'],
				data=[[uid, self._generate()]]
			).set_index('uid'),
			ts_columns='created',
			returning=['token'],
			schema='users_data'
		).token.values[0]
	
	def delete(self):
		uid = self._check_user()
		if self._is_admin(uid):
			return self.get_or_create()
		
		self.request.db.server.delete(
			f'users_token_{self.request.info.platform}',
			[('uid', '=', uid)],
			schema='users_data'
		)
	
	def is_expired(self) -> ty.Optional[bool]:
		uid = self._check_user()
		_q = f"""
		select extract(epoch from '{self.request.start}' - created) > {self.request.info.token_expiration_in_seconds} x
		from users_data."users_token_{self.request.info.platform}"
		where uid = {uid}
		"""
		res = self.request.db.server.custom(_q, None, to_commit=False, to_fetch=True)
		if res.empty:
			return
		return res.values[0][0]
	
	def get_or_create(self) -> dict:
		""" insert, read """
		uid = self._check_user()
		
		_q = f"""
		with sel as (
			select token, created, uid
			from users_data."users_token_{self.request.info.platform}"
			where uid = {uid}
		), ins as (
			insert into users_data."users_token_{self.request.info.platform}" (token, created, uid)
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
	
	def get(self, **kwargs) -> dict:
		res = self.request.db.server.read(
			f'users_token_{self.request.info.platform}',
			['token', 'created', 'uid'],
			[(k, '=', v) for k, v in kwargs.items()],
			schema='users_data'
		).to_dict('records')
		if not res:
			raise self.DoesNotExist
		
		return res[0]
	
	def create(self) -> dict:
		return self.get_or_create()


class MainMiddleware:
	# todo handle Broken Pipe
	
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
			ip = request.META.get('HTTP_X_FORWARDED_FOR', None)
			if not ip:
				ip = request.META.get('HTTP_X_REAL_IP', None)
				if not ip:
					ip = request.META.get('REMOTE_ADDR', None)
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
					res = wsgi_convertor(request).data['request']
				else:
					res = api_view([request.method])(lambda x: Response({'request': x}))(request).data['request']
				
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
				
				res = m_raise(
					request,
					djn_def.Messages.method_not_allowed,
					e,
					exc_comment=f'unexpected error while converting WSGI to DRF {djn_def.Messages.possible_attack}',
					code=405
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
			
			lang = request.headers.get('HTTP_ACCEPT_LANGUAGE', 'fa')
			if lang != 'fa' and lang != 'en':
				lang = 'fa'
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
			
			if request.method not in request.info.methods:
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
				| Result: null ** just_message **
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
			if re.match('postman|curl|nmap', ua):
				return m_raise(
					request,
					djn_def.Messages.bad_input,
					f'request from banned user agent `{ua}` {djn_def.Messages.possible_attack}',
					response_just_message=True
				)
			
			# ban bad host
			host = request.headers.get('HTTP_HOST', None)
			if host is None or host.split(':')[0] not in djn_def.allowed_hosts:
				return m_raise(
					request,
					djn_def.Messages.bad_input,
					f'bad host `{host}` {djn_def.Messages.possible_attack}',
					response_just_message=True
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
				
				__input = request.input_body.get('input', None)
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
				
				headers = input_data.get('HEADERS', None)
				contents = input_data.get('CONTENTS', None)
				
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
				
				timestamp = request.headers.get('HTTP_TIMESTAMP', None)
				if timestamp is None:
					return m_raise(
						request,
						djn_def.Messages.bad_input,
						comment=f'`TIMESTAMP` header not provided {djn_def.Messages.possible_attack} %100 {djn_def.Messages.encryption_at_risk}'
					)
				timestamp = Time.ts2dt(timestamp, 'gmt', remove_tz=True)
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
				app_version = request.headers.get('HTTP_APP_VERSION', None)
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
						result={'link': 'UPDATE_LINK'},
						code=426
					)
				
				to_update = {
					'token': request.headers.get('HTTP_AUTHENTICATION', None),
					'HTTP_APP_VERSION': app_version
				}
				request.headers.update(to_update)
				request.META.update(to_update)
			elif request.info.platform == djn_def.Platforms.test:
				request.headers.update({'token': request.headers.get('HTTP_AUTHENTICATION', None)})
				
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
				token = request.headers.get('token', None)
				
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
		def apply_output_model(request: ty.Union[CustomRequest, WSGIRequest], result: HttpResponse) -> HttpResponse:
			""" get output data ready for client """
			if hasattr(request.User, 'to_downgrade'):
				request.User.downgrade(request)
			
			if request.info.response_html:
				return result
			
			# noinspection PyUnresolvedReferences
			if hasattr(result, 'data'):
				data = result.data
				if request.info.output_model == djn_def.Models.app:
					result.content = f'"{Encryptions.V1().encrypt(Json.encode(data))}"'
				elif request.info.output_model == djn_def.Models.test:
					result.content = Json.encode(data)
				del result.data
			
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
			| RUN API VIEW
			| apply output model
			| close database connection

		Django Errors:
		-----
		main:
			| ---
		links:
			| UTILSD.main.MainMiddleware.utils.handle_resolver_match
			| UTILSD.main.MainMiddleware.utils.convert_request_wsgi_to_drf
			| UTILSD.main.MainMiddleware.utils.fill_request_params
			| UTILSD.main.MainMiddleware.utils.handler404
			| UTILSD.main.MainMiddleware.utils.ban_bad_requests
			| UTILSD.main.MainMiddleware.utils.check_input_model
			| UTILSD.main.MainMiddleware.utils.check_platform_required_data
			| UTILSD.main.MainMiddleware.utils.check_user_if_required
			| UTILSD.main.MainMiddleware.utils.check_active_user_if_detected
			| UTILSD.main.MainMiddleware.utils.check_api_input_data
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
		
		# handle resolvers
		request = self.utils.handle_resolver_match(request)
		
		# convert request from WSGI to DRF
		res = self.utils.convert_request_wsgi_to_drf(request)
		if isinstance(res, HttpResponse):
			return self.utils.apply_output_model(request, res)
		request = res
		
		# assign empty token to request headers
		request.headers.update({'token': None})
		
		# open a database connection for request
		request.db = CustomDb()
		request.db.open()
		
		# assign empty user to request
		request.User = CustomUser()
		
		# fill request input body and params
		request = self.utils.fill_request_params(request)
		
		# ban bad requests
		res = self.utils.ban_bad_requests(request)
		if isinstance(res, HttpResponse):
			request.db.close()
			return self.utils.apply_output_model(request, res)
		request = res
		
		# handle CORS
		res = self.utils.handle_cors(request)
		if isinstance(res, HttpResponse):
			request.db.close()
			return self.utils.apply_output_model(request, res)
		request = res
		
		# check input model
		res = self.utils.check_input_model(request)
		if isinstance(res, HttpResponse):
			request.db.close()
			return self.utils.apply_output_model(request, res)
		request = res
		
		# handle 404
		res = handler404(request, from_middleware=True)
		if isinstance(res, HttpResponse):
			request.db.close()
			return self.utils.apply_output_model(request, res)
		request = res
		
		# check request method
		res = self.utils.check_request_method(request)
		if isinstance(res, HttpResponse):
			request.db.close()
			return self.utils.apply_output_model(request, res)
		request = res
		
		# check platform required data
		res = self.utils.check_platform_required_data(request)
		if isinstance(res, HttpResponse):
			request.db.close()
			return self.utils.apply_output_model(request, res)
		request = res
		
		# check user if required
		res = self.utils.check_user_if_required(request)
		if isinstance(res, HttpResponse):
			request.db.close()
			return self.utils.apply_output_model(request, res)
		request = res
		
		# check active user if detected
		res = self.utils.check_active_user_if_detected(request)
		if isinstance(res, HttpResponse):
			request.db.close()
			return self.utils.apply_output_model(request, res)
		request = res
		
		# check api input data
		res = self.utils.check_api_input_data(request)
		if isinstance(res, HttpResponse):
			request.db.close()
			return self.utils.apply_output_model(request, res)
		request = res
		
		# RUN VIEW
		res = self.get_response(request)
		
		# response will reach this code no matter what (even if error occurs) [except for middleware errors]
		
		# apply output mode
		res = self.utils.apply_output_model(request, res)
		
		# close request database connection
		request.db.close()
		return res
	
	@staticmethod
	def process_exception(request, exc):
		if not isinstance(exc, CustomException):
			exc = d_raise(
				request,
				djn_def.Messages.unexpected,
				exc,
				exc_comment='[UNHANDLED]',
				do_raise=False,
			)
		
		if exc.template:
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
			'Server': 'Apache/2.4.1 (Unix)',
			'X-Frame-Options': 'SAMEORIGIN',
			'Referrer-Policy': 'strict-origin-when-cross-origin',
			'Vary': 'Origin',
			'Via': 'James',
		})
		if not hasattr(res, 'template_name') and not res.headers['Content-Type'].startswith('image'):
			res.headers['Content-Type'] = 'application/json'
		if hasattr(res, 'response_additional_headers'):
			res.headers.update(res.response_additional_headers)
		
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
			)
		
		if List.has_duplicates(data):
			return self._raise(
				djn_def.Messages.bad_input,
				f'`{tag}` contains duplicate values '
				f'{djn_def.Messages.possible_attack if possible_attack else ""}',
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
			)
		for item in required_keys:
			if item not in data:
				return self._raise(
					djn_def.Messages.bad_input,
					f'`{tag}` `{item}` which is required is not present in input '
					f'{djn_def.Messages.possible_attack if possible_attack else ""}',
				)
		if block_additional_keys:
			additional_keys = set(data.keys()) - set(required_keys + optional_keys)
			if additional_keys:
				return self._raise(
					djn_def.Messages.bad_input,
					f'`{tag}` contains additional key(s) which is blocked `{list(additional_keys)}`'
					f'{djn_def.Messages.possible_attack if possible_attack else ""}',
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
			)
		for item, types in required_keys.items():
			if item not in data:
				return self._raise(
					djn_def.Messages.bad_input,
					f'`{tag}` `{item}` which is required is not present in input '
					f'{djn_def.Messages.possible_attack if possible_attack else ""}',
				)
			if types and type(data[item]) not in types:
				return self._raise(
					djn_def.Messages.bad_input,
					f'`{tag}` `{item}` `{type(data[item])}` must be in {types} '
					f'{djn_def.Messages.possible_attack if possible_attack else ""}',
				)
			if 'checkTruthiness' in types and not data[item]:
				return self._raise(
					djn_def.Messages.bad_input,
					f'`{tag}` `{item}` checkTruthiness failed '
					f'{djn_def.Messages.possible_attack if possible_attack else ""}',
				)
		for item, types in optional_keys.items():
			if types and item in data:
				if type(data[item]) not in types:
					return self._raise(
						djn_def.Messages.bad_input,
						f'`{tag}` `{item}` `{type(data[item])})` must be in {types} '
						f'{djn_def.Messages.possible_attack if possible_attack else ""}',
					)
			
			if 'checkTruthiness' in types and item in data and not data[item]:
				return self._raise(
					djn_def.Messages.bad_input,
					f'`{tag}` `{item}` checkTruthiness failed '
					f'{djn_def.Messages.possible_attack if possible_attack else ""}',
				)
		
		if block_additional_keys:
			additional_keys = set(data.keys()) - set(list(required_keys.keys()) + list(optional_keys.keys()))
			if additional_keys:
				return self._raise(
					djn_def.Messages.bad_input,
					f'`{tag}` contains additional key(s) which is blocked `{list(additional_keys)}`'
					f'{djn_def.Messages.possible_attack if possible_attack else ""}',
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
	
	if template:
		if not request.info.response_html:
			Log.log(f'`{request.info.name}` cant render output when `info.response_html` is false (assuming true)')
			request.info.response_html = True
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
	if kwargs.pop('do_raise', True):
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
				template = djn_def.templates['main']['success']
			else:
				template = djn_def.templates['main']['error']
				data = {}
		
		with open(f'{prj_def.project_root}/templates/{template}', 'r', encoding='utf-8') as f:
			res = SimpleTemplateResponse('main.html', {'myhtml': f.read().format(**data)}, status=code)
			res.render()
	else:
		res = HttpResponse('', status=code)
		res.data = data
	
	res.response_additional_headers = request.info.response_additional_headers
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
		'Static_symbols': {
			'type': 'code',
			400: {
				'type': 'message',
				djn_def.Messages.maximum_symbols: {
					'type': 'lang',
					'fa': {
						'type': 'platform',
						'Web': 'PERSIAN'
					},
					'en': 'English Error',
				}
			}
		}
	}
	-------------------------------
	{
		'Static_symbols': 'XX'
	}
	"""
	
	def main(desc):
		if not isinstance(desc, dict):
			return desc
		
		if desc['type'] == 'code':
			return main(desc.get(code, None))
		elif desc['type'] == 'message':
			return main(desc.get(message, None))
		elif desc['type'] == 'lang':
			return main(desc.get(request.lang, None))
		elif desc['type'] == 'platform':
			return main(desc.get(request.info.platform, None))
	
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
		description = djn_def.descriptions_api_based.get(request.info.name, None)
	
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
			djn_def.descriptions_message_based.get(message, None),
			request,
			code,
			message
		)
	
	# region fill custom descriptions
	if request.info.name == 'User_update' and code == 406:
		description = description.format(
			djn_def.descriptions_user_info_field_translator.get(result.get('field', None), {}).get(request.lang, '')
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
			djn_def.Messages.bad_input,
			f'{djn_def.Messages.regex_error} `{field_name}` `{to_check}` {djn_def.Fields.regex_map[field_name]["err"]}',
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
