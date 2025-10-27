"""
BLE Sync Service for session data synchronization.

Implements a timestamp-based sync protocol that supports multiple clients.

The sync protocol uses:
1. Session Data (WRITE with response) - Client-driven loop
   - Write: uint32 lastSyncedStartTime (little-endian)
   - Response: JSON {"session": {...}, "remaining_sessions": N}
   - Client tracks their own lastSyncedStartTime locally
   - Server returns next session where start_time > lastSyncedStartTime

Key features:
- Multi-client safe: each client independently syncs from their last timestamp
- No server-side sync state: clients manage their own progress
- Survives storage resets: new sessions always have later timestamps

TODO: Add delete/cleanup protocol
- Sessions are currently kept indefinitely on the device
- Future: Add characteristic for client to confirm sync and trigger cleanup
- This will prevent flash wear from accumulating old session files
"""
import asyncio
import json
import struct
import typing as t

import aioble
import bluetooth

from models import Session
from state import SessionManager
from utils import log, unix_to_micropython_timestamp, micropython_to_unix_timestamp


# Sync Service UUID
SYNC_SERVICE_UUID = bluetooth.UUID("0000FF00-0000-1000-8000-00805f9b34fb")

# Characteristic UUIDs
SESSION_DATA_UUID = bluetooth.UUID(0xFF01)   # WRITE (with response)


def register_sync_service(session_manager: SessionManager) -> aioble.Service:
    """Register the BLE Sync Service with Session Data characteristic.

    Creates and registers:
    - Session Data characteristic (WRITE with response)
      Client writes uint32 timestamp, server responds with next session JSON

    Background task handles the write requests for Session Data.

    Args:
        session_manager: SessionManager for handling sync requests.

    Returns:
        The registered Sync Service with background task started.
    """
    # Create the service
    sync_service = aioble.Service(SYNC_SERVICE_UUID)

    # Session Data characteristic (READ/WRITE)
    # Use capture=True to get both connection and data in written()
    session_data_char = aioble.BufferedCharacteristic(
        sync_service,
        SESSION_DATA_UUID,
        read=True,
        write=True,
        capture=True,
        max_len=200,  # Allow up to 200 bytes for JSON response
        initial=b'',
    )

    # Start background task to handle writes
    asyncio.create_task(
        handle_session_data_requests(session_data_char, session_manager)
    )

    log("Sync Service registered")

    return sync_service


def parse_last_synced_timestamp(request_data: bytes) -> int:
    """Parse last synced timestamp from request bytes.

    Android sends timestamps in Unix epoch (1970), but MicroPython uses epoch 2000.
    This function converts the incoming Unix timestamp to MicroPython epoch for
    comparison with stored sessions.

    Args:
        request_data: Raw request bytes (should be 4 bytes uint32 little-endian)

    Returns:
        Parsed timestamp as integer (converted to MicroPython epoch 2000)

    Raises:
        ValueError: If request_data is invalid (wrong length or format)
    """
    if len(request_data) != 4:
        raise ValueError(
            f"Invalid request length: {len(request_data)} (expected 4 bytes)"
        )

    try:
        # Parse Unix epoch timestamp from Android
        unix_timestamp = struct.unpack('<I', request_data)[0]

        # Convert Unix epoch (1970) to MicroPython epoch (2000)
        micropython_timestamp = unix_to_micropython_timestamp(unix_timestamp)

    except struct.error as e:
        raise ValueError(f"Failed to parse request: {e}")

    return micropython_timestamp


def session_to_unix_dict(session: Session) -> t.Dict[str, t.Any]:
    """Convert a Session to dictionary with Unix epoch timestamps.

    The sync protocol uses Unix epoch (1970) for compatibility with standard systems,
    but sessions are stored with MicroPython epoch (2000) internally.

    Args:
        session: Session to convert

    Returns:
        Dictionary with timestamps converted to Unix epoch (1970)
    """
    session_dict = session.to_dict()
    return {
        "start_time": micropython_to_unix_timestamp(session_dict["start_time"]),
        "end_time": micropython_to_unix_timestamp(session_dict["end_time"]),
        "revolutions": session_dict["revolutions"],
    }


def build_sync_response_dict(sessions: t.List[Session]) -> t.Dict[str, t.Any]:
    """Build sync response dictionary from sessions list.

    Pure function that formats sessions into the sync protocol response format.

    Args:
        sessions: List of sessions to include in response (should be sorted by start_time)

    Returns:
        Response dict with:
        - If sessions is empty: {"session": None, "remaining_sessions": 0}
        - Otherwise: {"session": {...}, "remaining_sessions": N}
          where N is the count of remaining sessions after the first one

    Note:
        Session timestamps are converted from MicroPython epoch (2000) to Unix epoch (1970)
        for compatibility with Android/standard systems.
    """
    n = len(sessions)
    return {
        "session": session_to_unix_dict(sessions[0]) if n > 0 else None,
        "remaining_sessions": max(n - 1, 0)
    }


def process_session_data_request(
    request_data: bytes,
    session_manager: SessionManager
) -> bytes:
    """Process a single Session Data request and return the response.

    Orchestrates the sync request handling:
    1. Parses the request bytes to extract lastSyncedStartTime
    2. Queries sessions from session_manager
    3. Builds response dict
    4. Encodes to JSON bytes

    Protocol:
    - Input: uint32 lastSyncedStartTime (little-endian, 4 bytes)
    - Output: JSON bytes with {"session": {...}, "remaining_sessions": N}
              or {"error": "..."} on error

    Args:
        request_data: Raw request bytes (should be 4 bytes uint32)
        session_manager: SessionManager to lookup sessions

    Returns:
        JSON response as bytes
    """
    # Parse request (handles validation)
    try:
        last_synced = parse_last_synced_timestamp(request_data)
    except ValueError as e:
        error = {"error": str(e)}
        log(f"Request parse error: {e}")
        return json.dumps(error).encode('utf-8')

    log(f"Session Data request since {last_synced}")

    # Query completed sessions (automatically excludes current active session)
    sessions = session_manager.load_sessions_since(last_synced)

    # Build response dict
    response_dict = build_sync_response_dict(sessions)

    # Log what we're returning
    if response_dict["session"] is None:
        log("No more sessions to sync")
    else:
        remaining = response_dict["remaining_sessions"]
        session_start = response_dict["session"]["start_time"]
        log(f"Returning session {session_start}, {remaining} remaining")

    # Encode to JSON bytes
    json_str = json.dumps(response_dict)
    response = json_str.encode('utf-8')
    log(f"Response size: {len(response)} bytes")
    return response


async def handle_session_data_requests(
    characteristic: aioble.Characteristic,
    session_manager: SessionManager
) -> None:
    """Background task to handle Session Data write requests.

    Async loop that:
    1. Waits for BLE write requests
    2. Processes each request via process_session_data_request()
    3. Writes response back to characteristic

    MTU Requirements:
    - Response size is ~102 bytes (session JSON + remaining count)
    - Requires MTU >= 185 bytes (including BLE overhead)
    - Client MUST negotiate higher MTU on connection (default is 23 bytes)
    - Android: Call gatt.requestMtu(512) in onConnectionStateChange
    - Desktop clients: Usually automatic or default is sufficient

    Args:
        characteristic: Session Data characteristic
        session_manager: SessionManager to lookup sessions
    """
    while True:
        try:
            # Wait for a write (capture=True returns tuple of (connection, data))
            write_data = await characteristic.written()

            assert isinstance(write_data, tuple)

            connection, request_data = write_data

            log(f"[{connection.device.addr_hex()}] Session Data write")

            # Process request using pure function
            response = process_session_data_request(
                request_data, session_manager
            )

            # Write response to characteristic (client will read it)
            characteristic.write(response)

        except Exception as e:
            log(f"Session Data handler error: {e}")
            await asyncio.sleep(1)
