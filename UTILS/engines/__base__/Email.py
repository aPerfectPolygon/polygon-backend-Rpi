import os
import smtplib
import time as ti
import typing as ty
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from os.path import basename

import markdown

from UTILS.dev_utils import Defaults as dev_def, Decorators
from UTILS.dev_utils import Log

templates_path = f'{dev_def.project_root}/templates'


@Decorators.threaded
def _send(
		server: str,
		port: int,
		sender: str,
		password: str,
		receiver: str,
		subject: str,
		body: str = '',
		files: ty.List[str] = None,
		remove_files: bool = False,
		html: str = None,
		template: str = None,
		template_content: dict = None,
		callback: ty.Callable = None
):
	for _ in range(3):
		try:
			msg = MIMEMultipart('alternative')
			msg['Subject'] = subject
			msg['From'] = sender
			msg['To'] = receiver
			
			for f in files or []:
				with open(f, "rb") as fil:
					part = MIMEApplication(fil.read(), Name=basename(f))
				part['Content-Disposition'] = 'attachment; filename="%s"' % basename(f)
				msg.attach(part)
				if remove_files:
					os.remove(f)
			
			msg.attach(MIMEText(body, 'plain'))
			
			if html:
				msg.attach(MIMEText(html, 'html'))
			elif template:
				with open(f'{templates_path}/{template}', 'r', encoding='utf-8') as f:
					__data = f.read()
					if template_content:
						__data = __data.format(**template_content)
					msg.attach(MIMEText(markdown.markdown(__data), 'html'))
			
			_server = smtplib.SMTP(host=server, port=port)
			_server.starttls()
			_server.login(sender, password)
			_server.sendmail(sender, receiver, msg.as_string())
			_server.quit()
			
			if callback:
				callback(receiver, subject)
			else:
				print(f'MAIL sent {subject}')
			break
		
		except Exception as err:
			Log.log('[UNEXPECTED ERROR]', exc=err)
			ti.sleep(1)


def send(
		server: str,
		port: int,
		sender: str,
		password: str,
		receivers: ty.List[str],
		subject: str,
		body: str = None,
		files: ty.List[str] = None,
		remove_files: bool = False,
		html: str = None,
		template: str = None,
		template_content: dict = None,
		callback: ty.Callable = None
):
	if template_content is None:
		template_content = {}
	if body is None:
		body = ''
	
	if dev_def.disable_engine_email:
		print(
			f'[DISABLED] Email to {receivers} \n\t'
			f'Subject: {subject}\n\t'
			f'Body: {body}\n\t'
			f'Template: {template}\n\t'
			f'Template Content: {template_content}\n\t'
			f'html: {html}'
		)
		if callback:
			for rec in receivers:
				callback(rec, subject)
		return
	
	for receiver in receivers:
		_send(
			server, port, sender, password, receiver, subject, body, files,
			remove_files, html, template, template_content, callback
		)
