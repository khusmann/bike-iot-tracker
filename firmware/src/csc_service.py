"""BLE Cycling Speed and Cadence (CSC) Service implementation.

Implements the standard BLE CSC Service (0x1816) with continuous notifications.

Notification Behavior:
    Sends CSC Measurement notifications every 2 seconds, continuously
    broadcasting the current crank telemetry state (cumulative revolutions
    and last event time). This includes both active pedaling and idle periods.

    Per the CSC specification (https://www.bluetooth.com/specifications/specs/cycling-speed-and-cadence-profile-1-0/):
    "In typical applications, the CSC Measurement characteristic is notified
    approximately once per second. This interval may vary and is determined
    by the Server and not required to be configurable by the Client."

    We send notifications every 2 seconds (rather than 1 Hz) because with only
    one reed switch event per crank rotation, slow pedaling would alternate
    between showing accurate cadence and 0 RPM, causing a flickering display.

    Continuous notifications allow clients to:
    - Calculate real-time cadence (0 RPM when idle)
    - Detect connection status
    - Update UI immediately when state changes

Packet Format:
    5-byte CSC Measurement per BLE spec:
    - Byte 0: Flags (0x02 = crank data present)
    - Bytes 1-2: Cumulative crank revolutions (uint16, little-endian)
    - Bytes 3-4: Last crank event time (uint16, 1/1024 sec units, little-endian)
"""
import asyncio
import struct
import aioble
import bluetooth

from config import config
from models import CrankTelemetry
from state import TelemetryManager
from utils import log

# BLE Service and Characteristic UUIDs (from BLE specification)
# Cycling Speed and Cadence Service
CSC_SERVICE_UUID = bluetooth.UUID(0x1816)
# CSC Measurement Characteristic
CSC_MEASUREMENT_UUID = bluetooth.UUID(0x2A5B)

# CSC timing constants
# Time is measured in 1/1024 second units per BLE CSC spec
CSC_TIME_UNIT_HZ = 1024


def crank_telemetry_to_csc_measurement(telemetry: CrankTelemetry) -> bytes:
    """Format crank telemetry as CSC Measurement per BLE spec.

    Converts the physical time to CSC time units and wraps appropriately.

    Args:
        telemetry: CrankTelemetry instance to format.

    Returns:
        5-byte CSC measurement packet:
            - Byte 0: Flags (bit 1 = crank revolution data present)
            - Bytes 1-2: Cumulative crank revolutions (uint16, little-endian)
            - Bytes 3-4: Last crank event time (uint16, little-endian, 1/1024 sec units)
    """
    # Convert milliseconds to 1/1024 second units
    time_in_units = (
        telemetry.last_physical_time_ms * CSC_TIME_UNIT_HZ
    ) // 1000

    # Wrap at 16 bits (0-65535) per BLE spec
    wrapped_time = time_in_units & 0xFFFF

    flags = 0x02  # Bit 1: Crank Revolution Data Present
    return struct.pack(
        '<BHH',
        flags,
        telemetry.cumulative_revolutions,
        wrapped_time
    )


async def notify_csc_subscriptions(
    characteristic: aioble.Characteristic,
    telemetry_manager: TelemetryManager
) -> None:
    """Handle a single BLE connection by sending telemetry notifications.

    Runs as an independent task per connection, enabling concurrent
    multi-device support.

    Args:
        connection: Active BLE connection to serve.
        characteristic: CSC measurement characteristic to notify on.
        state: Application state containing telemetry data.
    """

    while True:
        # Sleep briefly for responsiveness to disconnection
        await asyncio.sleep(config.csc_notification_interval_s)

        measurement_data = crank_telemetry_to_csc_measurement(
            telemetry_manager.crank_telemetry
        )

        try:
            # Notify all subscribed clients (send_update = True)
            characteristic.write(measurement_data, send_update=True)
        except Exception as e:
            log(f"CSC update error: {e}")


def register_csc_service(telemetry_manager: TelemetryManager) -> aioble.Service:
    # Register CSC Service
    csc_service = aioble.Service(CSC_SERVICE_UUID)

    # Register CSC Measurement Characteristic (notify only)
    csc_measurement_char = aioble.Characteristic(
        csc_service,
        CSC_MEASUREMENT_UUID,
        read=False,
        write=False,
        notify=True,
        indicate=False
    )

    asyncio.create_task(
        notify_csc_subscriptions(csc_measurement_char, telemetry_manager)
    )

    return csc_service
