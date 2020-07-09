import asyncio

import rx.operators as ops
from quart import Quart, websocket, copy_current_websocket_context, request
from rx import Observable
from rx.disposable import Disposable
from rx.scheduler.eventloop import AsyncIOScheduler
from serial import SerialException

from serious import create_serial_task
from utils import from_aiter


async def com_is_up():
    while True:
        try:
            state = app.transport._serial
            if state is not None:
                yield True
            else:
                yield False
        except:
            yield False
        await waiter(3)


def setup_app() -> Quart:
    app = Quart(__name__)
    app.secret_key = 'so-secret'

    @app.before_serving
    async def setup_com():
        loop = asyncio.get_event_loop()
        try:
            app.transport, app.output = (await asyncio.gather(start_com(loop)))[0]
        except TypeError as ex:
            app.logger.error(f"{ex.with_traceback(None)}")
        try:
            app.com_watcher_disposable.dispose()
        except AttributeError:
            pass
        app.com_watcher_disposable = from_aiter(com_is_up(), loop).pipe(ops.filter(lambda i: not i),
                                                                        ops.debounce(3)).subscribe(
            on_next=lambda val: loop.create_task(setup_com()),
            on_error=lambda val: print(f"on_error {val}"),
            on_completed=None,
            scheduler=AsyncIOScheduler(loop)
        )

    async def start_com(loop):
        try:
            return await loop.create_task(create_serial_task(loop))
        except SerialException as ex:
            app.logger.error(f"{ex.strerror}")

    return app


app = setup_app()


async def send_str(cmd: str):
    app.transport.write(cmd.encode())
    return str


@app.route('/temps')
async def hello():
    return await send_str('%ETEMPC\r')


@app.route('/login')
async def login():
    return await send_str('%000000\n')


@app.route('/send')
async def send_cmd():
    cmd = request.args.get('cmd')
    return await send_str(f'%{cmd}\r')


@app.route('/disable_uart')
async def disable_uart():
    return await send_str('%UARTEVENT=0\r')


async def waiter(timeout):
    await asyncio.sleep(timeout)


@app.websocket('/watch')
async def watch():
    @copy_current_websocket_context
    async def ws_handler(val):
        await websocket.send(val)

    async def subscribe(obs, loop) -> Disposable:
        return obs.pipe(
            ops.buffer(obs.pipe(ops.debounce(1))),
            ops.map(lambda i: b"".join(i).decode())
        ).subscribe(
            on_next=lambda val: loop.create_task(ws_handler(val)),
            on_error=lambda val: print(f"on_error {val}"),
            on_completed=None,
            scheduler=AsyncIOScheduler(loop)
        )

    await send_str('%UARTEVENT=1\r')

    loop = asyncio.get_event_loop()

    obs: Observable = app.output.port_data
    await subscribe(obs, loop)
    while True:
        await waiter(1)
        if obs is not app.output.port_data:
            app.logger.error("Resubscribing to com data output since the subject changed")
            obs = app.output.port_data
            await subscribe(obs, loop)


def main():
    app.run(loop=asyncio.get_event_loop())


if __name__ == "__main__":
    main()
