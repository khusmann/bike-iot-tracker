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
import aioble
import bluetooth

from state import TelemetryManager
from utils import log

# BLE Service and Characteristic UUIDs
# Cycling Speed and Cadence Service
CSC_SERVICE_UUID = bluetooth.UUID(0x1816)
# CSC Measurement Characteristic
CSC_MEASUREMENT_UUID = bluetooth.UUID(0x2A5B)

# Notification interval: ~1 Hz per CSC spec recommendation
CSC_NOTIFICATION_INTERVAL_S = 2


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
        await asyncio.sleep(CSC_NOTIFICATION_INTERVAL_S)

        try:
            measurement_data = telemetry_manager.crank_telemetry.to_csc_measurement()

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
