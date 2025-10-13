"""
Filesystem storage for session data.

Handles persistent storage of sessions to the ESP32 filesystem with
atomic write operations for data integrity.
"""
import os
from models import SessionStore
from utils import log, atomic_write


def read_session_store(filename: str) -> SessionStore:
    """
    Load sessions from filesystem.

    Returns:
        SessionStore with loaded data, or empty store if file doesn't exist

    Handles:
        - Missing file (returns empty store)
        - Corrupted JSON (logs error, returns empty store)
        - Other I/O errors (logs error, returns empty store)
    """
    try:
        # Check if file exists
        try:
            os.stat(filename)
        except OSError:
            # File doesn't exist - return empty store
            log("No sessions file found, initializing empty store")
            return SessionStore()

        # Read file contents
        with open(filename, 'r') as f:
            json_str = f.read()

        # Parse JSON
        store = SessionStore.from_json(json_str)
        log(f"Loaded {len(store.sessions)} sessions from storage")
        return store

    except ValueError as e:
        # JSON parsing error
        log(f"Error parsing sessions file: {e}")
        log("Returning empty store")
        return SessionStore()

    except Exception as e:
        # Other errors
        log(f"Error loading sessions: {e}")
        log("Returning empty store")
        return SessionStore()


def write_session_store(store: SessionStore, filename: str) -> bool:
    """
    Save sessions to filesystem using atomic write.

    Args:
        store: SessionStore to save
        filename: Target file path

    Returns:
        True if save successful, False otherwise
    """
    try:
        # Serialize to JSON
        json_str = store.to_json()

        # Write using atomic write utility
        success = atomic_write(filename, json_str)

        if success:
            log(f"Saved {len(store.sessions)} sessions to storage")

        return success

    except Exception as e:
        log(f"Error saving sessions: {e}")
        return False
