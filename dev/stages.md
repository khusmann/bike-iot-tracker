# Implementation Stages

This outlines the main implementation stages for this project.

Tasks for the current stage are tracked in [tasks.md](tasks.md).

## Stage 1: Basic Setup (Completed)

**Goal:** Establish hardware functionality and development workflow

**Firmware:**

- LED toggles on crank rotation detection (reed switch on GPIO 5)
- WiFi connectivity with WebREPL for OTA updates
- Basic debouncing (50ms) for reed switch

**Status:** ✅ Complete

## Stage 2: BLE Proof-of-Concept (Completed)

**Goal:** Establish BLE communication between ESP32 and Android app using
standard Cycling Speed and Cadence (CSC) profile

**Firmware:**

- Implement BLE peripheral using aioble
- Expose Cycling Speed and Cadence Service (UUID 0x1816)
- Broadcast crank revolution count and timing via CSC Measurement characteristic
- Maintain WiFi/WebREPL for development

**Android App:**

- Scan and connect to ESP32 via BLE on app launch
- Subscribe to CSC Measurement notifications
- Display live telemetry: current cadence, total revolutions
- Simple UI with connection status

**Success Criteria:**

- App displays real-time cadence updates as bike is pedaled
- BLE connection establishes reliably
- Data matches physical pedaling rate

**Status:** ✅ Complete

## Stage 3: Background Sync to HealthConnect (Current)

**Goal:** Enable efficient background data synchronization directly to
HealthConnect while minimizing phone battery usage

**Firmware:**

- Store telemetry sessions locally (timestamp, duration, revolution count)
- Implement sync protocol: query available sessions, transfer sessions
- Persist session data across reboots

**Android App:**

- Implement WorkManager for periodic background syncs (e.g., hourly)
- Low-power BLE scanning (device name/service UUID filters)
- Connection duration under 30 seconds per sync
- Request HealthConnect permissions (READ + WRITE exercise)
- Write synced sessions directly to HealthConnect as ExerciseSession records
- Use BLE device address as bike identifier in metadata (multi-bike support)
- Query HealthConnect for last synced session per bike (no SharedPreferences
  needed)
- No local Room database needed (HealthConnect is the data store)

**Success Criteria:**

- App syncs data in background without user interaction
- No persistent foreground service required
- Battery usage remains minimal (< 2% per day)
- Cycling sessions appear in HealthConnect-compatible apps
- Data format matches standard cycling activity structure
- Multi-bike support: each bike tracks sync state independently via
  HealthConnect

**Status:** ✅ Complete

## Stage 4: Cadence Time Series Data (Future)

**Goal:** Add detailed cadence (RPM) time series data to enable richer workout
analysis in HealthConnect-compatible apps

**Firmware:**

- Record periodic cadence samples during active sessions (e.g., every 10-30
  seconds)
- Store samples with timestamp and RPM value
- Extend session data model to include cadence sample array
- Extend sync protocol to transfer cadence samples alongside session metadata
- Keep storage efficient: downsample or limit sample density as needed

**Android App:**

- Parse cadence samples from sync protocol
- Create `CyclingPedalingCadenceRecord` with samples alongside
  `ExerciseSessionRecord`
- Insert both records atomically using `insertRecords()`
- Request additional HealthConnect permission for cycling cadence data

**Success Criteria:**

- HealthConnect stores detailed cadence graphs for each workout
- Other fitness apps (Samsung Health, Google Fit, etc.) can display cadence
  trends
- Aggregate metrics (RPM_AVG, RPM_MIN, RPM_MAX) are automatically calculated
- Storage overhead on ESP32 remains manageable (< 100 bytes per sample)
- Sync performance remains fast (< 30 seconds for typical workouts)

**Design Notes:**

- Sample frequency should balance data richness vs storage/sync overhead
- Consider adaptive sampling: more frequent samples during cadence changes, less
  during steady state
- May need to implement sample compression or circular buffer if storage becomes
  constrained
