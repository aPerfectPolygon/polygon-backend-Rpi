import typing as ty

from UTILS import dev_utils
from UTILS.dev_utils import Decorators, Log
from UTILS.prj_utils import Defaults as prj_def


class Kavehnegar:
	url = f'https://api.kavenegar.com/v1/{prj_def.kavenegar_key}/verify/lookup.json'
	
	@Decorators.threaded
	def _send(self, body, rec, callback: ty.Callable = None) -> bool:
		res = dev_utils.safe_request(
			'get',
			self.url,
			params={**body, **{'receptor': rec}},
			use_proxy=False,
			expected_codes=200,
		)
		if res.is_success and res.status_code == 200:
			if res.Json['return']['status'] != 200 or res.Json['entries'][0]['status'] > 5:
				Log.log(f'[SMS API ERROR] {rec} {res.json}')
			else:
				if callback:
					callback(rec, body['template'])
				else:
					print(f'SMS sent {rec} {body["template"]}')
				return True
		else:
			Log.log('Kavehnegar not responding')
		return False
	
	def send(
			self,
			receivers: ty.List[str],
			template: str,
			var1: str = None,
			var2: str = None,
			var3: str = None,
			callback: ty.Callable = None
	):
		body = {'template': template, 'type': 'sms'}
		if var1 is not None:
			body.update({'token': str(var1).replace(' ', '\u200c')})
		if var2 is not None:
			body.update({'token2': str(var2).replace(' ', '\u200c')})
		if var3 is not None:
			body.update({'token3': str(var3).replace(' ', '\u200c')})
		
		if prj_def.disable_engine_sms:
			print(f'[DISABLED] SMS to {receivers} \n\t {body}')
			if callback:
				for rec in receivers:
					callback(rec, template)
			return True
		
		for receiver in receivers:
			if receiver.startswith('+'):
				receiver = f'00{receiver[1:]}'
			self._send(body, receiver, callback)


if __name__ == '__main__':
	Kavehnegar().send(
		['+989196864660'],
		'social2',
		'NAME',
		'LINK'
	)
	print('ok')
