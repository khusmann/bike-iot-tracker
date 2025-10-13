"""
Session management for tracking cycling sessions.

Manages the lifecycle of sessions: starting, ending, updating, and persisting.
"""
from typing import Optional
import time
from session import Session, SessionStore
from storage import load_sessions, save_sessions
from utils import log


class SessionManager:
    """
    Manages cycling session lifecycle and persistence.

    Tracks the currently active session (if any) and maintains the session store.
    """

    def __init__(self) -> None:
        """Initialize the session manager by loading persisted sessions."""
        self.store: SessionStore = load_sessions()
        self.current_session: Optional[Session] = None
        log(f"SessionManager initialized with {len(self.store.sessions)} stored sessions")

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

    def end_session(self) -> Optional[Session]:
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
        save_sessions(self.store)

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
            log(f"Session {self.current_session.id}: "
                f"revolution {self.current_session.revolutions}")

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
        success = save_sessions(self.store)
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
                save_sessions(self.store)
                log(f"Marked session {session_id} as synced")
                return True

        log(f"Session {session_id} not found")
        return False

    def has_active_session(self) -> bool:
        """Check if there is currently an active session."""
        return self.current_session is not None

    def get_current_session(self) -> Optional[Session]:
        """Get the current active session, if any."""
        return self.current_session
