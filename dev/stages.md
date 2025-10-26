# Project Status

Tasks for the current stage are tracked in [tasks.md](tasks.md).

## Current Status

**Completed:**
- Hardware setup: LED on GPIO 4, reed switch on GPIO 5 with 50ms debounce
- BLE communication using Cycling Speed and Cadence (CSC) profile
- Background sync to HealthConnect via WorkManager
- Multi-bike support via BLE device address
- Low-power BLE scanning and efficient sync patterns

**System works:**
- ESP32 stores pedaling sessions (timestamp, duration, revolutions)
- Android app syncs sessions hourly in background
- Data written to HealthConnect as ExerciseSession records
- Live cadence display when app is open

## Next Steps

**Goal:** Add cadence time series data to HealthConnect for richer workout analysis

**Firmware:**
- Record periodic cadence samples during sessions (every 10-30 seconds)
- Store samples with timestamp + RPM value
- Extend sync protocol to transfer samples
- Keep storage efficient (< 100 bytes per sample)

**Android App:**
- Parse cadence samples from sync protocol
- Create `CyclingPedalingCadenceRecord` alongside `ExerciseSessionRecord`
- Request cadence data permission for HealthConnect
- Insert records atomically

**Success criteria:**
- Cadence graphs appear in HealthConnect-compatible apps
- Sync completes in < 30 seconds for typical workouts
- Storage overhead remains manageable on ESP32

## Future Enhancements

### Alternative Sync Architecture: Companion Device Manager

**Current approach:** WorkManager with periodic sync (15-60 minute intervals)
- Subject to battery optimization restrictions
- Requires user to disable battery optimization for reliable sync
- Fixed schedule regardless of device proximity

**Alternative approach:** Android Companion Device Manager (CDM) API
- Designed specifically for BLE companion devices (like fitness trackers)
- Provides exemptions from battery optimization automatically
- Triggers sync when device appears in BLE range (proximity-based)
- More reliable and better user experience

**Implementation:**

1. **Pairing Flow:**
   - Use `CompanionDeviceManager.associate()` with BLE device filter
   - Shows system pairing dialog (like Fitbit/smartwatch apps)
   - User pairs bike once, system grants background permissions

2. **Device Presence Detection:**
   - Create `CompanionDeviceService` that extends Android's service
   - Override `onDeviceAppeared()` - called when bike comes in BLE range
   - Override `onDeviceDisappeared()` - called when bike moves out of range
   - System manages lifecycle automatically

3. **Background Permissions:**
   - Declare in AndroidManifest:
     - `REQUEST_COMPANION_RUN_IN_BACKGROUND` - wake app when device nearby
     - `REQUEST_COMPANION_USE_DATA_IN_BACKGROUND` - allow data access
     - `REQUEST_COMPANION_START_FOREGROUND_SERVICES_FROM_BACKGROUND`
   - System grants exemptions automatically after pairing

4. **Sync Trigger:**
   - When `onDeviceAppeared()` fires, trigger immediate sync
   - No need for periodic WorkManager job
   - Syncs naturally when you finish riding (bike still nearby)
   - More efficient than polling every 15 minutes

**Benefits:**
- ✅ Reliable background operation (like Fitbit)
- ✅ Battery optimization exemption without user intervention
- ✅ Syncs when bike is nearby, not on fixed schedule
- ✅ Better UX - "just works" like commercial fitness apps
- ✅ No location permission needed for BLE scanning

**Tradeoffs:**
- More complex initial implementation
- Requires Android 8.0+ (API 26+)
- User must complete pairing flow
- CDM-specific documentation/debugging

**When to implement:**
- For production app with daily use
- When current WorkManager approach proves unreliable
- When battery optimization becomes a support burden
- As a v2.0 feature for better user experience

**References:**
- [Companion Device Pairing Guide](https://developer.android.com/guide/topics/connectivity/companion-device-pairing)
- [Background BLE Communication](https://developer.android.com/develop/connectivity/bluetooth/ble/background)
