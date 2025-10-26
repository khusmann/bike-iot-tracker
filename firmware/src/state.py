"""
Session management for tracking cycling sessions.

Manages the lifecycle of sessions: starting, ending, updating, and persisting.
"""
import time
import typing as t
from udataclasses import dataclass, field

from config import config
from models import Session, CrankTelemetry
from storage import save_session
from utils import log


@dataclass
class TelemetryManager:
    """Manages telemetry state for BLE CSC notifications.

    Attributes:
        crank_telemetry: Current telemetry state.
    """

    crank_telemetry: CrankTelemetry = field(default_factory=CrankTelemetry)

    def record_revolution(self) -> None:
        """Record a new revolution by updating state in place."""
        current_time_ms = time.ticks_ms()

        # Wrap at 16 bits per CSC spec
        wrapped_revolutions = (
            self.crank_telemetry.cumulative_revolutions + 1
        ) & 0xFFFF

        self.crank_telemetry.cumulative_revolutions = wrapped_revolutions
        self.crank_telemetry.last_physical_time_ms = current_time_ms


@dataclass
class SessionManager:
    """Manages cycling session lifecycle and persistence.

    Tracks the currently active session (if any). Sessions are stored as
    individual files in the sessions directory, with lazy loading on demand.

    Attributes:
        current_session: Currently active session, if any.
    """
    current_session: t.Optional[Session] = None

    def start_session(self) -> Session:
        """Start a new cycling session.

        Creates a new session with the current timestamp as its unique identifier.

        Returns:
            The newly created Session.
        """
        if self.current_session is not None:
            log("Warning: Starting new session while another is active")

        current_time = int(time.time())

        self.current_session = Session(
            start_time=current_time,
            end_time=current_time,
            revolutions=0,
        )

        log(f"Started session at {current_time}")
        return self.current_session

    def end_session(self) -> t.Optional[Session]:
        """End the current active session and save it to storage.

        Sessions shorter than config.session_min_duration_s seconds are discarded and not saved.

        Returns:
            The ended Session, or None if no active session or session too short.
        """
        if self.current_session is None:
            log("No active session to end")
            return None

        # Save final state to disk
        self.maybe_save_current_session()

        log(f"Ended session {self.current_session.start_time}: "
            f"{self.current_session.revolutions} revolutions, ")

        ended_session = self.current_session

        self.current_session = None

        return ended_session

    def record_revolution(self) -> None:
        """Record a crank revolution in the current session.

        If no session is active, starts a new one.
        Increments the revolution counter and updates the end_time.
        """
        session = self.current_session or self.start_session()
        session.revolutions += 1
        session.end_time = int(time.time())
        log(f"Session {session.start_time}: revolution {session.revolutions}")

    def maybe_save_current_session(self) -> bool:
        """Save the current active session if conditions are met.

        This is for periodic persistence of active sessions to prevent
        data loss on unexpected shutdown. Only saves if:
        - There is an active session
        - Session meets minimum duration requirement

        Returns:
            True if save successful or no save needed, False on error.
        """
        if self.current_session is None:
            return True  # No active session

        # Update end time
        self.current_session.end_time = int(time.time())

        # Calculate duration
        duration_s = self.current_session.end_time - self.current_session.start_time

        # Don't save if session hasn't met minimum duration yet
        if duration_s < config.session_min_duration_s:
            log(f"Skipping save of short session {self.current_session.start_time}: "
                f"duration={duration_s}s (< {config.session_min_duration_s}s minimum)")
            return True  # Not an error, just too short

        # Save to its own file
        success = save_session(self.current_session)

        if not success:
            log(f"Failed to save active session {self.current_session.start_time}")

        return success


@dataclass
class AppState:
    """Mutable application state container.

    Encapsulates all mutable state in one place to avoid module-level globals.

    Attributes:
        telemetry_manager: Manages BLE telemetry state.
        session_manager: Manages session lifecycle and persistence.
    """
    telemetry_manager: TelemetryManager = field(
        default_factory=TelemetryManager
    )
    session_manager: SessionManager = field(default_factory=SessionManager)
