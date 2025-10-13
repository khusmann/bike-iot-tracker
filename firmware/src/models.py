"""
Session data structures and JSON serialization.

Defines the core data model for tracking cycling sessions.
"""
import typing as t
import struct
from udataclasses import dataclass, field
import json


@dataclass(frozen=True)
class Telemetry:
    """Mutable state for crank telemetry tracking"""
    cumulative_revolutions: int = 0
    last_event_time: int = 0
    last_physical_time_ms: int = 0

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
class Session:
    """
    Represents a single cycling session.

    Attributes:
        id: Unique session identifier (monotonically increasing)
        start_time: Unix timestamp in seconds when session started
        end_time: Unix timestamp in seconds when session ended (or last update)
        revolutions: Total crank revolutions in this session
        synced: Whether this session has been synced to the mobile app
    """
    id: int
    start_time: int
    end_time: int
    revolutions: int
    synced: bool = False

    def to_dict(self) -> dict[str, t.Any]:
        """Convert a Session to a dictionary for JSON serialization."""
        return {
            "id": self.id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "revolutions": self.revolutions,
            "synced": self.synced
        }

    @classmethod
    def from_dict(cls, data: dict[str, t.Any]):
        """Create a Session from a dictionary (JSON deserialization)."""
        return Session(
            id=data["id"],
            start_time=data["start_time"],
            end_time=data["end_time"],
            revolutions=data["revolutions"],
            synced=data.get("synced", False)
        )


@dataclass
class SessionStore:
    """
    Container for all sessions and metadata.

    Attributes:
        sessions: List of all stored sessions
        next_id: Next available session ID (auto-increments)
    """
    sessions: list[Session] = field(default_factory=lambda: [])
    next_id: int = 0

    def to_dict(self) -> dict[str, t.Any]:
        """Convert a SessionStore to a dictionary for JSON serialization."""
        return {
            "sessions": [s.to_dict() for s in self.sessions],
            "next_id": self.next_id
        }

    @classmethod
    def from_dict(cls, data: dict[str, t.Any]):
        """Create a SessionStore from a dictionary (JSON deserialization)."""
        sessions = [Session.from_dict(s) for s in data.get("sessions", [])]
        next_id = data.get("next_id", 0)
        return SessionStore(sessions=sessions, next_id=next_id)

    def to_json(self) -> str:
        """Serialize a SessionStore to JSON string."""
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, json_str: str):
        """Deserialize a SessionStore from JSON string."""
        data = json.loads(json_str)
        return SessionStore.from_dict(data)
