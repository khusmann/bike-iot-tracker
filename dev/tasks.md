# Tasks

Tasks for **Stage 3: Background Sync to HealthConnect**

## Status Overview

**Firmware:** ✅ Complete

- Session storage with timestamp-based IDs
- BLE sync service with timestamp-based protocol
- Multi-client safe, survives storage resets

**Android App:** ✅ Core sync complete, testing/UI remaining

- Background sync worker implemented
- HealthConnect integration complete
- MTU negotiation implemented
- Timestamp-based sync loop implemented

## Remaining Tasks

### Firmware Testing (F4)

- [ ] F4.1 Test session persistence across reboots
- [ ] F4.2 Verify session boundary detection with various idle periods
- [ ] F4.3 Test multi-client sync:
  - Run test_ble_client.py twice with different lastSyncedStartTime values
  - Verify both syncs get all requested sessions
  - Example: Client A syncs from 0, Client B syncs from middle timestamp
- [ ] F4.4 Test bike storage reset scenario:
  - Delete /sessions.json on bike
  - Do some rides (new sessions with current timestamps)
  - Verify old client with old lastSyncedStartTime still syncs new sessions
- [ ] F4.5 Ensure WiFi/WebREPL still works for development
- [ ] F4.6 Test with realistic session load (50+ sessions)
- [ ] F4.7 Verify sync protocol edge cases:
  - Request with lastSyncedStartTime = 0 (should return first session)
  - Request with lastSyncedStartTime = last session (should return null)
  - Request with lastSyncedStartTime in future (should return null)
  - Connection drops mid-sync (should resume from lastSynced on reconnect)
  - Verify remaining_sessions count accurate throughout sync

### Android App Testing (A1)

**Verification Tools:**

- Primary: `adb logcat` with TAG filters (e.g., `adb logcat BikeSync:V *:S`)
- All test logs already in BackgroundSyncWorker.kt

- [ ] A1.T1 Test WorkManager triggers background worker correctly
  - Use `adb logcat BikeSync:V *:S` to monitor logs
  - For faster testing: trigger manually via WorkManager test APIs
  - Verify "Background sync worker started" log appears
- [ ] A1.T2 Test low-power BLE scanning finds bike
  - Run `adb logcat BikeSync:V BluetoothAdapter:V *:S`
  - Verify "Device discovered: BikeTracker" appears in logs
  - Measure time between "scan started" and "device discovered"
- [ ] A1.T3 Test background connection lifecycle
  - Run `adb logcat BikeSync:V *:S` while worker runs
  - Verify connection sequence completes within 30 seconds
  - Check for error logs (connection timeouts, GATT errors)
- [ ] A1.T4 Test app is killed/closed scenarios
  - Close app via recent apps (swipe away)
  - Monitor via: `adb logcat BikeSync:V WorkManager:V *:S`
  - Watch for "Background sync worker started" log after scheduled time
- [ ] A1.T5 Test device reboot
  - Reboot phone
  - After boot + scheduled interval, run `adb logcat BikeSync:V *:S`
  - Verify "Background sync worker started" appears
- [ ] A1.T6 Verify foreground connection still works
  - Open app (triggers foreground connection)
  - Manually trigger background sync
  - Run `adb logcat BikeSync:V *:S`
  - Verify both connections work without errors
  - Verify no "GATT connection busy" or conflict errors

### UI Updates (A4)

- [ ] A4.1 Show last sync time in UI
  - Display timestamp of last successful sync completion
  - Show "Never synced" if no sync has occurred
- [ ] A4.2 Display sync status (syncing/idle/error)
  - During sync: show progress (e.g., "Syncing... 3 sessions remaining")
  - Use `remaining_sessions` count from protocol
- [ ] A4.3 Show count of stored sessions (optional)
  - Query HealthConnect for total cycling session count
- [ ] A4.4 Add manual sync trigger button
  - Trigger immediate sync (bypass WorkManager schedule)
  - Disable during active sync to prevent conflicts
- [ ] A4.5 Update UI to work without persistent connection
  - Remove connection status indicators (no persistent connection)
  - Show last sync status instead
