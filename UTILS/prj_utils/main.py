import os
import signal

import pandas as pd

from UTILS import Cache
from UTILS.dev_utils.Database import Psql
from UTILS.dev_utils.Objects import String
from UTILS.prj_utils import Encryptions as enc


class Encryptions:
	class V1(enc.Aes):
		def __init__(self):
			super().__init__('987fxvgklixfvzs56dvxgnhj69mdxfg5')
			self.slice_from = 2
			self.slice_len = 10
		
		def encrypt(self, message: str) -> str:
			output = super().encrypt(message)
			return f'{output[:self.slice_from]}{String.gen_random(self.slice_len)}{output[self.slice_from:]}'
		
		def decrypt(self, message: str) -> str:
			return super().decrypt(message[:self.slice_from] + message[self.slice_from + self.slice_len:])


def gunicorn_sighub():
	try:
		with open('/gunicorn_PolygonApi.pid') as f:
			os.kill(int(f.read()), signal.SIGHUP)
	except:
		pass


def get_popup(db: Psql, uid: int, lang: str, _id: int) -> dict:
	res = Cache.popup.loc[Cache.popup.id == _id].to_dict('records')
	if not res:
		raise ValueError(f'no popup found with this id `{_id}`')
	res = res[0]
	
	__translator = Cache.translations['popup'].by_lang[lang]
	if res['title'] is not None:
		res['title'] = __translator.get(res['title'], res['title'])
	if res['texts'] is not None:
		for i, item in enumerate(res['texts']):
			res['texts'][i] = __translator.get(res['texts'][i], res['texts'][i])
	if res['images'] is not None:
		for i, item in enumerate(res['images']):
			res['images'][i]['image'] = __translator.get(res['images'][i]['image'], res['images'][i]['image'])
	if res['buttons'] is not None:
		for i, item in enumerate(res['buttons']):
			res['buttons'][i]['name'] = __translator.get(res['buttons'][i]['name'], res['buttons'][i]['name'])
	if pd.isna(res['quiz_id']):
		res['quiz_id'] = None
	else:
		res['quiz_id'] = int(res['quiz_id'])
	
	db.custom(
		'update users_data.popup'
		' set users_seen  = (select array_agg(distinct e) x from unnest(users_seen || %s) e)'
		f' where id = {_id} and ({uid} = any(uids) or uids is null)',
		[[uid]],
		to_commit=True,
		to_fetch=False
	)
	
	return res


if __name__ == '__main__':
	print(Encryptions.V1().decrypt(Encryptions.V1().encrypt('hello')))
