"""
Session data structures and JSON serialization.

Defines the core data model for tracking cycling sessions.
"""
from __future__ import annotations

import json
import struct
import typing as t

from udataclasses import dataclass, field


@dataclass
class CrankTelemetry:
    """Crank telemetry tracking.

    Attributes:
        cumulative_revolutions: Total crank revolutions (wraps at 32 bits).
        last_event_time: Last event time in 1/1024 second units (wraps at 16 bits).
        last_physical_time_ms: Last event physical time in milliseconds.
    """
    cumulative_revolutions: int = 0
    last_event_time: int = 0
    last_physical_time_ms: int = 0

    def to_csc_measurement(self) -> bytes:
        """Format telemetry as CSC Measurement per BLE spec.

        Returns:
            7-byte CSC measurement packet:
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
    """Single cycling session.

    Attributes:
        id: Unique session identifier (monotonically increasing).
        start_time: Unix timestamp in seconds when session started.
        end_time: Unix timestamp in seconds when session ended (or last update).
        revolutions: Total crank revolutions in this session.
        synced: Whether this session has been synced to the mobile app.
    """
    id: int
    start_time: int
    end_time: int
    revolutions: int
    synced: bool = False

    def to_dict(self) -> dict[str, t.Any]:
        """Convert Session to dictionary for JSON serialization.

        Returns:
            Dictionary representation of session.
        """
        return {
            "id": self.id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "revolutions": self.revolutions,
            "synced": self.synced
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
            id=data["id"],
            start_time=data["start_time"],
            end_time=data["end_time"],
            revolutions=data["revolutions"],
            synced=data.get("synced", False)
        )


@dataclass
class SessionStore:
    """Container for all sessions and metadata.

    Attributes:
        sessions: List of all stored sessions.
        next_id: Next available session ID (auto-increments).
    """
    sessions: list[Session] = field(default_factory=lambda: [])
    next_id: int = 0

    def to_dict(self) -> dict[str, t.Any]:
        """Convert SessionStore to dictionary for JSON serialization.

        Returns:
            Dictionary representation of session store.
        """
        return {
            "sessions": [s.to_dict() for s in self.sessions],
            "next_id": self.next_id
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
        next_id = data.get("next_id", 0)
        return SessionStore(sessions=sessions, next_id=next_id)

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
