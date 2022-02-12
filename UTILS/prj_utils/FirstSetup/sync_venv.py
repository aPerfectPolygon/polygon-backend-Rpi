import os

from UTILS.prj_utils import Defaults as prj_def


def sync():
	root = str(prj_def.project_root)
	os.system(f'. {root}/venv/bin/activate && pip install -r {root}/requirements.txt > /dev/null')


if __name__ == '__main__':
	sync()
