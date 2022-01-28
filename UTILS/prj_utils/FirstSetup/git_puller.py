import os

from UTILS.prj_utils import Defaults as prj_def


def pull():
	if prj_def.is_backend:
		root = str(prj_def.project_root.parent)
	else:
		root = str(prj_def.project_root.parent.parent)

	for prj_name in [
		'Back-end',
		'IR/Web',
		'FX/Web',
		'IRFX/Web',
	]:
		if not os.path.exists(f'{root}/{prj_name}'):
			continue

		try:
			print(f'pulling {root}/{prj_name}')
			os.system(f'cd {root}/{prj_name} && git pull')
		except:
			print(f'unable to pull {root}/{prj_name}')


if __name__ == '__main__':
	pull()
