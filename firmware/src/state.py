"""
Session management for tracking cycling sessions.

Manages the lifecycle of sessions: starting, ending, updating, and persisting.
"""
import typing as t
import time
from dataclasses import dataclass, field
from models import Session, SessionStore, Telemetry
from storage import read_session_store, write_session_store
from utils import log


class TelemetryManager:
    # CSC timing constants
    # Time is measured in 1/1024 second units per BLE CSC spec
    TIME_UNIT_HZ = 1024

    def __init__(self) -> None:
        self.current_telemetry: Telemetry = Telemetry()

    def record_revolution(self) -> None:
        """Record a new revolution by updating state in place"""
        current_time_ms = time.ticks_ms()

        # Convert milliseconds to 1/1024 second units
        time_in_units = (current_time_ms * self.TIME_UNIT_HZ) // 1000
        # Wrap at 16 bits (0-65535) per BLE spec
        wrapped_time = time_in_units & 0xFFFF
        # Wrap at 32 bits per spec
        wrapped_revolutions = (
            self.current_telemetry.cumulative_revolutions + 1
        ) & 0xFFFFFFFF  # Wrap at 32 bits

        self.current_telemetry.cumulative_revolutions = wrapped_revolutions
        self.current_telemetry.last_event_time = wrapped_time
        self.current_telemetry.last_physical_time_ms = current_time_ms


class SessionManager:
    """
    Manages cycling session lifecycle and persistence.

    Tracks the currently active session (if any) and maintains the session store.
    """

    def __init__(self) -> None:
        """Initialize the session manager by loading persisted sessions."""
        self.store: SessionStore = read_session_store()
        self.current_session: t.Optional[Session] = None
        log(
            f"SessionManager initialized with {len(self.store.sessions)} stored sessions"
        )

    def start_session(self) -> Session:
        """
        Start a new cycling session.

        Creates a new session with the current timestamp and increments
        the session ID counter.

        Returns:
            The newly created Session
        """
        if self.current_session is not None:
            log("Warning: Starting new session while another is active")

        current_time = int(time.time())
        session_id = self.store.next_id

        self.current_session = Session(
            id=session_id,
            start_time=current_time,
            end_time=current_time,
            revolutions=0,
            synced=False
        )

        self.store.next_id += 1

        log(f"Started session {session_id} at {current_time}")
        return self.current_session

    def end_session(self) -> t.Optional[Session]:
        """
        End the current active session and save it to storage.

        Updates the end_time to now, adds the session to the store,
        and persists to disk.

        Returns:
            The ended Session, or None if no active session
        """
        if self.current_session is None:
            log("No active session to end")
            return None

        # Update end time
        self.current_session.end_time = int(time.time())

        # Add to store
        self.store.sessions.append(self.current_session)

        # Save to disk
        write_session_store(self.store)

        log(f"Ended session {self.current_session.id}: "
            f"{self.current_session.revolutions} revolutions, "
            f"duration={(self.current_session.end_time - self.current_session.start_time)}s")

        ended_session = self.current_session
        self.current_session = None

        return ended_session

    def record_revolution(self) -> None:
        """
        Record a crank revolution in the current session.

        If no session is active, starts a new one.
        Increments the revolution counter and updates the end_time.
        """
        if self.current_session is None:
            self.start_session()

        if self.current_session is not None:
            self.current_session.revolutions += 1
            self.current_session.end_time = int(time.time())
            log(
                f"Session {self.current_session.id}: "
                f"revolution {self.current_session.revolutions}"
            )

    def save_current_session(self) -> bool:
        """
        Save the current active session without ending it.

        This is for periodic persistence of active sessions to prevent
        data loss on unexpected shutdown.

        Returns:
            True if save successful, False otherwise
        """
        if self.current_session is None:
            return True  # Nothing to save

        # Update end time
        self.current_session.end_time = int(time.time())

        # Create a temporary store with just the current session
        # We append it temporarily, save, then remove it
        self.store.sessions.append(self.current_session)
        success = write_session_store(self.store)
        self.store.sessions.pop()  # Remove it (not truly ended yet)

        if success:
            log(f"Saved active session {self.current_session.id} "
                f"({self.current_session.revolutions} revs)")
        else:
            log(f"Failed to save active session {self.current_session.id}")

        return success

    def get_unsynced_sessions(self) -> list[Session]:
        """
        Get all sessions that haven't been synced yet.

        Returns:
            List of unsynced sessions (synced=False)
        """
        unsynced = [s for s in self.store.sessions if not s.synced]
        log(f"Found {len(unsynced)} unsynced sessions")
        return unsynced

    def mark_session_synced(self, session_id: int) -> bool:
        """
        Mark a session as synced.

        Args:
            session_id: ID of the session to mark as synced

        Returns:
            True if session found and marked, False otherwise
        """
        for session in self.store.sessions:
            if session.id == session_id:
                session.synced = True
                write_session_store(self.store)
                log(f"Marked session {session_id} as synced")
                return True

        log(f"Session {session_id} not found")
        return False

    def has_active_session(self) -> bool:
        """Check if there is currently an active session."""
        return self.current_session is not None

    def get_current_session(self) -> t.Optional[Session]:
        """Get the current active session, if any."""
        return self.current_session


@dataclass
class AppState:
    """
    Mutable application state container.

    Encapsulates all mutable state in one place to avoid module-level globals.
    """
    telemetry_manager: TelemetryManager = field(
        default_factory=TelemetryManager
    )
    session_manager: SessionManager = field(default_factory=SessionManager)
