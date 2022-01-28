import asyncio as aio
import concurrent.futures
import functools
import threading as thr
from UTILS.dev_utils import Log


def aio_threaded():
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            completed, pending = await aio.wait(
                [aio.get_event_loop().run_in_executor(
                    concurrent.futures.ThreadPoolExecutor(), func, *args
                )]
            )
            return [t.result() for t in completed][0]
        
        return wrapper
    
    return decorator


def threaded(func):
    def wrapper(*args, **kwargs):
        return thr.Thread(target=func, args=args, kwargs=kwargs).start()

    return wrapper


def retry_on_error(retry: int = 3, func_name: str = ''):
    cur_info = Log.curr_info()

    def decorator(func):
        def wrapper(*args, **kwargs):
            output = None
            for _ in range(retry):
                try:
                    output = func(*args, **kwargs)
                    break
                except Exception as e:
                    Log.log(func_name, location=cur_info, exc=e)
            return output

        return wrapper

    return decorator
