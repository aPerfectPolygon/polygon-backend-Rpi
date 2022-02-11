import os
from pathlib import Path
import platform as pla


def get_ip():
	import socket as sock
	s = sock.socket(sock.AF_INET, sock.SOCK_DGRAM)
	s.setsockopt(sock.SOL_SOCKET, sock.SO_BROADCAST, 1)
	try:
		# doesn't even have to be reachable
		s.connect(('4.2.2.4', 0))  # fixme if offline
		detected_ip = s.getsockname()[0]
	except Exception:
		detected_ip = '127.0.0.1'
	finally:
		s.close()
	return detected_ip


class Languages:
	fa = 'fa'
	en = 'en'
	all = [fa, en]


name = 'enz'
mobile = '+989196864660'
email = 'elyasnz.1999@gmail.com'

platform = pla.system()
is_server = os.path.exists('/is_server')
is_test_server = os.path.exists('/is_test_server')
ip = get_ip()
project_root = Path(__file__).parent.parent.parent.absolute()

logger_names = [
	'print',
	'default',
	'technical',
	'django',
]
standard_log_methods = [
	'debug',
	'info',
	'warning',
	'error',
	'critical',
	'exception'
]

proxies = {
	'http': 'http://aozijqzx-rotate:1lqmg4uww14f@p.webshare.io:80',
	'https': 'https://aozijqzx-rotate:1lqmg4uww14f@p.webshare.io:80',
}
