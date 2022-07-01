import os
import pathlib
import sys

args = sys.argv
file_addr = args.pop(0)
if not args:
	raise ValueError('Bad Args')

p = str(pathlib.Path(__file__).resolve().parent)
os.environ['PYTHONPATH'] = p
if p not in sys.path:
	sys.path.append(p)

if '/' in file_addr:
	file_addr = '/'.join(file_addr.split('/')[:-1])
else:
	file_addr = '.'

p = args[0].split('/')
_joined_args = " ".join(f'"{item}"' if ' ' in item else item for item in args[1:])
if len(p) == 1:
	os.system(f'cd {file_addr} && venv/bin/python {args[0]} {_joined_args}')
else:
	file = p.pop(-1)
	path = '/'.join(p)
	os.system(f'cd {file_addr} && . venv/bin/activate && cd {path} && python {file} {_joined_args}')

