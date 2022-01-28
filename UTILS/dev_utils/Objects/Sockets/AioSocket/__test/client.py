import asyncio as aio

from UTILS.dev_utils.Objects.Sockets import AioSocket


async def main():
	s = await AioSocket.connect('127.0.0.1', 1234)
	while True:
		await s.send('hello')
		data = await s.receive()
		if not data:
			break
		print(data)
		await aio.sleep(1)


if __name__ == '__main__':
	aio.run(main())
