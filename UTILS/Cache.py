from UTILS.dev_utils.Database.Psql import Psql

log_emails = []
mail_servers = {}


def fill_cache():
	global log_emails
	global mail_servers
	db = Psql('constants', open=True)

	# fill log_emails
	log_emails = db.read('log_emails', ['email', 'is_admin']).to_dict('records')
	
	# fill mail_servers
	mail_servers = {x['name']: x for x in db.read('mail_servers', '*').to_dict(orient='records')}
	
	db.close()

try:
	fill_cache()
except Exception as e:
	print(f'fill cache error: {e.__class__.__name__}({e})')
pass
