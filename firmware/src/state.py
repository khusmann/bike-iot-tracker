"""
Session management for tracking cycling sessions.

Manages the lifecycle of sessions: starting, ending, updating, and persisting.
"""
import time
import typing as t
from udataclasses import dataclass, field

from models import Session, SessionStore, CrankTelemetry
from storage import read_session_store, write_session_store
from utils import log

# File to save sessions to
SESSIONS_FILE = "/sessions.json"

# Minimum session duration in seconds (5 minutes)
SESSION_MIN_DURATION_S = 5 * 60


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

    Tracks the currently active session (if any) and maintains the session store.

    Attributes:
        SESSIONS_FILE: Path to sessions JSON file.
        store: Persistent session store.
        current_session: Currently active session, if any.
    """
    store: SessionStore = field(
        default_factory=lambda: read_session_store(SESSIONS_FILE)
    )
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

        Sessions shorter than SESSION_MIN_DURATION_S seconds are discarded and not saved.

        Returns:
            The ended Session, or None if no active session or session too short.
        """
        if self.current_session is None:
            log("No active session to end")
            return None

        # Calculate duration
        duration_s = self.current_session.end_time - self.current_session.start_time

        # Discard sessions shorter than minimum duration
        if duration_s < SESSION_MIN_DURATION_S:
            log(f"Discarded short session {self.current_session.start_time}: "
                f"{self.current_session.revolutions} revolutions, "
                f"duration={duration_s}s (< {SESSION_MIN_DURATION_S}s minimum)")
            self.current_session = None
            return None

        # Add to store
        self.store.sessions.append(self.current_session)

        # Save to disk
        write_session_store(self.store, SESSIONS_FILE)

        log(f"Ended session {self.current_session.start_time}: "
            f"{self.current_session.revolutions} revolutions, "
            f"duration={duration_s}s")

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

    def save_current_session(self) -> bool:
        """Save the current active session without ending it.

        This is for periodic persistence of active sessions to prevent
        data loss on unexpected shutdown.

        Returns:
            True if save successful, False otherwise.
        """
        if self.current_session is None:
            return True  # Nothing to save

        # Update end time
        self.current_session.end_time = int(time.time())

        # Create a temporary store with just the current session
        # We append it temporarily, save, then remove it
        self.store.sessions.append(self.current_session)
        success = write_session_store(self.store, SESSIONS_FILE)
        self.store.sessions.pop()  # Remove it (not truly ended yet)

        if success:
            log(f"Saved active session {self.current_session.start_time} "
                f"({self.current_session.revolutions} revs)")
        else:
            log(f"Failed to save active session {self.current_session.start_time}")

        return success

    def get_sessions_since(self, start_time: int) -> list[Session]:
        """Get all sessions that started after the given timestamp.

        Returns sessions sorted by start_time in ascending order.

        Args:
            start_time: Unix timestamp. Returns sessions where s.start_time > start_time.

        Returns:
            List of sessions after the given timestamp, sorted by start_time.
        """
        sessions = [s for s in self.store.sessions if s.start_time > start_time]
        sessions.sort(key=lambda s: s.start_time)
        log(f"Found {len(sessions)} sessions since {start_time}")
        return sessions

    def has_active_session(self) -> bool:
        """Check if there is currently an active session.

        Returns:
            True if a session is active, False otherwise.
        """
        return self.current_session is not None

    def get_current_session(self) -> t.Optional[Session]:
        """Get the current active session, if any.

        Returns:
            Current session or None.
        """
        return self.current_session


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
