import asyncio
import struct
from machine import Pin
from time import ticks_ms
from typing import Callable
import bluetooth
import aioble
import typing as t
from udataclasses import dataclass, field
from primitives import Pushbutton
from utils import ensure_wifi_connected, sync_ntp_time, log

# Hardware configuration
led = Pin(4, Pin.OUT)
reed = Pin(5, Pin.IN, Pin.PULL_UP)

# BLE Service and Characteristic UUIDs
# Cycling Speed and Cadence Service
CSC_SERVICE_UUID = bluetooth.UUID(0x1816)
# CSC Measurement Characteristic
CSC_MEASUREMENT_UUID = bluetooth.UUID(0x2A5B)

# Device name for advertising
DEVICE_NAME = "BikeTracker"

# CSC timing constants
# Time is measured in 1/1024 second units per BLE CSC spec
TIME_UNIT_HZ = 1024

# Interval for sending notifications when idle (no revolutions) in seconds
IDLE_NOTIFICATION_INTERVAL_S = 30

# Connection loop polling interval in seconds
CONNECTION_POLL_INTERVAL_S = 1


@dataclass
class TelemetryState:
    """Mutable state for crank telemetry tracking"""
    cumulative_revolutions: int = 0
    last_event_time: int = 0
    last_physical_time_ms: int = 0

    def record_revolution(self, current_time_ms: int) -> None:
        """Record a new revolution by updating state in place"""
        # Convert milliseconds to 1/1024 second units
        time_in_units = (current_time_ms * TIME_UNIT_HZ) // 1000
        # Wrap at 16 bits (0-65535) per BLE spec
        wrapped_time = time_in_units & 0xFFFF

        self.cumulative_revolutions = (
            self.cumulative_revolutions + 1) & 0xFFFFFFFF  # Wrap at 32 bits
        self.last_event_time = wrapped_time
        self.last_physical_time_ms = current_time_ms

    def to_csc_measurement(self) -> bytes:
        """
        Format state as CSC Measurement per BLE spec

        Format:
        - Byte 0: Flags (bit 1 = crank revolution data present)
        - Bytes 1-4: Cumulative crank revolutions (uint32, little-endian)
        - Bytes 5-6: Last crank event time (uint16, little-endian, 1/1024 sec units)
        """
        flags = 0x02  # Bit 1: Crank Revolution Data Present
        return struct.pack(
            '<BIH',
            flags,
            self.cumulative_revolutions,
            self.last_event_time
        )


@dataclass
class AppState:
    """
    Mutable application state container.

    Encapsulates all mutable state in one place to avoid module-level globals.
    """
    telemetry_state: TelemetryState = field(default_factory=TelemetryState)


def make_reed_press_handler(state: AppState) -> Callable[[], None]:
    """
    Create a reed switch press handler with access to state.

    Args:
        state: Application state object

    Returns:
        Handler function for reed switch press events
    """
    def on_reed_press() -> None:
        """Handler for reed switch press - updates telemetry on crank rotation"""
        current_time_ms = ticks_ms()

        # Update telemetry state in place
        state.telemetry_state.record_revolution(current_time_ms)

        # Toggle LED for visual feedback
        led.value(not led.value())

        log(f"Revolution {state.telemetry_state.cumulative_revolutions}")

    return on_reed_press


async def serve_connection(
    connection: aioble.device.DeviceConnection,
    characteristic: aioble.Characteristic,
    state: AppState
) -> None:
    """
    Handle a single BLE connection by sending telemetry notifications.

    Runs as an independent task per connection, enabling concurrent
    multi-device support.

    Args:
        connection: Active BLE connection to serve
        characteristic: CSC measurement characteristic to notify on
        state: Application state containing telemetry data
    """
    def log_connection(s: str):
        log(f"[{connection.device}] {s}")

    log_connection("Connected")

    # Give client time to enable notifications (descriptor write)
    await asyncio.sleep(1.5)

    last_seen_revolution = state.telemetry_state.cumulative_revolutions
    last_notification_ms = ticks_ms()
    notification_type: t.Literal["INIT", "REVOLUTION", "IDLE", "NONE"] = "INIT"

    try:
        while connection.is_connected():
            current_revolution = state.telemetry_state.cumulative_revolutions
            elapsed_s = (ticks_ms() - last_notification_ms) / 1000

            if notification_type != "NONE":
                measurement_data = state.telemetry_state.to_csc_measurement()
                characteristic.notify(connection, measurement_data)
                log_connection(
                    f"Notification {notification_type}: rev={current_revolution}"
                )
                last_notification_ms = ticks_ms()

            # Sleep briefly for responsiveness to disconnection
            await asyncio.sleep(CONNECTION_POLL_INTERVAL_S)

            if current_revolution > last_seen_revolution:
                last_seen_revolution = current_revolution
                notification_type = "REVOLUTION"
            elif elapsed_s >= IDLE_NOTIFICATION_INTERVAL_S:
                notification_type = "IDLE"
            else:
                notification_type = "NONE"

    except Exception as e:
        log_connection(f"Connection error: {e}")
    finally:
        log_connection(f"Disconnected")


async def advertise_and_serve(state: AppState) -> None:
    """
    Main BLE advertising loop that spawns independent connection tasks.

    Like a web server, continues advertising after accepting connections,
    enabling multiple concurrent devices (up to 3-4 on ESP32).

    Args:
        state: Application state object containing telemetry data
    """
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

    # Register the service
    aioble.register_services(csc_service)

    log("BLE services registered")

    while True:
        log(f"Advertising as '{DEVICE_NAME}'...")

        connection = await aioble.advertise(
            interval_us=250_000,  # 250ms advertising interval
            name=DEVICE_NAME,
            services=[CSC_SERVICE_UUID],
            appearance=0x0000,  # Generic appearance
        )

        # Spawn connection handler as independent task
        # This allows immediate return to advertising for multi-device support
        asyncio.create_task(serve_connection(
            connection, csc_measurement_char, state))

        log(f"Connection spawned, returning to advertising...")


async def main() -> None:
    """Main entry point - ensure WiFi/NTP then start BLE peripheral"""

    # Create application state
    state = AppState()

    # Set up reed switch using Pushbutton primitive
    # sense=1 because reed switch is active-low (PULL_UP, closed = 0)
    reed_button = Pushbutton(reed, sense=1)
    reed_button.press_func(make_reed_press_handler(state))

    log("Starting BikeTracker firmware...")
    log(f"LED on GPIO {led}")
    log(f"Reed switch on GPIO {reed}")

    # Ensure WiFi is connected
    await ensure_wifi_connected(led=led)

    # Sync NTP clock
    await sync_ntp_time(led=led)

    # Start BLE peripheral with state
    await advertise_and_serve(state)


# Run the async main loop
try:
    asyncio.run(main())
except KeyboardInterrupt:
    log("Shutting down...")
