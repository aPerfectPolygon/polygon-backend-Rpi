import typing as ty

from UTILS import Cache
from UTILS.engines.__base__ import Email


def send(
		receivers: ty.Union[ty.List[str], str],
		subject: str,
		body: str = None,
		files: ty.List[str] = None,
		remove_files: bool = False,
		html: str = None,
		template: str = None,
		template_content: dict = None,
		mail_server: str = None,
):
	if not isinstance(receivers, list):
		receivers = [receivers]
	
	if not mail_server:
		mail_server = 'polygon'
		if 'log' in str(subject).lower():
			mail_server = 'log'
		elif 'attack' in str(subject).lower():
			mail_server = 'attack'
	
	server = Cache.mail_servers[mail_server]['server']
	port = Cache.mail_servers[mail_server]['port']
	sender = Cache.mail_servers[mail_server]['address']
	password = Cache.mail_servers[mail_server]['password']
	
	Email.send(
		server,
		port,
		sender,
		password,
		receivers,
		subject,
		body,
		files,
		remove_files,
		html,
		template,
		template_content,
	)


if __name__ == '__main__':
	send(
		['elyasnz1999@gmail.com'],
		'Test Title',
		'Test body',
	)
	print('ok')
