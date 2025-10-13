# aioble/__init__.pyi — MicroPython aioble type stubs
# MIT license; Copyright (c) 2021 Jim Mussared

from typing import Any, Callable, Optional

# Re-exported from device module
from .device import Device as Device
from .device import DeviceDisconnectedError as DeviceDisconnectedError

# Re-exported from core module
from .core import GattError as GattError
from .core import log_info as log_info
from .core import log_warn as log_warn
from .core import log_error as log_error
from .core import config as config
from .core import stop as stop

# Re-exported from peripheral module (if available)
from .peripheral import advertise as advertise

# Re-exported from server module (if available)
from .server import Service as Service
from .server import Characteristic as Characteristic
from .server import BufferedCharacteristic as BufferedCharacteristic
from .server import Descriptor as Descriptor
from .server import register_services as register_services

# Constants
ADDR_PUBLIC: int
ADDR_RANDOM: int
