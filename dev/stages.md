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

**Goal:** Establish BLE communication between ESP32 and Android app using standard Cycling Speed and Cadence (CSC) profile

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

**Goal:** Enable efficient background data synchronization directly to HealthConnect while minimizing phone battery usage

**Firmware:**
- Store telemetry sessions locally (timestamp, duration, revolution count)
- Implement sync protocol: query available sessions, transfer sessions
- Persist session data across reboots

**Android App:**
- Remove foreground connection requirement
- Implement WorkManager for periodic background syncs (e.g., hourly)
- Low-power BLE scanning (device name/service UUID filters)
- Connection duration under 30 seconds per sync
- Request HealthConnect permissions (READ + WRITE exercise)
- Write synced sessions directly to HealthConnect as ExerciseSession records
- Use BLE device address as bike identifier in metadata (multi-bike support)
- Query HealthConnect for last synced session per bike (no SharedPreferences needed)
- No local Room database needed (HealthConnect is the data store)

**Success Criteria:**
- App syncs data in background without user interaction
- No persistent foreground service required
- Battery usage remains minimal (< 2% per day)
- Cycling sessions appear in HealthConnect-compatible apps
- Data format matches standard cycling activity structure
- Multi-bike support: each bike tracks sync state independently via HealthConnect

## Stage 4: Enhanced Telemetry & UI

**Goal:** Improve data richness and user experience

**Firmware:**
- Track session metrics: start/end time, cadence statistics
- Detect session boundaries (idle timeout)

**Android App:**
- Enhanced UI: query and display session history from HealthConnect
- Statistics and charts based on HealthConnect data
- Settings: sync frequency, session detection timeout
- Notifications for sync status (optional)

**Success Criteria:**
- User can view detailed session history from HealthConnect
- App provides useful insights into cycling habits

## Future Considerations

- **Stage 5:** Additional sensors (heart rate, speed/distance)
- **Stage 6:** Export/backup functionality
- **Stage 7:** Bike management UI (list bikes, rename, remove)

**Note:** Multi-bike support is built-in via BLE device address in clientRecordId (Stage 3)
