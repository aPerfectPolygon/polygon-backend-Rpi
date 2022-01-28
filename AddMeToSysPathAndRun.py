import os
import pathlib
import sys

args = sys.argv[1:]
if not args:
	raise ValueError('Bad Args')

p = str(pathlib.Path(__file__).resolve().parent)
os.environ['PYTHONPATH'] = p
if p not in sys.path:
	sys.path.append(p)

p = args[0].split('/')
if len(p) == 1:
	os.system(f'venv/bin/python {args[0]} {" ".join(args[1:])}')
else:
	file = p.pop(-1)
	path = '/'.join(p)
	os.system(f'. venv/bin/activate && cd {path} && python {file} {" ".join(args[1:])}')

