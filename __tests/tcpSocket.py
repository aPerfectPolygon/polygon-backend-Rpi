import asyncio as aio

from UTILS.prj_utils import main as prj_utils
from UTILS.dev_utils.Objects import Json
from UTILS.dev_utils.Objects.Sockets import AioSocket


async def main():
	# s = await AioSocket.connect('78.157.39.43', 6986)
	s = await AioSocket.connect('0.0.0.0', 1234)
	
	await s.send(Json.encode({'type': 'authenticate', 'data': 'Elyas', 'platform': 'Test'}))
	# await s.send(Json.encode({'type': 'market', 'data': 'orderbook_nobitex'}))
	# await s.send(Json.encode({'type': 'search', 'data': ['BTC/USDT_orderbook_nobitex', 'BTC/USDT']}))
	# await s.send(Json.encode({'type': 'cancel_search', 'data': ['BTC/USDT']}))
	# await s.send(Json.encode({'type': 'disconnect', 'data': None}))
	
	# print(await s.receive())
	# print(await s.receive())
	# print('wait for 1s ...')
	# ti.sleep(1)
	# print('searching ...')
	# await s.send(Json.encode({'type': 'search', 'data': ['ارفع']}))
	
	while True:
		data = await s.receive()
		if not data:
			break
		print(Json.decode(data))


# print(data)


if __name__ == '__main__':
	aio.run(main())
