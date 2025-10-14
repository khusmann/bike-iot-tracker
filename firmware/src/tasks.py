"""
Background tasks for the application.

All async background tasks are defined here. This centralizes task
orchestration and makes the concurrent structure of the application
easy to understand.
"""
import asyncio
from time import ticks_ms, ticks_diff

from state import SessionManager, AppState
from utils import log

# Session boundary detection: end session after 10 minutes of inactivity
# IDLE_TIMEOUT_MS = 10 * 60 * 1000  # 10 minutes in milliseconds
IDLE_TIMEOUT_MS = 30 * 1000  # 30 seconds in milliseconds (for debug)

# Periodic persistence: save active session every 5 minutes
SAVE_INTERVAL_S = 5 * 60  # 5 minutes in seconds


async def session_idle_timeout(
    session_manager: SessionManager,
    state: AppState
) -> None:
    """Monitor for idle periods and automatically end sessions.

    Checks the last_physical_time_ms from telemetry state. If more than
    IDLE_TIMEOUT_MS has elapsed without a crank event, ends the current session.

    Args:
        session_manager: SessionManager instance to end sessions.
        state: Application state containing telemetry.
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
        last_event_ms = state.telemetry_manager.crank_telemetry.last_physical_time_ms

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
    """Periodically save the active session.

    Saves the current session every SAVE_INTERVAL_S seconds without ending it.
    This ensures that session data is preserved even if the device loses power.

    Args:
        session_manager: SessionManager instance to save sessions.
    """
    log("Periodic save task started")

    while True:
        await asyncio.sleep(SAVE_INTERVAL_S)

        if session_manager.has_active_session():
            log("Periodic save triggered")
            session_manager.save_current_session()
