import asyncio as aio

import serial

from UTILS.dev_utils.Objects.Sockets import Serial


async def main():
	while True:
		while True:
			try:
				s = await Serial.connect('/dev/ttyACM0', 9600)
			except:
				print('CONNECTING ...')
				await aio.sleep(1)
			else:
				break
		
		print('CONNECTED')
	
		while True:
			r = await s.receive(30)
			if not r:
				break
			await s.send("IO|1|IA")
			print(r)
		
		print('DISCONNECTED')


if __name__ == '__main__':
	aio.run(main())
