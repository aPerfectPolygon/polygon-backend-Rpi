import markdown
import pandas as pd
from requests.structures import CaseInsensitiveDict

from UTILS import engines
from UTILS.dev_utils import Log
from UTILS.dev_utils.Database.Psql import Psql
import datetime as dt
from UTILS.prj_utils import Defaults as prj_def

try:
	__log_emails = Psql('constants').read(
		'log_emails',
		['email'],
		[('is_admin', '=', True)],
		auto_connection=True
	).email.values.tolist()
except:
	__log_emails = []


def log(
		body: dict = None,
		params: dict = None,
		raw_text: str = None,
		header: dict = None,
		ip: str = None,
		url: str = None,
		
		uid: int = None,
		
		location: str = None,
		start: dt.datetime = None,
		
		response_message: str = None,
		response_result: dict = None,
		response_headers: dict = None,
		response_code: int = None,
		
		comment: str = None,
		
		request=None,
		db=None,
		**kwargs
):
	if all(item is None for item in [
		body,
		params,
		raw_text,
		header,
		ip,
		url,
		uid,
		location,
		start,
		response_message,
		response_result,
		response_headers,
		response_code,
		comment,
		request,
	]):
		Log.log('no parameters specified')
		return
	location = location if location is not None else Log.curr_info(3)
	if request is not None:
		uid = request.User.uid if hasattr(request, 'User') else uid
		body = request.input_body
		params = request.input_params
		header = request.headers
		ip = request.client_ip
		start = request.start
		url = request.path
		db = request.db.server
	
	if db is None:
		db = Psql('logs', open=True)
		auto_connection = True
	else:
		auto_connection = False
	
	if isinstance(response_headers, CaseInsensitiveDict):
		response_headers = dict(response_headers)
	
	if header and header.get('CONTENT_TYPE', '').lower().startswith('multipart'):
		for k, v in body.items():
			if v.__class__.__name__ == 'InMemoryUploadedFile' or v.__class__.__name__ == 'TemporaryUploadedFile':
				if not request or not request.info.allow_files:
					comment = f'{comment} [FILE UPLOADED] [POSSIBLE ATTACK]'
				body[k] = v.name
	
	if comment and ('[POSSIBLE ATTACK]' in comment or '[UNEXPECTED ERROR]' in comment or '[UNHANDLED]' in comment):
		engines.Email.send(
			__log_emails,
			'[POSSIBLE ATTACK]' if '[POSSIBLE ATTACK]' in str(comment) else '[UNEXPECTED ERROR]',
			html=markdown.markdown(
				f"#Main: \n"
				f"&nbsp;&nbsp;&nbsp;&nbsp; <b>Comment:</b> {comment}<br>\n"
				f"&nbsp;&nbsp;&nbsp;&nbsp; <b>Url:</b> {url}<br>\n"
				f"&nbsp;&nbsp;&nbsp;&nbsp; <b>Ip:</b> {ip}<br>\n"
				f"&nbsp;&nbsp;&nbsp;&nbsp; <b>Uid:</b> {uid}<br>\n"
				f"&nbsp;&nbsp;&nbsp;&nbsp; <b>Location:</b> {location}<br>\n"
				f"&nbsp;&nbsp;&nbsp;&nbsp; <b>Start:</b> {start}<br>\n"
				
				f"#Input: \n"
				f"&nbsp;&nbsp;&nbsp;&nbsp; <b>Raw_text:</b> {raw_text}<br>\n"
				f"&nbsp;&nbsp;&nbsp;&nbsp; <b>Params:</b> {params}<br>\n"
				f"&nbsp;&nbsp;&nbsp;&nbsp; <b>Body:</b> {body}<br>\n"
				f"&nbsp;&nbsp;&nbsp;&nbsp; <b>Header:</b> {header}<br>\n"
				
				f"#Response: \n"
				f"&nbsp;&nbsp;&nbsp;&nbsp; <b>message:</b> {response_message}<br>\n"
				f"&nbsp;&nbsp;&nbsp;&nbsp; <b>result:</b> {response_result}<br>\n"
				f"&nbsp;&nbsp;&nbsp;&nbsp; <b>headers:</b> {response_headers}<br>\n"
				f"&nbsp;&nbsp;&nbsp;&nbsp; <b>code:</b> {response_code}<br>\n"
			)
		)
	
	db.insert(
		'log',
		pd.DataFrame(
			data=[[
				body,
				params,
				raw_text,
				header,
				ip,
				url,
				uid,
				location,
				start,
				response_message,
				response_result,
				response_headers,
				response_code,
				comment,
				prj_def.ip
			]],
			columns=[
				'body',
				'params',
				'raw_text',
				'header',
				'ip',
				'url',
				'uid',
				'location',
				'start',
				'response_message',
				'response_result',
				'response_headers',
				'response_code',
				'comment',
				'server_ip'
			]
		),
		custom_types={
			'response_result': 'auto' if response_result is None else 'json'
		},
		schema='logs',
		auto_connection=auto_connection,
	)


if __name__ == '__main__':
	log(
		{'this is': 'body'},
		{'this is': 'params'},
		'this is raw text',
		{'this is': 'headers'},
		'ip:ip:ip:ip',
		'this is url',
		10,
		'this is location',
		dt.datetime.now(),
		'this is res message',
		{'this is': 'res result'},
		{'this is': 'res headers'},
		200,
		'this is res comment [UNEXPECTED ERROR]',
	
	)
