import asyncio
import bluetooth
from machine import Pin

import aioble
from primitives import Pushbutton

import tasks
from state import AppState
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


def on_reed_press(state: AppState) -> None:
    """Handle reed switch press event.

    Updates telemetry on crank rotation, records revolution in session manager,
    and provides visual feedback via LED toggle.

    Args:
        state: Application state containing telemetry and session managers.
    """
    # Update telemetry state in place
    state.telemetry_manager.record_revolution()

    # Record revolution in session manager
    state.session_manager.record_revolution()

    # Toggle LED for visual feedback
    led.value(not led.value())

    log(f"Revolution {state.telemetry_manager.current_telemetry.cumulative_revolutions}")


async def advertise_and_serve(state: AppState) -> None:
    """Main BLE advertising loop that spawns independent connection tasks.

    Like a web server, continues advertising after accepting connections,
    enabling multiple concurrent devices (up to 3-4 on ESP32).

    Args:
        state: Application state object containing telemetry data.
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
        asyncio.create_task(
            tasks.ble_serve_connection(connection, csc_measurement_char, state)
        )

        log(f"Connection spawned, returning to advertising...")


async def main() -> None:
    """Main entry point.

    Initializes application state, ensures WiFi/NTP connectivity, starts
    background tasks, and runs BLE peripheral.
    """
    # Create application state (session manager initialized via default_factory)
    state = AppState()

    log(
        f"Initialized with {len(state.session_manager.store.sessions)} stored sessions"
    )

    # Set up reed switch using Pushbutton primitive
    # sense=1 because reed switch is active-low (PULL_UP, closed = 0)
    reed_button = Pushbutton(reed, sense=1)
    reed_button.press_func(on_reed_press, (state, ))

    log("Starting BikeTracker firmware...")
    log(f"LED on GPIO {led}")
    log(f"Reed switch on GPIO {reed}")

    # Ensure WiFi is connected
    await ensure_wifi_connected(led=led)

    # Sync NTP clock
    await sync_ntp_time(led=led)

    # Start background tasks
    asyncio.create_task(
        tasks.session_idle_timeout(state.session_manager, state)
    )

    asyncio.create_task(
        tasks.session_periodic_save(state.session_manager)
    )

    log("Background tasks started")

    # Start BLE peripheral with state
    await advertise_and_serve(state)


# Run the async main loop
try:
    asyncio.run(main())
except KeyboardInterrupt:
    log("Shutting down...")
