import typing as ty
import uuid

from UTILS import dev_utils
from UTILS.dev_utils.Objects import List
from UTILS.prj_utils import Defaults as prj_def


class Firebase:
	headers = {'Authorization': f'key={prj_def.fcm_api_key}'}
	
	def send(
			self,
			receivers: ty.List[str],
			title: str,
			body: str,
			image: str = None,
			icon: str = None,
			url: str = None,
			verbose: bool = False,
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
		
		data = {
			'title': title, 'body': body,
			'server_id': int(uuid.uuid1().int >> 64) % 10000000000,
		}
		if image:
			data.update({'image': image})
		if icon:
			data.update({'icon': icon})
		if url:
			data.update({'url': url})
		data.update(kwargs)
		
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
	
	def validate(self, token):
		res = dev_utils.safe_request(
			'post',
			'https://fcm.googleapis.com/fcm/send',
			{'registration_ids': [token]},
			headers=self.headers,
			expected_codes=200
		)
		if res.is_success and res.status_code == 200:
			print(res.Json)
			return res.Json.get('success', 0) == 1
		return False


if __name__ == '__main__':
	fb = Firebase()
	fb.send(
		[
			'd0GA2vaPQqW-H8K6NQz5JH:APA91bFaKkLbP4fOxnd3Z43Zhkvjs9iFBqZUlBCv7dyyyyVh72o2yff5GC7GZJ992WIUTqXSEOQsZzOc1xa2AvGasMvHod_hZroWYFDGeAZfOotHkytVuWSxSSDRmRB__fca9V0vvA54'
		],
		'Title',
		'body',
		verbose=True
	)
	print(fb.validate(
		'd0GA2vaPQqW-H8K6NQz5JH:APA91bFaKkLbP4fOxnd3Z43Zhkvjs9iFBqZUlBCv7dyyyyVh72o2yff5GC7GZJ992WIUTqXSEOQsZzOc1xa2AvGasMvHod_hZroWYFDGeAZfOotHkytVuWSxSSDRmRB__fca9V0vvA54'))
	
	pass
