"""
Session data structures and JSON serialization.

Defines the core data model for tracking cycling sessions.
"""
import json
import typing as t

from udataclasses import dataclass, field


@dataclass
class CrankTelemetry:
    """Crank telemetry tracking.

    Attributes:
        cumulative_revolutions: Total crank revolutions (wraps at 16 bits per CSC spec).
        last_physical_time_ms: Last event physical time in milliseconds.
    """
    cumulative_revolutions: int = 0
    last_physical_time_ms: int = 0


@dataclass
class Session:
    """Single cycling session.

    The start_time serves as the unique identifier for the session.
    This design supports multiple sync clients and survives storage resets,
    as timestamps are naturally monotonic and unique (30s minimum between sessions).

    Attributes:
        start_time: Unix timestamp in seconds when session started (serves as unique ID).
        end_time: Unix timestamp in seconds when session ended (or last update).
        revolutions: Total crank revolutions in this session.
    """
    start_time: int = 0
    end_time: int = 0
    revolutions: int = 0

    def to_dict(self) -> dict[str, t.Any]:
        """Convert Session to dictionary for JSON serialization.

        Returns:
            Dictionary representation of session.
        """
        return {
            "start_time": self.start_time,
            "end_time": self.end_time,
            "revolutions": self.revolutions,
        }

    @classmethod
    def from_dict(cls, data: dict[str, t.Any]):
        """Create Session from dictionary (JSON deserialization).

        Args:
            data: Dictionary containing session data.

        Returns:
            Session instance.
        """
        return Session(
            start_time=data["start_time"],
            end_time=data["end_time"],
            revolutions=data["revolutions"],
        )


@dataclass
class SessionStore:
    """Container for all sessions.

    Sessions are identified by their start_time timestamp, so no separate
    ID counter is needed.

    Attributes:
        sessions: List of all stored sessions, sorted by start_time.
    """
    sessions: list[Session] = field(default_factory=lambda: [])

    def to_dict(self) -> dict[str, t.Any]:
        """Convert SessionStore to dictionary for JSON serialization.

        Returns:
            Dictionary representation of session store.
        """
        return {
            "sessions": [s.to_dict() for s in self.sessions],
        }

    @classmethod
    def from_dict(cls, data: dict[str, t.Any]):
        """Create SessionStore from dictionary (JSON deserialization).

        Args:
            data: Dictionary containing session store data.

        Returns:
            SessionStore instance.
        """
        sessions = [Session.from_dict(s) for s in data.get("sessions", [])]
        # Sort sessions by start_time to maintain consistent ordering
        sessions.sort(key=lambda s: s.start_time)
        return SessionStore(sessions=sessions)

    def to_json(self) -> str:
        """Serialize SessionStore to JSON string.

        Returns:
            JSON string representation.
        """
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, json_str: str):
        """Deserialize SessionStore from JSON string.

        Args:
            json_str: JSON string to deserialize.

        Returns:
            SessionStore instance.
        """
        data = json.loads(json_str)
        return SessionStore.from_dict(data)
