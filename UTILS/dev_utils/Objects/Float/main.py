from UTILS.dev_utils.Objects import Convertors
from UTILS.dev_utils import Log
import typing as ty


def truncate(f: float, n: int) -> float:
	_x = 10 ** n
	return int(Convertors.float_(f) * _x) / _x


def divide(f, s, on_error=0.0, ndigits: int = None) -> float:
	try:
		output = f / s
		if ndigits is not None:
			output = round(output, ndigits)
		return output
	except ZeroDivisionError:
		return on_error
	except Exception as e:
		Log.log('[UNEXPECTED ERROR]', Log.curr_info(), exc=e)
		return on_error


def limit_digits(f: float, limit=8) -> ty.Union[int, float]:
	try:
		str_f = format(float(f), f'.{limit}f')
		s_int, s_float = str_f.split('.')
		if len(s_int) >= limit:
			return int(s_int)
		
		return float(str_f[:limit + 1])
	except Exception as e:
		Log.log(f'limit_digits error {f} {type(f)}', exc=e)
		return f
