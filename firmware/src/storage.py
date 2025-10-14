"""
Filesystem storage for session data.

Handles persistent storage of sessions to the ESP32 filesystem with
atomic write operations for data integrity.
"""
from models import SessionStore
from utils import log, atomic_write


def read_session_store(filename: str) -> SessionStore:
    """Load sessions from filesystem.

    Handles missing files, corrupted JSON, and I/O errors gracefully by
    returning an empty store.

    Args:
        filename: Path to the session store JSON file.

    Returns:
        SessionStore with loaded data, or empty store on error.
    """
    try:
        # Read file contents
        with open(filename, 'r') as f:
            json_str = f.read()
    except OSError as e:
        log(f"Error opening sessions file: {e}")
        log("Returning empty store")
        return SessionStore()

    try:
        # Parse JSON
        store = SessionStore.from_json(json_str)
        log(f"Loaded {len(store.sessions)} sessions from storage")
        return store
    except ValueError as e:
        log(f"Error parsing sessions file: {e}")
        log("Returning empty store")
        return SessionStore()


def write_session_store(store: SessionStore, filename: str) -> bool:
    """Save sessions to filesystem using atomic write.

    Args:
        store: SessionStore to save.
        filename: Target file path.

    Returns:
        True if save successful, False otherwise.
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
