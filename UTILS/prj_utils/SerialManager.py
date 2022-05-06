import asyncio as aio

import pandas as pd

from UTILS import Cache
from UTILS.dev_utils import Log
from UTILS.dev_utils.Database import Psql
from UTILS.dev_utils.Objects.Sockets import Serial
import typing as ty
import time as ti


class SerialManager:
	TAGS = {
		'0': 'WARNING',
		'1': 'NONE',
		'2': 'ERROR',
		'3': 'CRITICAL',
		'4': 'OUTPUT_CHANGED',
		'5': 'INPUT_CHANGED',
		'6': 'CONFIG_NEEDED',
		'7': 'OK',
		'8': 'READ_INPUT',
		'9': 'READ_OUTPUT',
	}
	LOCATIONS = {
		'0': 'NONE',
		'1': 'LISTBYTE_INIT',
		'2': 'LISTBYTE_INIT_MASK',
		'3': 'LISTBYTE_INIT_SM',
		'4': 'LISTBYTE_GETINDEX',
		'5': 'LISTBYTE_CONTAINS',
		'6': 'LISTBYTE_APPEND',
		'7': 'LISTBYTE_PUT',
		'8': 'LISTBYTE_POP',
		'9': 'LISTBYTE_REMOVE',
		'10': 'LISTBYTE_REPLACE',
		'11': 'LISTBYTE_FIND',
		'12': 'LISTBOOL_INIT',
		'13': 'LISTBOOL_INIT_MASK',
		'14': 'LISTBOOL_INIT_SM',
		'15': 'LISTBOOL_GETINDEX',
		'16': 'LISTBOOL_CONTAINS',
		'17': 'LISTBOOL_APPEND',
		'18': 'LISTBOOL_PUT',
		'19': 'LISTBOOL_POP',
		'20': 'LISTBOOL_REMOVE',
		'21': 'LISTBOOL_REPLACE',
		'22': 'LISTBOOL_FIND',
		'23': 'LISTMASK_INIT',
		'24': 'LISTMASK_INIT_SM',
		'25': 'LISTMASK_GETINDEX',
		'26': 'LISTMASK_CONTAINS',
		'27': 'LISTMASK_PUT',
		'28': 'LISTMASK_FIRST_FALSE',
		'29': 'LISTMASK_FIRST_TRUE',
		'30': 'IOMANAGER_DEBOUNCE_HANDLER_CALLBACK',
		'31': 'IOMANAGER_INPUT_ADD',
		'32': 'IOMANAGER_INPUT_READ',
		'33': 'IOMANAGER_INPUT_REMOVE',
		'34': 'IOMANAGER_OUTPUT_ADD',
		'35': 'IOMANAGER_OUTPUT_READ',
		'36': 'IOMANAGER_OUTPUT_SET',
		'37': 'IOMANAGER_OUTPUT_REMOVE',
		'38': 'IOMANAGER_IOMANAGER',
		'39': 'DEBOUNCEHANDLER_INIT_SM',
		'40': 'DEBOUNCEHANDLER_ADD',
		'42': 'SM_RECEIVER_CALLBACK_IA',
		'43': 'SM_RECEIVER_CALLBACK_RI',
		'44': 'SM_RECEIVER_CALLBACK_RO',
	}
	COMMENTS = {
		'0': 'NONE',
		'1': 'ALREADY_INIT',
		'2': 'ALREADY_MASK_INIT',
		'3': 'NOT_INIT',
		'4': 'NOT_MASK_INIT',
		'5': 'INCOMPATIBLE_SIZE',
		'6': 'ALREADY_SM_INIT',
		'7': 'INDEX_OUT_OF_RANGE',
		'8': 'NO_MASK_AND_DEFAULT_VALUE',
		'9': 'OVERFLOW',
		'10': 'NOT_FOUND',
		'11': 'NOT_AVAILABLE',
		'12': 'NOT_ANALOG',
		'13': 'ALREADY_INPUT',
		'14': 'OVERWRITING',
		'15': 'ALREADY_OUTPUT',
	}
	_io_config_io_map = {
		'DO': 0,
		'AO': 1,
		'DI': 2,
		'AI': 3
	}
	
	def __init__(self, io_callback: ty.Callable):
		self.s: Serial = None
		self.io_version = 'V0.1'
		self.io_callback = io_callback
	
	async def _wait_for_connection(self):
		self.s = None
		while True:
			try:
				self.s = await Serial.connect('/dev/ttyACM0', 9600)
			except:
				print('[CONNECTING] ...')
				await aio.sleep(1)
			else:
				break
		print('[CONNECTED]')
	
	def _translator(self, tag: str, loc: str, comment: str):
		try:
			tag = self.TAGS[tag]
		except:
			print(f'TAG NOT FOUND [{tag}]')
		try:
			loc = self.LOCATIONS[loc]
		except:
			print(f'LOC NOT FOUND [{loc}]')
		try:
			comment = self.COMMENTS[comment]
		except:
			print(f'COMMENT NOT FOUND [{comment}]')
		
		return tag, loc, comment
	
	async def serial_manager(self):
		while True:
			await self._wait_for_connection()
			while True:
				r = await self.s.receive()
				if not r:
					break
				
				try:
					_type, name, version, tag, loc, comment, pin, state = r.split('|')
				except Exception as e:
					Log.log('parsing error', exc=e)
					continue
				
				tag, loc, comment = self._translator(tag, loc, comment)
				
				if _type == 'IO':
					await self.io_callback(name, version, tag, loc, comment, int(pin), int(state))
				else:
					Log.log(f'module type {_type} not found')
	
	async def io_send_configs(self, name: str, configs: ty.List[dict]):
		sio = []
		read_inputs = []
		set_outputs = []
		for pin in configs:
			sio.append(f'{pin["pin"]}={self._io_config_io_map[pin["io"]]}')
			if pin['io'].endswith('I'):
				read_inputs.append(str(pin["pin"]))
			else:
				set_outputs.append(f'{pin["pin"]}={pin["state"]}')
		
		await self.s.send(
			f'IO|{name}|SIO{",".join(sio)}\n'
			f'IO|{name}|RI{",".join(read_inputs)}\n'
			f'IO|{name}|SO{",".join(set_outputs)}'
		)
	
	async def io_set_output(self, name: str, settings: dict):
		so = []
		for pin, state in settings.items():
			so.append(f'{pin}={state}')
		await self.s.send(f'IO|{name}|SO{",".join(so)}')
