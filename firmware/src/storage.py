"""
Filesystem storage for session data.

Handles persistent storage of sessions to the ESP32 filesystem with
atomic write operations for data integrity. Each session is stored as
a separate JSON file named by its start_time timestamp.
"""
import uos
from models import Session
from utils import log, atomic_write
from config import config


def save_session(session: Session) -> bool:
    """Save a session to its own JSON file using atomic write.

    Session is saved to {sessions_dir}/{start_time}.json.

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

        # Serialize to JSON
        json_str = session.to_json()

        # Write using atomic write utility
        filename = f"{config.sessions_dir}/{session.start_time}.json"
        success = atomic_write(filename, json_str)

        if success:
            log(f"Saved session {session.start_time} ({session.revolutions} revs)")

        return success

    except Exception as e:
        log(f"Error saving session {session.start_time}: {e}")
        return False


def load_sessions_since(start_time: int) -> list[Session]:
    """Load all sessions that started after the given timestamp.

    Lazy loads only matching sessions from the filesystem.

    Args:
        start_time: Unix timestamp. Returns sessions where s.start_time > start_time.
        sessions_dir: Directory path containing session files.

    Returns:
        List of sessions after the given timestamp, sorted by start_time.
    """
    sessions: list[Session] = []

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

            # Skip if not in range
            if session_start_time <= start_time:
                continue

            # Load the session file
            filepath = f"{config.sessions_dir}/{filename}"
            with open(filepath, 'r') as f:
                json_str = f.read()

            session = Session.from_json(json_str)
            sessions.append(session)

        except (ValueError, OSError) as e:
            log(f"Error loading session file {filename}: {e}")
            continue

    # Sort by start_time
    sessions.sort(key=lambda s: s.start_time)
    log(f"Loaded {len(sessions)} sessions since {start_time}")
    return sessions
