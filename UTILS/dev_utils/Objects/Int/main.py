import math
import random

from UTILS.dev_utils import Log


def gen_random(length: int = None) -> int:
	length = length if length is not None else 5
	
	range_start = 10 ** (length - 1)
	range_end = (10 ** length) - 1
	return random.randint(range_start, range_end)


def round_up(number: int, n_digits_from_left: int) -> int:
	_len = len(str(number))
	if n_digits_from_left > _len:
		Log.log(f"n_digits_from_left `{n_digits_from_left}` > number length `{_len}`")
		return number
	
	factor = 10 ** (_len - n_digits_from_left)
	number = math.ceil(number / factor) * factor
	
	return number


def round_dn(number: int, n_digits_from_left: int) -> int:
	_len = len(str(number))
	if n_digits_from_left > _len:
		Log.log(f"n_digits_from_left `{n_digits_from_left}` > number length `{_len}`")
		return number
	
	factor = 10 ** (_len - n_digits_from_left)
	number = math.floor(number / factor) * factor
	
	return number
