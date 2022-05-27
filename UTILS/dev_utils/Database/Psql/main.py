import warnings

warnings.simplefilter(action='ignore', category=UserWarning)

import configparser
import os
import typing as ty
from pathlib import Path

import jdatetime
import numpy as np
import pandas as pd
import psycopg2 as psql_engine
# noinspection PyProtectedMember
from pandas.api.types import is_datetime64_any_dtype as is_datetime

from UTILS import dev_utils
from UTILS.dev_utils import Defaults as dev_def
from UTILS.dev_utils import Log
from UTILS.dev_utils.Objects import String, Time, Dict, Json, List
import time as ti

__root = str(dev_def.project_root)
__root = __root[:__root.find('Project/')] + 'Files/'
__reader = configparser.ConfigParser()
__reader.read(__root + 'db.conf')
# noinspection PyProtectedMember
Databases = __reader._sections
Databases.update({'default': list(Databases.values())[0]})
__reader = configparser.ConfigParser()
__reader.read(__root + 'dbUsers.conf')
# noinspection PyProtectedMember
DatabseUsers = __reader._sections
DatabseUsers.update({'default': list(DatabseUsers.values())[0]})


class Psql:
	# noinspection PyShadowingBuiltins
	def __init__(self, schema, open=False, db_name='default'):
		self.db_name = db_name
		self.db_properties = Databases[db_name]
		self.schema = schema
		self.conn = None
		self.cur = None
		if open:
			self.open()
	
	@staticmethod
	def test():
		db = Psql('public')
		db.open()
		
		print('creating ...')
		db.create(
			'test',
			{
				'id': 'serial primary key',
				'str_tst': 'varchar(100)',
				'null_tst': 'varchar(100)',
				'int_tst': 'integer',
				'float_tst': 'decimal(10, 5)',
				'json_tst': 'json',
				'arr_tst': 'text[]',
			},
			ts_columns='created',
		)
		
		print('inserting returning')
		res = db.insert(
			'test',
			pd.DataFrame({
				'str_tst': ['x', 'd'],
				'int_tst': [1, 2],
				'float_tst': [1.2, 2.0],
				'null_tst': [None, np.nan],
				'json_tst': [{'a': 'b', 'x': 'd'}, {'a': 'b', 'x': 'd'}],
				'arr_tst': [
					[1, 2, 3],
					[4, 5, 6]
				],
				'created': [
					Time.dtnow(),
					Time.dtnow(),
				]
			}),
			returning=['str_tst', 'int_tst', 'arr_tst', 'json_tst', 'created'],
		)
		print(res)
		
		print('read')
		res = db.read(
			'test',
			'*',
			order_by=['id', 'DESC'],
		)
		print(res)
		
		print('updating')
		db.update(
			'test',
			pd.DataFrame({
				'str_tst': ['d'],
				'int_tst': [1000],
				'float_tst': [1000],
				'null_tst': [None],
				'json_tst': [{'a': 'b', 'x': 'f'}],
			}),
			[
				('str_tst', '=', 'd')
			],
			ts_columns='created',
		)
		
		print('read')
		res = db.read(
			'test',
			'*',
			order_by=['id', 'DESC'],
		)
		print(res)
		
		print('multiple updates')
		db.multiple_update(
			'test',
			pd.DataFrame({
				'str_tst': ['d', 'h', 'f', 'r'],
				'int_tst': [1000, 1000, 1000, 1000],
				'float_tst': [1000, 1000, 1000, 1000],
			}).set_index(['str_tst']),
		)
		
		print('read')
		res = db.read(
			'test',
			'*',
			order_by=['id', 'DESC'],
		)
		print(res)
		
		print('exists')
		print(db.exists('test', [('str_tst', '=', 'x')]))
		
		print('delete')
		db.delete('test', [('str_tst', '=', 'x')])
		
		print('exists')
		print(db.exists('test', [('str_tst', '=', 'x')]))
		
		print('table exists')
		print(db.table_exists('test'))
		
		print('drop')
		db.drop('test')
		
		print('table exists')
		print(db.table_exists('test'))
		
		db.close()
		
		pass
	
	@staticmethod
	def backup(destination=None):
		if destination is None:
			destination = Path('/root/dbBackup/psql')
		os.makedirs(destination, exist_ok=True)
		
		dirs = sorted(os.listdir(destination), reverse=True)
		while len(dirs) > 5:
			os.system(f'rm -R {destination}/{dirs[-1]}')
			dirs = sorted(os.listdir(destination), reverse=True)
		
		t_now = jdatetime.datetime.now().strftime('%Y_%m_%d-%H_%M_%S')
		destination += f'/{t_now}'
		os.makedirs(destination, exist_ok=True)
		
		command = f'pg_dump --dbname=postgresql://%s:%s@%s:%s/%s ' % (
			Databases['polygonStorage']['user'],
			Databases['polygonStorage']['pass'],
			Databases['polygonStorage']['host'],
			Databases['polygonStorage']['port'],
			Databases['polygonStorage']['name'],
			destination,
		)
		os.system(command)
	
	@staticmethod
	def restore(destination=None):
		if destination is None:
			destination = Path('/root/dbBackup/psql')
		destination = str(destination / sorted(os.listdir(destination), reverse=True)[0])
		
		command = f'psql --dbname=postgresql://%s:%s@%s:%s/%s -f %s/polygonStorage.sql' % (
			Databases['polygonStorage']['user'],
			Databases['polygonStorage']['pass'],
			Databases['polygonStorage']['host'],
			Databases['polygonStorage']['port'],
			Databases['polygonStorage']['name'],
			destination,
		)
		os.system(command)
	
	def handle_kwargs(self, kwargs) -> dict:
		return {
			'schema': self._handle_schema_name(kwargs.get('schema', self.schema)),
			'auto_connection': kwargs.get('auto_connection', False),
			'print_query': kwargs.get('print_query', False),
			'get_query': kwargs.get('get_query', False),
			'dt2ts': kwargs.get('dt2ts', False),
			'timezone': kwargs.get('timezone'),  # by-default all tz-aware datetimes are converted to tz-naive
			'limit_offset': kwargs.get('limit_offset'),
			'order_by': kwargs.get('order_by'),
			'ignore_conflict': kwargs.get('ignore_conflict', False),
			'returning': kwargs.get('returning'),
			'if_exists': kwargs.get('if_exists', True),
			'ts_columns': kwargs.get('ts_columns'),
			'custom_types': kwargs.get('custom_types', {}),
			'custom_read_types': kwargs.get('custom_read_types', None),
			'group_unique': kwargs.get('group_unique', []),
			'null_type_casting': kwargs.get('null_type_casting'),
			'group_by': kwargs.get('group_by'),
		}
	
	def get_query(self, query, params, do_print=False) -> ty.Optional[str]:
		if self.cur:
			query = self.cur.mogrify(query, params).decode()
			if do_print:
				print(query)
			return query
	
	def get_cols_from_cur(self) -> tuple:
		return tuple(map(lambda x: x[0], self.cur.description))
	
	def read_from_cursor(self, dt2ts: bool, timezone: str = None, custom_types: dict = None) -> pd.DataFrame:
		timezone = 'Asia/Tehran' if timezone == 'local' else timezone
		res = pd.DataFrame(self.cur.fetchall(), columns=self.get_cols_from_cur())
		res.custom_dtypes = {}
		for col in res.columns:
			if is_datetime(res[col]):
				res[col] = Time.series_tz_convert(res[col], timezone)
				if dt2ts:
					res[col] = Time.series_ts_from_dt(res[col])
			if custom_types is not None and col in custom_types:
				res.custom_dtypes.update({col: custom_types[col]})
				if custom_types[col] == 'int':
					res[col] = res[col].astype('Int64').replace({np.nan: None})
				elif custom_types[col] == 'float' or custom_types[col] == 'timestamp':
					res[col] = res[col].astype('float64').replace({np.nan: None})
		
		return res
	
	def _check_connection(self, auto_connection: bool) -> bool:
		"""
		check connection with database
		if this function returns False no further queries should be sent
		"""
		res = True
		if auto_connection:
			res = self.open()
		elif self.conn is None:
			Log.log(f'[{self.db_name}] No DB Connection', location_depth=3, class_name=self.__class__.__name__)
			res = False
		
		if not res:
			self.close()
		
		return res
	
	@staticmethod
	def optimize_row(row: list, custom_types: list) -> dict:
		"""
		get a list of items in row and make it ready for query and handle SQLI
		most used in :
			insert
		"""
		optimized_row = []
		parameters = []
		for i, item in enumerate(row):
			if custom_types[i] == 'auto':
				if dev_utils.is_null(item):
					optimized_row.append('NULL')
				elif dev_utils.is_dict(item):
					optimized_row.append('%s::json')
					parameters.append(Json.encode(item, None_as_null=False))
				elif dev_utils.is_itterable(item):
					# be sure for item to be list
					optimized_row.append('%s')
					parameters.append(list(item))
				else:
					if item == "timezone('utc', now())":
						optimized_row.append(item)
					else:
						optimized_row.append('%s')
						parameters.append(item)
			else:
				if custom_types[i] == 'json':
					optimized_row.append('%s::json')
					parameters.append(Json.encode(item, None_as_null=False))
		
		return {
			'row': optimized_row,
			'params': parameters
		}
	
	def _handle_columns(self, cols: ty.Union[list], **kwargs) -> ty.Optional[ty.Union[str, list]]:
		"""
		supported models are: (3 models)
			*
			['a', 'b', 'c'],
			[['a', 'aa'], ['b', 'bb'], ['c', 'cc']]
		"""
		if not cols:
			return
		if cols == '*':
			return '*'
		elif dev_utils.is_itterable(cols):
			# make a copy
			cols = [*cols]
			
			for i, item in enumerate(cols):
				if dev_utils.is_itterable(item):
					i1, i2 = item
					if not ('.' in i1 or '->' in i1 or ':' in i1 or ' ' in i1 or '(' in i1):
						i1 = f'"{item}"'
					cols[i] = f'{i1} as {i2}'
				elif not ('.' in item or '->' in item or ':' in item or ' ' in item or '(' in item):
					cols[i] = f'"{item}"'
			
			if kwargs.pop('do_join', True):
				cols = ','.join(cols)
			
			return cols
		
		Log.log(f'[{self.db_name}] bad columns {cols}', location_depth=3, class_name='myDb')
	
	@staticmethod
	def _handle_table_name(table_name: str) -> str:
		"""if table_name has upper case characters and doesn't start with " add double quote to beginning and end """
		if String.has_upper(table_name) and not table_name.startswith('"'):
			return f'"{table_name}"'
		else:
			return table_name
	
	@staticmethod
	def _handle_schema_name(schema_name: str) -> str:
		"""if schema_name has upper case characters and doesn't start with " add double quote to beginning and end """
		if String.has_upper(schema_name) and not schema_name.startswith('"'):
			return f'"{schema_name}"'
		else:
			return schema_name
	
	def _handle_conditions(self, cond: ty.List[tuple]) -> ty.Optional[dict]:
		"""
		supported models are: (1 model)
			[
				('mobile_number', '=', "+989196864660"),
				('mobile_number', 'in', ["+989196864660"]),
			]
		"""
		if not cond:
			return
		if dev_utils.is_itterable(cond):
			main = []
			params = []
			
			for item in cond:
				if dev_utils.is_itterable(item) and len(item) == 3:
					name, operator, value = item
					if not ('.' in name or '->' in name or ':' in name or ' ' in name):
						name = f'"{name}"'
					main.append(f'{name} {operator} %s')  # SQLI
					if operator == 'in' and dev_utils.is_itterable(value) and type(value) is not tuple:
						value = tuple(value)
					params.append(value)
				else:
					Log.log(
						f'[{self.db_name}] bad item in conditions {item}', location_depth=3, class_name='myDb'
					)
			
			return {
				'main': ' AND '.join(main),
				'params': params
			}
		
		Log.log(f'[{self.db_name}] bad conditions {cond}', location_depth=3, class_name='myDb')
		return
	
	def _handle_joins(self, joins: ty.List[tuple]) -> ty.Optional[str]:
		"""
		** `main_table` is the alias for first table
		supported models are: (1 model)
			[
				('inner', 'users_data.users_info', 'info', 'main_table.id', '=', 'info.uid'),
				('inner', 'users_data.users_token', 'token', 'main_table.id', '=', 'token.uid')
			]
		"""
		if not joins:
			return
		
		if dev_utils.is_itterable(joins):
			output = []
			for item in joins:
				if dev_utils.is_itterable(item) and len(item) == 6:
					mode, table, table_as, on_key, on_operator, on_val, = item
					output.append(f'{mode} join {table} {table_as} on {on_key} {on_operator} {on_val}')
				else:
					Log.log(f'[{self.db_name}] bad item in joins {item}', location_depth=3, class_name='myDb')
			return '\n\t'.join(output)
		
		Log.log(f'[{self.db_name}] bad joins {joins}', location_depth=3, class_name='myDb')
	
	def _handle_limit_offset(self, lo: tuple) -> ty.Optional[str]:
		"""
		supported models are:  (1 model)
			(limit, offset)
		"""
		if not lo:
			return
		
		if not dev_utils.is_itterable(lo) or len(lo) != 2:
			Log.log(f'[{self.db_name}] bad limit offset {lo}', location_depth=3, class_name='myDb')
			return
		
		return f'limit {lo[0]} offset {lo[1]}'
	
	def _handle_order_by(self, ob: ty.Union[tuple, str]) -> ty.Optional[str]:
		"""
		supported models are:  (2 model):
			'id'
			('id', 'desc')
		"""
		if not ob:
			return
		
		if dev_utils.is_itterable(ob):
			if len(ob) != 2:
				Log.log(f'[{self.db_name}] bad order by {ob}', location_depth=3, class_name='myDb')
				return
			else:
				return f'order by {ob[0]} {ob[1]}'
		elif isinstance(ob, str):
			return f'order by {ob}'
		else:
			Log.log(f'[{self.db_name}] bad order by type {ob}', location_depth=3, class_name='myDb')
	
	def _handle_group_by(self, gb: ty.Tuple[str]) -> ty.Optional[str]:
		"""
			('uid', 'order_id')
		"""
		if not gb:
			return
		
		return f"group by {self._handle_columns(gb)}"
	
	@staticmethod
	def _handle_ts_columns(ts_columns: ty.Union[str, ty.List[str]], **kwargs) -> ty.Optional[dict]:
		ts_columns = ts_columns if dev_utils.is_itterable(ts_columns) else [ts_columns]
		if not ts_columns:
			return
		
		to_create = kwargs.pop('to_create', False)
		if to_create:
			# is called from create method
			return {f'{c}': "timestamp default timezone('utc', now())" for c in ts_columns}
		else:
			# is called from update method
			return {f'"{c}"': "timezone('utc', now())" for c in ts_columns}
	
	@staticmethod
	def _handle_custom_types(custom_types: dict, columns) -> list:
		output = []
		for i, item in enumerate(columns):
			if item in custom_types:
				output.append(custom_types[item])
			else:
				output.append('auto')
		return output
	
	def open(self, wait_for_connection=True, do_log=True) -> bool:
		"""
		open connection if connection is not already open
		
		if `to many clients` error occur:
			if wait_for_connection is True:
				retry 3 times with 1 second sleep between them
				and if the error was not resolved after errors : log the error
			else:
				log the error
		return
			True  -> everything went OK
			False -> something  went WRONG (log saved)
		"""
		try:
			if self.conn is None:
				self.conn = psql_engine.connect(
					host=self.db_properties['host'],
					port=self.db_properties['port'],
					password=self.db_properties['pass'],
					user=self.db_properties['user'],
					database=self.db_properties['name'],
				)
				self.cur = self.conn.cursor()
			return True
		except psql_engine.OperationalError as e:
			if wait_for_connection and 'FATAL:  sorry, too many clients already' in str(e):
				for i in range(3):
					Log.log(
						f'[{self.db_name}] cant connect to db because too many requests, retrying...',
						no_log_on_local=True
					)
					ti.sleep(1)
					__open = self.open(wait_for_connection=False, do_log=False)
					if __open:
						return True
					if __open is False:
						return False
			if do_log:
				Log.log(f'[{self.db_name}]', exc=e, class_name=self.__class__.__name__)
			return None
		except Exception as e:
			Log.log(f'[{self.db_name}]', exc=e, class_name=self.__class__.__name__)
			return False
	
	def close(self):
		"""
		close connection if it is open.
		"""
		if self.conn is not None:
			self.cur.close()
			self.conn.close()
			self.conn = None
			self.cur = None
	
	def reopen(self):
		"""
		close and open connection if it is open.
		"""
		if self.conn is not None:
			self.close()
			self.open()
	
	def create_user_with_default_user(self):
		os.system(
			f""" psql "host={self.db_properties['host']} port={self.db_properties['port']} user='{DatabseUsers['default']['user']}' password='{DatabseUsers['default']['pass']}' dbname=template1" -c "create user {self.db_properties['user']} superuser createdb createrole replication bypassrls encrypted password '{self.db_properties['pass']}'" """)
	
	def create_db(self):
		os.system(
			f""" psql "host={self.db_properties['host']} port={self.db_properties['port']} user='{self.db_properties['user']}' password='{self.db_properties['pass']}' dbname=template1" -c 'create database "{self.db_properties['name']}" with owner "{self.db_properties['user']}"' """)
	
	def create(self, table: str, columns: ty.Dict[str, str], **kwargs) -> bool:
		"""
		create table if not exist

		Example:
			db.create(
				'test',
				{
					'id': 'serial primary key',
					'created': "timestamp default timezone('utc'::text, now())",
				}
			)

		"""
		schema, auto_connection, print_query, get_query, ie, ts_columns, group_unique = Dict.multiselect(
			self.handle_kwargs(kwargs),
			['schema', 'auto_connection', 'print_query', 'get_query', 'if_exists', 'ts_columns', 'group_unique']
		).values()
		
		if not self._check_connection(auto_connection):
			return False
		
		table = self._handle_table_name(table)
		
		if ts_columns:
			columns.update(self._handle_ts_columns(ts_columns, to_create=True))
		
		cols = []
		for k, v in columns.items():
			cols.append(f'"{k}" {v}')
		cols = ','.join(cols)
		
		_q = f'create table if not exists {schema}.{table} ({cols}'
		if group_unique:
			_q += ', unique ("' + '","'.join(group_unique) + '")'
		_q += ')'
		_p = None
		
		try:
			if print_query:
				self.get_query(_q, _p, True)
			if get_query:
				# noinspection PyTypeChecker
				return self.get_query(_q, _p, False)
			self.cur.execute(_q, _p)
			self.conn.commit()
			result = True
		except Exception as e:
			Log.log(f'[{self.db_name}]', location_depth=3, class_name='myDb', exc=e, query=self.get_query(_q, _p))
			result = False
			self.reopen()
		
		if auto_connection:
			self.close()
		
		return result
	
	def insert(self, table: str, data: pd.DataFrame, **kwargs) -> pd.DataFrame:
		"""
		insert `data` to `table`

		if timezone is specified and there are tz-aware objects in input or output(if returning is specified)
			of function their time zone will be converted to selected time zone
		if returning is specified the function will inserted `data` and return with selected columns

		Example:
			res = db.insert(
			'test',
			df,
			# returning=['str_tst', 'int_tst', 'arr_tst', 'json_tst', 'created'],
			# dt2ts=True
			# timezone='local',
			# timezone='gmt',
		)
		"""
		schema, auto_connection, print_query, get_query, ct, ic, returning, dt2ts, tz, crt = Dict.multiselect(
			self.handle_kwargs(kwargs),
			[
				'schema', 'auto_connection', 'print_query', 'get_query', 'custom_types',
				'ignore_conflict', 'returning', 'dt2ts', 'timezone', 'custom_read_types'
			]
		).values()
		
		if not self._check_connection(auto_connection):
			return pd.DataFrame()
		
		table = self._handle_table_name(table)
		
		for col in data.columns:
			if is_datetime(data[col]):
				data[col] = Time.series_tz_convert(data[col], tz)
		
		returning = self._handle_columns(returning)
		columns = self._handle_columns(list(data.columns.values))
		ct = self._handle_custom_types(ct, data.columns)
		
		insert_values = []
		_p = []
		for row in tuple(data.itertuples(index=False, name=None)):
			o_row = self.optimize_row(row, ct)
			insert_values.append('(' + ', '.join(o_row["row"]) + ')')
			_p += o_row['params']
		insert_values = ',\n\t'.join(insert_values)
		
		_q = f"""insert into {schema}.{table}({columns}) \nvalues\n\t{insert_values}"""
		
		# add ignore conflict
		if ic:
			_q += 'on conflict do nothing'
		
		# add returning
		if returning:
			_q += f"\nreturning {returning}"
		
		res = pd.DataFrame()
		try:
			if print_query:
				self.get_query(_q, _p, True)
			if get_query:
				# noinspection PyTypeChecker
				return self.get_query(_q, _p, False)
			self.cur.execute(_q, _p)
			self.conn.commit()
			if returning:
				res = self.read_from_cursor(dt2ts, tz, crt)
		except Exception as e:
			Log.log(f'[{self.db_name}]', location_depth=3, class_name='myDb', exc=e, query=self.get_query(_q, _p))
			self.reopen()
		
		if auto_connection:
			self.close()
		
		return res
	
	def read(
			self,
			table: str,
			columns: ty.Union[str, list],
			conditions: ty.List[tuple] = None,
			joins: ty.List[tuple] = None,
			**kwargs
	) -> pd.DataFrame:
		schema, auto_connection, print_query, get_query, dt2ts, tz, lo, ob, gb, crt = Dict.multiselect(
			self.handle_kwargs(kwargs),
			[
				'schema', 'auto_connection', 'print_query', 'get_query',
				'dt2ts', 'timezone', 'limit_offset', 'order_by', 'group_by', 'custom_read_types'
			]
		).values()
		
		if not self._check_connection(auto_connection):
			return pd.DataFrame()
		
		table = self._handle_table_name(table)
		columns = self._handle_columns(columns)
		conditions = self._handle_conditions(conditions)
		joins = self._handle_joins(joins)
		lo = self._handle_limit_offset(lo)
		ob = self._handle_order_by(ob)
		gb = self._handle_group_by(gb)
		
		# first part of query
		_q = f'select {columns}\nfrom {schema}.{table} main_table'
		
		# add joins
		if joins is not None:
			_q += f'\n\t{joins}'
		
		# add conditions
		if conditions is not None:
			_q += f"\nwhere {conditions['main']} "
			_p = conditions['params']
		else:
			_p = []
		
		# add group by
		if gb:
			_q += f'\n{gb}'
		
		# add order by
		if ob:
			_q += f'\n{ob}'
		
		# add limit offset
		if lo:
			_q += f'\n{lo}'
		
		try:
			if print_query:
				self.get_query(_q, _p, True)
			if get_query:
				# noinspection PyTypeChecker
				return self.get_query(_q, _p, False)
			self.cur.execute(_q, _p)
			result = self.read_from_cursor(dt2ts, tz, crt)
		except Exception as e:
			Log.log(f'[{self.db_name}]', location_depth=3, class_name='myDb', exc=e, query=self.get_query(_q, _p))
			result = pd.DataFrame()
			self.reopen()
		
		if auto_connection:
			self.close()
		
		return result
	
	def update(self, table: str, data: pd.DataFrame, conditions: ty.List[tuple], **kwargs) -> pd.DataFrame:
		schema, auto_connection, print_query, get_query, ct, ts_columns, tz, returning, dt2ts, crt = Dict.multiselect(
			self.handle_kwargs(kwargs),
			[
				'schema', 'auto_connection', 'print_query', 'get_query', 'custom_types',
				'ts_columns', 'timezone', 'returning', 'dt2ts', 'custom_read_types'
			]
		).values()
		if not self._check_connection(auto_connection):
			return pd.DataFrame()
		
		returning = self._handle_columns(returning)
		conditions = self._handle_conditions(conditions)
		ct = self._handle_custom_types(ct, data.columns)
		table = self._handle_table_name(table)
		
		if not conditions:
			Log.log(f'[{self.db_name}] No `conditions` specified', location_depth=3, class_name='myDb')
			return pd.DataFrame()
		if len(data) > 1:
			Log.log(f'[{self.db_name}] data length ({len(data)}) must be 1', location_depth=3, class_name='myDb')
			return pd.DataFrame()
		
		for col in data.columns:
			if is_datetime(data[col]):
				data[col] = Time.series_tz_convert(data[col], tz)
		
		data = data.to_dict(orient='records')[0]
		columns = self._handle_columns(list(data.keys()), do_join=False)
		values = self.optimize_row(list(data.values()), ct)
		
		data = dict(zip(columns, values['row']))
		if ts_columns:
			data.update(self._handle_ts_columns(ts_columns))
		data = ',\n\t'.join(f'{k} = {v}' for k, v in data.items())
		
		_q = f'update {schema}.{table} set \n\t{data}\nwhere\n\t{conditions["main"]} '
		_p = values['params'] + conditions["params"]
		
		# add returning
		if returning:
			_q += f"\nreturning {returning}"
		
		result = pd.DataFrame()
		try:
			if print_query:
				self.get_query(_q, _p, True)
			if get_query:
				# noinspection PyTypeChecker
				return self.get_query(_q, _p, False)
			self.cur.execute(_q, _p)
			self.conn.commit()
			if returning:
				result = self.read_from_cursor(dt2ts, tz, crt)
		except Exception as e:
			Log.log(f'[{self.db_name}]', location_depth=3, class_name='myDb', exc=e, query=self.get_query(_q, _p))
			self.reopen()
		
		if auto_connection:
			self.close()
		
		return result
	
	def delete(self, table: str, conditions: ty.List[tuple], **kwargs) -> pd.DataFrame:
		"""
		delete row from table where conditions match

		Example:
			db.delete('test', [('str_tst', '=', 'x')])
		"""
		schema, auto_connection, print_query, get_query, tz, returning, dt2ts, crt = Dict.multiselect(
			self.handle_kwargs(kwargs),
			[
				'schema', 'auto_connection', 'print_query', 'get_query',
				'timezone', 'returning', 'dt2ts', 'custom_read_types'
			]
		).values()
		
		if not self._check_connection(auto_connection):
			return pd.DataFrame()
		
		returning = self._handle_columns(returning)
		conditions = self._handle_conditions(conditions)
		table = self._handle_table_name(table)
		
		if not conditions:
			Log.log(f'[{self.db_name}] No `conditions` specified', location_depth=3, class_name='myDb')
			return pd.DataFrame()
		
		_q = f"delete from {schema}.{table} where {conditions['main']}"
		_p = conditions['params']
		
		# add returning
		if returning:
			_q += f"\nreturning {returning}"
		
		result = pd.DataFrame()
		try:
			if print_query:
				self.get_query(_q, _p, True)
			if get_query:
				# noinspection PyTypeChecker
				return self.get_query(_q, _p, False)
			self.cur.execute(_q, _p)
			self.conn.commit()
			if returning:
				result = self.read_from_cursor(dt2ts, tz, crt)
		except Exception as e:
			Log.log(f'[{self.db_name}]', location_depth=3, class_name='myDb', exc=e, query=self.get_query(_q, _p))
			self.reopen()
		
		if auto_connection:
			self.close()
		
		return result
	
	def drop(self, table: str, **kwargs) -> bool:
		"""
		drop table if exists

		Example:
			db.drop('test')
		"""
		schema, auto_connection, print_query, get_query = Dict.multiselect(
			self.handle_kwargs(kwargs),
			['schema', 'auto_connection', 'print_query', 'get_query']
		).values()
		
		if not self._check_connection(auto_connection):
			return False
		
		table = self._handle_table_name(table)
		
		_q = f'drop table if exists {schema}.{table} cascade'
		_p = None
		
		try:
			if print_query:
				self.get_query(_q, _p, True)
			if get_query:
				# noinspection PyTypeChecker
				return self.get_query(_q, _p, False)
			self.cur.execute(_q, _p)
			self.conn.commit()
			result = True
		except Exception as e:
			Log.log(f'[{self.db_name}]', location_depth=3, class_name='myDb', exc=e, query=self.get_query(_q, _p))
			result = False
			self.reopen()
		
		if auto_connection:
			self.close()
		
		return result
	
	def multiple_update(self, table: str, data: pd.DataFrame, **kwargs) -> bool:
		"""
		update multiple rows in single query
		update data.columns based on data.indexes

		Example:
			db.multiple_update(
				'test',
				pd.DataFrame({
					'str_tst': ['d', 'h', 'f', 'r'],
					'int_tst': [1000, 1000, 1000, 1000],
					'float_tst': [1000, 1000, 1000, 1000],
				}).set_index(['str_tst', 'int_tst']),
			)
		"""
		schema, auto_connection, print_query, get_query, ct, ntc = Dict.multiselect(
			self.handle_kwargs(kwargs),
			['schema', 'auto_connection', 'print_query', 'get_query', 'custom_types', 'null_type_casting']
		).values()
		if not self._check_connection(auto_connection):
			return False
		
		table = self._handle_table_name(table)
		
		if data.index.name is None:
			Log.log(f'[{self.db_name}] no index specified', location_depth=3, class_name='myDb')
			return False
		
		columns = self._handle_columns(data.columns.tolist(), do_join=False)
		index_columns = data.index.names
		all_columns = List.drop_duplicates(index_columns + columns)
		ct = self._handle_custom_types(ct, all_columns)
		
		# noinspection SqlWithoutWhere
		_q = f"update {schema}.{table} as main_table set \n\t"
		_q += ',\n\t'.join(f'{c} = new_table.{c}' for c in columns)
		
		# add values
		_q += '\nfrom (values \n\t'
		__q = []
		_p = []
		for row in tuple(data.itertuples(index=True, name=None)):
			if dev_utils.is_itterable(row[0]):
				# data has multiple indexes:
				row = [x for x in row[0]] + list(row[1:])
			
			o_row = self.optimize_row(row, ct)
			__q.append('(' + ', '.join(o_row["row"]) + ')')
			_p += o_row['params']
		
		_q += ',\n\t'.join(__q)
		_q += f'\n) as new_table(' + ','.join(all_columns) + ')'
		
		# add conditions
		_q += '\nwhere \n\t' + ' and\n\t'.join(f'new_table.{c} = main_table.{c}' for c in index_columns)
		
		if ntc:
			_q = self.get_query(_q, _p, False).replace('NULL', f'NULL::{ntc}')
			_p = []
		
		try:
			if print_query:
				self.get_query(_q, _p, True)
			if get_query:
				# noinspection PyTypeChecker
				return self.get_query(_q, _p, False)
			self.cur.execute(_q, _p)
			self.conn.commit()
			result = True
		except Exception as e:
			Log.log(f'[{self.db_name}]', location_depth=3, class_name='myDb', exc=e, query=self.get_query(_q, _p))
			result = False
			self.reopen()
		
		if auto_connection:
			self.close()
		
		return result
	
	def exists(self, table: str, conditions: ty.List[tuple], **kwargs) -> bool:
		"""
		if row with `conditions` exists in `table`

		Example:
			db.exists('test', [('str_tst', '=', 'x')])
		"""
		schema, auto_connection, print_query, get_query = Dict.multiselect(
			self.handle_kwargs(kwargs),
			['schema', 'auto_connection', 'print_query', 'get_query']
		).values()
		
		if not self._check_connection(auto_connection):
			return False
		
		table = self._handle_table_name(table)
		conditions = self._handle_conditions(conditions)
		
		if not conditions:
			Log.log(f'[{self.db_name}] No `conditions` specified', location_depth=3, class_name='myDb')
			return False
		
		_q = f"select case when exists (select true x from {schema}.{table} where {conditions['main']}) then true else false end y"
		_p = conditions['params']
		
		try:
			if print_query:
				self.get_query(_q, _p, True)
			if get_query:
				# noinspection PyTypeChecker
				return self.get_query(_q, _p, False)
			self.cur.execute(_q, _p)
			result = self.cur.fetchall()[0][0]  # True or False
		except Exception as e:
			Log.log(f'[{self.db_name}]', location_depth=3, class_name='myDb', exc=e, query=self.get_query(_q, _p))
			result = False
			self.reopen()
		
		if auto_connection:
			self.close()
		
		return result
	
	def table_exists(self, table: str, **kwargs) -> bool:
		"""
		if `table` exists in schema

		Example:
			db.table_exists('test')
		"""
		schema, auto_connection, print_query, get_query = Dict.multiselect(
			self.handle_kwargs(kwargs),
			['schema', 'auto_connection', 'print_query', 'get_query']
		).values()
		
		if not self._check_connection(auto_connection):
			return False
		
		table = self._handle_table_name(table)
		
		_q = f"select to_regclass('{schema}.{table}')"
		_p = None
		
		try:
			if print_query:
				self.get_query(_q, _p, True)
			if get_query:
				# noinspection PyTypeChecker
				return self.get_query(_q, _p, False)
			self.cur.execute(_q, _p)
			result = not (self.cur.fetchall()[0][0] is None)  # True or False
		except Exception as e:
			Log.log(f'[{self.db_name}]', location_depth=3, class_name='myDb', exc=e, query=self.get_query(_q, _p))
			result = False
			self.reopen()
		
		if auto_connection:
			self.close()
		
		return result
	
	def schema_exists(self, **kwargs) -> bool:
		"""
		if `schema` exists in database

		Example:
			db.table_exists(schema='xxx')
		"""
		schema, auto_connection, print_query, get_query = Dict.multiselect(
			self.handle_kwargs(kwargs),
			['schema', 'auto_connection', 'print_query', 'get_query']
		).values()
		
		if not self._check_connection(auto_connection):
			return False
		
		_q = f"select case when exists (select true x from information_schema.schemata WHERE schema_name = '{schema}') then true else false end y;"
		_p = None
		
		try:
			if print_query:
				self.get_query(_q, _p, True)
			if get_query:
				# noinspection PyTypeChecker
				return self.get_query(_q, _p, False)
			self.cur.execute(_q, _p)
			result = self.cur.fetchall()[0][0]  # True or False
		except Exception as e:
			Log.log(f'[{self.db_name}]', location_depth=3, class_name='myDb', exc=e, query=self.get_query(_q, _p))
			result = False
			self.reopen()
		
		if auto_connection:
			self.close()
		
		return result
	
	def schema_tables(self, **kwargs) -> pd.DataFrame:
		"""
		get all tables that are in `schema`

		Example:
			res = db.schema_tables(schema='xxx')
		"""
		schema, auto_connection, print_query, get_query = Dict.multiselect(
			self.handle_kwargs(kwargs),
			['schema', 'auto_connection', 'print_query', 'get_query']
		).values()
		
		if not self._check_connection(auto_connection):
			return pd.DataFrame()
		
		_q = f""" SELECT * FROM information_schema.tables WHERE table_schema='{schema.replace('"', '')}' """
		_p = None
		
		try:
			if print_query:
				self.get_query(_q, _p, True)
			if get_query:
				# noinspection PyTypeChecker
				return self.get_query(_q, _p, False)
			self.cur.execute(_q, _p)
			result = self.read_from_cursor(False)
		except Exception as e:
			Log.log(f'[{self.db_name}]', location_depth=3, class_name='myDb', exc=e, query=self.get_query(_q, _p))
			result = pd.DataFrame()
			self.reopen()
		
		if auto_connection:
			self.close()
		
		return result
	
	def create_schema(self, owner: str = None, **kwargs) -> bool:
		"""
		create `schema` if not exists in database with `owner`

		Example:
			db.create_schema(schema='xxx', owner='username')
		"""
		schema, auto_connection, print_query, get_query = Dict.multiselect(
			self.handle_kwargs(kwargs),
			['schema', 'auto_connection', 'print_query', 'get_query']
		).values()
		if owner is None:
			owner = self.db_properties['user']
		
		if not self._check_connection(auto_connection):
			return False
		
		_q = f"create schema if not exists {schema}"
		if owner:
			_q += f" authorization {owner}"
		_p = None
		
		try:
			if print_query:
				self.get_query(_q, _p, True)
			if get_query:
				# noinspection PyTypeChecker
				return self.get_query(_q, _p, False)
			self.cur.execute(_q, _p)
			self.conn.commit()
			result = True
		except Exception as e:
			Log.log(f'[{self.db_name}]', location_depth=3, class_name='myDb', exc=e, query=self.get_query(_q, _p))
			result = False
			self.reopen()
		
		if auto_connection:
			self.close()
		
		return result
	
	def custom(
			self,
			query: str,
			params: ty.Optional[list],
			to_commit: bool = True,
			to_fetch: bool = False,
			**kwargs
	) -> pd.DataFrame:
		"""
			run custom query and select if `to_commit` and `to_fetch`

			Example:
				res = db.custom(
					'select * from users_data.account_account',
					[],
					to_commit=False,
					to_fetch=True
				)

			res = db.custom(
				'update users_data.account_account set is_admin=%s where id=3',
				[True],
				to_commit=True,
				to_fetch=False
			)

		"""
		schema, auto_connection, print_query, get_query, dt2ts, tz, crt = Dict.multiselect(
			self.handle_kwargs(kwargs),
			['schema', 'auto_connection', 'print_query', 'get_query', 'dt2ts', 'timezone', 'custom_read_types']
		).values()
		
		if not self._check_connection(auto_connection):
			return pd.DataFrame()
		
		result = pd.DataFrame()
		
		try:
			if print_query:
				self.get_query(query, params, True)
			if get_query:
				# noinspection PyTypeChecker
				return self.get_query(query, params, False)
			if type(params) is list:
				self.cur.execute(query, params)
			else:
				self.cur.execute(query)
			if to_commit:
				self.conn.commit()
			if to_fetch:
				result = self.read_from_cursor(dt2ts, tz, crt)
		except Exception as e:
			Log.log(
				f'[{self.db_name}]',
				location_depth=3,
				class_name='myDb',
				exc=e,
				query=self.get_query(query, params)
			)
			self.reopen()
		
		if auto_connection:
			self.close()
		
		return result
	
	def upsert(self, table: str, data: pd.DataFrame, **kwargs) -> pd.DataFrame:
		"""
		insert `data` to `table` if not exists else update it

		if timezone is specified and there are tz-aware objects in input or output(if returning is specified)
			of function their time zone will be converted to selected time zone
		if returning is specified the function will inserted `data` and return with selected columns

		update is done base on `data.index` (it must be unique column in db)

		Example:
			res = db.upsert(
				'users_token',
				pd.DataFrame(
					columns=['uid', 'token'],
					data=[
						[2, 'u2'],
						[3, 'u3'],
					]
				).set_index('uid'),
				ts_columns='created',
				returning=['uid', 'token', 'created'],
			)
		"""
		schema, auto_connection, print_query, get_query, ct, returning, dt2ts, tz, ts_columns, crt = Dict.multiselect(
			self.handle_kwargs(kwargs),
			[
				'schema', 'auto_connection', 'print_query', 'get_query', 'custom_types',
				'returning', 'dt2ts', 'timezone', 'ts_columns', 'custom_read_types'
			]
		).values()
		
		if not self._check_connection(auto_connection):
			return pd.DataFrame()
		if data.index.name is None:
			Log.log(f'[{self.db_name}] no index specified', location_depth=3, class_name='myDb')
			return pd.DataFrame()
		if len(data.index.names) > 1:
			Log.log(f'[{self.db_name}] too many indexes', location_depth=3, class_name='myDb')
			return pd.DataFrame()
		
		index = str(data.index.name)
		data.reset_index(inplace=True)
		table = self._handle_table_name(table)
		
		for col in data.columns:
			if is_datetime(data[col]):
				data[col] = Time.series_tz_convert(data[col], tz)
		
		if ts_columns:
			ts_columns = ts_columns if type(ts_columns) is list else [ts_columns]
			for c in ts_columns:
				# upgrademe better way to add timestamps
				data[c] = Time.dtnow('gmt', remove_tz=True)
		
		returning = self._handle_columns(returning)
		columns = self._handle_columns(list(data.columns.values), do_join=False)
		ct = self._handle_custom_types(ct, data.columns)
		
		insert_values = []
		_p = []
		for row in tuple(data.itertuples(index=False, name=None)):
			o_row = self.optimize_row(row, ct)
			insert_values.append('(' + ', '.join(o_row["row"]) + ')')
			_p += o_row['params']
		insert_values = ',\n\t'.join(insert_values)
		
		_q = f"insert into {schema}.{table}({','.join(columns)}) \nvalues\n\t{insert_values}\n on conflict({index}) do update set " + ','.join(
			f"{c} = excluded.{c}" for c in columns if c.strip('"') != index)
		
		# add returning
		if returning:
			_q += f"\nreturning {returning}"
		
		res = pd.DataFrame()
		try:
			if print_query:
				self.get_query(_q, _p, True)
			if get_query:
				# noinspection PyTypeChecker
				return self.get_query(_q, _p, False)
			self.cur.execute(_q, _p)
			self.conn.commit()
			if returning:
				res = self.read_from_cursor(dt2ts, tz, crt)
		except Exception as e:
			Log.log(f'[{self.db_name}]', location_depth=3, class_name='myDb', exc=e, query=self.get_query(_q, _p))
			self.reopen()
		
		if auto_connection:
			self.close()
		
		return res
	
	def count(self, table: str, column: str = None, conditions: ty.List[tuple] = None, **kwargs) -> int:
		schema, auto_connection, print_query, get_query = Dict.multiselect(
			self.handle_kwargs(kwargs),
			['schema', 'auto_connection', 'print_query', 'get_query']
		).values()
		
		if not self._check_connection(auto_connection):
			return -1
		
		table = self._handle_table_name(table)
		conditions = self._handle_conditions(conditions)
		if column:
			column = self._handle_columns([column])
		else:
			column = '*'
		
		# first part of query
		_q = f'select count({column}) x from {schema}.{table} main_table'
		
		# add conditions
		if conditions is not None:
			_q += f"\nwhere {conditions['main']} "
			_p = conditions['params']
		else:
			_p = []
		
		try:
			if print_query:
				self.get_query(_q, _p, True)
			if get_query:
				# noinspection PyTypeChecker
				return self.get_query(_q, _p, False)
			self.cur.execute(_q, _p)
			result = self.read_from_cursor(False).values[0][0]
		except Exception as e:
			Log.log(f'[{self.db_name}]', location_depth=3, class_name='myDb', exc=e, query=self.get_query(_q, _p))
			result = -1
			self.reopen()
		
		if auto_connection:
			self.close()
		
		return result
	
	def alter_column_add(self, table: str, columns: ty.Dict[str, str], **kwargs) -> bool:
		"""
		create table if not exist

		Example:
			db.alter_column_add(
				'test',
				{
					'id': 'serial primary key',
					'created': "timestamp default timezone('utc'::text, now())",
				}
			)

		"""
		schema, auto_connection, print_query, get_query, ts_columns = Dict.multiselect(
			self.handle_kwargs(kwargs),
			['schema', 'auto_connection', 'print_query', 'get_query', 'ts_columns']
		).values()
		
		if not self._check_connection(auto_connection):
			return False
		
		table = self._handle_table_name(table)
		
		if ts_columns:
			columns.update(self._handle_ts_columns(ts_columns, to_create=True))
		
		cols = []
		for k, v in columns.items():
			cols.append(f'add column "{k}" {v}')
		cols = ','.join(cols)
		
		_q = f'alter table {schema}.{table} {cols}'
		_p = None
		
		try:
			if print_query:
				self.get_query(_q, _p, True)
			if get_query:
				# noinspection PyTypeChecker
				return self.get_query(_q, _p, False)
			self.cur.execute(_q, _p)
			self.conn.commit()
			result = True
		except Exception as e:
			Log.log(f'[{self.db_name}]', location_depth=3, class_name='myDb', exc=e, query=self.get_query(_q, _p))
			result = False
			self.reopen()
		
		if auto_connection:
			self.close()
		
		return result
	
	def refresh_id(self, table: str, table_id_seq: str = None, **kwargs) -> bool:
		schema, auto_connection, print_query, get_query = Dict.multiselect(
			self.handle_kwargs(kwargs),
			['schema', 'auto_connection', 'print_query', 'get_query']
		).values()
		
		if not self._check_connection(auto_connection):
			return False
		
		if not table_id_seq:
			table_id_seq = f'"{table}_id_seq"'
		table = self._handle_table_name(table)
		
		_q = f"SELECT setval('{schema}.{table_id_seq}', COALESCE((SELECT MAX(id)+1 y FROM {schema}.{table}), 1), false) x"
		_p = None
		
		try:
			if print_query:
				self.get_query(_q, _p, True)
			if get_query:
				# noinspection PyTypeChecker
				return self.get_query(_q, _p, False)
			self.cur.execute(_q, _p)
			self.conn.commit()
			result = True
		except Exception as e:
			Log.log(f'[{self.db_name}]', location_depth=3, class_name='myDb', exc=e, query=self.get_query(_q, _p))
			result = False
			self.reopen()
		
		if auto_connection:
			self.close()
		
		return result


if __name__ == '__main__':
	_db = Psql('services', open=True)
	# res = db.update(
	# 	'news',
	# 	pd.DataFrame([[10]], columns=['clicks']),
	# 	[('id', '=', 9981130)],
	# 	returning=['id', 'link']
	# )
	# _res = _db.delete(
	# 	'news',
	# 	[('id', '=', 9981130)],
	# 	returning=['id', 'link']
	# )
	# print(_res)
	# _db.backup()
	# _db.restore()
	
	_db.close()
