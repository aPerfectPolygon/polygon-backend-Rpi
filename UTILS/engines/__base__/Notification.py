import copy
import typing as ty
import uuid

from UTILS import dev_utils
from UTILS.dev_utils import Log
from UTILS.dev_utils.Objects import List
from UTILS.prj_utils import Defaults as prj_def
from urllib.parse import urlencode


class Firebase:
	headers = {'Authorization': f'key={prj_def.fcm_api_key}'}

	class Topic:
		@staticmethod
		def assign(topic: str, tokens: ty.List[str]):
			for r in List.split(tokens, count_per_item=1000):
				dev_utils.safe_request(
					'post',
					'https://iid.googleapis.com/iid/v1:batchAdd',
						{'to': topic, 'registration_tokens': r},
					headers=Firebase.headers,
					expected_codes=[200]
				)

		@staticmethod
		def unassign(topic: str, tokens: ty.List[str]):
			for r in List.split(tokens, count_per_item=1000):
				dev_utils.safe_request(
					'post',
					'https://iid.googleapis.com/iid/v1:batchRemove',
					{'to': topic, 'registration_tokens': r},
					headers=Firebase.headers,
					expected_codes=[200]
				)

	@staticmethod
	def _prepare_data(
			title: str,
			body: str,
			image: str = None,
			icon: str = None,
			url: str = None,
			choices: ty.List[str] = None,
			web_url: str = None,
			**kwargs
	) -> dict:
		data = {
			'title': title, 'body': body,
			'server_id': int(uuid.uuid1().int >> 64) % 10000000000,
			'data': {  # for web
				'url': None
			}
		}
		quiz_id = kwargs.pop('quiz_id', None)
		target = kwargs.pop('target', None)

		if target is not None:
			data.update({'target': target})
		if image:
			data.update({'image': image})
			data['data'].update({'image': image})
		if icon:
			data.update({'icon': icon})
			data['data'].update({'icon': icon})
		if quiz_id:
			data.update({'quiz_id': quiz_id})
			data['data'].update({'quiz_id': quiz_id})
		if web_url:
			data['data']['url'] = f'{web_url}?{urlencode({**kwargs, **{"n": "true"}})}'
		if url:
			data.update({'url': url})
			data['data']['url'] = url
		if choices:
			data.update({'choices': choices})
			data.update({'actions': [{'title': choice, 'action': f'{i}'} for i, choice in enumerate(choices)]})
		data.update(kwargs)
		return data

	def send(
			self,
			receivers: ty.List[str],
			title: str,
			body: str,
			image: str = None,
			icon: str = None,
			url: str = None,
			verbose: bool = False,
			choices: ty.List[str] = None,
			web_url: str = None,
			**kwargs
	) -> list:
		"""
		*** Body Can Not More than 2KB ***
		image :
			big picture
		icon:
			small picture
		"""
		result = []

		receivers = List.drop_selected(receivers, [None, ''])
		if not receivers:
			return result

		data = self._prepare_data(title, body, image, icon, url, choices, web_url, **kwargs)
		if prj_def.disable_engine_notification:
			print(f'[DISABLED] Notification to {receivers} \n\t {data}')
			return result

		for r in List.split(receivers, count_per_item=1000):
			body_to_send = {'data': data, 'registration_ids': r}
			if verbose:
				print(body_to_send)
			result.append(
				dev_utils.safe_request(
					'post',
					'https://fcm.googleapis.com/fcm/send',
					body_to_send,
					headers=self.headers,
					expected_codes=200
				).Json
			)

		return result

	def send2topic(
			self,
			topic: str,
			title: str,
			body: str,
			image: str = None,
			icon: str = None,
			url: str = None,
			verbose: bool = False,
			choices: ty.List[str] = None,
			web_url: str = None,
			**kwargs
	) -> dict:
		"""
		*** Body Can Not More than 2KB ***
		image :
			big picture
		icon:
			small picture
		"""
		data = self._prepare_data(title, body, image, icon, url, choices, web_url, **kwargs)

		if prj_def.disable_engine_notification:
			print(f'[DISABLED] Notification to topic {topic} \n\t {data}')
			return
		
		body_to_send = {'data': data, 'to': topic}
		if verbose:
			print(body_to_send)
		return dev_utils.safe_request(
			'post',
			'https://fcm.googleapis.com/fcm/send',
			body_to_send,
			headers=self.headers,
			expected_codes=200
		).Json

	def validate(self, tokens: ty.Union[ty.List[str], str]) -> ty.List[ty.Optional[str]]:
		"""
		validate tokens and return a list of new tokens
			invalid tokens will be replaced by `None` in the response
		"""
		if isinstance(tokens, str):
			tokens = [tokens]

		response = copy.deepcopy(tokens)
		not_none_tokens_with_index = [[i, item] for i, item in enumerate(tokens) if item is not None]
		if not_none_tokens_with_index:
			for t in List.split(not_none_tokens_with_index, count_per_item=1000):
				try:
					res = dev_utils.safe_request(
						'post',
						'https://fcm.googleapis.com/fcm/send',
						{'registration_ids': [item for i, item in t], 'dry_run': True},
						headers=self.headers,
						expected_codes=[200]
					)
					if res.is_success and res.status_code == 200:
						for i, (token_index, token) in enumerate(t):
							response[token_index] = token if 'error' not in res.Json['results'][i] else None
				except Exception as e:
					Log.log('Firebase Token Validation Error', exc=e)
		return response


if __name__ == '__main__':
	fb = Firebase()
	# fb.send(
	# 	[
	# 		'd0GA2vaPQqW-H8K6NQz5JH:APA91bFaKkLbP4fOxnd3Z43Zhkvjs9iFBqZUlBCv7dyyyyVh72o2yff5GC7GZJ992WIUTqXSEOQsZzOc1xa2AvGasMvHod_hZroWYFDGeAZfOotHkytVuWSxSSDRmRB__fca9V0vvA54'
	# 	],
	# 	'Title',
	# 	'body',
	# 	verbose=True
	# )
	print(fb.validate([
		'ecJbJMOk0340sH1mZuNpEm:APA91bGyGAqlFFs-65gknPigB5cbBtioMkEF5UAXNZa9cMhSGJuMFuZeL64ZbklG4Q_NB0kKfKa5q5zBgjiAnJB7llhHYh3nz4gE9qZLiFbvKyJsxU4IbOxcJX1f8RWG6jiWgxZvFyyT',
		'dk4Bxh7RS6SH4iQq0nAlqx:APA91bGl9YMIcSMlpyDK5BJL6ndywEma2-LjcvV-seI48DpUUEgzr80vs0rNg1MG_GGuIgjSNIAKPmy0L3X987NRvub9rJYd8su6TC2SvaMW2pxiNgWj8VeWPdaaDb8ewg6TJ_YFokZV'
	]))

	pass
