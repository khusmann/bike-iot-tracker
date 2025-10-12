# aioble/server.pyi — MicroPython aioble server module type stubs
# MIT license; Copyright (c) 2021 Jim Mussared

from typing import Any, Optional, Sequence
from .device import DeviceConnection
import asyncio

# Flag constants
_FLAG_READ: int
_FLAG_WRITE_NO_RESPONSE: int
_FLAG_WRITE: int
_FLAG_NOTIFY: int
_FLAG_INDICATE: int
_FLAG_READ_ENCRYPTED: int
_FLAG_READ_AUTHENTICATED: int
_FLAG_READ_AUTHORIZED: int
_FLAG_WRITE_ENCRYPTED: int
_FLAG_WRITE_AUTHENTICATED: int
_FLAG_WRITE_AUTHORIZED: int
_FLAG_WRITE_CAPTURE: int

class Service:
    """Represents a GATT service"""
    uuid: Any
    characteristics: list['BaseCharacteristic']

    def __init__(self, uuid: Any) -> None: ...
    def _tuple(self) -> tuple: ...

class BaseCharacteristic:
    """Base class for characteristics and descriptors"""
    _value_handle: Optional[int]
    _initial: Optional[bytes]

    # Class variables for capture mode
    _capture_queue: Any
    _capture_write_event: asyncio.ThreadSafeFlag
    _capture_consumed_event: asyncio.ThreadSafeFlag
    _capture_task: asyncio.Task

    def _register(self, value_handle: int) -> None: ...
    def read(self) -> bytes: ...
    def write(self, data: bytes, send_update: bool = False) -> None: ...
    @staticmethod
    def _init_capture() -> None: ...
    @staticmethod
    async def _run_capture_task() -> None: ...
    async def written(self, timeout_ms: Optional[int] = None) -> DeviceConnection | tuple[DeviceConnection, bytes]: ...
    def on_read(self, connection: DeviceConnection) -> int: ...
    @staticmethod
    def _remote_write(conn_handle: int, value_handle: int) -> None: ...
    @staticmethod
    def _remote_read(conn_handle: int, value_handle: int) -> Optional[int]: ...

class Characteristic(BaseCharacteristic):
    """Represents a GATT characteristic"""
    uuid: Any
    flags: int
    descriptors: list['Descriptor']
    _write_event: asyncio.ThreadSafeFlag
    _write_data: Optional[DeviceConnection | tuple[DeviceConnection, bytes]]
    _indicate_connection: Optional[DeviceConnection]
    _indicate_event: asyncio.ThreadSafeFlag
    _indicate_status: Optional[int]

    def __init__(
        self,
        service: Service,
        uuid: Any,
        read: bool = False,
        write: bool = False,
        write_no_response: bool = False,
        notify: bool = False,
        indicate: bool = False,
        initial: Optional[bytes] = None,
        capture: bool = False,
    ) -> None: ...

    def _tuple(self) -> tuple: ...
    def notify(self, connection: DeviceConnection, data: Optional[bytes] = None) -> None: ...
    async def indicate(self, connection: DeviceConnection, data: Optional[bytes] = None, timeout_ms: int = 1000) -> None: ...
    @staticmethod
    def _indicate_done(conn_handle: int, value_handle: int, status: int) -> None: ...

class BufferedCharacteristic(Characteristic):
    """Characteristic with extended buffer for longer values"""
    _max_len: int
    _append: bool

    def __init__(
        self,
        *args: Any,
        max_len: int = 20,
        append: bool = False,
        **kwargs: Any
    ) -> None: ...

    def _register(self, value_handle: int) -> None: ...

class Descriptor(BaseCharacteristic):
    """Represents a GATT descriptor"""
    uuid: Any
    flags: int
    _write_event: asyncio.ThreadSafeFlag
    _write_data: Optional[DeviceConnection]

    def __init__(
        self,
        characteristic: Characteristic,
        uuid: Any,
        read: bool = False,
        write: bool = False,
        initial: Optional[bytes] = None
    ) -> None: ...

    def _tuple(self) -> tuple: ...

def register_services(*services: Service) -> None: ...
