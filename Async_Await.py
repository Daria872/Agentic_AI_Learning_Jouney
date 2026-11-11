#The library asyncio is commonly used to use asynchronous functions

import asyncio

async def say_hello():
    print("Hello")
    await asyncio.sleep(1)  # Pause without blocking other async work
    print("World")


asyncio.run(say_hello())