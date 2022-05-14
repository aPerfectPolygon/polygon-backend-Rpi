import os
import pathlib
import sys

sys.path.append(str(pathlib.Path(__file__).resolve().parent.parent.parent.parent))

from UTILS import dev_utils
from UTILS.dev_utils import Log
from UTILS.prj_utils import Defaults as prj_def
import pandas as pd

from UTILS.dev_utils.Database.Psql.main import Psql
from UTILS.prj_utils.FirstSetup import git_puller, sync_venv


__prj_root = str(prj_def.project_root)
files_translations = __prj_root[:__prj_root.find('Project/')] + 'Files/translations.xlsx'
if os.path.exists(files_translations):
	# translations = pd.read_excel(files_translations)
	translations = pd.read_excel('translations.xlsx')  # removeme
else:
	translations = pd.read_excel('translations.xlsx')
	

def supervisor_config():
	dev_utils.supervisor_create_or_restart_service(
		'PolygonApi',
		'PolygonApi',
		'root',
		f'sh {prj_def.project_root}/run/api/gunicorn/service.bash',
		prj_def.project_root,
		f'{prj_def.project_root}/Logs/IRFX-Api/log.log',
		f'{prj_def.project_root}/Logs/IRFX-Api/log.log',
	)


def server_first_setup():
	db = Psql('', open=True)
	if db.conn is None:
		db.create_user_with_default_user()
		db.create_db()
		db = Psql('', open=True)
		if db.conn is None:
			Log.log('cant create Database')
			return
	
	# region constants
	db.schema = 'constants'
	db.create_schema()
	
	if not db.table_exists('mail_servers'):
		db.create(
			'mail_servers',
			{
				'name': 'varchar(100)',
				'server': 'varchar(100)',
				'port': 'integer ',
				'address': 'varchar(100)',
				'password': 'varchar(100)',
			},
		)
		
		db.insert(
			'mail_servers',
			pd.DataFrame(
				columns=['name', 'server', 'port', 'address', 'password'],
				data=[
					['polygon', 'smtp.gmail.com', 587, 'aperfectpolygon@gmail.com', '0m1dr#@A'],
					['log', 'smtp.gmail.com', 587, 'aperfectpolygon@gmail.com', '0m1dr#@A'],
					['attack', 'smtp.gmail.com', 587, 'aperfectpolygon@gmail.com', '0m1dr#@A'],
					['gmail', 'smtp.gmail.com', 587, 'aperfectpolygon@gmail.com', '0m1dr#@A'],
				]
			)
		)
	
	if not db.table_exists('log_emails'):
		db.create(
			'log_emails',
			{
				'email': 'varchar',
				'is_admin': 'bool default false',
			},
		)
		db.insert(
			'log_emails',
			pd.DataFrame(
				columns=['email', 'is_admin'],
				data=[
					['elyasnz1999@gmail.com', True],
				]
			)
		)
	
	if db.table_exists('translations'):
		db.drop('translations')
	
	db.create(
		'translations',
		{
			'groups': 'text[]',
			'key': 'varchar unique',
			**{lang: 'varchar' for lang in prj_def.Languages.all}
		},
		ts_columns='created',
	)
	db.insert('translations', translations)
	
	# endregion
	
	# region services
	db.schema = 'services'
	db.create_schema()
	
	db.create(
		'mail_stack',
		{
			'id': 'serial primary key',
			'receivers': 'text[]',
			'subject': 'varchar',
			'body': 'varchar',
			'template': 'varchar',
			'template_content': 'json',
			'mail_server': 'varchar',
			'kwargs': 'json',
		},
	)
	
	if not db.table_exists('modules'):
		db.create(
			'modules',
			{
				'id': 'serial primary key',
				'type': 'varchar',
				'name': 'varchar',
			},
		)
		db.insert('modules', pd.read_excel('modules.xlsx'))
	
	if not db.table_exists('modules_io'):
		db.create(
			'modules_io',
			{
				'id': 'serial primary key',
				'module': 'integer references services.modules(id) on delete cascade',
				'pin': 'integer',
				'io': 'varchar(2)',
				'state': 'integer default 0',
			},
			group_unique=['module', 'pin']
		)
		db.insert('modules_io', pd.read_excel('modules_io.xlsx'))

	if not db.table_exists('home_objects'):
		db.create(
			'home_objects',
			{
				'id': 'serial primary key',
				'room_id': 'integer references services.home_objects(id) on delete cascade',
				'name': 'varchar',
				'type': 'varchar',
				'module_type': 'varchar',
				'module_io': 'integer references services.modules_io(id) on delete cascade',
			},
			group_unique=['room_id', 'name']
		
		)
		db.insert('home_objects', pd.read_excel('home_objects.xlsx'))

	# endregion
	
	# region logs
	db.schema = 'logs'
	db.create_schema()
	
	db.create(
		'log',
		{
			'id': 'serial primary key',
			'url': 'varchar(500) default null',
			'body': 'json default null',
			'params': 'json default null',
			'raw_text': 'varchar(500) default null',
			'header': 'json default null',
			'ip': 'varchar default null',
			'uid': 'integer  default null',
			'location': 'varchar(500) default null',
			'response_message': 'varchar(500) default null',
			'response_result': 'json default null',
			'response_headers': 'json default null',
			'response_code': 'integer  default null',
			'comment': 'varchar(500) default null',
			'start': 'timestamp default null',
			'server_ip': 'varchar(100) default null',
		},
		ts_columns='created',
	)
	
	# endregion
	
	# region users_data
	db.schema = 'users_data'
	db.create_schema()
	create_users_data = True
	if not db.table_exists('account_account'):
		root = str(prj_def.project_root).replace('\\', '/')
		manage_py = f'{root}/manage.py'
		
		if os.path.exists(manage_py):
			os.system(f'. {root}/venv/bin/activate && python {manage_py} makemigrations && python {manage_py} migrate')
		else:
			Log.log('could not find manage.py file to create migrations')
			create_users_data = False
	
	if create_users_data:
		db.create(
			'tokens_email',
			{
				'id': 'serial primary key',
				'uid': 'integer  references users_data.account_account(id) on delete cascade',
				'token': 'varchar(30)',
				'is_used': 'boolean default false',
			},
			ts_columns='created'
		)
		
		db.create(
			'tokens_forget_pass',
			{
				'id': 'serial primary key',
				'uid': 'integer  references users_data.account_account(id) on delete cascade',
				'token': 'varchar(30)',
				'is_used': 'boolean default false',
				'is_verified': 'boolean default false',
			},
			ts_columns='created'
		)
		
		for platform in ['App', 'Web', 'Test']:
			db.create(
				f'users_token_{platform}',
				{
					'id': 'serial primary key',
					'uid': 'integer  unique references users_data.account_account(id) on delete cascade',
					'token': 'varchar(50)',
				},
				ts_columns='created'
			)
		
		db.create(
			'users_info',
			{
				'id': 'serial primary key',
				'uid': 'integer  references users_data.account_account(id) on delete cascade',
				
				'lang': "varchar(10) default 'en-us'",
				'auth_email': "boolean default false",
			},
			ts_columns=['created', 'modified']
		)
		
		db.create(
			'users_notification_settings',
			{
				'id': 'serial primary key',
				'uid': 'integer unique references users_data.account_account(id) on delete cascade',
				
				'token_app': 'varchar(200) default null',
				'token_web': 'varchar(200) default null',
				'token_test': 'varchar(200) default null',
			},
			ts_columns='created'
		)
		
		db.create(
			'users_unread_counts',
			{
				'id': 'serial primary key',
				'uid': 'integer unique references users_data.account_account(id) on delete cascade',
				
				'notification': "integer default 0",
			},
			ts_columns='created'
		)
		
		db.create(
			'users_notification_inventory',
			{
				'id': 'serial primary key',
				'uids': 'int[]',
				'title': 'varchar(100)',
				'body': 'varchar(500)',
				'target': 'int default 0',
				'image': 'varchar(500)',
				'icon': 'varchar(500)',
				'url': 'varchar(500)',
				'keywords': 'json',
				'meta': 'varchar(1000)',
				'users_seen': 'integer[] default array[]::integer[]',
				'res': 'json',
				'important': 'boolean default false',
				'args_title': 'text[] default array[]::text[]',
				'args_body': 'text[] default array[]::text[]',
			},
			ts_columns='created',
			set_index=True,
		)
		
		db.create(
			'users_notification_quiz',
			{
				'id': 'serial primary key',
				'uids': 'int[]',
				'topic': 'varchar(50)',
				'title': 'varchar(100)',
				'body': 'varchar(500)',
				'target': 'int default 0',
				'image': 'varchar(500)',
				'res': 'json',
				'choices': 'text[] default array[]::text[]',
				'right_choice': 'integer',
				'users_right': 'integer[] default array[]::integer[]',
				'users_wrong': 'integer[] default array[]::integer[]',
			},
			ts_columns='created',
			set_index=True,
		)
	
	# endregion
	
	db.close()


if __name__ == '__main__':
	args = sys.argv
	if 'Supervisor' in args:
		supervisor_config()
	if 'VenvSync' in args:
		sync_venv.sync()
	if 'GitPull' in args:
		git_puller.pull()
	
	server_first_setup()
