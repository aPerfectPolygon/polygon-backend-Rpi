import pandas as pd
import Email
import sys
from time import sleep
import datetime as dt

args = sys.argv[1:]
if not args:
	raise ValueError('Bad Args')

emails = []
for item in args:
	emails.extend(pd.read_csv(item).squeeze().tolist())

for i, email in enumerate(emails):
	if i % 2 != 0:
		continue

	gp = [email]
	try:
		gp.append(emails[i+1])
	except:
		pass
	print(i, gp)
	sleep(1)

