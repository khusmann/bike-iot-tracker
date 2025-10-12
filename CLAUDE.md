# Bike IoT Tracker System Specification

## Environment / System

Activate the Python virtual environment and install dependencies:

```bash
source activate.sh
```

Hardware Configuration:

- LED: GPIO Pin 4
- Reed Switch: GPIO Pin 5 (with internal pull-up) (connected to crank, not
  wheel)
- Debounce period: 50ms

## 1. Overview

Create a firmware and an Android app for my stationary bike. The bike has a
ESP32 installed in it with a single red LED and a reed switch to track pedaling.
It's plugged into the wall, so no need to worry about battery performance.

### Goal

- Firmware stores telemetry data
- Phone app syncs telemetry data via BLE in the background
- Phone app updates telemetry into HealthConnect
- Phone app has a simple display with current status

### Design principles

In the firmware:

- We use micropython and type hints as much as possible (using the
  3rdparty/typing.py shim module)
- Use async libraries (like aioble)

In the mobile app:

- Keep code as simple as possible
- App should minimize battery usage of the phone by running in the background
  using BLE scan wake-up patterns:
  - Use Android's `ScanSettings.SCAN_MODE_LOW_POWER` with scan filters
  - Match on device name or service UUID in filter
  - Use `JobScheduler` or `WorkManager` for periodic sync attempts
  - Keep BLE connection short (< 30 seconds per sync)
  - No persistent foreground service needed

Everywhere:

- Keep a functional style; avoid mutation in favor of immutable data structure
  patterns
- Always take a simple approach first. Requirements can be changed to simplify
  implementation -- when a chance in requirement could simplify the
  implementation, please prompt me to suggest the change.

### Implementation Stages

#### 1. Basic setup (current state of project)

- Firmware only, no mobile app implementation
- Basic LED toggle on wheel rotation detection
- WiFi connectivity with WebREPL for OTA updates

#### 2. BLE proof-of-concept

- Add BLE support to the firmware
  - Send CSC crank revolution notifications
- Create a basic mobile app to talk to the firmware
  - When opening the app, it should connect to the firmware via BLE and display
    a live output of the data it's getting.

#### 3. TBA (we'll fill this in later)
