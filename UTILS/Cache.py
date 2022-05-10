import pandas as pd

from UTILS.dev_utils.Database.Psql import Psql
from UTILS.dev_utils import Defaults as dev_def
from UTILS import dev_utils

log_emails = []
mail_servers = {}
translations = {}
home_objects = pd.DataFrame(columns=['id', 'room_id', 'name', 'type', 'module_type', 'module_io'])
modules = pd.DataFrame(columns=['id', 'type', 'name'])
modules_io = pd.DataFrame(columns=['id', 'module', 'name', 'pin', 'io'])
home_objects_api = []


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
	global home_objects
	global modules
	global modules_io
	
	update_translations()
	db = Psql('constants', open=True)
	
	# fill log_emails
	log_emails = db.read('log_emails', ['email', 'is_admin']).to_dict('records')
	
	# fill mail_servers
	mail_servers = {x['name']: x for x in db.read('mail_servers', '*').to_dict(orient='records')}
	
	# fill modules
	db.schema = 'services'
	home_objects = db.read('home_objects', ['id', 'room_id', 'name', 'type', 'module_type', 'module_io'])
	modules = db.read('modules', ['id', 'type', 'name'])
	modules_io = db.read(
		'modules',
		['io.id', 'module', 'name', 'pin', 'io'],
		[('type', '=', 'IO')],
		joins=[('inner', 'services.modules_io', 'io', 'main_table.id', '=', 'io.module')],
	)

	db.close()


try:
	fill_cache()
except Exception as e:
	print(f'fill cache error: {e.__class__.__name__}({e})')
pass
