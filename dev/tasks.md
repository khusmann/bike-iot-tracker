# Tasks

Tasks for **Stage 3: Background Sync Architecture**

## Firmware Tasks

### F1. Session Storage

- [ ] F1.1 Design session data structure
  - Create `Session` dataclass with: id, start_time, end_time, revolutions, synced
  - Create `SessionStore` dataclass with: sessions list, next_id counter
  - Define JSON serialization/deserialization functions
- [ ] F1.2 Implement filesystem storage module
  - Create `storage.py` with functions to load/save sessions from/to `sessions.json`
  - Implement atomic file writes (write to temp file, then rename)
  - Handle missing file case (initialize empty store)
  - Add error handling for file I/O operations
- [ ] F1.3 Implement session management module
  - Create `session_manager.py` with `SessionManager` class
  - Track current active session (or None if idle)
  - Implement `start_session()` - creates new session with current timestamp
  - Implement `end_session()` - finalizes current session, saves to storage
  - Implement `get_unsynced_sessions()` - returns list of sessions where synced=False
- [ ] F1.4 Add session boundary detection with 10-minute idle timeout
  - Add idle timeout task that monitors `last_physical_time_ms`
  - When 10 minutes pass without crank event, call `end_session()`
  - Reset timeout on each crank revolution
  - Auto-start new session on first crank after idle period
- [ ] F1.5 Add periodic active session persistence (every 5 minutes)
  - Create background task that saves active session every 5 minutes
  - Update active session's `end_time` and `revolutions` before saving
  - Ensure this doesn't interfere with idle timeout logic
- [ ] F1.6 Integrate session tracking with existing main.py
  - Add SessionManager to AppState
  - Update `on_reed_press()` to notify session manager of new revolution
  - Start session management tasks in `main()`
  - Keep existing CSC broadcast running (no changes to BLE code)

### F2. Sync Protocol

#### Protocol Specification

**Service:**
- UUID: `0000FF00-0000-1000-8000-00805f9b34fb`
- Name: Bike Tracker Sync Service

**Characteristics:**
```
├─ Session Range (0xFF01) [READ]  → JSON: {"start": 0, "count": 10}
├─ Session Data  (0xFF02) [WRITE] → Write: uint16 session_id, Response: JSON session
└─ Mark Synced   (0xFF03) [WRITE] → uint16 session_id, Response: empty/ack
```

**Design Pattern:**
- Uses BLE's built-in write-with-response mechanism
- Simple request/response: write session_id, get JSON back synchronously
- No notifications needed (overkill for periodic sync)
- 3 characteristics total (minimal, clean)

**Data Formats:**
- Session Range: JSON, `{"start": 0, "count": 10}` (~25 bytes)
- Session Data Write: Binary uint16 little-endian (2 bytes)
- Session Data Response: JSON, `{"id": 0, "start_time": 1728849600, "end_time": 1728851400, "revolutions": 1234, "synced": false}` (~95 bytes)
- Mark Synced Write: Binary uint16 little-endian (2 bytes)

**Sync Flow:**
1. Android connects to ESP32
2. Android reads Session Range characteristic → `{"start": 0, "count": 10}`
3. For each session ID in [start, start+count):
   - Android writes session_id to Session Data characteristic
   - ESP32 returns JSON session in write response (or error if synced/missing)
   - Android stores session locally
   - Android writes session_id to Mark Synced characteristic
4. Android disconnects

**Gap Handling:**
- Client requests all IDs in range
- Server returns error/empty for already-synced sessions
- Simple, tolerates gaps without complex multi-range logic

**Error Handling:**
- Sessions marked synced only after Android confirms storage
- Connection drops leave sessions unsynced for retry next sync
- No chunking initially (sessions < 100 bytes, well within MTU)

#### Tasks

- [x] F2.1 Create sync service with UUID 0000FF00-0000-1000-8000-00805f9b34fb
- [x] F2.2 Register Session Range characteristic (0xFF01, READ)
- [x] F2.3 Register Session Data characteristic (0xFF02, WRITE with response)
- [x] F2.4 Register Mark Synced characteristic (0xFF03, WRITE with response)
- [x] F2.5 Implement Session Range read handler
  - Get unsynced sessions from SessionManager
  - Calculate start (first unsynced session ID) and count
  - Return JSON: `{"start": N, "count": M}`
- [x] F2.6 Implement Session Data write handler
  - Parse uint16 session_id from write data (little-endian)
  - Lookup session in SessionManager
  - Return session JSON in write response (or error if not found/synced)
- [x] F2.7 Implement Mark Synced write handler
  - Parse uint16 session_id from write data (little-endian)
  - Call SessionManager.mark_session_synced(session_id)
  - Return success/ack in write response
- [x] F2.8 Extend test_ble_client.py to test sync protocol
  - Add Sync Service UUIDs and characteristic UUIDs (0xFF00, 0xFF01, 0xFF02, 0xFF03)
  - Add `SyncClient` class for sync operations
  - Implement `read_session_range()` - reads Session Range characteristic, parses JSON
  - Implement `request_session(session_id)` - writes uint16 to Session Data, parses JSON response
  - Implement `mark_synced(session_id)` - writes uint16 to Mark Synced characteristic
  - Add `sync_all_sessions()` function that orchestrates full sync flow:
    - Read session range
    - For each session in range: request → parse → mark synced
    - Print summary of synced sessions
  - Add command-line argument to choose mode: `--monitor` (CSC) or `--sync` (sync protocol)
  - Test with multiple sessions, verify JSON parsing
  - Test connection drops mid-sync (manual disconnect)

### F3. Multi-Client Sync Refactor (Timestamp-Based IDs)

**Rationale:** Current `synced: bool` flag doesn't work with multiple clients. Solution: Use `start_time` as the session ID (unique due to 30s idle timeout), remove `synced` flag and `next_id` counter. Clients track their own `lastSyncedStartTime` locally.

**Benefits:**
- Multi-client safe: each client independently syncs sessions > their last timestamp
- Survives bike storage resets: new sessions always have later timestamps
- Simpler: removes 3 pieces of state (`synced`, `next_id`, redundant id field)
- Cleaner protocol: no "mark synced" round-trip needed

#### Firmware Changes

- [ ] F3.1 Update Session model (models.py)
  - Use `start_time` as unique identifier (remove separate `id` field if exists)
  - Remove `synced: bool` field
  - Keep: `start_time`, `end_time`, `revolutions`
  - Update `to_dict()` and `from_dict()` to reflect schema changes
  - Add docstring clarifying `start_time` serves as unique ID
- [ ] F3.2 Update SessionStore model (models.py)
  - Remove `next_id: int` field (no longer needed)
  - Update `to_dict()` and `from_dict()` to reflect schema changes
- [ ] F3.3 Update SessionManager (state.py)
  - Modify `start_session()`: use `current_time` as session identifier
  - Remove `mark_session_synced()` method (no longer needed)
  - Remove `get_unsynced_sessions()` method
  - Add `get_sessions_since(start_time: int) -> list[Session]` method
    - Returns sessions where `s.start_time > start_time`
    - Sorted by start_time ascending
- [ ] F3.4 Update Sync Service protocol (sync_service.py)
  - Remove Session Range characteristic (0xFF01) entirely:
    - Remove characteristic registration
    - Remove `create_session_range_response()` function
  - Modify Session Data characteristic (0xFF02) to be client-driven loop:
    - Request format: uint32 little-endian (lastSyncedStartTime - timestamp)
    - Response format:
      ```json
      {
        "session": {"start_time": 1728849600, "end_time": 1728851400, "revolutions": 456},
        "remaining_sessions": 2
      }
      ```
      Or if no more sessions: `{"session": null, "remaining_sessions": 0}`
    - Handler logic:
      - Receive lastSyncedStartTime from write
      - Find next session where `s.start_time > lastSyncedStartTime` (sorted order)
      - If found: return session + count of remaining sessions after this one
      - If not found: return null session + 0 remaining
    - Remove `synced` check (all sessions requestable)
    - **MTU Note:** Response ~102 bytes, requires MTU negotiation (client must request 185+ bytes)
  - Remove Mark Synced characteristic (0xFF03) entirely:
    - Remove characteristic registration
    - Remove `_handle_mark_synced_writes()` background task
    - Update service registration in main.py to not include it
- [ ] F3.5 Update test_ble_client.py
  - Remove Session Range characteristic code (no longer exists)
  - Update Session Data request protocol:
    - Write uint32 lastSyncedStartTime (little-endian, 4 bytes)
    - Read JSON response: `{"session": {...}, "remaining_sessions": N}`
    - Parse and handle null session (termination condition)
  - Implement sync loop:
    ```python
    last_synced = 0
    while True:
        write_uint32(last_synced)
        response = read_json()
        if response["session"] is None:
            break
        print(f"Session: {response['session']}, Remaining: {response['remaining_sessions']}")
        last_synced = response["session"]["start_time"]
    ```
  - Remove Mark Synced test code entirely
  - Test with multiple "clients" (run twice, verify both can sync same sessions)
  - Test progress indication (verify remaining_sessions decrements correctly)

#### Android App Changes

- [ ] F3.6 Update sync protocol (BleManager or new SyncManager)
  - **MTU Negotiation (CRITICAL):**
    - Call `gatt.requestMtu(512)` in `onConnectionStateChange` when connected
    - Wait for `onMtuChanged()` callback before starting sync
    - Verify MTU >= 185 bytes (response size ~102 bytes + overhead)
    - Log warning/error if MTU negotiation fails
  - Add SharedPreferences key: `LAST_SYNCED_START_TIME` (Long, default 0)
  - Implement sync loop:
    ```kotlin
    var lastSynced = prefs.getLong("LAST_SYNCED_START_TIME", 0L)

    while (true) {
        // Write lastSyncedStartTime as uint32 little-endian
        characteristic.write(lastSynced.toUInt32LE())

        // Read response
        val response = characteristic.read().parseJson()
        // {"session": {...}, "remaining_sessions": N} or {"session": null, "remaining_sessions": 0}

        if (response.session == null) {
            break  // No more sessions
        }

        // Optional: Update UI with progress
        Log.d("Sync", "Remaining: ${response.remaining_sessions}")

        // Store session in local database
        database.insert(response.session)

        // Update pointer for next request
        lastSynced = response.session.start_time
    }

    // Persist final sync state
    prefs.edit().putLong("LAST_SYNCED_START_TIME", lastSynced).apply()
    ```
  - Handle errors gracefully:
    - Connection drops: save partial progress (lastSynced), retry later
    - Parse errors: log and skip session
    - MTU too small: disconnect and warn user
- [ ] F3.7 Update local database schema (if started)
  - Change session primary key from auto-increment to `start_time` (Long)
  - Remove any `synced` tracking if present
  - Add migration if database already exists
- [ ] F3.8 Update Models.kt (if session model exists)
  - Change session ID type from Int/auto to Long (Unix timestamp)
  - Remove any `synced` field if present

### F4. Integration & Testing

- [ ] F4.1 Test session persistence across reboots
- [ ] F4.2 Verify session boundary detection with various idle periods
- [ ] F4.3 Test multi-client sync:
  - Run test_ble_client.py twice in succession with different lastSyncedStartTime values
  - Verify both syncs get all requested sessions (no "already synced" errors)
  - Verify each can independently track progress from different starting points
  - Example: Client A syncs from 0, Client B syncs from middle timestamp
- [ ] F4.4 Test bike storage reset scenario:
  - Delete /sessions.json on bike
  - Do some rides (new sessions with current timestamps)
  - Verify old client with old lastSyncedStartTime still syncs new sessions correctly
  - Confirm old sessions are gone, new sessions have later timestamps
- [ ] F4.8 Test MTU handling:
  - Verify firmware response fits in negotiated MTU
  - Test with low MTU devices (if available)
  - Confirm graceful failure if MTU < 185 bytes
- [ ] F4.5 Ensure WiFi/WebREPL still works for development
- [ ] F4.6 Test with realistic session load (50+ sessions)
- [ ] F4.7 Verify sync protocol with edge cases:
  - Request with lastSyncedStartTime = 0 (should return first session)
  - Request with lastSyncedStartTime = last session (should return null session)
  - Request with lastSyncedStartTime in future (should return null session)
  - Connection drops mid-sync (should resume from lastSynced on reconnect)
  - Verify remaining_sessions count is accurate throughout sync

## Android App Tasks

### A1. Background Sync Infrastructure

- [ ] A1.1 Remove foreground connection requirement from UI
- [ ] A1.2 Set up WorkManager dependency
- [ ] A1.3 Create periodic background sync worker (e.g., hourly)
- [ ] A1.4 Implement low-power BLE scanning (SCAN_MODE_LOW_POWER)
- [ ] A1.5 Add device name and service UUID filters for scanning
- [ ] A1.6 Ensure connection duration under 30 seconds per sync

### A2. Local Database

- [ ] A2.1 Set up Room database dependency
- [ ] A2.2 Design session entity schema
- [ ] A2.3 Create DAO for session storage
- [ ] A2.4 Implement database initialization
- [ ] A2.5 Add migration strategy

### A3. Sync Implementation

- [ ] A3.1 Create BLE sync service/manager
- [ ] A3.2 Implement session range read from ESP32
- [ ] A3.3 Implement session data transfer (request + receive)
- [ ] A3.4 Parse and store sessions in local database
- [ ] A3.5 Send "mark as synced" confirmation to ESP32
- [ ] A3.6 Handle sync errors and retries gracefully
- [ ] A3.7 Negotiate higher MTU on connection (request 512 bytes)

### A4. UI Updates

- [ ] A4.1 Show last sync time in UI
- [ ] A4.2 Display sync status (syncing/idle/error)
- [ ] A4.3 Show count of stored sessions
- [ ] A4.4 Add manual sync trigger button
- [ ] A4.5 Update UI to work without persistent connection

### A5. Battery Optimization

- [ ] A5.1 Verify SCAN_MODE_LOW_POWER is used
- [ ] A5.2 Ensure no persistent foreground service
- [ ] A5.3 Add wake locks only during active sync
- [ ] A5.4 Test actual battery usage over 24 hours

## Testing

- [ ] T1 Test background sync while app is closed
- [ ] T2 Verify sync works after device reboot
- [ ] T3 Test sync with multiple sessions queued
- [ ] T4 Test sync failure recovery
- [ ] T5 Measure battery usage (target: < 2% per day)
- [ ] T6 Test sync reliability over multiple days
- [ ] T7 Verify no data loss during sync

## Documentation

- [ ] D1 Document sync protocol specification
- [ ] D2 Document session data format
- [ ] D3 Add WorkManager configuration details
- [ ] D4 Document battery optimization techniques used
- [ ] D5 Update setup instructions
