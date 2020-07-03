import asyncio

import rx.operators as ops
import serial_asyncio
from quart import Quart, websocket, copy_current_websocket_context
from rx.subject import Subject

from serious import Output, get_usb_com_port_device


def setup_app() -> Quart:
    app = Quart(__name__)
    app.secret_key = 'so-secret'

    @app.before_serving
    async def setup_com():
        app.transport, app.output = (await asyncio.gather(start_com()))[0]

    async def start_com():
        loop = asyncio.get_event_loop()

        coro = serial_asyncio.create_serial_connection(loop, Output, get_usb_com_port_device(), baudrate=115200)
        return await loop.create_task(coro)

    return app


app = setup_app()


@app.route('/')
async def hello():
    app.transport.write(b'%ETEMPC\n')
    return 'oi\n'


async def waiter(timeout):
    await asyncio.sleep(timeout)


@app.websocket('/api')
async def api():
    @copy_current_websocket_context
    async def ws_handler(val):
        await websocket.send(val)

    obs: Subject = app.output.port_data
    obs.pipe(
        ops.buffer(obs.pipe(ops.filter(b"\r".__eq__))),
        ops.map(lambda i: b"".join(i).decode())
    ).subscribe(
        on_next=lambda val: asyncio.get_event_loop().create_task(ws_handler(val)),
        on_error=lambda val: print(f"on_error {val}"),
        on_completed=print("on_completed"),
    )

    while True:
        await waiter(1)


def main():
    app.run(loop=asyncio.get_event_loop())


if __name__ == "__main__":
    main()
