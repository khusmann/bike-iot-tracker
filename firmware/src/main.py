import asyncio
import struct
from machine import Pin
from time import ticks_ms, localtime
from typing import Callable
import bluetooth
import aioble
import network
import ntptime
from udataclasses import dataclass, field
from primitives import Pushbutton

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
    new_revolution_event: asyncio.Event = field(default_factory=asyncio.Event)


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

        # Signal that new data is available
        state.new_revolution_event.set()

        print(f"Revolution {state.telemetry_state.cumulative_revolutions}")

    return on_reed_press


async def ensure_wifi_and_sync_ntp() -> None:
    """
    Ensure WiFi is connected and sync NTP clock.

    If WiFi is not connected, blink the LED and keep retrying until connected.
    Once connected, set the time via NTP.
    """
    wlan = network.WLAN(network.STA_IF)

    # Wait for WiFi connection
    retry_count = 0
    while not wlan.isconnected():
        retry_count += 1
        print(f"WiFi not connected. Attempt #{retry_count} to reconnect...")

        # Blink LED while waiting
        led.value(1)
        await asyncio.sleep(0.5)
        led.value(0)
        await asyncio.sleep(0.5)

    # WiFi is connected
    print(f"WiFi connected: {wlan.ifconfig()}")

    # Sync NTP clock
    try:
        print("Setting time via NTP...")
        ntptime.settime()
        # Display current time
        current_time = localtime()
        print(
            f"NTP time synchronized successfully: {current_time[0]}-{current_time[1]:02d}-{current_time[2]:02d} {current_time[3]:02d}:{current_time[4]:02d}:{current_time[5]:02d} UTC"
        )
    except Exception as e:
        print(f"Failed to sync NTP time: {e}")
        # Enter error state with distinct LED pattern (rapid double-blink)
        print("Entering NTP error state...")
        while True:
            # Double-blink pattern: on-off-on-off-pause
            led.value(1)
            await asyncio.sleep(0.1)
            led.value(0)
            await asyncio.sleep(0.1)
            led.value(1)
            await asyncio.sleep(0.1)
            led.value(0)
            await asyncio.sleep(0.7)  # Longer pause between double-blinks


async def serve_connection(
    connection: aioble.device.DeviceConnection,
    characteristic: aioble.Characteristic,
    state: AppState
) -> None:
    """
    Handle a single BLE connection by sending telemetry notifications.

    Args:
        connection: Active BLE connection to serve
        characteristic: CSC measurement characteristic to notify on
        state: Application state containing telemetry data
    """
    print(f"Connected to {connection.device}")

    try:
        while connection.is_connected():
            current_time = localtime()
            timestamp = f"{current_time[3]:02d}:{current_time[4]:02d}:{current_time[5]:02d}"
            measurement_data = state.telemetry_state.to_csc_measurement()

            characteristic.notify(connection, measurement_data)
            print(
                f"[{timestamp}] Notification sent: rev={state.telemetry_state.cumulative_revolutions}"
            )

            # Wait for new revolution event or 30s timeout for keepalive
            try:
                await asyncio.wait_for(
                    state.new_revolution_event.wait(),
                    timeout=30.0
                )
                state.new_revolution_event.clear()
            except asyncio.TimeoutError:
                print(f"Revolution timeout")
    except Exception as e:
        print(f"Connection error: {e}")
    finally:
        print("Disconnected")


async def advertise_and_serve(state: AppState) -> None:
    """
    Main BLE advertising and connection serving loop.

    Args:
        state: Application state object containing telemetry and event data
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

    print("BLE services registered")

    while True:
        print(f"Advertising as '{DEVICE_NAME}'...")

        connection = await aioble.advertise(
            interval_us=250_000,  # 250ms advertising interval
            name=DEVICE_NAME,
            services=[CSC_SERVICE_UUID],
            appearance=0x0000,  # Generic appearance
        )

        await serve_connection(connection, csc_measurement_char, state)


async def main() -> None:
    """Main entry point - ensure WiFi/NTP then start BLE peripheral"""

    # Create application state
    state = AppState()

    # Set up reed switch using Pushbutton primitive
    # sense=1 because reed switch is active-low (PULL_UP, closed = 0)
    reed_button = Pushbutton(reed, sense=1)
    reed_button.press_func(make_reed_press_handler(state))

    print("Starting BikeTracker firmware...")
    print(f"LED on GPIO {led}")
    print(f"Reed switch on GPIO {reed}")

    # Ensure WiFi is connected and sync NTP clock
    await ensure_wifi_and_sync_ntp()

    # Start BLE peripheral with state
    await advertise_and_serve(state)


# Run the async main loop
try:
    asyncio.run(main())
except KeyboardInterrupt:
    print("Shutting down...")
