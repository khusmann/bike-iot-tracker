# Bike IoT Tracker System Specification

## Hardware Configuration

**Platform:** ESP32 with wall power (no battery constraints)

**Components:**
- LED: GPIO Pin 4
- Reed Switch: GPIO Pin 5 (internal pull-up enabled, monitors crank rotation)
- Debounce period: 50ms

## Development Environment

Activate Python virtual environment:

```bash
source activate.sh
```

## System Overview

A stationary bike tracking system consisting of ESP32 firmware and an Android companion app.

**Architecture:**
1. ESP32 firmware collects and stores pedaling telemetry
2. Android app syncs data via BLE in the background
3. Android app writes telemetry to HealthConnect
4. Android app displays current bike status

## Design Principles

### Firmware (MicroPython)
- Use type hints with `3rdparty/typing.py` shim module
- Use async libraries (aioble for BLE)
- Functional style with immutable data structures

### Android App
- Minimize phone battery usage via efficient BLE patterns:
  - `ScanSettings.SCAN_MODE_LOW_POWER` with device name/service UUID filters
  - `WorkManager` for periodic background syncs
  - BLE connections under 30 seconds
  - No persistent foreground service
- Functional style with immutable data structures
- Prioritize simplicity

### General Philosophy
- Simplicity first: suggest requirement changes when they enable simpler implementations
- Prefer immutable data structures over mutation
- Use functional patterns throughout

## Implementation Stages

### Stage 1: Basic Setup (Current)
- Firmware-only implementation
- LED toggles on crank rotation detection
- WiFi with WebREPL for OTA updates

### Stage 2: BLE Proof-of-Concept
**Firmware:**
- Implement BLE peripheral with Cycling Speed and Cadence (CSC) service
- Broadcast crank revolution count and timing via CSC notifications

**Android App:**
- Connect to ESP32 via BLE on app launch
- Display live CSC telemetry stream

### Stage 3: TBD
