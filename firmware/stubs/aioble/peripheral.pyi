# aioble/peripheral.pyi — MicroPython aioble peripheral module type stubs
# MIT license; Copyright (c) 2021 Jim Mussared

from typing import Any, Optional, Sequence
from .device import DeviceConnection

# Advertising type constants
_ADV_TYPE_FLAGS: int
_ADV_TYPE_NAME: int
_ADV_TYPE_UUID16_COMPLETE: int
_ADV_TYPE_UUID32_COMPLETE: int
_ADV_TYPE_UUID128_COMPLETE: int
_ADV_TYPE_UUID16_MORE: int
_ADV_TYPE_UUID32_MORE: int
_ADV_TYPE_UUID128_MORE: int
_ADV_TYPE_APPEARANCE: int
_ADV_TYPE_MANUFACTURER: int
_ADV_PAYLOAD_MAX_LEN: int

async def advertise(
    interval_us: int,
    adv_data: Optional[bytes | bytearray] = None,
    resp_data: Optional[bytes | bytearray] = None,
    connectable: bool = True,
    limited_disc: bool = False,
    br_edr: bool = False,
    name: Optional[str | bytes] = None,
    services: Optional[Sequence[Any]] = None,
    appearance: int = 0,
    manufacturer: Optional[tuple[int, bytes]] = None,
    timeout_ms: Optional[int] = None,
) -> DeviceConnection: ...
