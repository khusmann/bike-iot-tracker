"""
BLE Sync Service for session data synchronization.

Provides characteristics for reading session metadata and transferring
session data to Android app.

The sync protocol uses:
1. Session Range (READ) - Returns JSON with unsynced session range
2. Session Data (READ/WRITE) - Write session_id request, read JSON response
3. Mark Synced (READ/WRITE) - Write session_id request, read JSON response
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
SESSION_RANGE_UUID = bluetooth.UUID(0xFF01)  # READ
SESSION_DATA_UUID = bluetooth.UUID(0xFF02)   # READ/WRITE
MARK_SYNCED_UUID = bluetooth.UUID(0xFF03)    # READ/WRITE


def create_session_range_response(session_manager: SessionManager) -> bytes:
    """Create JSON response for Session Range characteristic.

    Returns metadata about unsynced sessions: the starting ID and count.

    Args:
        session_manager: SessionManager to query for unsynced sessions.

    Returns:
        JSON bytes: {"start": <first_unsynced_id>, "count": <num_unsynced>}
    """
    unsynced = session_manager.get_unsynced_sessions()

    if len(unsynced) == 0:
        response = {"start": 0, "count": 0}
    else:
        # Find the range of unsynced session IDs
        first_id = unsynced[0].id
        last_id = unsynced[-1].id
        count = last_id - first_id + 1
        response = {"start": first_id, "count": count}

    json_str = json.dumps(response)
    log(f"Session Range response: {json_str}")
    return json_str.encode('utf-8')


def register_sync_service(session_manager: SessionManager) -> aioble.Service:
    """Register the BLE Sync Service with all characteristics.

    Creates and registers:
    - Session Range characteristic (READ)
    - Session Data characteristic (READ/WRITE)
    - Mark Synced characteristic (READ/WRITE)

    Background tasks handle the write requests for Session Data and Mark Synced.

    Args:
        session_manager: SessionManager for handling sync requests.

    Returns:
        The registered Sync Service with background tasks started.
    """
    # Create the service
    sync_service = aioble.Service(SYNC_SERVICE_UUID)

    # Session Range characteristic (READ only)
    # Override on_read to dynamically generate response
    session_range_char = aioble.Characteristic(
        sync_service,
        SESSION_RANGE_UUID,
        read=True,
        write=False,
        notify=False,
        indicate=False
    )

    # Override the on_read method to provide custom handler
    def session_range_on_read(connection: aioble.device.DeviceConnection):  # type: ignore
        log(f"[{connection.device.addr_hex()}] Session Range read")
        response = create_session_range_response(session_manager)
        session_range_char.write(response)
        return 0  # Return 0 to use the data written to the characteristic

    session_range_char.on_read = session_range_on_read

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

    # Mark Synced characteristic (READ/WRITE)
    # Use capture=True to get both connection and data in written()
    mark_synced_char = aioble.BufferedCharacteristic(
        sync_service,
        MARK_SYNCED_UUID,
        read=True,
        write=True,
        capture=True,
        max_len=100,  # Allow up to 100 bytes for JSON response
        initial=b'',
    )

    # Start background tasks to handle writes
    asyncio.create_task(
        _handle_session_data_writes(session_data_char, session_manager)
    )
    asyncio.create_task(
        _handle_mark_synced_writes(mark_synced_char, session_manager)
    )

    log("Sync Service registered")

    return sync_service


async def _handle_session_data_writes(
    characteristic: aioble.Characteristic,
    session_manager: SessionManager
) -> None:
    """Background task to handle Session Data write requests.

    When a write occurs:
    1. Read the session_id from the characteristic
    2. Look up the session
    3. Write the JSON response back to the characteristic

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
                if len(request_data) != 2:
                    error = {"error": "Invalid request length"}
                    response = json.dumps(error).encode('utf-8')
                else:
                    session_id = struct.unpack('<H', request_data)[0]
                    log(f"Session Data request for session {session_id}")

                    # Find the session
                    session = None
                    for s in session_manager.store.sessions:
                        if s.id == session_id:
                            session = s
                            break

                    if session is None:
                        error = {"error": f"Session {session_id} not found"}
                        log(error["error"])
                        response = json.dumps(error).encode('utf-8')
                    elif session.synced:
                        error = {
                            "error": f"Session {session_id} already synced"}
                        log(error["error"])
                        response = json.dumps(error).encode('utf-8')
                    else:
                        # Return session JSON
                        response_dict = session.to_dict()
                        json_str = json.dumps(response_dict)
                        log(f"Returning session {session_id}: {len(json_str)} bytes")
                        response = json_str.encode('utf-8')

                # Write response to characteristic (client will read it)
                characteristic.write(response)

            except Exception as e:
                error = {"error": f"Request error: {e}"}
                log(error["error"])
                characteristic.write(json.dumps(error).encode('utf-8'))

        except Exception as e:
            log(f"Session Data handler error: {e}")
            await asyncio.sleep(1)


async def _handle_mark_synced_writes(
    characteristic: aioble.Characteristic,
    session_manager: SessionManager
) -> None:
    """Background task to handle Mark Synced write requests.

    When a write occurs:
    1. Read the session_id from the characteristic
    2. Mark the session as synced
    3. Write the success/error response back to the characteristic

    Args:
        characteristic: Mark Synced characteristic
        session_manager: SessionManager to mark sessions
    """
    while True:
        try:
            # Wait for a write (capture=True returns tuple of (connection, data))
            write_data = await characteristic.written()

            assert isinstance(write_data, tuple)

            connection, request_data = write_data  # type: ignore

            log(f"[{connection.device.addr_hex()}] Mark Synced write")

            # Parse and handle request
            try:
                if len(request_data) != 2:
                    error = {"error": "Invalid request length"}
                    response = json.dumps(error).encode('utf-8')
                else:
                    session_id = struct.unpack('<H', request_data)[0]
                    log(f"Mark Synced request for session {session_id}")

                    # Mark the session as synced
                    success = session_manager.mark_session_synced(session_id)

                    if success:
                        response_dict = {"success": True}
                        log(f"Session {session_id} marked as synced")
                    else:
                        response_dict = {
                            "error": f"Session {session_id} not found"}

                    response = json.dumps(response_dict).encode('utf-8')

                # Write response to characteristic (client will read it)
                characteristic.write(response)

            except Exception as e:
                error = {"error": f"Request error: {e}"}
                log(error["error"])
                characteristic.write(json.dumps(error).encode('utf-8'))

        except Exception as e:
            log(f"Mark Synced handler error: {e}")
            await asyncio.sleep(1)
