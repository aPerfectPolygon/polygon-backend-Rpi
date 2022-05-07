import pandas as pd

from UTILS import Cache
from UTILS.dev_utils import Log
from SocketServers import client_handler, sockets as connected_sockets, tracker_manager as sockets_tracker_manager, \
	broadcast as broadcast_to_sockets
from UTILS.dev_utils.Database import Psql
from UTILS.dev_utils.Objects import Json
from UTILS.dev_utils.Objects.Sockets import AioSocket
from UTILS.prj_utils.SerialManager import SerialManager
import asyncio as aio


async def io_serial_handler(name: str, version: str, tag: str, loc: str, comment: str, pin: int, state: int):
	print(name, version, tag, loc, comment, pin, state)
	if name not in Cache.modules_io.name.tolist():
		Log.log(f'io module {name} not found')
		return
	
	if tag == 'CONFIG_NEEDED':
		await serial_manager.io_send_configs(
			name,
			Psql('services').read(
				'modules_io',
				['pin', 'io', 'state'],
				[('module', '=', Cache.modules_io.loc[Cache.modules_io.name == name, 'id'].tolist()[0])],
				auto_connection=True
			).to_dict('records')
		)
	elif tag == 'READ_INPUT':
		Psql('services').update(
			'modules_io',
			pd.DataFrame([[state]], columns=['state']),
			[
				('module', '=', Cache.modules_io.loc[Cache.modules_io.name == name, 'id'].tolist()[0]),
				('pin', '=', pin),
			],
			auto_connection=True
		)
	elif tag == 'READ_OUTPUT':
		Psql('services').update(
			'modules_io',
			pd.DataFrame([[state]], columns=['state']),
			[
				('module', '=', Cache.modules_io.loc[Cache.modules_io.name == name, 'id'].tolist()[0]),
				('pin', '=', pin),
			],
			auto_connection=True
		)
	elif tag == 'OUTPUT_CHANGED':
		# get objects assigned to this pin
		pin_id = Cache.modules_io.loc[
			(Cache.modules_io.name == name)
			& (Cache.modules_io.pin == pin)
		].id.tolist()
		if not pin_id:
			Log.log(f'pin `{pin}` not found')
			return
		
		object_ids = Cache.home_objects.loc[
			(Cache.home_objects.module_type == 'IO')
			& (Cache.home_objects.module_io == pin_id[0])
		].id.tolist()
		
		if not pin_id:
			Log.log(f'pin `{pin}` not assigned to any object')
			return
		
		# get trackers that are tracking thease objects
		for object_id in object_ids:
			trackers = sockets_tracker_manager.get_trackers(object_id).id.tolist()
			if trackers:
				await broadcast_to_sockets(
					Json.encode({'type': 'changed', 'data': {'object': object_id, 'state': state}}),
					trackers
				)
				sockets_tracker_manager.untrack(tag=object_id, auto_added=True)


if __name__ == '__main__':
	serial_manager = SerialManager(io_serial_handler)
	
	loop = aio.get_event_loop()
	loop.run_until_complete(aio.gather(
		serial_manager.serial_manager(),
		AioSocket.serve('0.0.0.0', 1234, client_handler, serial_manager=serial_manager)
	))
	loop.run_forever()
