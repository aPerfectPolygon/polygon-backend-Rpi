import asyncio as aio
from UTILS.dev_utils.Objects.Sockets import WebSocket


async def client_handler(socket: WebSocket.WebSocket):
	while True:
		data = await socket.receive()
		if not data:
			break
		await socket.send('> ' + data)


if __name__ == '__main__':
	loop = aio.get_event_loop()
	loop.run_until_complete(
		aio.gather(
			WebSocket.serve('127.0.0.1', 1234, client_handler),
		)
	)
	loop.run_forever()
	