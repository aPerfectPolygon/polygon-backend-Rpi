import asyncio as aio
import datetime as dt
import time as ti
import typing as ty
from asyncio.streams import StreamReader, StreamWriter

import UTILS.dev_utils.Objects.Sockets as sck_utils
from UTILS.dev_utils import Log
from UTILS.dev_utils.Objects import String

# `BUFF_SIZE` cant be less than `MARKER` length
MARKER = '[END]\n'
BUFF_SIZE = 8192
MAX_RECEIVE = 1024 * 1024 * 1


class AioSocket(sck_utils.BasicSocket):
	def __init__(self, reader_writer: ty.Tuple[StreamReader, StreamWriter], **kwargs):
		super().__init__('SOCKET', **kwargs)
		
		# class variables
		self._receive_left_over = ''
		self._max_receive = MAX_RECEIVE
		if kwargs.pop('no_receive_limit', False):
			self._max_receive = None
		
		# main
		self.reader, self.writer = reader_writer
		
		# noinspection PyUnresolvedReferences, PyProtectedMember
		self.conn = self.reader._transport._sock
		
		# names
		self.host_name = self.conn.getsockname()
		self.peer_name = self.conn.getpeername()
		self.ip = self.peer_name[0]
		self.name = f'{String.gen_random(5)}_{self.ip}_{self.host_name[1]}'
	
	@property
	def is_closed(self):
		"""
		determines whether connection is closed or not
		"""
		try:
			return self.conn.fileno() < 0 or not self.conn.getsockname() or not self.conn.getpeername()
		except:
			return False
	
	@sck_utils.handle_error('_receive', '')
	async def _receive(self, timeout: ty.Union[float, int]) -> str:
		if timeout is None:
			data = await self.reader.read(BUFF_SIZE)
		else:
			data = await aio.wait_for(self.reader.read(BUFF_SIZE), timeout)
		
		if data:
			return data.decode()
		return ''
	
	@sck_utils.handle_error('_send', False)
	async def _send(self, data: str, drain=True) -> bool:
		self.writer.write(data.encode())
		if drain:
			await self.writer.drain()
		return True
	
	async def queue_discharger(self):
		"""
		| set `_queue_discharger_is_active` to True
			-> to make sure that only one instance of this function will be active simultaneously
		| while data is available in _queue send it and close the connection if any error occurs
		| set `_queue_discharger_is_active` to False
		"""
		if self._queue_discharger_is_active:
			return
		
		self._queue_discharger_is_active = True
		
		while self._queue:
			data = self._queue.pop(0)
			
			# check data timestamp
			if data['check_ts'] and int(ti.time()) - data['ts'] > sck_utils.PACKETS_TIME_TO_LIVE:
				continue
			
			if not await self._send(data['data']):
				await self.close()
				break
		
		self._queue_discharger_is_active = False
	
	async def receive(self, timeout: ty.Union[float, int] = None, marker: str = None) -> str:
		"""
		receive data from client until `marker` is seen

		** this function also could be done with `read_until` method of `self.reader`
		since the `recv()` function of `socket` only supports receiving in chunks of a limited size (`BUFF_SIZE`)
			these chunks should be stored in a temporary list (`total_data`)

		since we are storing chunks to a list and also waiting to find `marker` in it there could be 2 scenarios
			1: [the easy one] `marker` will be all available in last chunk
				-> 'Something[MARKER]'
			2: `marker` will be splitted between last two chunks
				-> 'Something[MAR', 'KER]'

		since we are using `marker` to determine end of packet there could be 2 scenarios:
			** the `_receive_left_over` will be parsed in the next call of `receive()`
			1: [the easy one] `marker` will be the last character in packet without anything after it
				-> 'Something[MARKER]' -> `_receive_left_over` will be ''
			2: because of high-speed sending it's not far from mind that the packets collapse with each other
				-> 'Something[MARKER]SomethingElse[MARKER]' -> `_receive_left_over` will be 'SomethingElse[MARKER]'

		Parameters
		----------
		timeout : (seconds)
		marker : to recognize end of packet with

		Returns
		-------
		str(response) if ok else ''

		"""
		if marker is None:
			marker = MARKER
		total_data = self._receive_left_over
		
		while True:
			#  check if `marker` was present in `total_data`
			if marker in total_data:
				break
			
			# check if _max_receive is reached
			if self._max_receive and len(total_data) > self._max_receive:
				Log.log('MAX_RECEIVE reached')
				await self.close()
				self._receive_left_over = ''
				return ''
			
			# receive from socket
			_data = await self._receive(timeout)
			total_data += _data
			if not _data:
				break
		
		index = total_data.find(marker)
		self._receive_left_over = total_data[index + len(marker):]
		return self.decrypt_if_needed(total_data[:index])
	
	async def send(self, data: str, marker: str = None, **kwargs) -> bool:
		"""
		this function uses class _queue to send `data` to client

		Parameters
		----------
		data : string to be sent to client
		marker : to recognize end of packet with
		kwargs :
			empty_queue -> if True: the _queue will be empty
			add2first -> if True: `data` will be added to beginning of _queue
			check_ts -> if True: queued data will not be sent to client if it's older than `PACKETS_TIME_TO_LIVE` seconds

		Returns
		-------
		False if socket is closed else True
		"""
		if self.is_closed:
			return False
		if marker is None:
			marker = MARKER
		if kwargs.pop('empty_queue', False):
			self.empty_queue()
		
		data = {
			'ts': int(ti.time()),
			'check_ts': kwargs.pop('check_ts', True),
			'data': self.encrypt_if_needed(data) + marker
		}
		
		if kwargs.pop('add2first', False):
			self._queue = [data] + self._queue
		else:
			self._queue.append(data)
		
		if not self._queue_discharger_is_active:
			await self.queue_discharger()
		
		return True
	
	async def close(self):
		"""
		Close the connection if it's not already closed
		"""
		self._queue = []
		if not self.is_closed:
			print(f'closed {self}')
			self.writer.close()


def serve(ip: str, port: int, callback: ty.Callable, **kwargs):
	async def __callback(reader: StreamReader, writer: StreamWriter):
		s = AioSocket((reader, writer), **kwargs)
		print(f'{dt.datetime.now()} new connection {s.ip}')
		await callback(s)
	
	print(f"socket server listening on {ip}:{port}")
	return aio.start_server(__callback, ip, port)


async def connect(ip: str, port: int, **kwargs) -> AioSocket:
	return AioSocket(
		await aio.open_connection(ip, port),
		**kwargs
	)
