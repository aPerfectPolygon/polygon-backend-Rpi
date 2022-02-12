
. venv/bin/activate
cd UTILS/prj_utils/FirstSetup || exit
python main.py GitPull $1 $2
deactivate

supervisorctl restart all