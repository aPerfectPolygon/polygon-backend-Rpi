import typing as ty

import pandas as pd

from UTILS import Cache
from UTILS.dev_utils import Decorators, Log
from UTILS.dev_utils.Database.Psql import Psql
from UTILS.engines.__base__ import Notification
from UTILS.prj_utils import Defaults as prj_def

__max_body_words = 50
fb = Notification.Firebase()
web_url_translator = {}


@Decorators.threaded
def send(
		receivers: ty.Union[ty.List[int], int],
		title: str,
		body: str,
		target: int = 0,
		image: str = None,
		icon: str = None,
		url: str = None,
		web_url: str = None,
		choices: ty.List[str] = None,
		**kwargs
):
	if not receivers:
		return
	
	if not isinstance(receivers, list):
		receivers = [receivers]
	
	important = kwargs.pop('important', False)
	inventory_all = kwargs.pop('inventory_all', False)
	do_send = kwargs.pop('do_send', True)
	args_title = kwargs.pop('args_title', [])
	args_body = kwargs.pop('args_body', [])
	right_choice = kwargs.pop('right_choice', None)
	if not web_url:
		web_url = web_url_translator.get(target, prj_def.host)

	__splitted = body.split(' ')
	if len(__splitted) > __max_body_words:
		body = ' '.join(__splitted[:__max_body_words]) + ' ...'
	
	market = kwargs.pop('market', None)
	if market:
		kwargs.update({'market': 'tse' if 'tse' in market else market})
	
	db = Psql('users_data', open=True)
	receivers = db.custom(
		'select uns.uid, lang, array[token_app, token_web, token_test] as token, (token_app is not null or token_web is not null or token_test is not null) as has_token '
		'from users_data.users_notification_settings uns inner join users_data.users_info ui on uns.uid = ui.uid '
		'where ui.uid in %s',
		[tuple(receivers)], to_commit=False, to_fetch=True
	)
	
	multilingual = title.startswith('notifTranslate') or body.startswith('notifTranslate')
	is_quiz = bool(choices)
	if is_quiz:
		multilingual = multilingual or any(choice.startswith('notifTranslate') for choice in choices)
		quiz_id = int(db.insert(
			'users_notification_quiz',
			pd.DataFrame(
				columns=[
					'title',
					'body',
					'target',
					'image',
					'choices',
					'right_choice',
				],
				data=[[
					title,
					body,
					target,
					image,
					choices,
					right_choice
				]]
			),
			returning=['id']
		).id[0])
		kwargs.update({'quiz_id': quiz_id})

	result = []
	if do_send:
		if any(receivers.has_token):
			if multilingual:
				__translator = Cache.translations['notification'].by_lang
				for lang in prj_def.Languages.all:
					try:
						tokens = receivers.loc[receivers.lang == lang].token.explode().tolist()
						if not tokens:
							continue

						_choices = {}
						if is_quiz:
							_choices = {'choices': choices}

						result.extend(fb.send(
							tokens,
							__translator[lang].get(title, title).format(*[
								__translator[lang].get(item, item) for item in args_title
							]),
							__translator[lang].get(body, body).format(*[
								__translator[lang].get(item, item) for item in args_body
							]),
							image, icon, url,
							verbose=not prj_def.is_server,
							target=target,
							web_url=web_url,
							**_choices,
							**kwargs,
						))
					except Exception as e:
						Log.log('Notification Sender Multilingual Error', exc=e)
			else:
				_choices = {}
				if is_quiz:
					_choices = {'choices': choices}

				result = fb.send(
					receivers.token.explode().tolist(),
					title, body,
					image, icon, url,
					verbose=not prj_def.is_server,
					target=target,
					web_url=web_url,
					**_choices,
					**kwargs
				)
	else:
		result = None
	
	if inventory_all:
		uids = None
	else:
		uids = receivers.uid.tolist()

	if is_quiz:
		# noinspection PyUnboundLocalVariable
		db.update(
			'users_notification_quiz',
			pd.DataFrame([[uids, result]], columns=['uids', 'res']),
			[('id', '=', quiz_id)],
			custom_types={'res': 'json'},
			auto_connection=True
		)
	else:
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


class Topic:
	@staticmethod
	@Decorators.threaded
	def assign(topic: str, tokens: ty.List[str]):
		Notification.Firebase.Topic.assign(f'/topics/{topic}', tokens)

	@staticmethod
	@Decorators.threaded
	def unassign(topic: str, tokens: ty.List[str]):
		Notification.Firebase.Topic.unassign(f'/topics/{topic}', tokens)

	@staticmethod
	@Decorators.threaded
	def send(
			server_mode: str,
			topic: str,
			title: str,
			body: str,
			target: int = 0,
			image: str = None,
			icon: str = None,
			url: str = None,
			web_url: str = None,
			choices: ty.List[str] = None,
			**kwargs
	):
		right_choice = kwargs.pop('right_choice', None)
		if not web_url:
			web_url = web_url_translator.get(target, prj_def.host)

		is_quiz = bool(choices)
		_choices = {}
		if is_quiz:
			db = Psql('users_data', open=True, db_name=server_mode)
			quiz_id = int(db.insert(
				'users_notification_quiz',
				pd.DataFrame(
					columns=[
						'title',
						'topic',
						'body',
						'image',
						'choices',
						'right_choice',
					],
					data=[[
						title,
						topic,
						body,
						image,
						choices,
						right_choice
					]]
				),
				returning=['id']
			).id[0])
			kwargs.update({'quiz_id': quiz_id})
			_choices.update({'choices': choices})

		result = fb.send2topic(
			f'/topics/{topic}',
			title, body,
			image, icon, url,
			verbose=not prj_def.is_server,
			target=target,
			web_url=web_url,
			**_choices,
			**kwargs
		)

		if is_quiz:
			# noinspection PyUnboundLocalVariable
			db.update(
				'users_notification_quiz',
				pd.DataFrame([[result]], columns=['res']),
				[('id', '=', quiz_id)],
				custom_types={'res': 'json'},
				auto_connection=True
			)

		return result


def validate(token: str):
	if not token:
		return True
	return fb.validate([token])


@Decorators.threaded
def validate_tokens():
	db = Psql('users_data', True)

	tokens = db.read(
		'users_notification_settings',
		['uid', 'token_app', 'token_web', 'token_test'],
	).set_index('uid')
	tokens['token_app'] = fb.validate(tokens.token_app.tolist())
	tokens['token_web'] = fb.validate(tokens.token_web.tolist())
	tokens['token_test'] = fb.validate(tokens.token_test.tolist())

	db.multiple_update('users_notification_settings', tokens)
	db.close()


if __name__ == '__main__':
	# send(
	# 	prj_def.server_mode,
	# 	[1, 2],
	# 	'title',
	# 	'body',
	# 	choices=['test1', 'test2', 'test3'],
	# 	important=True,
	# 	target=1
	# )
	# send2topic(
	# 	prj_def.server_mode,
	# 	'FARIBORZx',
	# 	'title',
	# 	'body',
	# 	choices=['test'],
	# )
	validate_tokens('IRFX')
	print('ok')
	pass
