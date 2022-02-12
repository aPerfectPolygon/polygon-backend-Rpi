import os

from UTILS.prj_utils import Defaults as prj_def


def pull():
	root = str(prj_def.project_root)
	try:
		print(f'pulling {root}')
		os.system(f'cd {root} && git pull')
	except:
		print(f'unable to pull {root}')


if __name__ == '__main__':
	pull()
