import datetime
import logging
import os
import pathlib
import traceback

import termcolor

from UTILS.dev_utils import Defaults as dev_def


def setup_logger(
		name,
		file=None,
		level=None,
		_format=None
):
	if file is None:
		file = pathlib.Path(
			__file__).parent.parent.parent.parent / f'Logs/{datetime.datetime.today().date()}.log'
	_format = _format if _format is not None else '%(asctime)s:%(levelname)s:%(name)s: %(message)s'
	level = level if level is not None else logging.DEBUG

	logger = logging.getLogger(name)
	logger.setLevel(level)
	logger.propagate = False
	formatter = logging.Formatter(_format)

	os.makedirs(file.parent, exist_ok=True)
	file_handler = logging.FileHandler(file, encoding='utf-8')
	# file_handler = TimedRotatingFileHandler(file, when="m", interval=1, encoding='utf-8')

	file_handler.setFormatter(formatter)
	logger.addHandler(file_handler)
	return logger


def log(
		text: str,
		logger: str = None,
		**kwargs
):
	no_log_on_server = kwargs.pop('no_log_on_server', False)
	if no_log_on_server and dev_def.is_server:
		return

	logger = logger if logger is not None else 'default'

	query = kwargs.pop('query', None)
	silent_on_server = kwargs.pop('silent_on_server', False)
	exc = kwargs.pop('exc', None)
	method = kwargs.pop('method', 'info')
	location = kwargs.pop('location', None)
	text = str(text).replace('\n', '[\\n]')

	if not location:
		location = curr_info(
			kwargs.pop('location_depth', 3),
			kwargs.pop('class_name', None)
		)

	if exc is not None:
		_exc = str(exc).replace('\n', '[\\n]')
		text = f"{exc.__class__.__name__}({_exc}) {text}"
		del _exc
		method = 'exception'
	if query:
		text += f'\nRelated Query -> {query}\n'

	text = f'++ {location}: {text}'

	if not (silent_on_server and dev_def.is_server):
		Print(text, color='red')

	if logger not in dev_def.logger_names:
		Print(f'Bad logger name{logger}', color='red')
	elif method not in dev_def.standard_log_methods:
		Print(f'Bad logger method {method}', color='red')
	else:
		getattr(loggers[logger], method)(text)

	return text


# noinspection PyPep8Naming
def Print(
		*args,
		sep: str = ' ',
		end: str = '\n',
		tags: list = None,
		**kwargs
):
	silent_on_server = kwargs.pop('silent_on_server', False)
	if silent_on_server and dev_def.is_server:
		return

	tags = tags if tags is not None else []
	do_log = kwargs.pop('do_log', False)
	color = kwargs.pop('color', 'blue')
	get_time = kwargs.pop('get_time', None)
	location = kwargs.pop('location', None)
	method = kwargs.pop('method', 'info')
	logger = kwargs.pop('logger', 'print')

	if get_time is None:
		get_time = True

	text = sep.join([str(item) for item in args])
	if location:
		text = f'{location}: {text}'

	if tags:
		for i, tag in enumerate(tags):
			tags[i] = f'[{tag.upper()}]'
		text = ' '.join(tags) + ' -> ' + text

	if do_log:
		if method not in dev_def.standard_log_methods:
			Print(f'Bad logger method {method}', do_log=True, color='red')
			return
		else:
			getattr(loggers[logger], method)(text)

	if get_time:
		_time = datetime.datetime.now().strftime('%Y/%m/%d %H:%M:%S')
		text = f'{_time} -> {text}'

	if not dev_def.is_server:
		termcolor.cprint(text, end=end, color=color)
	else:
		print(text, end=end)


def curr_info(depth: int = 2, cls: str = None) -> str:
	stack = traceback.extract_stack()
	try:
		filename, lineno, function_name, code = stack[-depth]
	except:
		log('not enough stack in curr_info', location='')
		filename, lineno, function_name, code = stack[-2]

	filename = '/'.join(pathlib.Path(filename).parts[3:]).replace('.py', '')

	if cls is not None:
		return f'"{filename}".{cls}.{function_name}()[{lineno}]'
	else:
		return f'"{filename}".{function_name}()[{lineno}]'


loggers = {logger: setup_logger(logger) for logger in dev_def.logger_names}
