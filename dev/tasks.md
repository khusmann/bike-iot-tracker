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

- [ ] F2.1 Design custom BLE service for sync protocol
- [ ] F2.2 Implement "query available sessions" characteristic
- [ ] F2.3 Implement "request session data" characteristic
- [ ] F2.4 Implement "mark as synced" characteristic
- [ ] F2.5 Add session transfer with chunking if needed
- [ ] F2.6 Ensure atomic sync operations

### F3. Integration & Testing

- [ ] F3.1 Test session persistence across reboots
- [ ] F3.2 Verify session boundary detection with various idle periods
- [ ] F3.3 Test sync protocol with multiple unsyncced sessions
- [ ] F3.4 Ensure WiFi/WebREPL still works for development

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
- [ ] A3.2 Implement session query from ESP32
- [ ] A3.3 Implement session data transfer
- [ ] A3.4 Parse and store sessions in local database
- [ ] A3.5 Send "mark as synced" confirmation to ESP32
- [ ] A3.6 Handle sync errors and retries gracefully

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
