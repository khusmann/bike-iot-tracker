"""
Filesystem storage for session data.

Handles persistent storage of sessions to the ESP32 filesystem with
atomic write operations for data integrity.
"""
import os
from models import SessionStore
from utils import log


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

    Atomic write pattern:
    1. Write to temporary file
    2. Rename temporary file to target (atomic operation on most filesystems)

    Args:
        store: SessionStore to save

    Returns:
        True if save successful, False otherwise
    """
    temp_filename = filename + ".tmp"

    try:
        # Serialize to JSON
        json_str = store.to_json()

        # Write to temporary file
        with open(temp_filename, 'w') as f:
            f.write(json_str)

        # Atomic rename
        try:
            # Remove target file if it exists (required on some filesystems)
            try:
                os.remove(filename)
            except OSError:
                pass  # File doesn't exist, that's fine

            # Rename temp file to target
            os.rename(temp_filename, filename)

        except Exception as e:
            log(f"Error during atomic rename: {e}")
            return False

        log(f"Saved {len(store.sessions)} sessions to storage")
        return True

    except Exception as e:
        log(f"Error saving sessions: {e}")
        return False

    finally:
        # Clean up temp file if it still exists
        try:
            os.remove(temp_filename)
        except OSError:
            pass  # Temp file doesn't exist, that's fine
