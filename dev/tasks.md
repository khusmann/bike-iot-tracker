# Tasks

Tasks for **Stage 3: Background Sync Architecture**

## Firmware Tasks

### F1. Session Storage

- [ ] F1.1 Design session data structure (timestamp, duration, revolution count)
- [ ] F1.2 Implement persistent storage using filesystem or NVS
- [ ] F1.3 Create session boundary detection (idle timeout logic)
- [ ] F1.4 Store sessions locally with unique IDs
- [ ] F1.5 Handle storage cleanup for synced sessions

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
