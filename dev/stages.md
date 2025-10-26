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
