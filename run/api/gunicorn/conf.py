"""
Documentation: https://docs.gunicorn.org/en/0.17.2/configure.html

"""
import os
from multiprocessing import cpu_count
from pathlib import Path
from UTILS.prj_utils import Defaults as prj_def

proc_name = 'PolygonApi'
user = 'root'
group = 'root'
django_settings = 'Rpi.settings'
root = str(Path(__file__).resolve().parent.parent.parent.parent)
pythonpath = root + ':' + os.environ.get('PYTHONPATH', '')

port = 5947

if prj_def.is_server:
	workers = (cpu_count() * 2) + 1
	bind = f'127.0.0.1:{port}'
else:
	workers = 1
	bind = f'0.0.0.0:{port}'

worker_class = 'gevent'
worker_connections = 100

limit_request_line = 4094
limit_request_fields = 200
limit_request_field_size = 8190

secure_scheme_headers = {}
forwarded_allow_ips = '*'

loglevel = 'warning'  # debug info warning error critical
os.system(f'touch {root}/Logs/gunicorn.log')
errorlog = f'{root}/Logs/gunicorn.log'  # None, '-', FILE
accesslog = None  # None, '-', FILE
access_log_format = '%(t)s "%(r)s" [%(h)s] "%(a)s" %(D)s'

# TODO syslog
