# python AddMeToSysPathAndRun UTILS/engines/Bulk/Sms.py <templateName> <csvAddress> <Token1(optional)> <Token2(optional)> <Token3Optional>

import re
import sys
from time import sleep

import pandas as pd

from UTILS.dev_utils.Objects import List
from UTILS.engines import Sms

args = sys.argv[1:]
if not args:
	raise ValueError('Bad Args')

template = args.pop(0)
csv = args.pop(0)

if '/' in csv:
	_addr = '/'.join(csv.split('/')[:-1])
else:
	_addr = '.'
sent_file = f'{_addr}/sent_{"_".join(template.split("/"))}.csv'

to_send = pd.read_csv(csv, header=None, dtype='str').squeeze().drop_duplicates().tolist()
try:
	sent = pd.read_csv(sent_file, header=None, dtype='str').squeeze().drop_duplicates().tolist()
except:
	sent = []

popper = List.Popper(to_send)
for i, item in enumerate(to_send):
	if re.search('^(?:\+989|09|00989)([012349])[0-9]{8}$', item):
		if item.startswith('0098'):
			to_send[i] = '+98' + item[4:]
		elif item.startswith('09'):
			to_send[i] = '+98' + item[1:]
	else:
		popper.add(item)
popper.pop()
to_send = List.drop_duplicates(to_send + sent, keep=False)


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
		
		print(i, round(100*i/len(to_send), 2), gp)
		Sms.send(
			gp,
			template,
			*args,
			callback=sent_success
		)
		
		sleep(0.2)
