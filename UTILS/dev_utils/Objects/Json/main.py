import json
import typing as ty

import numpy as np

from UTILS.dev_utils import Log


class NpEncoder(json.JSONEncoder):
	def default(self, obj):
		if isinstance(obj, np.integer):
			return int(obj)
		elif isinstance(obj, np.floating):
			return float(obj)
		elif isinstance(obj, np.bool_):
			return bool(obj)
		elif isinstance(obj, np.ndarray):
			return obj.tolist()
		else:
			return super(NpEncoder, self).default(obj)


def encode(data, None_as_null=True, **kwargs) -> ty.Optional[str]:
	try:
		if data is None and not None_as_null:
			return
		return json.dumps(data, cls=NpEncoder, **kwargs)
	except Exception as _e:
		Log.log('[UNEXPECTED ERROR]', location=Log.curr_info(3), exc=_e)
		return '""'


def decode(data, **kwargs):
	__do_raise = kwargs.pop('do_raise', False)
	__silent = kwargs.pop('silent', False)
	try:
		return json.loads(str(data), **kwargs)
	except Exception as _e:
		if 'Unexpected UTF-8 BOM' in str(_e):
			try:
				return json.loads(str(data).encode().decode('utf-8-sig'))
			except:
				pass

		if __do_raise:
			raise
		
		if not __silent:
			Log.log('[UNEXPECTED ERROR]', location=Log.curr_info(3), exc=_e)
		return {}
