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
		trackers = sockets_tracker_manager.get_trackers('OUTPUT_CHANGED', str(pin)).id.tolist()
		if trackers:
			print(trackers)
			await broadcast_to_sockets(
				Json.encode({'type': 'event', 'data': {'event': 'OUTPUT_CHANGED', 'pin': str(pin), 'state': state}}),
				trackers
			)
			sockets_tracker_manager.untrack(tag='OUTPUT_CHANGED', value=str(pin), auto_added=True)
			print(sockets_tracker_manager.get_trackers('OUTPUT_CHANGED', str(pin)).id.tolist())


if __name__ == '__main__':
	serial_manager = SerialManager(io_serial_handler)
	
	loop = aio.get_event_loop()
	loop.run_until_complete(aio.gather(
		serial_manager.serial_manager(),
		AioSocket.serve('0.0.0.0', 1234, client_handler, serial_manager=serial_manager)
	))
	loop.run_forever()
