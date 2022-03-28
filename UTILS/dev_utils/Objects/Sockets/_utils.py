import functools
import typing as ty
from asyncio.exceptions import TimeoutError

from websockets.exceptions import ConnectionClosedError, ConnectionClosedOK

from UTILS.dev_utils import Log
from UTILS.dev_utils.Objects import String

PACKETS_TIME_TO_LIVE = 5  # in seconds


def check_encryption_method(do_check: bool, enc):
	"""
	Parameters
	----------
	do_check : if false -> enc will be returned immediately
	enc : must be a class with `encrypt` and `decrypt` methods that accepts str and returns str
	"""
	if not do_check:
		return enc
	
	if not callable(getattr(enc, 'encrypt', None)):
		raise ValueError('encrypt not Callable')
	
	data = 'TestEncrypt'
	encrypted = enc.encrypt(data)
	if not isinstance(encrypted, str):
		raise ValueError('bad encrypt output type')
	
	if not callable(getattr(enc, 'decrypt', None)):
		raise ValueError('decrypt not Callable')
	
	decrypted = enc.decrypt(encrypted)
	if not isinstance(decrypted, str):
		raise ValueError('bad decrypt output type')
	if decrypted != data:
		raise ValueError('bad encrypt-decrypt pair')
	
	return enc


def handle_error(func_name, on_error):
	cur_info = Log.curr_info()
	
	def decorator(func):
		@functools.wraps(func)
		async def wrapper(*args, **kwargs):
			try:
				return await func(*args, **kwargs)
			except TimeoutError:
				pass
			except ConnectionClosedError:
				pass
			except ConnectionClosedOK:
				pass
			except ConnectionResetError:
				pass
			except ConnectionAbortedError:
				pass
			except Exception as e:
				Log.log(f'{func_name} unexpected', location=cur_info, exc=e)
			return on_error
		
		return wrapper
	
	return decorator


class BasicSocket:
	def __init__(self, mode, **kwargs):
		self.uid = None
		
		# class variables
		self._queue = []
		self._queue_discharger_is_active = False
		
		self.mode = mode  # SOCKET, WEBSOCKET
		
		# names
		self.host_name = [None, None, None]
		self.peer_name = [None, None, None]
		self.name = f'{String.gen_random(5)}'
		
		self.ip = None
		
		# encryption
		self.check_encryption_method = kwargs.pop('check_encryption_method', False)
		encryption = kwargs.pop('encryption', None)
		if encryption:
			self.encryption = encryption
		else:
			self._encryption = None
	
	def __repr__(self):
		return str(self.ip)
	
	def __str__(self):
		return str(self.ip)
	
	def empty_queue(self):
		self._queue = []
	
	@property
	def encryption(self):
		return self._encryption
	
	@encryption.setter
	def encryption(self, enc):
		self._encryption = check_encryption_method(self.check_encryption_method, enc)
	
	def decrypt_if_needed(self, data: str):
		if self._encryption is not None and data:
			try:
				return self._encryption.decrypt(data)
			except:
				return f'DECRYPTION_ERROR -> {data}'
		return data
	
	def encrypt_if_needed(self, data: str):
		if self._encryption is not None:
			return self._encryption.encrypt(data)
		return data
	
	@property
	def is_closed(self):
		raise NotImplementedError
	
	async def _send(self, data: str) -> bool:
		raise NotImplementedError
	
	async def _receive(self, timeout: ty.Union[float, int]) -> str:
		raise NotImplementedError
	
	async def queue_discharger(self):
		raise NotImplementedError
	
	async def send(self, data: str, **kwargs):
		raise NotImplementedError
	
	async def receive(self, timeout: ty.Union[float, int] = None, **kwargs) -> str:
		raise NotImplementedError
	
	async def close(self, code=1000):
		raise NotImplementedError
