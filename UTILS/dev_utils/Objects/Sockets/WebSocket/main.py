import asyncio as aio
import datetime as dt
import time as ti
import typing as ty

import websockets as wsock
from websockets.legacy.server import WebSocketServerProtocol

import UTILS.dev_utils.Objects.Sockets as sck_utils
from UTILS.dev_utils.Objects import String


class WebSocket(sck_utils.BasicSocket):
	def __init__(self, ws: WebSocketServerProtocol, **kwargs):
		super().__init__('WEBSOCKET', **kwargs)
		
		# main
		self.ws = ws
		self.kwargs = kwargs
		
		try:
			# noinspection PyProtectedMember
			conn = ws.reader._transport._sock
			self.host_name = conn.getsockname()
			self.peer_name = conn.getpeername()
			
			self.ip = self.peer_name[0] if self.peer_name[0] != '127.0.0.1' else self.ws.request_headers.get(
				'x-forwarded-for', self.peer_name[0])
			self.name = f'{String.gen_random(5)}_{self.ip}_{self.host_name[1]}'
		except:
			pass
	
	@property
	def is_closed(self):
		"""
		determines whether connection is closed or not
		"""
		return not self.ws.open
	
	@sck_utils.handle_error('_receive', '')
	async def _receive(self, timeout: ty.Union[float, int]) -> str:
		if timeout is None:
			return await self.ws.recv()
		else:
			return await aio.wait_for(self.ws.recv(), timeout)
	
	@sck_utils.handle_error('_send', False)
	async def _send(self, data: str) -> bool:
		await self.ws.send(data)
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
	
	async def receive(self, timeout: ty.Union[float, int] = None, **kwargs) -> str:
		return self.decrypt_if_needed(
			await self._receive(timeout)
		)
	
	async def send(self, data: str, **kwargs):
		"""
		this function uses class _queue to send `data` to client

		Parameters
		----------
		data : string to be sent to client
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
		if kwargs.pop('empty_queue', False):
			self.empty_queue()
		
		data = {
			'ts': int(ti.time()),
			'check_ts': kwargs.pop('check_ts', True),
			'data': self.encrypt_if_needed(data)
		}
		
		if kwargs.pop('add2first', False):
			self._queue = [data] + self._queue
		else:
			self._queue.append(data)
		
		if not self._queue_discharger_is_active:
			await self.queue_discharger()
		
		return True
	
	async def close(self, code=1000):
		"""
		Close the connection if it's not already closed
		"""
		await self.ws.close(code)


def serve(ip: str, port: int, callback: ty.Callable, **kwargs):
	async def __callback(ws, _):
		s = WebSocket(ws, **kwargs)
		print(f'{dt.datetime.now()} new connection {s.ip}')
		await callback(s)
	
	print(f"webSocket server listening on {ip}:{port}")
	return wsock.serve(__callback, ip, port)


async def connect(address: str, **kwargs) -> WebSocket:
	return WebSocket(await wsock.connect(address), **kwargs)
