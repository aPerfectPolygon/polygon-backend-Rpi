# python AddMeToSysPathAndRun UTILS/engines/Bulk/Email.py <subject> <templateName> <csvAddress>

import re
import sys
from time import sleep

import pandas as pd

from UTILS.dev_utils.Objects import List
from UTILS.engines import Email

args = sys.argv[1:]
if not args:
	raise ValueError('Bad Args')

subj = args.pop(0)
template = args.pop(0)
csv = args.pop(0)

if '/' in csv:
	_addr = '/'.join(csv.split('/')[:-1])
else:
	_addr = '.'
sent_file = f'{_addr}/sent_{"_".join(template.split("/"))}.csv'

to_send = pd.read_csv(csv, header=None).squeeze().drop_duplicates().tolist()
try:
	sent = pd.read_csv(sent_file, header=None).squeeze().drop_duplicates().tolist()
except:
	sent = []

to_send = List.drop_duplicates(to_send + sent, keep=False)
popper = List.Popper(to_send)
for item in to_send:
	if not re.search('^(?!\.)(?!.*\.$)(?!.*?\.\.)[a-zA-Z0-9._-]{0,61}@(?!\.)[a-zA-Z]+\.(?!\.)[a-zA-Z]+$', item):
		popper.add(item)
popper.pop()


def sent_success(receiver: str, subject: str):
	print(f'{subject} sent to {receiver}')
	sent.append(receiver)
	pd.Series(sent).to_csv(sent_file, index=False, header=False)


if __name__ == '__main__':
	for i, item in enumerate(to_send):
		if i % 2 != 0:
			continue
		
		gp = [item]
		try:
			gp.append(to_send[i + 1])
		except:
			pass
		
		print(i, round(100 * i / len(to_send), 2), gp)
		Email.send(
			gp,
			subj,
			template=template,
			callback=sent_success
		)
		
		sleep(1)
