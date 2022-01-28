import os

from UTILS.prj_utils import Defaults as prj_def


def sync():
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

		os.system(
			f'. {root}/{prj_name}/venv/bin/activate '
			f'&& pip install -r {root}/{prj_name}/requirements.txt > /dev/null'
		)


if __name__ == '__main__':
	sync()
