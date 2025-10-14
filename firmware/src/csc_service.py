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

# Interval for sending notifications when idle (no revolutions) in seconds
CSC_NOTIFICATION_INTERVAL_S = 0.2


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
