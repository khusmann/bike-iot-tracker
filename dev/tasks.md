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

### Sync Persistence & Debugging (Current Priority)

**Problem:** Syncs may not be persisting across reboots. Need diagnostic UI and
testing plan.

**Root Cause Analysis:**

- Last sync timestamp is queried from HealthConnect, not stored locally
- WorkManager should persist across reboots (ExistingPeriodicWorkPolicy.KEEP)
- Need UI to verify sync state and manually control sync schedule

**Plan:**

#### Phase 1: Add Local Sync State Persistence

1. Create SharedPreferences storage for sync metadata:

   - Last successful sync timestamp
   - Last sync attempt timestamp
   - Last synced session ID
   - Sync success/failure count
   - Last error message (if any)

2. Update BackgroundSyncWorker to:
   - Write sync results to SharedPreferences after each sync
   - Compare SharedPreferences timestamp with HealthConnect timestamp (detect HC
     data loss)
   - Log sync attempts for debugging

#### Phase 2: Add Sync Settings UI (Second Tab)

1. Restructure MainActivity to support two tabs:

   - **Tab 1: "Device"** - Current connection/RPM display (existing UI)
   - **Tab 2: "Sync"** - New sync settings and diagnostics

2. Create SyncSettingsScreen composable with:

   - **Last Sync Info Section:**

     - Last sync time (human-readable, e.g., "2 hours ago")
     - Last synced session timestamp (Unix time + formatted date)
     - Sync status indicator (success/failed with error message)

   - **Sync Schedule Control:**

     - Display current WorkManager state (scheduled/not scheduled)
     - Toggle to enable/disable periodic sync
     - Dropdown/slider to adjust sync interval (15min/30min/1hr/2hr)
     - "Sync Now" button (manual trigger)

   - **Diagnostic Info:**
     - Number of syncs since app install (success/failure counts)
     - HealthConnect vs SharedPreferences timestamp comparison
     - WorkManager job status (next scheduled run time)
     - Bike address of last synced device

3. Add state management:
   - Extend BikeState or create new SyncState data class
   - Add ViewModel or state holders for sync settings tab
   - Query WorkManager status to display "sync timer enabled" state

#### Phase 3: Testing Plan for Reboot Persistence

1. **Test Setup:**

   - Clear app data
   - Fresh install of app

2. **Test Scenarios:**

   - **Scenario A: Normal Operation**

     1. Perform manual sync
     2. Verify sync timestamp appears in Sync tab
     3. Reboot device
     4. Open app and check Sync tab (timestamp should persist)
     5. Wait for next scheduled sync (or trigger manually)
     6. Verify new sync completes successfully

   - **Scenario B: WorkManager Persistence**

     1. Enable periodic sync (verify "timer enabled" indicator)
     2. Note next scheduled sync time
     3. Reboot device (without opening app)
     4. Wait for scheduled sync time to pass
     5. Open app and check if sync occurred (last sync time updated)

   - **Scenario C: HealthConnect Data Loss**

     1. Perform successful sync
     2. Clear HealthConnect data (Settings → Apps → Health Connect → Clear Data)
     3. Open app and check Sync tab
     4. Should show warning: SharedPreferences timestamp exists but HC timestamp
        is 0
     5. Next sync should re-download all sessions

   - **Scenario D: App Data Cleared**
     1. Perform successful sync
     2. Clear app data (Settings → Apps → Bike Tracker → Clear Data)
     3. Reboot device
     4. Open app - sync schedule should NOT be active (user must re-enable)

3. **Logging & Debugging:**
   - Add LogCat tags for all sync operations
   - Log WorkManager job scheduling/cancellation
   - Log SharedPreferences writes
   - Add "Export Logs" button in Sync tab (copy diagnostic info to clipboard)

#### Phase 4: Implementation Order

1. ✅ Create SyncPreferences helper class (SharedPreferences wrapper)
2. ✅ Update BackgroundSyncWorker to persist sync state
3. ✅ Add tab navigation to MainActivity
4. ✅ Implement SyncSettingsScreen composable
5. ✅ Add sync state to ViewModel/state holders
6. ✅ Implement sync schedule controls (enable/disable/interval)
7. ✅ Add diagnostic displays (timestamps, status, counts)
8. ✅ Run test scenarios A-D and document results
9. ✅ Fix any identified issues
10. ✅ Update sync interval to 1 hour (production setting)
