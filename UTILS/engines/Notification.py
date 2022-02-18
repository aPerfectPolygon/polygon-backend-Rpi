import typing as ty

import pandas as pd

from UTILS import Cache
from UTILS.dev_utils import Decorators, Log
from UTILS.dev_utils.Database.Psql import Psql
from UTILS.engines.__base__ import Notification
from UTILS.prj_utils import Defaults as prj_def

__max_body_words = 50
fb = Notification.Firebase()


@Decorators.threaded
def send(
		server_mode: str,
		receivers: ty.List[int],
		title: str,
		body: str,
		target: int = 0,
		image: str = None,
		icon: str = None,
		url: str = None,
		**kwargs
):
	"""
	Dashboard = 0
	Strategy = 1
	Support = 2
	News = 3
	Profile = 5
	Examination = 6
	Messages = 8
	Invite = 9
	CustomerClub = 10
	ExaminationQuestion = 13
	PaymentList = 14
	MyMarketWatch = 21
	Agreement = 23
	Faq = 24
	Subscription = 26
	AboutUs = 27
	Settings = 29
	SupervisorMessage = 31
	MyPayments = 34
	NotificationSettings = 35
	CandleYaar = 37
	Filter = 38
	Candlebaan = 40
	ScanResults = 42
	AddMarketWatch = 43
	PortfolioHolder = 44
	PortfolioPreview = 45
	PortfolioRead = 46
	RecommendedShares = 47
	AddStrategy = 50
	CandleNerkh = 52
	ClubActivities = 53
	ClubGifts = 54
	ClubCodes = 55
	ClubReports = 56
	
	target:
		#  Can Be -> [news, supervisor_message, candle_yaar, risk_test, subscription, scanner]
		if target == news:
			Required Keys = {
				"url": "***",
				"search": "***",  # not in version 35  (at next version it replaces "url" key) (when in-app preview is enabled)
			}
		elif target == supervisor_message:
			Required Keys = {
				"url": "***",
				"search": "***",  # not in version 35  (at next version it replaces "url" key) (when in-app preview is enabled)
			}
		elif target == candle_yaar:
			Required Keys = {
				"symbol": "***",
				"market": "***",
				"timeframe": "***",
				"indicators": ["***", "***", ...]
			}
		elif target == risk_test:
			Required Keys = {}
		elif target == subscription:
			Required Keys = {}
		elif target == scanner:
			Required Keys = {
				"market": "***",
				"mode": "***" -> Can be -> [strategy, offer]
				"name": "***"  # user strategy name or [BUY, SELL]
			}
	"""
	if not receivers:
		return
	
	if not isinstance(receivers, list):
		receivers = [receivers]
	
	important = kwargs.pop('important', False)
	inventory_all = kwargs.pop('inventory_all', False)
	do_send = kwargs.pop('do_send', True)
	args_title = kwargs.pop('args_title', [])
	args_body = kwargs.pop('args_body', [])
	
	__splitted = body.split(' ')
	if len(__splitted) > __max_body_words:
		body = ' '.join(__splitted[:__max_body_words]) + ' ...'
	
	market = kwargs.pop('market', None)
	if market:
		kwargs.update({'market': 'tse' if 'tse' in market else market})
	
	db = Psql('users_data', open=True, db_name=server_mode)
	receivers = db.read(
		'users_notification_settings',
		['main_table.uid', 'lang', 'token'],
		[('main_table.uid', 'in', receivers), ('token', 'is not', None)],
		[('inner', 'users_data.users_info', 'info', 'main_table.uid', '=', 'info.uid')]
	)
	
	multilingual = title.startswith('notifTranslate') or body.startswith('notifTranslate')
	
	result = []
	if do_send:
		if multilingual:
			__translator = Cache.translations['notification'].by_lang
			for lang in prj_def.Languages.all:
				try:
					tokens = receivers.loc[receivers.lang == lang].token.tolist()
					if not tokens:
						continue
					
					result.extend(fb.send(
						tokens,
						__translator[lang].get(title, title).format(*[
							__translator[lang].get(item, item) if item.startswith('notifTranslate') else item
							for item in args_title
						]),
						__translator[lang].get(body, body).format(*[
							__translator[lang].get(item, item) if item.startswith('notifTranslate') else item
							for item in args_body
						]),
						image, icon, url,
						verbose=not prj_def.is_server,
						target=target,
						**kwargs
					))
				except Exception as e:
					Log.log('Notification Sender Multilingual Error', exc=e)
		else:
			result = fb.send(
				receivers.token.tolist(),
				title, body,
				image, icon, url,
				verbose=not prj_def.is_server,
				target=target,
				**kwargs
			)
	else:
		result = None
	
	if inventory_all:
		uids = None
	else:
		uids = receivers.uid.tolist()
	
	db.insert(
		'users_notification_inventory',
		pd.DataFrame(
			columns=[
				'uids',
				'title',
				'body',
				'target',
				'image',
				'icon',
				'url',
				'keywords',
				'meta',
				'res',
				'important',
				'args_title',
				'args_body',
			],
			data=[[
				uids,
				title,
				body,
				target,
				image,
				icon,
				url,
				kwargs,
				kwargs.get('meta', None),
				result,
				important,
				args_title,
				args_body
			]]
		),
		custom_types={'res': 'json'},
		auto_connection=True
	)
	return result


def validate(token):
	return fb.validate(token)


@Decorators.threaded
def validate_tokens(server_mode):
	db = Psql('users_data', True, db_name=server_mode)
	
	tokens = db.read('users_notification_settings', ['uid', 'token'], [('token', 'is not', None)])
	tokens['is_valid'] = tokens.token.apply(fb.validate)
	tokens = tokens.loc[~tokens.is_valid, 'uid'].values.tolist()
	
	if tokens:
		db.update(
			'users_notification_settings',
			pd.DataFrame([[None]], columns=['token']),
			[('uid', 'in', tokens)]
		)


if __name__ == '__main__':
	send(
		prj_def.server_mode,
		[1],
		'notifTranslate_title',
		'notifTranslate_body',
		important=True,
		args_title=['notifTranslate_helloTitle'],
		args_body=['notifTranslate_helloBody']
	)
	print('ok')
	pass
