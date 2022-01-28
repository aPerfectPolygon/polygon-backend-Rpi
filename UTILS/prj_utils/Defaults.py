import os
import platform as pla
from pathlib import Path


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


platform = pla.system()
is_server = os.path.exists('/is_server')
is_test_server = os.path.exists('/is_test_server')
ip = get_ip()
project_root = Path(__file__).resolve().parent.parent.parent.absolute()
