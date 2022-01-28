import typing as ty


def bool_(data) -> ty.Optional[bool]:
	data = str(data).lower()
	if data in ['true', '1', 't']:
		return True
	if data in ['false', '0', 'f']:
		return False


def bool_with_raise(data) -> ty.Optional[bool]:
	data = str(data).lower()
	if data in ['true', '1', 't']:
		return True
	if data in ['false', '0', 'f']:
		return False
	raise RuntimeError('cant convert to bool')


def int_(data, on_error: int = 0) -> int:
	try:
		return int(data)
	except:
		return on_error


def float_(data, on_error: float = 0.0) -> float:
	try:
		return float(data)
	except:
		return on_error
