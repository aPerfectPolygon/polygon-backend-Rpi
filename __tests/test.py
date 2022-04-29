import asyncio as aio
import time as ti

import serial




if __name__ == '__main__':
	loop = aio.get_event_loop()
	
	manager = SerialManager(loop, '/dev/ttyACM0', 9600, CallbackManager)
	manager.run()
	
	loop.run_forever()
