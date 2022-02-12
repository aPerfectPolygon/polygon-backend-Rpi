import pathlib
import sys

sys.path.append(str(pathlib.Path(__file__).resolve().parent.parent.parent.parent))

import logging
import sys
import time as _time

from paste.translogger import TransLogger
from waitress import serve

from Rpi.wsgi import application
from UTILS.prj_utils import Defaults as prj_def


class LOGGER(TransLogger):
	format = (
		'[%(time)s] [%(PORT)s] %(status)s %(REMOTE_ADDR)s '
		'[%(HTTP_USER_AGENT)s] %(REQUEST_METHOD)s %(REQUEST_URI)s %(bytes)s'
	)

	def write_log(self, environ, method, req_uri, start, status, bytes_cnt):
		if bytes_cnt is None:
			bytes_cnt = '-'

		# if time.daylight:
		#     offset = time.altzone / 60 / 60 * -100
		# else:
		#     offset = time.timezone / 60 / 60 * -100
		#
		# if offset >= 0:
		#     offset = "+%0.4d" % (offset)
		# elif offset < 0:
		#     offset = "%0.4d" % (offset)

		remote_addr = '-'
		if environ.get('HTTP_X_REAL_IP'):
			remote_addr = environ['HTTP_X_REAL_IP']
		elif environ.get('HTTP_X_FORWARDED_FOR'):
			remote_addr = environ['HTTP_X_FORWARDED_FOR']
		elif environ.get('REMOTE_ADDR'):
			remote_addr = environ['REMOTE_ADDR']

		print(self.format % {
			'REMOTE_ADDR': remote_addr,
			'REQUEST_METHOD': method,
			'REQUEST_URI': req_uri,
			# 'HTTP_VERSION': environ.get('SERVER_PROTOCOL'),
			'time': _time.strftime('%Y/%m/%d %H:%M:%S', start),  # + offset,
			'status': status.split(None, 1)[0],
			'bytes': bytes_cnt,
			# 'HTTP_REFERER': environ.get('HTTP_REFERER', '-'),
			'HTTP_USER_AGENT': environ.get('HTTP_USER_AGENT', '-'),
			'PORT': environ.get('HTTP_X_PORT', '-'),
		})


def run(addr):
	print(f'Server is Running on http://{addr}/')
	serve(
		LOGGER(
			application,
			logging_level=logging.CRITICAL,
			set_logger_level=logging.CRITICAL,
			setup_console_handler=False
		),
		listen=addr,
		_quiet=True,
		threads=250
	)


if __name__ == '__main__':
	address = '0.0.0.0:5947'
	
	if len(sys.argv) > 1:
		address = sys.argv[1]

	run(address)
