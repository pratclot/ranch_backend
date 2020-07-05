import asyncio

from rx.scheduler.eventloop import AsyncIOScheduler
import rx
import rx.operators as ops
import serial_asyncio
from quart import Quart, websocket, copy_current_websocket_context, request
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
    app.transport.write(b'%ETEMPC\r')
    return 'oi\n'


@app.route('/login')
async def login():
    app.transport.write(b'%000000\n')
    return 'oi\n'


@app.route('/send')
async def send_cmd():
    cmd = request.args.get('cmd')
    app.transport.write(f'%{cmd}\r'.encode())
    return f'{cmd}\n'


@app.route('/disable_uart')
async def disable_uart():
    app.transport.write(b'%UARTEVENT=0\r')
    return 'oi\n'


async def waiter(timeout):
    await asyncio.sleep(timeout)


@app.websocket('/watch')
async def watch():
    @copy_current_websocket_context
    async def ws_handler(val):
        await websocket.send(val)

    app.transport.write(b'%UARTEVENT=1\r')

    loop = asyncio.get_event_loop()
    obs: Subject = app.output.port_data
    obs.pipe(
        ops.buffer(obs.pipe(ops.debounce(1))),
        ops.map(lambda i: b"".join(i).decode())
    ).subscribe(
        on_next=lambda val: loop.create_task(ws_handler(val)),
        on_error=lambda val: print(f"on_error {val}"),
        on_completed=print("on_completed"),
        scheduler=AsyncIOScheduler(loop)
    )

    while True:
        await waiter(1)
    

@app.websocket('/api')
async def api():
    @copy_current_websocket_context
    async def ws_handler(val):
        await websocket.send(val)

    obs: Subject = app.output.port_data
    obs.pipe(
        ops.buffer(obs.pipe(ops.filter(lambda i: b"CMD OK" in i))),
#        ops.buffer(obs.pipe(ops.filter(b"\r".__eq__))),
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
