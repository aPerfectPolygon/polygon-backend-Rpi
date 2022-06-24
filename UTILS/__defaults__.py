import os
from pathlib import Path
import platform as pla
import socket as sock


def get_ip():
	s = sock.socket(sock.AF_INET, sock.SOCK_DGRAM)
	s.setsockopt(sock.SOL_SOCKET, sock.SO_BROADCAST, 1)
	try:
		s.connect(('4.2.2.4', 0))
		detected_ip = s.getsockname()[0]
	except Exception:
		detected_ip = '127.0.0.1'
	finally:
		s.close()
	return detected_ip


class Languages:
	fa = 'fa-ir'
	en = 'en-us'
	all = [fa, en]


platform = pla.system()
is_server = os.path.exists('/is_server')
is_test_server = os.path.exists('/is_test_server')
disable_engine_sms = os.path.exists('/disable_candle_engine_sms')
disable_engine_notification = os.path.exists('/disable_candle_engine_notification')
disable_engine_email = os.path.exists('/disable_candle_engine_email')

ip = get_ip()
project_root = Path(__file__).parent.parent.absolute()

proxies = {  # fillme
	'http': '',
	'https': ''
}
