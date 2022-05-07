"""
About:
-------
	| client connects
	| wait for client to send `token`(SeeAlso: Input Models)
	|
	| ** note that when tracking anything you must untrack it after you`re done working with it **
	|
	| sample send: "{"type": "authenticate", "data": "TOKEN"}[END]"
	| sample receive: "{"type": "sample", "data": ["xxx"]}[END]"
	|
	| type `changed` will be sent
	|   * after detecting a change in objects that are being tracked
	| type `changed_error` will be sent
	|   * after detecting an error in changing an output


Input Models:
--------------
	| authenticate client (4S Timeout)
	| {
	| 	"type": "authenticate",
	| 	"data": "TOKEN"
	| }
	| -----------------------------------------------
	| track individual object
	| {
	| 	"type": "track",
	| 	"data": [1, 2, 3]  # list of object ids
	| }
	| -----------------------------------------------
	| untrack individual object
	| {
	| 	"type": "untrack",
	| 	"data": [1, 2, 3]  # list of object ids (can be null to untrack everything)
	| }
	| -----------------------------------------------
	| untrack individual object
	| {
	| 	"type": "change",
	| 	"data": [[1, 100], [2, 0]]  # list of (object_id, state)
	| }
	| -----------------------------------------------
	| disconnect gracefully
	| {
	| 	"type": "disconnect",
	| 	"data": null  # must be null
	| }
	| -----------------------------------------------



Output Models:
--------------
	| detected a change in objects that are being tracked
	| {
	| 	"type": "changed",
	| 	"data": {"object": int, "state": int}
	| }
	| -----------------------------------------------
	| detected an error in changing an output
	| {
	| 	"type": "changed_error",
	| 	"data": {"object": int, "state": int}
	| }
	| -----------------------------------------------

"""
import asyncio as aio
import time as ti
import typing as ty
import datetime as dt

import pandas as pd

import UTILS.dev_utils.Objects.Sockets as sck_utils
from UTILS import dev_utils, Cache
from UTILS.dev_utils import Log
from UTILS.dev_utils.Database.Psql import Psql
from UTILS.dev_utils.Database.main import log as db_log
from UTILS.dev_utils.Objects import Json
from UTILSD import Defaults as djn_def

sockets = pd.DataFrame(columns=['socket', 'name', 'uid'])
tracker_manager = dev_utils.TrackerManager()
maximum_user_active_connections = 20


class Messages:
	bad_token = '[BAD TOKEN]'
	unexpected = '[UNEXPECTED ERROR]'
	bad_input = '[BAD INPUT]'
	connect = '[CONNECT]'
	disconnect = '[DISCONNECT]'
	search = '[SEARCH]'
	cancel_search = '[CANCEL SEARCH]'
	payload = '[PAYLOAD]'
	too_many_connections = '[TOO MANY CONNECTIONS]'


def socket_log(
		socket: sck_utils.BasicSocket,
		message: str,
		comment: ty.Optional[str],
		code: int,
		response_result: dict = None,
		raw_text: str = None,
		input_data: dict = None,
		no_print=False,
		**kwargs
):
	location = Log.curr_info(3)
	if not no_print:
		Log.log(f'{code} {message} {comment}', location=location)
	
	db_log(
		location=location,
		
		url=socket.mode,
		uid=socket.uid,
		ip=str(socket.ip),
		
		body=input_data,
		comment=comment,
		raw_text=raw_text,
		response_message=message,
		
		response_code=code,
		response_result=response_result,
		**kwargs
	)


async def authenticate(socket: sck_utils.BasicSocket, data: str) -> ty.Optional[int]:
	"""
	** timeout -> 4S **
	receive a packet from socket and treat it as `authenticate` request

	Example: {
		"type": "authenticate",
		"data": "TOKEN"
	}

	| check if timeout occurred
	| check_data()
	| check if type == 'authenticate'
	| check if token exists
	| check if token expired

	Returns
	--------
	user_id if ok else None
	"""
	data = check_data(socket, data)
	if not data:
		return
	
	if data['type'] != 'authenticate':
		socket_log(socket, Messages.bad_token, f'bad type {data["type"]}', 401, input_data=data)
		return
	
	platform = data.get('platform', None)
	if platform is None:
		socket_log(socket, Messages.bad_input, f'platform not specified', 400, input_data=data)
		return
	
	if platform not in djn_def.Platforms.all:
		socket_log(socket, Messages.bad_input, f'bad platform {platform}', 400, input_data=data)
		return
	
	db_data = Psql('users_data').read(
		f'users_token_{platform}',
		['uid', 'created'],
		[('token', '=', data['data'])],
		auto_connection=True
	).to_dict('records')
	if not db_data:
		socket_log(socket, Messages.bad_token, 'token not found', 401, input_data=data)
		return
	
	db_data = db_data[0]
	uid = db_data['uid']
	socket.uid = uid
	
	if (ti.time() - db_data['created'].timestamp()) > getattr(djn_def.TokenExpiration, platform.lower()):
		socket_log(socket, Messages.bad_token, 'token expired', 401, input_data=data)
		return
	
	socket_log(socket, Messages.connect, None, 200, no_print=True, input_data=data)
	
	return uid


def check_data(socket: sck_utils.BasicSocket, data: str, **kwargs) -> ty.Optional[dict]:
	"""
	| check if is json serializable
	| check if has `type` and `data` keys
	| check if has `type` is str
	"""
	decoded_data = Json.decode(data)
	if not decoded_data:
		socket_log(socket, Messages.bad_input, 'not json serializable', 400, raw_text=data, **kwargs)
		return
	data = decoded_data
	
	if data.get('type', 'NO') == 'NO' or data.get('data', 'NO') == 'NO':
		socket_log(socket, Messages.bad_input, 'bad keys', 400, input_data=data, **kwargs)
		return
	
	if not isinstance(data['type'], str):
		socket_log(socket, Messages.bad_input, '`type` must be string', 400, input_data=data, **kwargs)
		return
	
	return data


async def client_handler(socket: sck_utils.BasicSocket):
	global sockets
	
	data = await socket.receive(4)
	if not data:
		socket_log(socket, Messages.bad_token, 'token not sent', 401)
		await socket.close()
		return
	
	uid = await authenticate(socket, data)
	if uid is None:
		await socket.close(1003)
		return
	
	# remove and close if this uid has previous connections
	user_active_connections = sockets.loc[sockets.uid == uid].to_dict('records')
	if len(user_active_connections) >= maximum_user_active_connections:
		for item in user_active_connections[:-(maximum_user_active_connections - 1)]:
			sockets = sockets.loc[sockets.name != item['name']]
			socket_log(item['socket'], Messages.too_many_connections, None, 400)
			tracker_manager.untrack(item['name'])
			await item['socket'].close()
	
	sockets = sockets.append(pd.DataFrame([[socket, socket.name, uid]], columns=['socket', 'name', 'uid']))
	
	try:
		while True:
			data = await socket.receive()
			if not data:
				break
			
			data = check_data(socket, data)
			if not data:
				break
			
			if data['type'] == 'track':
				_home_object_ids = Cache.home_objects.id.tolist()
				_has_err = False
				for object_id in data['data']:
					if object_id not in _home_object_ids:
						socket_log(socket, Messages.bad_input, f'bad object_id {object_id}', 400, input_data=data)
						_has_err = True
						break
					tracker_manager.track(socket.name, object_id)
				if _has_err:
					break
			elif data['type'] == 'untrack':
				if data['data'] is None:
					tracker_manager.untrack(socket.name)
				else:
					for object_id in data['data']:
						tracker_manager.untrack(socket.name, object_id)
			elif data['type'] == 'change':
				_has_err = False
				for object_id, state in data['data']:
					object_data = Cache.home_objects.loc[Cache.home_objects.id == object_id].to_dict('records')
					if not object_data:
						socket_log(socket, Messages.bad_input, f'bad object_id {object_id}', 400, input_data=data)
						_has_err = True
						break
						
					object_data = object_data[0]
					if object_data['module_type'] == 'IO' and object_data['module_io'] is not None:
						module_data = Cache.modules_io.loc[
							Cache.modules_io.id == object_data['module_io']
						].to_dict('records')
						if not module_data:
							socket_log(
								socket,
								Messages.bad_input,
								f'object related module not found {object_id}',
								400,
								input_data=data
							)
							_has_err = True
							break
						module_data = module_data[0]
						
						tracker_manager.track(socket.name, object_id, auto_added=True)
						await socket.kwargs['serial_manager'].io_set_output(
							module_data['name'], {module_data['pin']: state}
						)
					else:
						socket_log(
							socket,
							Messages.bad_input,
							f'object bad configuration {object_id}',
							400,
							input_data=data
						)
						_has_err = True
						break
				if _has_err:
					break
			elif data['type'] == 'disconnect':
				socket_log(socket, Messages.disconnect, None, 200, input_data=data, no_print=True)

				break
	except Exception as e:
		socket_log(socket, Messages.unexpected, f'{e.__class__.__name__}({e})', 400)
	
	if not data or data.get('type', None) != 'disconnect':
		socket_log(socket, Messages.disconnect, None, 200, no_print=True)
	
	sockets = sockets.loc[sockets.name != socket.name]
	tracker_manager.untrack(socket.name)
	
	await socket.close()


async def broadcast(message: str, socket_names=None, socket_uids=None):
	if socket_names:
		s = sockets.loc[sockets.name.isin(socket_names)]
	elif socket_uids:
		s = sockets.loc[sockets.uid.isin(socket_uids)]
	else:
		s = sockets.copy()
	
	if s.empty:
		return
	
	for socket in s.drop_duplicates(['name']).socket.tolist():
		await socket.send(message)
	