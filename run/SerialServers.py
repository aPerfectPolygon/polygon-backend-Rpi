import asyncio as aio

import pandas as pd

from SocketServers import client_handler, tracker_manager as sockets_tracker_manager, broadcast as broadcast_to_sockets
from UTILS import Cache, dev_utils
from UTILS.dev_utils import Log
from UTILS.dev_utils.Database import Psql
from UTILS.dev_utils.Objects import Json
from UTILS.dev_utils.Objects.Sockets import AioSocket
from UTILS.prj_utils.SerialManager import SerialManager


class IO:
	@staticmethod
	async def output_changed(module_id: int, pin: int, state: int, pin_id: int = None):
		"""
		take some actions when an output state changes
		"""
		if pin_id is None:
			# find pin id
			try:
				pin_id = Cache.modules_io_pins.loc[
					(Cache.modules_io_pins.module_id == module_id)
					& (Cache.modules_io_pins.pin == pin), 'id'
				].tolist()[0]
			except:
				Log.log(f'pin `{pin}` not found for module_id `{module_id}`')
				return
		
		db = Psql('home', open=True)
		
		# if pin state really changed
		old_state = db.read('modules_io_pins', ['state'], [('id', '=', pin_id)]).state.tolist()[0]
		if state == old_state:
			return
		# update new pin state in db
		db.update('modules_io_pins', pd.DataFrame([[state]], columns=['state']), [('id', '=', pin_id)])
		
		# get a list of objects that are assigned to this pin
		objects_data = Cache.objects_output.loc[Cache.objects_output.module_pin_id == pin_id].to_dict('records')
		
		# remove waiter tags (fast loop)
		for _object in objects_data:
			waiter.event_occured(f'IO|change|{_object["object_id"]}')
		
		# get trackers that are tracking thease objects
		for _object in objects_data:
			# if object state really changed
			old_state = db.read('objects', ['state'], [('id', '=', _object['object_id'])]).state.tolist()[0]
			if state == old_state:
				continue
			# update new object state in db
			db.update('objects', pd.DataFrame([[state]], columns=['state']), [('id', '=', _object['object_id'])])
			
			trackers = sockets_tracker_manager.get_trackers(_object['object_id']).id.tolist()
			if trackers:
				await broadcast_to_sockets(
					Json.encode({'type': 'changed', 'data': {'object': _object['object_id'], 'state': state}}),
					trackers
				)
				sockets_tracker_manager.untrack(tag=_object['object_id'], auto_added=True)
		db.close()
	
	@staticmethod
	async def input_changed(module_id: int, pin: int, state: int, pin_id: int = None):
		"""
		take some actions when an input state changes
		"""
		if pin_id is None:
			# find pin id
			try:
				pin_id = Cache.modules_io_pins.loc[
					(Cache.modules_io_pins.module_id == module_id)
					& (Cache.modules_io_pins.pin == pin), 'id'
				].tolist()[0]
			except:
				Log.log(f'pin `{pin}` not found for module_id `{module_id}`')
				return
		
		db = Psql('home', open=True)
		
		# if pin state really changed
		old_state = db.read('modules_io_pins', ['state'], [('id', '=', pin_id)]).state.tolist()[0]
		if state == old_state:
			return
		# update new pin state in db
		db.update('modules_io_pins', pd.DataFrame([[state]], columns=['state']), [('id', '=', pin_id)])
		
		# get a list of objects that are assigned to this pin
		objects_data = Cache.objects_input.loc[Cache.objects_input.module_pin_id == pin_id].to_dict('records')
		
		# remove waiter tags
		for _object in objects_data:
			waiter.event_occured(f'IO|change|{_object["object_id"]}')
		
		# get trackers that are tracking thease objects
		for _object in objects_data:
			# if object state really changed
			old_state = db.read('objects', ['state'], [('id', '=', _object['object_id'])]).state.tolist()[0]
			if state == old_state:
				continue
			# update new object state in db
			db.update('objects', pd.DataFrame([[state]], columns=['state']), [('id', '=', _object['object_id'])])
			
			trackers = sockets_tracker_manager.get_trackers(_object['object_id']).id.tolist()
			if trackers:
				await broadcast_to_sockets(
					Json.encode({'type': 'changed', 'data': {'object': _object['object_id'], 'state': state}}),
					trackers
				)
				sockets_tracker_manager.untrack(tag=_object['object_id'], auto_added=True)
		
		# get objects that are controlled by this pin
		objects = Cache.objects_output.loc[Cache.objects_output.controlled_by == pin_id]
		if not objects.empty:
			# fast loop to assign waiter tags
			for object_id in objects.object_id.drop_duplicates():
				waiter.wait_for_event(f'IO|change|{object_id}', 1)
			
			# get module_id and pin number of that objects and send new state to them
			for module in Cache.modules_io_pins.loc[
				Cache.modules_io_pins.id.isin(objects.module_pin_id.tolist())
			].groupby('module_id')['pin'].apply(list).to_dict('records'):
				for _pin in module['pin']:
					await serial_manager.io_set_output(module['module_name'], {_pin: state})
		
		db.close()
	
	@staticmethod
	async def callback(name: str, version: str, tag: str, loc: str, comment: str, pin: int, state: int):
		print(name, version, tag, loc, comment, pin, state)
		
		try:
			module_data = Cache.modules.loc[
				(Cache.modules.name == name) & (Cache.modules.type == 'IO')
				].to_dict('records')[0]
		except:
			Log.log(f'io module {name} not found')
			return
		
		if tag == 'CONFIG_NEEDED':
			await serial_manager.io_send_configs(
				name,
				Psql('services').read(
					'modules_io_pins',
					['pin', 'io', 'state'],
					[('module_id', '=', module_data['id'])],
					auto_connection=True
				).to_dict('records')
			)
		elif tag == 'READ_INPUT':
			await IO.input_changed(module_data['id'], pin, state)
		elif tag == 'READ_OUTPUT':
			await IO.output_changed(module_data['id'], pin, state)
		elif tag == 'OUTPUT_CHANGED':
			await IO.output_changed(module_data['id'], pin, state)


async def module_waiter_timeout(event):
	module_type, tag, object_id = event.split('|')
	object_id = int(object_id)
	trackers = sockets_tracker_manager.get_trackers(object_id).id.tolist()
	if not trackers:
		return
	
	if module_type == 'IO':
		old_state = Psql('home').read(
			'objects', ['state'], [('id', '=', object_id)], auto_connection=True
		).state.tolist()[0]
		await broadcast_to_sockets(
			Json.encode({'type': 'cant_change', 'data': {'object': object_id, 'state': old_state}}),
			trackers
		)
		sockets_tracker_manager.untrack(tag=object_id, auto_added=True)
	else:
		Log.log(f'event {event} unknown module type')
		return


if __name__ == '__main__':
	serial_manager = SerialManager(IO.callback)
	waiter = dev_utils.WaitForEvents(async_cb=module_waiter_timeout)
	
	loop = aio.get_event_loop()
	loop.run_until_complete(aio.gather(
		serial_manager.serial_manager(),
		waiter.aio_loop_check_events(),
		AioSocket.serve('0.0.0.0', 1234, client_handler, serial_manager=serial_manager, waiter=waiter)
	))
	loop.run_forever()
