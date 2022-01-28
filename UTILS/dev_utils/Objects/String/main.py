import math
import random as ra
import re
import string
import time as ti
import typing as ty


def split(data: str, **kwargs) -> list:
	"""
	split string to list of packets

	kwargs -> (count_per_item: int, items_count: int)

	count_per_item
		specify maximum length of each item of output
		'xxxyyyzzz', count_per_item = 2  ->  ['xx', 'xy', 'yy', 'zz', 'z']

	items_count
		specify maximum length of output
		'xxxyyyzzz', items_count = 2  ->  ['xxxyy', 'yzzz']

	"""
	count_per_item = kwargs.pop('count_per_item', None)
	items_count = kwargs.pop('items_count', None)
	
	if not any((count_per_item, items_count,)):
		raise Exception('at least one of ["count_per_item", "items_count"] must be specified')
	
	_len = len(data)
	if items_count:
		count_per_item = math.ceil(_len / items_count)
	
	return [data[i:i + count_per_item] for i in range(0, _len, count_per_item)]


def replace(data: str, to_replace: ty.Union[list, tuple], replacement: str = None) -> str:
	"""replace all occurrences of all items in 'to_replace' with 'replacement'"""
	replacement = replacement if replacement is not None else ''
	
	for item in to_replace:
		data = data.replace(item, replacement)
	return data


def replace2(text: str, mapping: ty.Union[dict, list], **kwargs) -> str:
	"""
	replace all occurrences of 'mapping' keys with their values
	[HIGH SPEED]
	"""
	if type(mapping) is list:
		mapping = dict.fromkeys(mapping, kwargs.pop('replacement', ''))
	pattern = "|".join(map(re.escape, mapping.keys()))
	return re.sub(pattern, lambda m: mapping[m.group()], str(text))


def rreplace(data: str, to_replace: str, replacement: str) -> str:
	"""
	right replace

	replace last occurrence of 'to_replace' with 'replacement'
	"""
	index = data.rfind(to_replace)
	to_change = data[:index] + replacement + data[index + len(to_replace):]
	return to_change


def lreplace(data: str, to_replace: str, replacement: str) -> str:
	"""
	left replace

	replace first occurrence of 'to_replace' with 'replacement'
	"""
	index = data.find(to_replace)
	to_change = data[:index] + replacement + data[index + len(to_replace):]
	return to_change


def r_handle_illegal_chars(to_check, **kwargs) -> bool:
	"""
	specify to remove or return False on finding illegal characters in 'to_check'

	illegal characters are divided to 3 groups -> [main, ultra, injection_avoid]

	:return
		if False
			none off specified characters were found
		if True
			illegal characters found
	"""
	
	ultra = kwargs.pop('ultra', False)
	injection_avoid = kwargs.pop('injection_avoid', False)
	except_keys = kwargs.pop('except_keys', [])
	remove = kwargs.pop('remove', False)
	
	main = [
		"\\'", '/', ':', '*', '\\"',
		'<', '>', '|', '~', '#', '%',
		'&', '+', '{', '}', '\\-', '\\n',
		'\\t',
	]
	_ultra = [
		'(', ')', ';', '\\[', '\\]',
		',', '!', '@', '#', '$',
		'%', '^', '&', '+', '=',
		'.'
	]
	_injection_avoid = [
		'(', ')', '{', '}', '\\[', '\\]',
		',', '!', '?', '%', '@', '#',
		'%', '^', '&', '\\-', '+', '=',
		"'", '\\"', '%', '.', ';', '$',
		'/', '\\\\'
	]
	if ultra:
		main += _ultra
	if injection_avoid:
		main += _injection_avoid
	
	# remove 'except_keys' items from main
	for item in except_keys:
		if item in main:
			main.remove(item)
	
	if remove:
		for ch in main:
			to_check.replace(ch, '')
		return False
	else:
		_re = '[' + ''.join(main) + ']'
		res = bool(re.search(_re, to_check))
		return not res


def handle_illegal_chars(to_check, **kwargs) -> bool:
	"""
	specify to remove or return False on finding illegal characters in 'to_check'

	illegal characters are divided to 3 groups -> [main, ultra, injection_avoid]

	:return
		if False
			none off specified characters were found
		if True
			illegal characters found
	"""
	
	ultra = kwargs.pop('ultra', False)
	injection_avoid = kwargs.pop('injection_avoid', False)
	replace_illegals = kwargs.pop('replace_illegals', False)
	except_keys = kwargs.pop('except_keys', [])
	
	main = [
		"'", '/', ':', '*', '"',
		'<', '>', '|', '~', '#', '%',
		'&', '+', '{', '}', '-', '\n',
		'\t',
	]
	_ultra = [
		'(', ')', ';', '[', ']',
		',', '!', '@', '#', '$',
		'%', '^', '&', '+', '=',
		'.'
	]
	_injection_avoid = [
		'(', ')', '{', '}', '[', ']',
		',', '!', '?', '%', '@', '#',
		'%', '^', '&', '-', '+', '=',
		"'", '"', '%', '.', ';', '$',
		'/', '\\'
	]
	if ultra:
		main += _ultra
	
	if injection_avoid:
		main += _injection_avoid
	
	for item in except_keys:
		if item in main:
			main.remove(item)
	
	for ch in main:
		if ch in to_check:
			if not replace_illegals:
				return False
			else:
				to_check.replace(ch, '')
	
	return True


def gen_random(length: int = None, choices: str = None) -> str:
	if choices is None:
		choices = string.ascii_lowercase
	if length is None:
		length = ra.randint(10, 20)
		
	return ''.join(ra.choice(choices) for i in range(length))


def gen_random_with_timestamp() -> str:
	return f'{str(int(ti.time()))[-5:]}{ra.randint(100, 1000)}'


def cleanup(text: str) -> str:
	return replace2(text, {'\u200c': ' ', '  ': ' '}).strip()


def has_upper(text: str) -> bool:
	return any(x.isupper() for x in text)
