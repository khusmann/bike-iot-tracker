# Bike IoT Tracker System Specification

## Hardware Configuration

**Platform:** ESP32 with wall power (no battery constraints)

**Components:**

- LED: GPIO Pin 4
- Reed Switch: GPIO Pin 5 (internal pull-up enabled, monitors crank rotation)
- Debounce period: 50ms

## System Overview

A stationary bike tracking system consisting of ESP32 firmware and an Android
companion app.

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

- Keep Android App build / setup as simple as possible, and easy to build
  without Android studio
- Minimize phone battery usage via efficient BLE patterns:
  - `ScanSettings.SCAN_MODE_LOW_POWER` with device name/service UUID filters
  - `WorkManager` for periodic background syncs
  - BLE connections under 30 seconds
  - No persistent foreground service
- Prefer functional style with immutable data structures (but if mutable is more
  idiomatic, e.g. a Python class representing a service, then mutable is fine)
- Prioritize simplicity

### General Philosophy

- Simplicity first: suggest requirement changes when they enable simpler
  implementations
- Prefer immutable data structures over mutation
- Use functional patterns throughout

### /dev

This folder contains notes and task tracking for ongoing development.

- `stages.md` — high-level project goals and implementation stages
- `tasks.md` — current actionable tasks for the active stage
