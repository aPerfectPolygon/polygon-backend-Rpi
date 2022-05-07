import asyncio as aio
from time import sleep
from UTILS.dev_utils.Objects import Json
from UTILS.dev_utils.Objects.Sockets import AioSocket


async def main():
	s = await AioSocket.connect('0.0.0.0', 1234)
	
	await s.send(Json.encode({'type': 'authenticate', 'data': 'Elyas', 'platform': 'Test'}))
	await s.send(Json.encode({'type': 'track', 'data': [2, 4]})); sleep(0.1)
	await s.send(Json.encode({'type': 'change', 'data': [(2, 100), (4, 100)]})); sleep(0.1)
	await s.send(Json.encode({'type': 'untrack', 'data': [2]})); sleep(0.1)
	await s.send(Json.encode({'type': 'change', 'data': [(2, 0), (4, 0)]})); sleep(0.1)
	# await s.send(Json.encode({'type': 'untrack', 'data': None})); sleep(0.1)
	await s.send(Json.encode({'type': 'change', 'data': [(2, 100), (4, 100)]}))
	
	while True:
		data = await s.receive()
		if not data:
			break
		print(Json.decode(data))


if __name__ == '__main__':
	aio.run(main())
