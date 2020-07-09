import asyncio

import serial_asyncio
from rx.subject import Subject
from serial_asyncio import SerialTransport


class Output(asyncio.Protocol):
    def __init__(self):
        self.transport: SerialTransport
        self.port_data = Subject()
        self.port_data.on_completed = None

    def connection_made(self, transport):
        self.transport = transport
        print('port opened\n', transport)
        # transport.serial.rts = False  # You can manipulate Serial object via transport
        transport.write(b'000000\n')  # Write serial data via transport

    def data_received(self, data):
        self.port_data.on_next(data)

    def connection_lost(self, exc):
        print('port closed')
        # self.transport.loop.stop()

    def pause_writing(self):
        print('pause writing')
        print(self.transport.get_write_buffer_size())

    def resume_writing(self):
        print(self.transport.get_write_buffer_size())
        print('resume writing')


def get_usb_com_port_device() -> str:
    from serial.tools import list_ports
    try:
        return next(list_ports.grep('USB')).device
    except StopIteration:
        pass


def create_serial_task(loop):
    return serial_asyncio.create_serial_connection(loop, Output, get_usb_com_port_device(), baudrate=115200)
