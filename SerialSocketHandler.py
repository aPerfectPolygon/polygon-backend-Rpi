import pandas as pd

from UTILS import Cache
from UTILS.dev_utils import Log
import UTILS.dev_utils.Objects.Sockets as sck_utils
from UTILS.dev_utils.Database import Psql
from UTILS.prj_utils.SerialManager import SerialManager
import asyncio as aio


async def client_handler(socket: sck_utils.BasicSocket):
	while True:
		data = await socket.receive()
		if not data:
			return
		print(data)


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


if __name__ == '__main__':
	serial_manager = SerialManager(io_serial_handler)
	
	loop = aio.get_event_loop()
	loop.run_until_complete(aio.gather(
		serial_manager.serial_manager(),
		# AioSocket.serve('0.0.0.0', 1234, client_handler)
	))
	loop.run_forever()
