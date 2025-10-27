"""
Filesystem storage for session data.

Handles persistent storage of sessions to the ESP32 filesystem with
atomic write operations for data integrity. Each session is stored as
a separate JSON file named by its start_time timestamp.
"""
import typing as t
import uos
from models import Session
from utils import log, atomic_write
from config import config


def save_session(session: Session) -> bool:
    """Save a session to its own JSON file using atomic write.

    Session is saved to {sessions_dir}/{start_time}.json.
    The session's version is incremented before each save to support
    HealthConnect upsert functionality.

    Args:
        session: Session to save.
        sessions_dir: Directory path for session files.

    Returns:
        True if save successful, False otherwise.
    """
    try:
        # Create directory if it doesn't exist
        try:
            uos.mkdir(config.sessions_dir)
            log(f"Created sessions directory: {config.sessions_dir}")
        except OSError:
            pass  # Directory already exists

        # Increment version before saving
        session.version += 1

        # Serialize to JSON
        json_str = session.to_json()

        # Write using atomic write utility
        filename = f"{config.sessions_dir}/{session.start_time}.json"
        success = atomic_write(filename, json_str)

        if success:
            log(f"Saved session {session.start_time} ({session.revolutions} revs, v{session.version})")

        return success

    except Exception as e:
        log(f"Error saving session {session.start_time}: {e}")
        return False


def available_sessions() -> list[int]:
    """Get list of available session start times from filesystem.

    Returns session IDs (start_time values) by reading filenames only,
    without loading the full session data.

    Returns:
        List of session start_time values, sorted chronologically.
    """
    session_ids: list[int] = []

    try:
        files = uos.listdir(config.sessions_dir)
    except OSError as e:
        log(f"Error reading sessions directory: {e}")
        return []

    for filename in files:
        # Skip non-JSON files and temp files
        if not filename.endswith('.json') or filename.endswith('.tmp'):
            continue

        try:
            # Extract start_time from filename
            session_start_time = int(filename.replace('.json', ''))
            session_ids.append(session_start_time)
        except ValueError as e:
            log(f"Invalid session filename {filename}: {e}")
            continue

    session_ids.sort()
    return session_ids


def load_session(start_time: int) -> t.Optional[Session]:
    """Load a single session by its start_time.

    Args:
        start_time: The session's start_time (used as unique identifier).

    Returns:
        The Session object, or None if not found or error loading.
    """
    try:
        filepath = f"{config.sessions_dir}/{start_time}.json"
        with open(filepath, 'r') as f:
            json_str = f.read()

        session = Session.from_json(json_str)
        return session

    except (OSError, ValueError) as e:
        log(f"Error loading session {start_time}: {e}")
        return None
