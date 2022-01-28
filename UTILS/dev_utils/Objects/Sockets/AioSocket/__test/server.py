import asyncio as aio

from UTILS.dev_utils.Objects.Sockets import AioSocket


async def client_handler(socket: AioSocket.AioSocket):
	while True:
		data = await socket.receive()
		if not data:
			break
		await socket.send('> ' + data)
	await socket.close()


if __name__ == '__main__':
	loop = aio.get_event_loop()
	loop.run_until_complete(
		AioSocket.serve('127.0.0.1', 1234, client_handler)
	)
	loop.run_forever()
