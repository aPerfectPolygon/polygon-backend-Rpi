import os
import smtplib
import time as ty
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from os.path import basename
from threading import Thread
from UTILS.dev_utils import Defaults as dev_def

import markdown
import pandas as pd

from UTILS import Cache
from UTILS.dev_utils import Log
from UTILS.dev_utils.Database.Psql import Psql


def _send(
		receivers,
		subject,
		body='',
		files=None,
		template=None,
		template_content=None,
		remove_files=False,
		mail_server=None,
		**kwargs
):
	# noinspection PyShadowingNames
	def main(
			receiver,
			subject,
			body,
			files,
			template,
			template_content,
			remove_files,
			mail_server,
			**kwargs
	):
		for _ in range(3):
			try:
				if not mail_server:
					mail_server = 'gmail'
				
				sender = Cache.mail_servers[mail_server]['address']
				password = Cache.mail_servers[mail_server]['password']
				server = Cache.mail_servers[mail_server]['server']
				port = Cache.mail_servers[mail_server]['port']
				
				msg = MIMEMultipart('alternative')
				msg['Subject'] = subject
				msg['From'] = sender
				msg['To'] = receiver
				
				for f in files or []:
					with open(f, "rb") as fil:
						part = MIMEApplication(
							fil.read(),
							Name=basename(f)
						)
					# After the file is closed
					part['Content-Disposition'] = 'attachment; filename="%s"' % basename(f)
					msg.attach(part)
				
				msg.attach(MIMEText(body, 'plain'))
				
				html = kwargs.pop('html', None)
				if html:
					msg.attach(MIMEText(html, 'html'))
				elif template:
					with open(f'{dev_def.project_root}/templates/{template}', 'r', encoding='utf-8') as f:
						msg.attach(MIMEText(
							markdown.markdown(f.read().format(**template_content)),
							'html'
						))
				
				server = smtplib.SMTP(host=server, port=port)
				server.starttls()
				server.login(sender, password)
				server.sendmail(sender, receiver, msg.as_string())
				server.quit()
				
				if remove_files:
					for file in files:
						os.remove(file)
				
				print(f'MAIL sent {subject}')
				break
			
			except Exception as err:
				Log.log('[UNEXPECTED ERROR]', exc=err)
				ty.sleep(3)
	
	if files is None:
		files = []
	
	if template_content is None:
		template_content = {}
	
	for receiver in receivers:
		Thread(
			target=main,
			args=(receiver, subject, body, files, template, template_content, remove_files, mail_server),
			kwargs=kwargs
		).start()


def send(
		receivers,
		subject,
		body='',
		files=None,
		template=None,
		template_content=None,
		remove_files=False,
		mail_server=None,
		**kwargs
):
	if type(receivers) is not list:
		receivers = [receivers]
	
	if files is None:
		# add to stack
		Psql('services').insert(
			'mail_stack',
			pd.DataFrame(
				columns=['receivers', 'subject', 'body', 'template', 'template_content', 'mail_server', 'kwargs'],
				data=[[receivers, subject, body, template, template_content, mail_server, kwargs]]
			),
			auto_connection=True
		)
		
		# check if discharger is active
		if os.path.exists('/mail_stack_discharger'):
			return
		
		# begin to discharge stack
		os.system('touch /mail_stack_discharger')
		
		try:
			db = Psql('services', open=True)
			stack = db.read(
				'mail_stack',
				['id', 'receivers', 'subject', 'body', 'template', 'template_content', 'mail_server', 'kwargs']
			)
			for item in stack.to_dict('records'):
				_send(
					item['receivers'],
					subject=item['subject'],
					body=item['body'],
					template=item['template'],
					template_content=item['template_content'],
					mail_server=item['mail_server'],
					**item['kwargs']
				)
				db.delete('mail_stack', [('id', '=', item['id'])])
		except Exception as e:
			Log.log('MAIL sending error', exc=e)
		finally:
			try:
				os.remove('/mail_stack_discharger')
			except:
				pass
	else:
		_send(
			receivers,
			subject=subject,
			body=body,
			files=files,
			template=template,
			template_content=template_content,
			remove_files=remove_files,
			mail_server=mail_server,
			**kwargs
		)


if __name__ == '__main__':
	send('elyasnz1999@gmail.com', '[test]', 'testxx')
