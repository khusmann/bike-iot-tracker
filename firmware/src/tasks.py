"""
Background tasks for the application.

All async background tasks are defined here. This centralizes task
orchestration and makes the concurrent structure of the application
easy to understand.
"""
import asyncio
from time import ticks_ms, ticks_diff
from typing import Any
import typing as t
import aioble
from session_manager import SessionManager
from utils import log


# Session boundary detection: end session after 10 minutes of inactivity
IDLE_TIMEOUT_MS = 10 * 60 * 1000  # 10 minutes in milliseconds

# Periodic persistence: save active session every 5 minutes
SAVE_INTERVAL_S = 5 * 60  # 5 minutes in seconds

# Interval for sending notifications when idle (no revolutions) in seconds
IDLE_NOTIFICATION_INTERVAL_S = 30

# Connection loop polling interval in seconds
CONNECTION_POLL_INTERVAL_S = 1


async def session_idle_timeout(
    session_manager: SessionManager,
    state: Any
) -> None:
    """
    Monitor for idle periods and automatically end sessions.

    Checks the last_physical_time_ms from telemetry state. If more than
    IDLE_TIMEOUT_MS has elapsed without a crank event, ends the current session.

    Args:
        session_manager: SessionManager instance to end sessions
        state: Application state containing telemetry
    """
    log("Idle timeout task started")

    # Initial delay to allow system startup
    await asyncio.sleep(10)

    while True:
        # Check every 30 seconds
        await asyncio.sleep(30)

        if not session_manager.has_active_session():
            continue

        # Check time since last crank event
        current_time_ms = ticks_ms()
        last_event_ms = state.telemetry_state.last_physical_time_ms

        # Handle the case where no events have happened yet
        if last_event_ms == 0:
            continue

        elapsed_ms = ticks_diff(current_time_ms, last_event_ms)

        if elapsed_ms >= IDLE_TIMEOUT_MS:
            log(f"Idle timeout detected: {elapsed_ms}ms since last event")
            session_manager.end_session()


async def session_periodic_save(
    session_manager: SessionManager
) -> None:
    """
    Periodically save the active session.

    Saves the current session every SAVE_INTERVAL_S seconds without ending it.
    This ensures that session data is preserved even if the device loses power.

    Args:
        session_manager: SessionManager instance to save sessions
    """
    log("Periodic save task started")

    while True:
        await asyncio.sleep(SAVE_INTERVAL_S)

        if session_manager.has_active_session():
            log("Periodic save triggered")
            session_manager.save_current_session()


async def ble_serve_connection(
    connection: aioble.device.DeviceConnection,
    characteristic: aioble.Characteristic,
    state: Any
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
        log(f"[{connection.device.addr_hex()}] {s}")

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
