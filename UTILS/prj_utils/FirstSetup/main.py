import os
import pathlib
import sys

from UTILS.dev_utils import Log
from UTILS.prj_utils import Defaults as prj_def
import pandas as pd

sys.path.append(str(pathlib.Path(__file__).resolve().parent.parent.parent.parent))

from UTILS.dev_utils.Database.Psql.main import Psql, Databases
from UTILS.prj_utils.FirstSetup import git_puller, sync_venv


def server_first_setup():
	db = Psql('', open=True)
	if db.conn is None:
		print(
			f'run this query -> *create database "{Databases["default"]["name"]}" with owner "{Databases["default"]["user"]}"*')
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
		
		for platform in ['App', 'Test']:
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
				
				'avatar': "varchar(100) default 'media/static/male/1.png'",
				'auth_email': "boolean default false",
			},
			ts_columns=['created', 'modified']
		)
		
	# endregion
	
	db.close()


if __name__ == '__main__':
	args = sys.argv
	if 'VenvSync' in args:
		sync_venv.sync()
	if 'GitPull' in args:
		git_puller.pull()
	
	server_first_setup()
