import pandas as pd

from UTILS.dev_utils.Database.Psql import Psql
from UTILS.dev_utils import Defaults as dev_def
from UTILS import dev_utils
from UTILS.dev_utils.Objects import List

log_emails = []
mail_servers = {}
translations = {}
popup = pd.DataFrame(columns=['id', 'title', 'texts', 'images', 'buttons', 'quiz_id'])
api_popups = pd.DataFrame(columns=['id', 'uids', 'api'])

# home
modules = pd.DataFrame(columns=['id', 'type', 'name'])
modules_io_pins = pd.DataFrame(columns=['id', 'module_id', 'module_name', 'pin', 'io'])
rooms = pd.DataFrame(columns=['id', 'room_id', 'name'])
objects = pd.DataFrame(columns=['id', 'room_id', 'room_name', 'module_pin_id', 'state', 'name', 'type'])
objects_input = pd.DataFrame(columns=[
	'id', 'room_id', 'room_name', 'object_id', 'module_pin_id',
	'object_state', 'object_name', 'object_type', 'invert', 'is_momentary'
])
objects_output = pd.DataFrame(columns=[
	'id', 'room_id', 'room_name', 'object_id', 'module_pin_id',
	'object_state', 'object_name', 'object_type', 'controlled_by'
])


def update_translations():
	global translations
	__trans = Psql('constants').read('translations', ['groups', 'key'] + dev_def.Languages.all, auto_connection=True)
	for lang in dev_def.Languages.all:
		__trans[lang] = __trans[lang].str.replace('\\n', '\n', regex=False).str.replace('\\t', '\t', regex=False)
	for gp, data in __trans.explode('groups').groupby('groups'):
		translations.update(
			{gp: dev_utils.MultiLingual(data.drop(columns=['groups']).set_index('key').to_dict('index'))})


def fill_cache():
	global log_emails
	global mail_servers
	global popup
	global api_popups
	
	global rooms
	global modules
	global modules_io_pins
	global objects
	global objects_input
	global objects_output
	
	update_translations()
	db = Psql('constants', open=True)
	
	# fill log_emails
	log_emails = db.read('log_emails', ['email', 'is_admin']).to_dict('records')
	
	# fill mail_servers
	mail_servers = {x['name']: x for x in db.read('mail_servers', '*').to_dict(orient='records')}
	
	# fill popup
	_popup = db.read(
		'popup',
		['id', 'title', 'texts', 'images', 'buttons', 'quiz_id', 'is_active', 'uids', 'apis'],
		schema='users_data'
	)
	popup = _popup[['id', 'title', 'texts', 'images', 'buttons', 'quiz_id']]
	api_popups = _popup.loc[_popup.is_active, ['id', 'uids', 'apis']].explode('apis').rename(columns={'apis': 'api'})
	api_popups['uids'] = '|' + api_popups.uids.apply(lambda x: List.join(x, '|')) + '|'
	
	# fill modules
	db.schema = 'home'
	modules = db.read('modules', ['id', 'type', 'name'])
	modules_io_pins = db.read(
		'modules_io_pins', ['main_table.id', 'module_id', 'name as module_name', 'pin', 'io'],
		joins=[('inner', 'home.modules', 'm', 'main_table.module_id', '=', 'm.id')]
	)
	rooms = db.read('rooms', ['id', 'room_id', 'name'])
	objects = db.read(
		'objects', ['main_table.id', 'main_table.room_id', 'r.name as room_name', 'module_pin_id', 'state', 'main_table.name', 'type'],
		joins=[('inner', 'home.rooms', 'r', 'main_table.room_id', '=', 'r.id')]
	)
	objects_input = db.read(
		'objects_input', [
			'main_table.id', 'o.room_id', 'r.name as room_name', 'object_id', 'module_pin_id',
			'state as object_state', 'o.name as object_name', 'type as object_type', 'invert', 'is_momentary'
		],
		joins=[
			('inner', 'home.objects', 'o', 'main_table.object_id', '=', 'o.id'),
			('inner', 'home.rooms', 'r', 'o.room_id', '=', 'r.id'),
		]
	)
	objects_output = db.read(
		'objects_output', [
			'main_table.id', 'o.room_id', 'r.name as room_name', 'object_id', 'module_pin_id',
			'state as object_state', 'o.name as object_name', 'type as object_type', 'controlled_by'
		],
		joins=[
			('inner', 'home.objects', 'o', 'main_table.object_id', '=', 'o.id'),
			('inner', 'home.rooms', 'r', 'o.room_id', '=', 'r.id'),
		]
	)
	
	db.close()


try:
	fill_cache()
except Exception as e:
	print(f'fill cache error: {e.__class__.__name__}({e})')
pass
