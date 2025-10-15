import asyncio
from machine import Pin

import aioble
from primitives import Pushbutton

import tasks
from state import AppState
from utils import ensure_wifi_connected, sync_ntp_time, log
from sync_service import register_sync_service
from csc_service import register_csc_service

# Hardware configuration
led = Pin(4, Pin.OUT)
reed = Pin(5, Pin.IN, Pin.PULL_UP)

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

    log(f"Revolution {state.telemetry_manager.crank_telemetry.cumulative_revolutions}")


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

    # Register CSC Service
    csc_service = register_csc_service(state.telemetry_manager)

    # Register Sync Service
    sync_service = register_sync_service(state.session_manager)

    # Register all services
    aioble.register_services(csc_service, sync_service)

    log("BLE services registered (CSC + Sync)")

    # Start BLE advertise as the main task
    await tasks.ble_advertise(
        DEVICE_NAME,
        [csc_service.uuid, sync_service.uuid]
    )


# Run the async main loop
try:
    asyncio.run(main())
except KeyboardInterrupt:
    log("Shutting down...")
