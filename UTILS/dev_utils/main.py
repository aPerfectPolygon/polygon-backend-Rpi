import asyncio as aio
import multiprocessing as mprc
import os
import time as ti
import typing as ty

import aiohttp
import pandas as pd
import psutil
import requests
from requests.structures import CaseInsensitiveDict as _cid

from UTILS.dev_utils import Defaults as dev_def
from UTILS.dev_utils import Log
from UTILS.dev_utils.Objects import Json, Dict


class Tracking:
	def __init__(self, items):
		self.items_trackers = {item: [] for item in items}
		self.trackers_items = {}
	
	def get_trackers(self, items: list):
		return Dict.multiselect(self.items_trackers, items)
	
	def add_trackers(self, items: list):
		self.items_trackers.update({item: [] for item in items if item not in self.items_trackers})
	
	def untrack_all(self, tracker):
		if tracker not in self.trackers_items:
			return
		for item in self.trackers_items[tracker]:
			self.items_trackers[item].remove(tracker)
		self.trackers_items[tracker] = []
	
	def tracker_untrack(self, tracker, items):
		if tracker not in self.trackers_items:
			return
		for item in items:
			try:
				self.trackers_items[tracker].remove(item)
			except:
				pass
			try:
				self.items_trackers[item].remove(tracker)
			except:
				pass
	
	def tracker_track(self, tracker, items):
		self.untrack_all(tracker)
		for item in items:
			self.items_trackers[item].append(tracker)
		self.trackers_items.update({tracker: items})
	
	def tracker_remove(self, tracker):
		self.untrack_all(tracker)
		self.trackers_items.pop(tracker, None)
	
	def tracker_add(self, tracker):
		self.trackers_items.update({tracker: []})


class TrackerManager:
	def __init__(self):
		self.trackers = pd.DataFrame(columns=['id', 'tag', 'value', 'auto_added'])
	
	def untrack(self, tracker_id: str = None, tag: str = None, value: str = None, auto_added: bool = None):
		conds = pd.Series([True] * len(self.trackers.id))
		if tracker_id:
			conds &= (self.trackers.id == tracker_id)
		if tag is not None:
			conds &= (self.trackers.tag == tag)
		if value is not None:
			conds &= (self.trackers.value == value)
		if auto_added is not None:
			conds &= (self.trackers.auto_added == auto_added)
		
		self.trackers = self.trackers.loc[~conds].reset_index(drop=True)
	
	def track(self, tracker_id: str, tag: str, value: str = None, auto_added: bool = None):
		# check if it already exists
		conds = (self.trackers.id == tracker_id) & (self.trackers.tag == tag)
		if value is not None:
			conds &= (self.trackers.value == value)
		
		if self.trackers.loc[conds].empty:
			self.trackers = self.trackers.append(
				pd.DataFrame(
					[[tracker_id, tag, value, auto_added]], columns=['id', 'tag', 'value', 'auto_added']
				)
			).reset_index(drop=True)
	
	def get_trackers(self, tag: str, value: str = None):
		conds = (self.trackers.tag == tag)
		if value is not None:
			conds &= (self.trackers.value == value)
		
		return self.trackers.loc[conds]


class AioResponse(aiohttp.ClientResponse):
	Json: dict = {}
	is_success: bool = False
	status_code: int


class AioResponseError:
	text = 'NoResponse'
	status_code = 408
	Json = {}
	headers = {}
	is_success = False


async def aio_safe_request(
		method: str,
		url: str,
		json: dict = None,
		data: dict = None,
		params: dict = None,
		headers: dict = None,
		use_proxy: bool = False,
		expected_codes: ty.Union[list, int] = None,
		show_link: bool = False,
		**kwargs
) -> AioResponse:
	"""

	Parameters
	----------
	url : url of endpoint
	method : method of request (must be in methods supported by `requests` library)
	json : body of request in json format {"key": "value"}
	data : body of request in form format {"key": ["value"]}
	params : parameters of request
	headers : headers of request
	use_proxy : set if this request must be sent with pre-set(`UTILS.dev_utils.Defaults.proxies`) proxy or not
	expected_codes : a list of status_codes that is expected from API
	show_link : log the link and method ?
	"""
	
	def return_error():
		return AioResponseError
	
	def return_response(response: ty.Optional[aiohttp.ClientResponse]):
		if response is None:
			return return_error()
		response.Json = Json.decode(response.text, silent=True)
		response.is_success = True
		response.status_code = response.status
		
		return response
	
	# check method
	if method not in ['get', 'post', 'put', 'options', 'delete']:
		raise ValueError(f"bad method `{method}` (if you're sure that method is correct add it to list above)")
	
	# add User-Agent to request headers
	request_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:85.0) Gecko/20100101 Firefox/85.0'
	if headers:
		if 'User-Agent' not in headers:
			headers.update({'User-Agent': request_agent})
	else:
		headers = {'User-Agent': request_agent}
	
	# check if to use proxy or not
	proxies = kwargs.pop('proxies', None)
	if not proxies:
		if use_proxy:
			proxies = dev_def.proxies['http']
		else:
			proxies = None
	
	# check `expected_codes` type
	if isinstance(expected_codes, int):
		expected_codes = [expected_codes]
	
	if show_link:
		print(f'[{method}]({url})')
	
	# send request
	request_response = None
	for retry_on_bad_status_no in range(3):
		request_response = None
		for retry_on_error_no in range(3):
			request_response = None
			session = aiohttp.ClientSession()
			
			try:
				# noinspection PyProtectedMember
				request_response = await session._request(
					method.upper(),
					url,
					json=json,
					data=data,
					params=params,
					headers=headers,
					proxy=proxies,
					ssl=True,
					**kwargs
				)
				request_response.text = await request_response.text()
				request_response.close()
				await session.close()
				break
			except Exception as e:
				Log.log(f'[RequestError] {url}', exc=e)
				await aio.sleep(1)
			
			await session.close()
		if request_response is None:
			# noinspection PyTypeChecker
			return return_error()
		
		if not expected_codes or request_response.status in expected_codes:
			# noinspection PyTypeChecker
			return return_response(request_response)
		else:
			Log.log(
				f'[BadStatusCode] `{request_response.status}` not in {expected_codes} `{request_response.text[:10]}`... {url}')
			await aio.sleep(1)
	# noinspection PyTypeChecker
	return return_response(request_response)


class NewRequestResponse(requests.models.Response):
	Json: dict = {}
	headers: dict = {}
	is_success: bool = False


def safe_request(
		method: str,
		url: str,
		json: dict = None,
		data: dict = None,
		params: dict = None,
		headers: dict = None,
		use_proxy: bool = False,
		expected_codes: ty.Union[list, int] = None,
		show_link: bool = False,
		**kwargs
) -> NewRequestResponse:
	"""

	Parameters
	----------
	url : url of endpoint
	method : method of request (must be in methods supported by `requests` library)
	json : body of request in json format {"key": "value"}
	data : body of request in form format {"key": ["value"]}
	params : parameters of request
	headers : headers of request
	use_proxy : set if this request must be sent with pre-set(`UTILS.dev_utils.Defaults.proxies`) proxy or not
	expected_codes : a list of status_codes that is expected from API
	show_link : log the link and method ?
	"""
	
	def return_error() -> NewRequestResponse:
		response = NewRequestResponse()
		response._content = 'NoResponse'.encode('utf-8')
		response.status_code = 408
		response.Json = {}
		response.is_success = False
		response.headers = dict(response.headers)
		return response
	
	def return_response(response: ty.Optional[requests.models.Response]) -> NewRequestResponse:
		if response is None:
			return return_error()
		response.Json = Json.decode(response.text, silent=True)
		response.is_success = True
		response.headers = dict(response.headers)
		
		if _encoding:
			response.encoding = _encoding
		
		# noinspection PyTypeChecker
		return response
	
	# check method
	if method not in ['get', 'post', 'put', 'options', 'delete']:
		raise ValueError(f"bad method `{method}` (if you're sure that method is correct add it to list above)")
	
	# add User-Agent to request headers
	request_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:85.0) Gecko/20100101 Firefox/85.0'
	if headers:
		if 'User-Agent' not in headers:
			headers.update({'User-Agent': request_agent})
	else:
		headers = {'User-Agent': request_agent}
	
	# check if to use proxy or not
	proxies = kwargs.pop('proxies', None)
	if not proxies:
		if use_proxy:
			proxies = dev_def.proxies
		else:
			proxies = None
	
	_encoding = kwargs.pop('encoding', None)
	
	# check `expected_codes` type
	if isinstance(expected_codes, int):
		expected_codes = [expected_codes]
	
	if show_link:
		print(f'[{method}]({url})')
	
	# send request
	request_response = None
	for retry_on_bad_status_no in range(3):
		request_response = None
		for retry_on_error_no in range(3):
			request_response = None
			try:
				request_response = requests.request(
					method,
					url,
					json=json,
					data=data,
					params=params,
					headers=headers,
					proxies=proxies,
					**kwargs
				)
				break
			except Exception as e:
				Log.log(f'[RequestError] {url}', exc=e)
				ti.sleep(1)
		
		if request_response is None:
			return return_error()
		
		if not expected_codes or request_response.status_code in expected_codes:
			return return_response(request_response)
		else:
			Log.log(
				f'[BadStatusCode] `{request_response.status_code}` not in {expected_codes} `{request_response.text[:10]}` {url}')
			ti.sleep(1)
	return return_response(request_response)


def wait4threads(threads: list, to_run=False) -> list:
	"""runs threads and returns empty list"""
	
	if threads:
		if to_run:
			[th.run() for th in threads]
		else:
			[th.start() for th in threads]
			[th.join() for th in threads]
	
	return []


async def aio_wait4threads(func: ty.Callable, args: ty.Iterable):
	return await aio.gather(*[func(item) for item in args])


def wait4processes(func: ty.Callable, args: ty.Union[list, tuple], processes=None, use_starmap=False) -> list:
	"""
	run a function multiple times using multiple processes and return a list of function calls results

	processes:
		specify how many processes you want to run
		default :
			length of args
	use_starmap:
		if `func` has multiple arguments you should pass them in `args` like ((1, 2), (1, 2))

	Example:
		simple function:
			def x(n):
				print(f'in {n}')
				sleep(1)
				print(f'out {n}')
				return n
			if __name__ == '__main__':
				res = wait4processes(x, (1, 2))
				print(res)  # res -> [1, 2]

		starmap:
			def x(n, c):
				print(f'in {n} {c}')
				sleep(1)
				print(f'out {n} {c}')
				return n + c
			if __name__ == '__main__':
				res = wait4processes(x, ((1, 2), (3, 4)), use_starmap=True)
				print(res)  # res -> [3, 7]

	"""
	if not processes:
		processes = len(args)
	
	with mprc.Pool(processes=processes) as pool:
		if use_starmap:
			res = pool.starmap(func, args)
		else:
			res = pool.map(func, args)
		pool.close()
		pool.join()
	return res


def get_processes(name: str) -> list:
	"""get processes that contain given name"""
	
	# Iterate over the all the running process
	processes = []
	for proc in psutil.process_iter():
		try:
			# Check if process name contains the given name string.
			if name.lower() in proc.name().lower():
				processes.append(proc)
		except:
			pass
	return processes


def compare_dfs(df_1: pd.DataFrame, df_2: pd.DataFrame, exclude_from_new: list = None) -> dict:
	"""
	compare two dateframes and return {'changed_column': {'changed_index': {'old': '', 'new': ''}}}

	Example:
	--------
	>>> df1 = pd.DataFrame(
	... 		[
	... 			['i1', 'r1-c1-First', 'r1-c2-First', 'r1-c3-First'],
	... 			['i2', 'r2-c1-First', 'r2-c2-First', 'r2-c3-First'],
	... 			['i3', 'r3-c1-First', 'r3-c2-First', 'r3-c3-First']
	... 		],
	... 		columns=['i', 'c1', 'c2', 'c3']
	... 	).set_index('i')
	>>> df1
			c1           c2           c3
	i
	i1  r1-c1-First  r1-c2-First  r1-c3-First
	i2  r2-c1-First  r2-c2-First  r2-c3-First
	i3  r3-c1-First  r3-c2-First  r3-c3-First
	>>> df2 = df1.copy()
	>>> df2.loc['i1']['c2'] = 'x'
	>>> df2.loc['i2']['c2'] = 'z'
	>>> df2.loc['i2']['c3'] = 'y'
	>>> df2
			c1           c2           c3
	i
	i1  r1-c1-First            x  r1-c3-First
	i2  r2-c1-First            z            y
	i3  r3-c1-First  r3-c2-First  r3-c3-First
	>>> compare_dfs(df1, df2)
	{
		'c2': {'i1': {'old': 'r1-c2-First', 'new': 'x'}, 'i2': {'old': 'r2-c2-First', 'new': 'z'}},
		'c3': {'i2': {'old': 'r2-c3-First', 'new': 'y'}}
	}

	"""
	# sync indexes
	df_1 = df_1.loc[df_2.index]
	
	# get changed_data
	_cmp = df_1 == df_2
	changed_data = _cmp[_cmp.isin([False]).any(axis=1)]
	
	# join changed data with old and new data
	all_data = changed_data.join(df_2, rsuffix='_new').join(df_1, rsuffix='_old')
	
	output = {}
	for col in df_1.columns:
		# from all_data get related columns to `col` -> [col, col_old, col_new]
		data: pd.DataFrame = all_data[[col, f'{col}_old', f'{col}_new']].query(f'{col} == False')
		if data.empty:
			continue
		
		data = data.rename(columns={
			f'{col}_old': 'old',
			f'{col}_new': 'new',
		})[['old', 'new']]
		
		if exclude_from_new:
			for item in exclude_from_new:
				data = data.loc[data.new != item]
		
		output.update({col: data.to_dict('index')})
	
	return output


def find_tags(data: pd.Series, tags: pd.Series) -> pd.DataFrame:
	"""
	find `tags` in `data` and return a dataframe of found `tag_keys` and `tag_values` with index of `data`

	Example:
	--------
	>>> _data = pd.Series([
	... 	'some text with a `tag`',
	... 	'some string with a tag',
	... 	'no tags are in this',
	... 	'something with another tag'
	... ])
	>>> _data
	0        some text with a `tag`
	1        some string with a tag
	2    something with another tag
	dtype: object
	>>> _tags = pd.Series({'TAG': ['`tag`', 'tag'], 'TEXT': ['text', 'string'], 'TAG2': ['another tag']})
	>>> _tags
	TAG       [`tag`, tag]
	TEXT    [text, string]
	TAG2     [another tag]
	dtype: object
	>>> find_tags(_data, _tags)
			tag_values     tag_keys
	0       [text, `tag`]  [TEXT, TAG]
	1       [string, tag]  [TEXT, TAG]
	3  [another tag, tag]  [TAG2, TAG]

	"""
	if data.empty or tags.empty:
		return pd.DataFrame(columns=['tag_values', 'tag_keys'])
	
	data = data.replace({
		'ك': 'ک',
		'دِ': 'د',
		'بِ': 'ب',
		'زِ': 'ز',
		'ذِ': 'ذ',
		'شِ': 'ش',
		'سِ': 'س',
		'ى': 'ی',
		'ي': 'ی'
	}, regex=True)
	
	normalized = ' ' + data.str.lower() + ' '
	normalized = normalized.str.replace(r'"|\(|\)|,', ' ', regex=True)
	
	tags = tags.explode()
	tags.index.name = 'key'
	tags = tags.reset_index(name='value')
	
	# make regex
	r = (' ' + ' | '.join(tags.value.values) + ' ')
	
	r = r.replace('(', '\\(').replace(')', '\\)')
	# handle overlaps
	r = f'(?=({r}))'
	
	# search and remove rows where no tags found and explode-strip tags
	tag_value = normalized.str.findall(r).apply(list).explode().dropna().str.strip()
	
	tag_value.name = 'tag_values'
	output_tags = pd.DataFrame(tag_value)
	output_tags['tag_keys'] = tag_value.replace(tags.set_index('value')['key'].to_dict())
	
	index_group_by = output_tags.reset_index().groupby('index')
	output_tags['tag_values'] = index_group_by.tag_values.apply(lambda x: list(x.drop_duplicates()))
	output_tags['tag_keys'] = index_group_by.tag_keys.apply(lambda x: list(x.drop_duplicates()))
	
	output_tags = output_tags[~output_tags.index.duplicated()]
	
	return output_tags


def is_itterable(item) -> bool:
	return type(item) in [list, tuple, set]


def is_number(item) -> bool:
	return type(item) in [int, float] and not is_nan(item)


def is_nan(item) -> bool:
	return item != item


def is_null(item) -> bool:
	return item is None or is_nan(item) or str(item) in ['NULL', 'None', 'nan']


def is_dict(item) -> bool:
	return type(item) in [dict, _cid]


def create_service(
		service_name,
		description,
		working_directory,
		exec_start,
		log_file,
		restart='always',
		user='root',
		wanted_by='multi-user.target'
):
	service_file = f'/lib/systemd/system/{service_name}.service'
	config = f"""[Unit]
Description={description}

[Service]
User={user}
WorkingDirectory={working_directory}
ExecStart={exec_start}
Restart={restart}
StandardOutput=file:{log_file}
StandardError=file:{log_file}

[Install]
WantedBy={wanted_by}"""
	
	if os.path.exists(service_file):
		with open(service_file, 'r', encoding='utf-8') as f:
			if f.read() == config:
				os.system(f'sudo systemctl restart {service_name}.service')
			else:
				os.system(f'rm {service_file}')
	
	if not os.path.exists(service_file):
		with open(service_file, 'w', encoding='utf-8') as f:
			f.write(config)
		os.system(
			f'sudo systemctl daemon-reload && sudo systemctl start {service_name}.service && sudo systemctl enable {service_name}.service')


def supervisor_create_or_restart_service(
		program,
		process_name,
		user,
		command,
		directory,
		stdout_logfile,
		stderr_logfile,
		environment='LANG=en_US.UTF-8,LC_ALL=en_US.UTF-8',
		auto_start=True,
		auto_restart=True,
		start_retries=3,
		stdout_logfile_maxbytes='10MB',
		stderr_logfile_maxbytes='10MB',
		stdout_logfile_backups=1000000,
		stderr_logfile_backups=1000000,
		serverurl='AUTO',
		stopasgroup=True,
		stopsignal='QUIT'
):
	"""
	http://supervisord.org/configuration.html#program-x-section-example
	"""
	
	config = f"""[program:{program}]
process_name={process_name}
user={user}
command={command}
directory={directory}
autostart={auto_start}
autorestart={auto_restart}
startretries={start_retries}
stdout_logfile={stdout_logfile}
stdout_logfile_maxbytes={stdout_logfile_maxbytes}
stdout_logfile_backups={stdout_logfile_backups}
stderr_logfile={stderr_logfile}
stderr_logfile_maxbytes={stderr_logfile_maxbytes}
stderr_logfile_backups={stderr_logfile_backups}
environment={environment}
serverurl={serverurl} 
stopasgroup={stopasgroup}
stopsignal={stopsignal} """
	addr = f'/etc/supervisor/conf.d/{program}.conf'
	
	os.system(f'mkdir -p $(dirname {stdout_logfile}) && touch {stdout_logfile}')
	os.system(f'mkdir -p $(dirname {stderr_logfile}) && touch {stderr_logfile}')
	
	if os.path.exists(addr):
		with open(addr, 'r', encoding='utf-8') as f:
			if f.read() == config:
				os.system(f'sudo supervisorctl restart {program}')
			else:
				os.system(f'rm {addr}')
	
	if not os.path.exists(addr):
		with open(addr, 'w', encoding='utf-8') as f:
			f.write(config)
		os.system(f'sudo supervisorctl reread && sudo supervisorctl update && supervisorctl restart {program}')


class MultiLingual:
	__all = dev_def.Languages.all
	
	def __init__(self, data: ty.Dict[str, ty.Dict[str, str]] = None):
		self.by_lang = {lang: {} for lang in self.__all}
		self.by_key = {}
		if data:
			self.update(data)
	
	def asdict(self):
		return {'by_lang': self.by_lang, 'by_key': self.by_key}
	
	def update(self, data: ty.Dict[str, ty.Dict[str, str]]):
		for k, languauges in data.items():
			if k not in self.by_key:
				self.by_key.update({k: {lang: '' for lang in self.__all}})
			
			for lang in self.__all:
				if lang not in languauges:
					if lang in self.by_key[k] and self.by_key[k][lang]:
						languauges.update({lang: self.by_key[k][lang]})
					else:
						Log.log(f'no translation for `{k}` in `{lang}`')
						languauges.update({lang: ''})
				self.by_lang[lang].update({k: languauges[lang]})
			self.by_key.update({k: languauges})


def if_truthiness(x, none=None):
	return x if x else none


if __name__ == '__main__':
	aio.run(
		aio_safe_request(
			'get',
			# 'https://httpbin.org/get'
			'https://api.binance.com/api/v3/ticker/24hr',
			# 'https://www.forex.com/_Srvc/feeds/LiveRates.asmx/GetProductRates',
			use_proxy=True
		)
	)
	
	safe_request(
		'get',
		# 'https://httpbin.org/get'
		'https://api.binance.com/api/v3/ticker/24hr',
		use_proxy=True
	)
