"""
Session data structures and JSON serialization.

Defines the core data model for tracking cycling sessions.
"""
import json
import typing as t

from udataclasses import dataclass


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
        version: Incremented each time the session is saved. Used for HealthConnect upsert.
    """
    start_time: int = 0
    end_time: int = 0
    revolutions: int = 0
    version: int = 0

    def to_dict(self) -> dict[str, t.Any]:
        """Convert Session to dictionary for JSON serialization.

        Returns:
            Dictionary representation of session with timestamps in native
            MicroPython epoch (seconds since 2000-01-01).
        """
        return {
            "start_time": self.start_time,
            "end_time": self.end_time,
            "revolutions": self.revolutions,
            "version": self.version,
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
            version=data["version"],
        )

    def to_json(self) -> str:
        """Serialize Session to JSON string.

        Returns:
            JSON string representation.
        """
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, json_str: str):
        """Deserialize Session from JSON string.

        Args:
            json_str: JSON string to deserialize.

        Returns:
            Session instance.
        """
        data = json.loads(json_str)
        return Session.from_dict(data)
