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
"""
import asyncio
import json
import struct

import aioble
import bluetooth

from state import SessionManager
from utils import log


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
        _handle_session_data_writes(session_data_char, session_manager)
    )

    log("Sync Service registered")

    return sync_service


async def _handle_session_data_writes(
    characteristic: aioble.Characteristic,
    session_manager: SessionManager
) -> None:
    """Background task to handle Session Data write requests.

    Protocol:
    1. Client writes uint32 lastSyncedStartTime (little-endian)
    2. Server finds next session where start_time > lastSyncedStartTime
    3. Server responds with JSON:
       {"session": {...}, "remaining_sessions": N} or
       {"session": null, "remaining_sessions": 0} if no more sessions

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

            # Parse and handle request
            try:
                if len(request_data) != 4:
                    error = {"error": "Invalid request length (expected 4 bytes)"}
                    response = json.dumps(error).encode('utf-8')
                else:
                    # Parse uint32 lastSyncedStartTime
                    last_synced = struct.unpack('<I', request_data)[0]
                    log(f"Session Data request since {last_synced}")

                    # Get sessions after this timestamp
                    sessions = session_manager.get_sessions_since(last_synced)

                    if len(sessions) == 0:
                        # No more sessions
                        response_dict = {
                            "session": None,
                            "remaining_sessions": 0
                        }
                        log("No more sessions to sync")
                    else:
                        # Return first session and count remaining
                        next_session = sessions[0]
                        remaining = len(sessions) - 1

                        response_dict = {
                            "session": next_session.to_dict(),
                            "remaining_sessions": remaining
                        }
                        log(f"Returning session {next_session.start_time}, "
                            f"{remaining} remaining")

                    json_str = json.dumps(response_dict)
                    response = json_str.encode('utf-8')
                    log(f"Response size: {len(response)} bytes")

                # Write response to characteristic (client will read it)
                characteristic.write(response)

            except Exception as e:
                error = {"error": f"Request error: {e}"}
                log(error["error"])
                characteristic.write(json.dumps(error).encode('utf-8'))

        except Exception as e:
            log(f"Session Data handler error: {e}")
            await asyncio.sleep(1)
